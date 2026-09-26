import os
import json
import uuid
import queue
from flask import Flask, render_template, request, jsonify, Response
from whatsapp_manager import WhatsAppManager

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "whatsapp_replica_secret_key"

# Initialize WhatsApp Manager
manager = WhatsAppManager()

# Register External REST API v1 (for other apps to send/receive messages and subscribe to webhooks)
from api_service import register_api_routes
register_api_routes(app, manager)

@app.route('/')
def index():
    """
    Renders the WhatsApp Web clone interface.
    """
    return render_template("index.html")

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """
    Returns a list of all configured accounts and their statuses.
    """
    accounts = []
    for acc_id, info in manager.profile_info.items():
        accounts.append({
            "id": acc_id,
            "name": info.get("name", ""),
            "jid": info.get("jid", ""),
            "phone": info.get("phone", ""),
            "status": manager.statuses.get(acc_id, "Disconnected"),
            "qr": manager.qr_codes.get(acc_id, "")
        })
    return jsonify(accounts)

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    """
    Generates a new account ID, registers it, and initiates connection.
    """
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    
    # Register empty metadata in manager
    manager.profile_info[account_id] = {
        "id": account_id,
        "name": f"Account {account_id[4:]}",
        "jid": "",
        "phone": ""
    }
    manager.statuses[account_id] = "Connecting"
    manager.save_accounts()
    
    # Start background client connection thread
    manager.start_account(account_id)
    
    return jsonify({
        "success": True,
        "account_id": account_id
    })

@app.route('/api/accounts/delete', methods=['POST'])
def delete_account():
    """
    Removes an account, stops its worker, and deletes its credentials.
    """
    data = request.json or {}
    account_id = data.get("account_id")
    if not account_id:
        return jsonify({"success": False, "error": "Missing account_id"}), 400
        
    ok = manager.delete_account(account_id)
    return jsonify({"success": ok})

@app.route('/api/accounts/<account_id>/login', methods=['POST'])
def login_account(account_id):
    """
    Reconnects / logs in the specified account session.
    """
    ok = manager.reconnect_account(account_id)
    return jsonify({"success": ok, "status": manager.statuses.get(account_id, "Connecting")})

@app.route('/api/accounts/<account_id>/logout', methods=['POST'])
def logout_account(account_id):
    """
    Disconnects / logs out the specified account session without deleting credentials.
    """
    ok = manager.disconnect_account(account_id)
    return jsonify({"success": ok, "status": manager.statuses.get(account_id, "Disconnected")})

@app.route('/api/accounts/<account_id>/settings', methods=['GET', 'POST'])
def account_settings(account_id):
    """
    GET: Returns per-account settings (theme, keyword rules, Gemini AI configuration).
    POST: Saves per-account settings.
    """
    if request.method == 'POST':
        data = request.json or {}
        ok = manager.save_account_settings(account_id, data)
        return jsonify({"success": ok, "settings": data})
    else:
        settings = manager.get_account_settings(account_id)
        return jsonify(settings)

@app.route('/api/accounts/<account_id>/logs', methods=['GET'])
def get_account_logs(account_id):
    """
    Returns safety violation audit logs (keyword matches and Gemini AI flags) for the account.
    """
    limit = int(request.args.get('limit', 100))
    logs = manager.get_audit_logs(account_id, limit=limit)
    return jsonify(logs)

@app.route('/api/accounts/<account_id>/logs/clear', methods=['POST'])
def clear_account_logs(account_id):
    """
    Clears safety violation logs for this account.
    """
    ok = manager.clear_audit_logs(account_id)
    return jsonify({"success": ok})

@app.route('/api/accounts/<account_id>/contacts', methods=['GET'])
def get_contacts(account_id):
    """
    Returns the contacts list for the specified account JID.
    """
    contacts = manager.get_contacts(account_id)
    return jsonify(contacts)

