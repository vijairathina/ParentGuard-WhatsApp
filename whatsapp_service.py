import os
import time
import threading
import io
import base64
import traceback
import json
import signal
import sys
import qrcode
from neonize.client import NewClient
from neonize.events import QREv, ConnectedEv, MessageEv
from neonize.utils.jid import build_jid
import state_manager
import re
import connectivity

# --- Configuration ---
SESSION_DB = "whatsapp_session.db"
OUTBOX_FILE = "whatsapp_outbox.json"

CONTACTS_FILE = "whatsapp_contacts.json"
HISTORY_FILE = "whatsapp_history.json"
MAX_HISTORY = 100

_client = None
_is_connected = False
_own_jid = None  # Store our own JID to identify AI messages

def log(message):
    print(f"[WhatsApp Service] {message}", flush=True)

def update_qr_state(qr_data_bytes):
    try:
        # Generate QR Image from raw bytes
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data_bytes)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to Base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        state_manager.update_state(whatsapp_status="Waiting for Login", whatsapp_qr=qr_base64)
        log("✅ QR Code generated and state updated.")
    except Exception as e:
        log(f"❌ Error generating QR: {e}")

def update_connection_state(connected):
    global _is_connected
    _is_connected = connected
    status = "Connected" if connected else "Disconnected"
    # Clear QR code on connection
    qr_val = None if connected else state_manager.get_state().get('whatsapp_qr')
    state_manager.update_state(whatsapp_status=status, whatsapp_qr=qr_val)
    log(f"✅ Connection state updated: {status}")

def save_contact(phone, name=None):
    """Saves a contact to the local JSON list."""
    try:
        contacts = []
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, 'r') as f:
                contacts = json.load(f)
        
        # Check if exists
        existing = next((c for c in contacts if c['target'] == phone), None)
        if not existing:
            contacts.append({
                'name': name or phone,
                'target': phone,
                'platform': 'whatsapp',
                'timestamp': time.time()
            })
        else:
            existing['timestamp'] = time.time() # Update last used
            
        contacts.sort(key=lambda x: x['timestamp'], reverse=True)
        contacts = contacts[:50] # Keep last 50
        
        with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, indent=2)
    except Exception as e:
        log(f"⚠️ Error saving contact: {e}")

def save_message_history(sender_jid, sender_name, body, group_jid=None, is_ai=False):
    """Saves a message to the local history JSON."""
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError: # Handle empty or malformed JSON
                    pass
        
        history.append({
            'sender_jid': str(sender_jid),
            'sender_name': sender_name or str(sender_jid),
            'body': body,
            'group_jid': str(group_jid) if group_jid else None,
            'timestamp': time.time(),
            'platform': 'whatsapp',
            'is_ai': is_ai
        })
        
        history = history[-MAX_HISTORY:] # Keep last 100
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        log(f"⚠️ Error saving message history: {e}")

def process_outbox():
    """Reads whatsapp_outbox.json and sends pending messages."""
    global _client, _is_connected, _own_jid
    
    if not _is_connected or not _client:
        return

    PROCESSING_FILE = "whatsapp_outbox.processing"
    
    if os.path.exists(OUTBOX_FILE):
        try:
            # Atomic rename to prevent multiple workers from reading the same outbox
            os.rename(OUTBOX_FILE, PROCESSING_FILE)
            with open(PROCESSING_FILE, "r", encoding="utf-8") as f:
                messages = json.load(f)
            os.remove(PROCESSING_FILE)

            for msg in messages:
                target = msg.get('target')
                body = msg.get('message') or msg.get('body')
                if target and body:
                    try:
                        target = target.strip()
                        # If target already contains '@', it's a full JID (e.g. group 1234@g.us)
                        if '@' in target:
                            from neonize.utils.jid import JID
                            try:
                                user, server = target.split('@')
                                # Neonize JID objects require all fields
                                jid = JID(User=user, Server=server, RawAgent=0, Device=0, Integrator=0)
                                log(f"📤 Sending to JID {target}...")
                                _client.send_message(jid, body)
                                # Save outgoing message to history as AI
                                save_message_history(_own_jid or "Me", "AI", body, target if "@g.us" in target else None, is_ai=True)
                            except Exception as jid_err:
                                log(f"⚠️ JID Error {target}: {jid_err}")
                                # Fallback: some versions might take the string or require build_jid
                                _client.send_message(target, body)
                                save_message_history(_own_jid or "Me", "AI", body, target if "@g.us" in target else None, is_ai=True)
                        else:
                            clean_phone = target.replace('+', '').replace(' ', '')
                            jid = build_jid(clean_phone)
                            log(f"📤 Sending message to {clean_phone}...")
                            _client.send_message(jid, body)
                            save_contact(clean_phone)
                            # Save outgoing message to history as AI
                            save_message_history(_own_jid or "Me", "AI", body, is_ai=True)
                        time.sleep(1)
                    except Exception as e:
                        log(f"❌ Error sending message to {target}: {e}")
        except Exception as e:
            if os.path.exists(PROCESSING_FILE): os.remove(PROCESSING_FILE)
            log(f"⚠️ Error processing outbox: {e}")

