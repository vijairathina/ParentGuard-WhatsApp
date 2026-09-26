"""
ParentGuard WhatsApp - External REST API (v1)
Enables third-party applications, CRMs, scripts, and automations to:
1. List and inspect configured WhatsApp accounts.
2. Send WhatsApp messages to contacts or groups.
3. Retrieve chat lists and received message histories.
4. Poll latest messages across all chats (since timestamp).
5. Register webhooks for real-time incoming/outgoing/deleted message notifications.
"""

import os
import json
import time
import threading
import requests
from flask import Blueprint, request, jsonify

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

WEBHOOKS_FILE = "accounts/webhooks.json"
_webhook_lock = threading.Lock()

def load_webhooks():
    if os.path.exists(WEBHOOKS_FILE):
        try:
            with open(WEBHOOKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_webhooks(webhooks):
    with _webhook_lock:
        try:
            os.makedirs("accounts", exist_ok=True)
            with open(WEBHOOKS_FILE, "w", encoding="utf-8") as f:
                json.dump(webhooks, f, indent=2)
            return True
        except Exception as e:
            print(f"[Webhook] Error saving webhooks: {e}")
            return False

def dispatch_webhook_event(event_type: str, account_id: str, data: dict):
    """Sends webhook POST notifications to all subscribed third-party URLs."""
    webhooks = load_webhooks()
    if not webhooks:
        return

    payload = {
        "event": event_type,
        "account_id": account_id,
        "timestamp": int(time.time()),
        "data": data
    }

    def _send(wh):
        url = wh.get("url")
        if not url:
            return
        headers = {"Content-Type": "application/json"}
        if wh.get("secret"):
            headers["X-Webhook-Secret"] = wh.get("secret")
        try:
            requests.post(url, json=payload, headers=headers, timeout=5)
        except Exception as e:
            print(f"[Webhook] Failed sending to {url}: {e}")

    for wh in webhooks:
        events = wh.get("events", ["all"])
        if "all" in events or event_type in events:
            threading.Thread(target=_send, args=(wh,), daemon=True).start()

# --- API Documentation ---
@api_v1.route('/', methods=['GET'])
@api_v1.route('/docs', methods=['GET'])
def api_docs():
    """Returns endpoint documentation and usage instructions for external developers."""
    return jsonify({
        "name": "ParentGuard WhatsApp External API",
        "version": "1.0",
        "description": "REST API to manage accounts, send/receive WhatsApp messages, and receive webhook notifications.",
        "endpoints": {
            "GET /api/v1/accounts": "List all configured accounts and statuses",
            "GET /api/v1/accounts/<account_id>": "Get status and details of an account",
            "POST /api/v1/accounts/<account_id>/connect": "Connect / start WhatsApp session",
            "POST /api/v1/accounts/<account_id>/disconnect": "Disconnect / logout WhatsApp session",
            "POST /api/v1/accounts/<account_id>/send": "Send a text message: {'to': 'phone_or_jid', 'message': 'text'}",
            "GET /api/v1/accounts/<account_id>/chats": "List all chats with last message & timestamps",
            "GET /api/v1/accounts/<account_id>/messages": "Get message history: ?contact=919876543210&limit=50",
            "GET /api/v1/accounts/<account_id>/messages/latest": "Poll latest messages across all chats: ?since=<unix_timestamp>",
            "POST /api/v1/webhooks/subscribe": "Register webhook: {'url': 'https://...', 'secret': '...', 'events': ['message', 'message_revoked', 'security_alert']}",
            "GET /api/v1/webhooks": "List registered webhooks",
            "POST /api/v1/webhooks/unsubscribe": "Remove a webhook by URL: {'url': 'https://...'}"
        }
    })

def register_api_routes(app, manager):
    """Registers API v1 blueprint and injects WhatsAppManager instance."""

    # 1. Accounts Endpoints
    @api_v1.route('/accounts', methods=['GET'])
    def list_accounts():
        accounts = []
        for acc_id, info in manager.profile_info.items():
            accounts.append({
                "id": acc_id,
                "name": info.get("name", ""),
                "jid": info.get("jid", ""),
                "phone": info.get("phone", ""),
                "status": manager.statuses.get(acc_id, "Disconnected")
            })
        return jsonify({"success": True, "accounts": accounts, "count": len(accounts)})

    @api_v1.route('/accounts/<account_id>', methods=['GET'])
    def get_account_detail(account_id):
        if account_id not in manager.profile_info:
            return jsonify({"success": False, "error": f"Account '{account_id}' not found"}), 404
        info = manager.profile_info[account_id]
        status = manager.statuses.get(account_id, "Disconnected")
        settings = manager.get_account_settings(account_id)
        return jsonify({
            "success": True,
            "account": {
                "id": account_id,
                "name": info.get("name", ""),
                "jid": info.get("jid", ""),
                "phone": info.get("phone", ""),
                "status": status,
                "settings": settings
            }
        })

    @api_v1.route('/accounts/<account_id>/connect', methods=['POST'])
    def connect_account(account_id):
        ok = manager.reconnect_account(account_id)
        return jsonify({"success": ok, "status": manager.statuses.get(account_id, "Connecting")})

    @api_v1.route('/accounts/<account_id>/disconnect', methods=['POST'])
    def disconnect_account(account_id):
        ok = manager.disconnect_account(account_id)
        return jsonify({"success": ok, "status": manager.statuses.get(account_id, "Disconnected")})

    # 2. Send Message Endpoint
    @api_v1.route('/accounts/<account_id>/send', methods=['POST'])
    def send_message_api(account_id):
        data = request.json or {}
        # Support both 'to' and 'recipient' parameter names
        to_target = data.get("to") or data.get("recipient") or data.get("target")
        body = data.get("message") or data.get("body") or data.get("text")

        if not to_target or not body:
            return jsonify({
                "success": False, 
                "error": "Missing parameters. Required: 'to' (phone or JID) and 'message' (text string)."
            }), 400

        to_target = str(to_target).strip()
        body = str(body).strip()

        success = manager.send_whatsapp_message(account_id, to_target, body)
        if success:
            # Trigger external webhooks
            dispatch_webhook_event("message_sent", account_id, {
                "target": to_target,
                "message": body,
                "timestamp": int(time.time())
            })
            return jsonify({
                "success": True,
                "account_id": account_id,
                "to": to_target,
                "message": body,
                "timestamp": int(time.time())
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to send message via account '{account_id}'. Verify that the account is connected."
            }), 500

    # 3. Retrieve Chats & Conversations
    @api_v1.route('/accounts/<account_id>/chats', methods=['GET'])
    def get_chats_api(account_id):
        chats = manager.get_contacts(account_id)
        return jsonify({
            "success": True,
            "account_id": account_id,
            "count": len(chats),
            "chats": chats
        })

    # 4. Retrieve Message History for a Contact
    @api_v1.route('/accounts/<account_id>/messages', methods=['GET'])
    def get_messages_api(account_id):
        contact = request.args.get("contact") or request.args.get("chat_jid") or request.args.get("to")
        if not contact:
            return jsonify({
                "success": False, 
                "error": "Missing query parameter 'contact' (e.g. ?contact=919876543210 or ?contact=123@g.us)"
            }), 400

        limit = int(request.args.get("limit", 100))
        messages = manager.get_messages(account_id, contact)
        if limit and len(messages) > limit:
            messages = messages[-limit:]

        return jsonify({
            "success": True,
            "account_id": account_id,
            "contact": contact,
            "count": len(messages),
            "messages": messages
        })

    # 5. Poll Latest Messages across all chats since timestamp
    @api_v1.route('/accounts/<account_id>/messages/latest', methods=['GET'])
    def get_latest_messages_api(account_id):
        since_ts = int(request.args.get("since", 0))
        limit = int(request.args.get("limit", 100))

        HISTORY_FILE = f"accounts/history_{account_id}.json"
        all_msgs = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    for chat_jid, msgs in history.items():
                        for m in msgs:
                            ts = m.get("timestamp", 0)
                            if ts >= since_ts:
                                m_copy = dict(m)
                                m_copy["chat_jid"] = chat_jid
                                all_msgs.append(m_copy)
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        all_msgs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        if limit:
            all_msgs = all_msgs[:limit]

        return jsonify({
            "success": True,
            "account_id": account_id,
            "since": since_ts,
            "count": len(all_msgs),
            "messages": all_msgs
        })

    # 6. Webhooks Management
    @api_v1.route('/webhooks/subscribe', methods=['POST'])
    def subscribe_webhook():
        data = request.json or {}
        url = data.get("url")
        if not url:
            return jsonify({"success": False, "error": "Missing 'url' parameter"}), 400

        secret = data.get("secret", "")
        events = data.get("events", ["all"])

        webhooks = load_webhooks()
        # Update if URL already exists, or append new
        found = False
        for wh in webhooks:
            if wh.get("url") == url:
                wh["secret"] = secret
                wh["events"] = events
                found = True
                break
        if not found:
            webhooks.append({"url": url, "secret": secret, "events": events})

        save_webhooks(webhooks)
        return jsonify({"success": True, "message": f"Webhook registered for {url}", "webhooks": webhooks})

    @api_v1.route('/webhooks', methods=['GET'])
    def list_webhooks():
        return jsonify({"success": True, "webhooks": load_webhooks()})

    @api_v1.route('/webhooks/unsubscribe', methods=['POST'])
    def unsubscribe_webhook():
        data = request.json or {}
        url = data.get("url")
        if not url:
            return jsonify({"success": False, "error": "Missing 'url' parameter"}), 400

        webhooks = [wh for wh in load_webhooks() if wh.get("url") != url]
        save_webhooks(webhooks)
        return jsonify({"success": True, "message": f"Webhook unregistered: {url}", "webhooks": webhooks})

    # Register blueprint with Flask
    app.register_blueprint(api_v1)