@app.route('/api/accounts/<account_id>/messages', methods=['GET'])
def get_messages(account_id):
    """
    Returns message history between the selected account and a contact JID.
    """
    contact_jid = request.args.get("contact")
    if not contact_jid:
        return jsonify({"success": False, "error": "Missing contact JID"}), 400
        
    messages = manager.get_messages(account_id, contact_jid)
    return jsonify(messages)

@app.route('/api/accounts/<account_id>/send', methods=['POST'])
def send_message(account_id):
    """
    Sends a message via the specified account to a target phone number or JID.
    """
    data = request.json or {}
    target = data.get("target")
    message = data.get("message")
    
    if not target or not message:
        return jsonify({"success": False, "error": "Missing target or message parameters"}), 400
        
    success = manager.send_whatsapp_message(account_id, target, message)
    return jsonify({"success": success})

@app.route('/api/events')
def events():
    """
    SSE stream endpoint. Delivers real-time events to the frontend including
    connection updates, new QR codes, and incoming/outgoing message notifications.
    """
    def event_stream():
        q = manager.register_listener()
        try:
            # Yield initial sync event
            yield f"data: {json.dumps({'event': 'welcome'})}\n\n"
            while True:
                try:
                    # Timeout yields a ping to prevent client connection timeout
                    item = q.get(timeout=15)
                    yield f"data: {json.dumps(item)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'event': 'ping'})}\n\n"
        except GeneratorExit:
            # Clean up when connection closes
            pass
        finally:
            manager.unregister_listener(q)
            
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/accounts/<account_id>/import_history', methods=['POST'])
def import_history(account_id):
    """
    Imports history from the old eCourt whatsapp_history.json flat-list format.
    POST body: {"history_path": "path/to/whatsapp_history.json"}
    """
    data = request.json or {}
    history_path = data.get("history_path", "")
    if not history_path:
        return jsonify({"success": False, "error": "Missing history_path"}), 400

    count = manager.import_ecourt_history(account_id, history_path)
    # After import, also refresh contacts from history
    manager.merge_contacts_groups(account_id)
    manager.broadcast("contacts_updated", account_id, {})
    return jsonify({"success": True, "imported": count})

if __name__ == '__main__':
    # Start configured accounts in background
    print("[ParentGuard] Starting connected WhatsApp sessions...")
    manager.start_all()

    # Optional auto-import eCourt history when running locally.
    # Set ECOURT_HISTORY=/path/to/whatsapp_history.json on Linux, or place
    # whatsapp_history.json in the repo root.
    ECOURT_HISTORY = os.environ.get("ECOURT_HISTORY")
    if not ECOURT_HISTORY:
        candidate = os.path.join(os.path.dirname(__file__), "whatsapp_history.json")
        if os.path.exists(candidate):
            ECOURT_HISTORY = candidate

    if ECOURT_HISTORY and os.path.exists(ECOURT_HISTORY):
        import threading as _threading
        def _auto_import():
            import time as _time
            _time.sleep(5)  # wait for accounts to connect first
            for acc_id in list(manager.profile_info.keys()):
                HISTORY_FILE = f"accounts/history_{acc_id}.json"
                # Only import if not already done (check for ecourt_ prefixed ids)
                already_imported = False
                if os.path.exists(HISTORY_FILE):
                    try:
                        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                            h = json.load(f)
                        # Check if any ecourt_ ids exist
                        for msgs in h.values():
                            if any(m.get('id','').startswith('ecourt_') for m in msgs):
                                already_imported = True
                                break
                    except:
                        pass
                if not already_imported:
                    print(f"[App] Auto-importing eCourt history for {acc_id}...")
                    manager.import_ecourt_history(acc_id, ECOURT_HISTORY)
                    manager.merge_contacts_groups(acc_id)
                    manager.broadcast("contacts_updated", acc_id, {})
        _threading.Thread(target=_auto_import, daemon=True).start()

    # Start web app on port
    port = int(os.environ.get("FLASK_PORT", os.environ.get("PORT", 5003)))
    print(f"[ParentGuard] Launching ParentGuard WhatsApp Web App on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