def main():
    global _client
    # Write PID to file for app.py to manage
    try:
        with open("whatsapp.pid", "w") as f:
            f.write(str(os.getpid()))
    except: pass

    log("🚀 Starting standalone WhatsApp Service...")
    
    # 1. Initialize Client
    try:
        _client = NewClient(SESSION_DB)
    except Exception as e:
        log(f"❌ Failed to initialize client: {e}")
        return

    # 2. Define Callbacks
    def on_qr(client, qr_data: bytes):
        log(f"📲 QR Data received ({len(qr_data)} bytes)")
        update_qr_state(qr_data)

    def on_connected(client, connected_ev):
        global _own_jid
        log("✅ Connected Event Received!")
        try:
            me = client.get_me()
            if me and hasattr(me, 'JID'):
                _own_jid = f"{me.JID.User}@{me.JID.Server}"
                log(f"👤 Logged in as: {_own_jid}")
        except Exception as me_err:
            log(f"⚠️ Could not get own JID: {me_err}")
            
        update_connection_state(True)
        # Wait for connection to fully settle before querying groups
        time.sleep(3)
        # Save joined groups so the dashboard can display them
        GROUPS_FILE = "whatsapp_groups.json"
        
        # Load existing cache to avoid refetching names
        cache = {}
        if os.path.exists(GROUPS_FILE):
            try:
                with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                    cache = {item['jid']: item['name'] for item in old_data if item.get('name') and item['name'] != "Unknown Group" and "@" in item.get('jid', '')}
            except: pass

        try:
            groups = client.get_joined_groups()
            groups_data = []
            import re
            for i, g in enumerate(groups):
                gs = str(g)
                
                # 1. Extract clean JID (user@server)
                jid_str = "Unknown"
                jid_obj = None
                try:
                    jid_obj = getattr(g, 'JID', None)
                    if jid_obj and hasattr(jid_obj, 'User') and hasattr(jid_obj, 'Server'):
                        jid_str = f"{jid_obj.User}@{jid_obj.Server}"
                    else:
                        u_m = re.search(r'User:\s*"([^"]+)"', gs, re.IGNORECASE)
                        s_m = re.search(r'Server:\s*"([^"]+)"', gs, re.IGNORECASE)
                        if u_m and s_m:
                            jid_str = f"{u_m.group(1)}@{s_m.group(2)}"
                except:
                    jid_str = "Error Parsing JID"

                # 2. Extract Group Name (Check Cache First)
                name = cache.get(jid_str, "")
                
                if not name or name == "Unknown Group":
                    # Try direct attribute access
                    for attr in ['Name', 'GroupName', 'Topic', 'Subject']:
                        try:
                            val = getattr(g, attr, None)
                            if val and isinstance(val, str) and val.strip():
                                name = val.strip()
                                break
                        except: continue
                
                # If name is still missing and not in cache, try to fetch it
                if (not name or name == "Unknown Group") and jid_str != "Unknown":
                    try:
                        log(f"🔍 Fetching extra info for {jid_str}...")
                        info = client.get_group_info(jid_obj if jid_obj else jid_str)
                        if info:
                            name = getattr(info, 'GroupName', getattr(info, 'Name', getattr(info, 'Topic', '')))
                            if not name:
                                info_s = str(info)
                                m = re.search(r'GroupName:\s*"([^"]*)"', info_s, re.IGNORECASE)
                                if m: name = m.group(1).strip()
                        time.sleep(1.0)
                    except Exception as e:
                        log(f"⚠️ Could not fetch extra info for {jid_str}: {e}")
                        if "429" in str(e):
                            log("🛑 Rate limited by WhatsApp. Using JID as name fallback.")
                            name = name or jid_str

                # Fallback to regex if attributes/cache failed
                if not name:
                    patterns = [r'GroupName:\s*"([^"]*)"', r'Name:\s*"([^"]*)"', r'Topic:\s*"([^"]*)"']
                    for p in patterns:
                        m = re.search(p, gs, re.IGNORECASE)
                        if m:
                            name = m.group(1).strip()
                            break
                
                if not name:
                    name = str(jid_str)
                
                if not name or name == "Unknown":
                    name = "Unknown Group"

                groups_data.append({
                    'name': str(name),
                    'jid': str(jid_str),
                })
            
            groups_data.sort(key=lambda x: str(x.get('name', '')).lower())
            with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
                json.dump(groups_data, f, indent=2)
            log(f"✅ Saved {len(groups_data)} groups to {GROUPS_FILE}")
        except Exception as e:
            if "no such group" in str(e).lower():
                log("ℹ️ No joined groups found (or sync in progress).")
            else:
                log(f"⚠️ Could not fetch groups: {e}")

    def on_message(client, message_ev):
        try:
            info = getattr(message_ev, 'Info', None)
            if not info: return
            
            # 1. Extract JIDs from MessageSource (most reliable for sender/chat)
            ms = getattr(info, 'MessageSource', None)
            sender = "Unknown"
            chat_jid = "Unknown"
            
            if ms:
                # Use getattr with fallback to strings
                try:
                    s_obj = getattr(ms, 'Sender', None)
                    if s_obj:
                        sender = f"{s_obj.User}@{s_obj.Server}"
                    else:
                        sender = str(getattr(ms, 'SenderAlt', "Unknown"))
                except:
                    sender = str(getattr(ms, 'Sender', "Unknown"))
                    
                try:
                    c_obj = getattr(ms, 'Chat', None)
                    if c_obj:
                        chat_jid = f"{c_obj.User}@{c_obj.Server}"
                except:
                    chat_jid = str(getattr(ms, 'Chat', "Unknown"))

            # Fallback if MessageSource failed
            if sender == "Unknown" or not "@" in sender:
                # Try direct Info attributes
                for attr in ['Sender', 'sender', 'Source', 'source']:
                    val = getattr(info, attr, None)
                    if val:
                        sender = str(val)
                        break

            # Clean any remaining "User:" Protobuf strings
            if "User:" in sender and "@" not in sender:
                u = re.search(r'User:\s*"([^"]+)"', sender)
                s = re.search(r'Server:\s*"([^"]+)"', sender)
                if u and s: sender = f"{u.group(1)}@{s.group(2)}"
            
            if "User:" in chat_jid and "@" not in chat_jid:
                u = re.search(r'User:\s*"([^"]+)"', chat_jid)
                s = re.search(r'Server:\s*"([^"]+)"', chat_jid)
                if u and s: chat_jid = f"{u.group(1)}@{s.group(2)}"

            # 2. Get Pushname (Profile Name)
            push_name = getattr(info, 'Pushname', "") or getattr(info, 'PushName', "") or sender
            
            # 3. Extract text
            msg = getattr(message_ev, 'Message', None)
            text = ""
            if msg:
                if hasattr(msg, 'conversation') and msg.conversation:
                    text = msg.conversation
                elif hasattr(msg, 'extendedTextMessage') and msg.extendedTextMessage:
                    text = getattr(msg.extendedTextMessage, 'text', "")
            
            if not text:
                # Log that we got a message but couldn't read text (e.g. image/sticker)
                log(f"ℹ️ Received non-text message from {push_name}")
                return

            # Extract chat and group info
            chat_type = "Direct Chat"
            group_jid = None
            
            if "@g.us" in chat_jid:
                chat_type = "Group"
                group_jid = chat_jid
            elif "@lid" in chat_jid:
                chat_type = "LID Chat"
            
            is_ai = False
            if _own_jid and sender == _own_jid:
                is_ai = True
                push_name = "AI"
            
            save_message_history(sender, push_name, text, group_jid, is_ai=is_ai)
            log(f"📩 History: From {push_name} ({sender}) in {chat_type}: {text[:50]}...")

            # 4. Check for Keyword Reminders
            import datetime
            state = state_manager.get_state()
            schedules = state.get('wa_auto_schedules', [])
            for s in schedules:
                if s.get('type') == 'keyword' and s.get('enabled', True):
                    keyword = s.get('customMsg', '').strip().lower()
                    target = s.get('target', '').strip()
                    if keyword and keyword in text.lower():
                        clean_sender = sender.split('@')[0]
                        clean_chat = chat_jid.split('@')[0]
                        clean_target = target.split('@')[0] if target else ''
                        
                        # Match if target is empty (listen to all) or target matches sender/group
                        if not clean_target or clean_target in [clean_sender, clean_chat, target]:
                            pending = state.get('wa_pending_reminders', [])
                            pending.append({
                                'schedule_id': s.get('id'),
                                'target': chat_jid,
                                'text': text,
                                'days': s.get('reminderDays', 3),
                                'time': s.get('time', '08:00'),
                                'receivedAt': datetime.datetime.now().isoformat()
                            })
                            state_manager.update_state(wa_pending_reminders=pending)
                            log(f"🔔 Keyword '{keyword}' matched in chat {chat_jid}! Scheduled reminder for {s.get('reminderDays')} days later.")


        except Exception as e:
            log(f"⚠️ Error in on_message: {e}")

    # 3. Register Callbacks
    _client.qr(on_qr)
    _client.event(ConnectedEv)(on_connected)
    _client.event(MessageEv)(on_message)

    # 4. Start Outbox Poller in a separate thread
    def outbox_loop():
        FETCH_GROUPS_FLAG = "fetch_groups.flag"
        GROUPS_FILE = "whatsapp_groups.json"
        while True:
            # Only process if internet is available
            if connectivity.is_internet_available():
                process_outbox()
                # Check for on-demand group refresh request from dashboard
                if _client is not None and os.path.exists(FETCH_GROUPS_FLAG):
                    try:
                        os.remove(FETCH_GROUPS_FLAG)
                        log("🔄 On-demand group refresh triggered...")
                        groups = _client.get_joined_groups()
                        groups_data = []
                        import re
                        for i, g in enumerate(groups):
                            gs = str(g)
                            # Extract clean JID (user@server)
                            jid_str = ""
                            u_m = re.search(r'User:\s*"([^"]+)"', gs, re.IGNORECASE)
                            s_m = re.search(r'Server:\s*"([^"]+)"', gs, re.IGNORECASE)
                            
                            if u_m and s_m:
                                jid_str = f"{u_m.group(1)}@{s_m.group(2)}"
                            else:
                                jid_str = str(getattr(g, 'JID', 'Unknown JID'))
                                if 'User: "' in jid_str:
                                    u_inner = re.search(r'User:\s*"([^"]+)"', jid_str, re.IGNORECASE)
                                    s_inner = re.search(r'Server:\s*"([^"]+)"', jid_str, re.IGNORECASE)
                                    if u_inner and s_inner:
                                        jid_str = f"{u_inner.group(1)}@{s_inner.group(2)}"

                            # Extract Group Name
                            name = ""
                            name_m = re.search(r'GroupName:\s*"([^"]*)"', gs, re.IGNORECASE)
                            if name_m:
                                name = name_m.group(1).strip()
                            
                            if not name:
                                name_m2 = re.search(r'Name:\s*"([^"]*)"', gs, re.IGNORECASE)
                                if name_m2:
                                    name = name_m2.group(1).strip()
                            
                            if not name:
                                name = jid_str

                            groups_data.append({
                                'name': name,
                                'jid': jid_str
                            })
                        groups_data.sort(key=lambda x: x['name'].lower())
                        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
                            json.dump(groups_data, f, indent=2)
                        log(f"✅ On-demand refresh: saved {len(groups_data)} groups")
                    except Exception as e:
                        log(f"⚠️ On-demand group refresh failed: {e}")
            else:
                log("🌐 Internet is offline. Skipping outbox processing.")
            time.sleep(5) # Check every 5 seconds when offline or between cycles
    
    outbox_thread = threading.Thread(target=outbox_loop, daemon=True)
    outbox_thread.start()

    # 5. Start Server-Side Auto Scheduler Thread
    def auto_scheduler_loop():
        """
        Server-side scheduler: reads wa_auto_schedules from shared state,
        checks time/day match, generates report via Flask API, queues to outbox.
        Runs every 60 seconds so it doesn't miss the configured minute.
        """
        import datetime
        import urllib.request

        SCHED_LAST_FIRED_KEY = 'wa_sched_last_fired'
        FLASK_BASE = 'http://127.0.0.1:5001'

        def fetch_json(url, data=None):
            """Minimal HTTP helper that works without requests."""
            import urllib.parse
            body = json.dumps(data).encode('utf-8') if data else None
            method = 'POST' if data is not None else 'GET'
            req = urllib.request.Request(
                url, data=body, method=method,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode('utf-8'))

        log("⏰ Server-side auto-scheduler started.")

        while True:
            try:
                state = state_manager.get_state()
                schedules = state.get('wa_auto_schedules', [])
                last_fired = state.get(SCHED_LAST_FIRED_KEY, {})
                default_target = state.get('whatsapp_target', '')
                pending_reminders = state.get('wa_pending_reminders', [])

                now = datetime.datetime.now()
                current_h   = now.hour
                current_m   = now.minute
                current_day = now.weekday() + 1
                js_day = now.weekday() + 1 if now.weekday() < 6 else 0
                date_key = f"{now.year}-{now.month}-{now.day}"

                # 1. Process Pending Keyword Reminders
                if pending_reminders:
                    remaining = []
                    fired_any = False
                    for p in pending_reminders:
                        try:
                            received_dt = datetime.datetime.fromisoformat(p['receivedAt'])
                            days_diff = (datetime.datetime(now.year, now.month, now.day) - datetime.datetime(received_dt.year, received_dt.month, received_dt.day)).days
                            
                            target_days = int(p.get('days', 3))
                            sched_time = p.get('time', '08:00')
                            if ':' in sched_time:
                                sched_h, sched_m = map(int, sched_time.split(':'))
                                
                                if days_diff >= target_days:
                                    if current_h == sched_h and current_m == sched_m:
                                        msg_to_send = f"Remainder: {p['text']}"
                                        log(f"⏰ Firing Keyword Reminder to {p['target']}")
                                        from whatsapp_notifier import send_whatsapp_message
                                        ok = send_whatsapp_message(p['target'], msg_to_send)
                                        if ok:
                                            log(f"✅ Keyword Reminder sent to {p['target']}")
                                        fired_any = True
                                        continue
                        except Exception as e:
                            log(f"⚠️ Error processing pending reminder: {e}")
                        remaining.append(p)
                        
                    if fired_any:
                        state_manager.update_state(wa_pending_reminders=remaining)

                # 2. Process Regular Schedules
                if not schedules:
                    time.sleep(60)
                    continue

                for s in schedules:
                    if not s.get('enabled', True):
                        continue

                    sched_time = s.get('time', '')
                    if ':' not in sched_time:
                        continue
                    sched_h, sched_m = map(int, sched_time.split(':'))

                    if current_h != sched_h or current_m != sched_m:
                        continue

                    # Check day match for weekly schedules
                    frequency = s.get('frequency', 'daily')
                    if frequency == 'weekly':
                        weekdays = s.get('weekdays', [])
                        if js_day not in weekdays:
                            continue
                    if frequency == 'keyword':
                        continue # Processed separately via on_message and pending_reminders

                    # Dedup — don't fire more than once per time slot per day
                    fire_key = f"{js_day if frequency == 'weekly' else ''}-{date_key}-{sched_time}"
                    if last_fired.get(s['id']) == fire_key:
                        continue

                    log(f"⏰ Firing server-side schedule: type={s.get('type')} at {sched_time}")

                    try:
                        api_payload = {
                            "timeframe": s.get('type', 'today'),
                            "s": s
                        }
                        api_res = fetch_json(f"{FLASK_BASE}/api/whatsapp/generate_report", api_payload)
                        report = api_res.get('report') if api_res else None
                        
                        log(f"⏰ API Response length: {len(report) if report else 'None'}")
                        if report:
                            log(f"⏰ Report Preview: {report[:50]}...")
                        
                        if report and not report.startswith('No hearings'):
                            target = s.get('target') or default_target
                            if not target:
                                log(f"⚠️ Schedule {s['id']}: no target phone set, skipping.")
                            else:
                                from whatsapp_notifier import send_whatsapp_message
                                ok = send_whatsapp_message(target, report)
                                if ok:
                                    log(f"✅ Schedule {s['id']} sent to {target}")
                                else:
                                    log(f"❌ Schedule {s['id']} send failed")
                        else:
                            log(f"ℹ️ Schedule {s['id']}: no hearings to report ({s.get('type')}), marking fired.")

                        # Always mark as fired to prevent retries this minute
                        last_fired[s['id']] = fire_key
                        state_manager.update_state(**{SCHED_LAST_FIRED_KEY: last_fired})

                    except Exception as fire_err:
                        log(f"⚠️ Error firing schedule {s.get('id')}: {fire_err}")

            except Exception as loop_err:
                log(f"⚠️ Auto-scheduler loop error: {loop_err}")

            time.sleep(60)  # Check every minute

    scheduler_thread = threading.Thread(target=auto_scheduler_loop, daemon=True)
    scheduler_thread.start()

    # 6. Connect (Blocking Call)
    log("🔗 Connecting to WhatsApp...")
    try:
        _client.connect()
    except Exception as e:
        log(f"❌ Connection Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Signal handling handled by OS for subprocess usually, but good practice
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    main()
