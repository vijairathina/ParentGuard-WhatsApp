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

# ========================================================
# ADVANCED SCHEDULED MESSAGES API (Birthdays, Greetings, Festivals)
# ========================================================
import scheduler_service

@app.route('/api/schedules', methods=['GET', 'POST'])
def handle_schedules():
    """
    GET: Returns all scheduled message rules.
    POST: Creates a new scheduled message rule.
    """
    if request.method == 'POST':
        data = request.json or {}
        sched_id = f"sched_{uuid.uuid4().hex[:8]}"
        new_sched = {
            "id": sched_id,
            "title": data.get("title", "Untitled Schedule"),
            "category": data.get("category", "custom"),
            "schedule_type": data.get("schedule_type", "once"),
            "time_of_day": data.get("time_of_day", "09:00"),
            "scheduled_datetime": data.get("scheduled_datetime"),
            "annual_month": int(data.get("annual_month", 1)) if data.get("annual_month") else 1,
            "annual_day": int(data.get("annual_day", 1)) if data.get("annual_day") else 1,
            "days_of_week": data.get("days_of_week", [0]),
            "account_id": data.get("account_id", "any"),
            "recipients": data.get("recipients", []),
            "message_template": data.get("message_template", ""),
            "enabled": bool(data.get("enabled", True)),
            "created_at": int(time.time()),
            "last_status": "Scheduled"
        }
        new_sched["next_run"] = scheduler_service.compute_next_run(new_sched)
        schedules = scheduler_service.load_schedules()
        schedules.append(new_sched)
        scheduler_service.save_schedules(schedules)
        return jsonify({"success": True, "schedule": new_sched})
    else:
        schedules = scheduler_service.load_schedules()
        return jsonify(schedules)

@app.route('/api/schedules/<sched_id>', methods=['PUT', 'DELETE'])
def manage_schedule_item(sched_id):
    """
    PUT: Updates an existing schedule (enable/disable, change time or content).
    DELETE: Removes a schedule.
    """
    schedules = scheduler_service.load_schedules()
    sched = next((s for s in schedules if s.get("id") == sched_id), None)
    if not sched:
        return jsonify({"success": False, "error": "Schedule not found"}), 404

    if request.method == 'DELETE':
        schedules = [s for s in schedules if s.get("id") != sched_id]
        scheduler_service.save_schedules(schedules)
        return jsonify({"success": True})

    elif request.method == 'PUT':
        data = request.json or {}
        for key in ["title", "category", "schedule_type", "time_of_day", "scheduled_datetime", 
                    "annual_month", "annual_day", "days_of_week", "account_id", "recipients", 
                    "message_template", "enabled"]:
            if key in data:
                sched[key] = data[key]
        sched["next_run"] = scheduler_service.compute_next_run(sched)
        scheduler_service.save_schedules(schedules)
        return jsonify({"success": True, "schedule": sched})

@app.route('/api/schedules/<sched_id>/test', methods=['POST'])
def test_send_schedule(sched_id):
    """
    Immediately sends a test execution of the scheduled message to its recipients.
    """
    schedules = scheduler_service.load_schedules()
    sched = next((s for s in schedules if s.get("id") == sched_id), None)
    if not sched:
        return jsonify({"success": False, "error": "Schedule not found"}), 404

    account_id = sched.get("account_id")
    if not account_id or account_id == "any":
        for acc_id, status in manager.statuses.items():
            if status == "Connected":
                account_id = acc_id
                break

    if not account_id or manager.statuses.get(account_id) != "Connected":
        return jsonify({"success": False, "error": "No connected WhatsApp account available to send test."}), 400

    recipients = sched.get("recipients", [])
    if not recipients:
        return jsonify({"success": False, "error": "No recipients configured for this schedule."}), 400

    template_text = sched.get("message_template", "")
    sent_count = 0
    for rec in recipients:
        target_jid = rec.get("jid") or rec.get("phone") or ""
        target_name = rec.get("name") or ""
        if target_jid:
            body = scheduler_service.format_template_message(template_text, target_name)
            if manager.send_whatsapp_message(account_id, target_jid, body):
                sent_count += 1

    return jsonify({"success": True, "sent_count": sent_count})

@app.route('/api/schedules/templates', methods=['GET'])
def get_sample_templates():
    """
    Returns curated sample message templates grouped by category:
    birthdays, anniversaries, morning, afternoon, night, festivals, wellness.
    """
    return jsonify(scheduler_service.SAMPLE_TEMPLATES)

if __name__ == '__main__':
    import time
    # Start configured accounts in background
    print("[ParentGuard] Starting connected WhatsApp sessions...")
    manager.start_all()

    # Start web app on port
    port = int(os.environ.get("FLASK_PORT", os.environ.get("PORT", 5003)))
    print(f"[ParentGuard] Launching ParentGuard WhatsApp Web App on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
