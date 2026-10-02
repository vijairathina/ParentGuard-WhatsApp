import os
import json
import time
import threading
import io
import base64
import queue
import qrcode
from typing import Dict, List, Any, Optional

import sys
from content_monitor import ContentMonitor

from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv, HistorySyncEv, LoggedOutEv, DisconnectedEv
from neonize.utils.jid import build_jid

ACCOUNTS_FILE = "accounts/accounts.json"
_lock = threading.Lock()

def is_valid_name(name: Any) -> bool:
    """Returns True if the string is a valid human-readable name (not empty, not dots, not raw digits/LIDs)."""
    if not name or not isinstance(name, str):
        return False
    name = name.strip()
    if not name or name in ('.', '..', '-', 'WA', 'Unknown', 'null', 'None', 'Member'):
        return False
    import re
    clean = re.sub(r'[@\s\-\+\(\)\.]', '', name)
    if clean.isdigit() or (name.endswith('@lid') and name[:-4].isdigit()):
        return False
    return True

class WhatsAppManager:
    def __init__(self):
        self.clients: Dict[str, NewClient] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.statuses: Dict[str, str] = {}
        self.qr_codes: Dict[str, str] = {}
        self.profile_info: Dict[str, Dict[str, Any]] = {}
        self.listeners: List[queue.Queue] = []
        self.monitor = ContentMonitor()
        self.lid_maps: Dict[str, Dict[str, Dict[str, str]]] = {}
        
        # Ensure directory exists
        os.makedirs("accounts", exist_ok=True)
        self.load_accounts()
        self.start_external_history_watcher()

    def start_external_history_watcher(self):
        """
        Continuously watches external whatsapp_history.json (produced by whatsapp_service.py)
        and merges any newly arrived messages into active WhatsApp accounts in real-time.
        """
        def _watcher():
            mtimes = {}
            candidate_paths = [
                os.path.join(os.path.dirname(__file__), "whatsapp_history.json"),
                r"D:\PY\eCourt\Backup\whatsapp_history.json",
                r"D:\PY\eCourt\eCourtsServices 3.0\ecourt_flask\whatsapp_history.json",
                r"D:\PY\eCourt\eCourtsServices 3.0\ecourt_flask - Copy\whatsapp_history.json",
                r"D:\PY\eCourt\ecourt_flask 1.0\whatsapp_history.json"
            ]
            env_path = os.environ.get("ECOURT_HISTORY")
            if env_path and env_path not in candidate_paths:
                candidate_paths.insert(0, env_path)

            # Initialize initial modification times
            for p in candidate_paths:
                if p and os.path.exists(p):
                    try:
                        mtimes[p] = os.path.getmtime(p)
                    except Exception:
                        pass

            while True:
                time.sleep(1.5)
                for p in candidate_paths:
                    if not p or not os.path.exists(p):
                        continue
                    try:
                        mtime = os.path.getmtime(p)
                        last_m = mtimes.get(p)
                        if last_m is None:
                            mtimes[p] = mtime
                            continue
                        if mtime > last_m:
                            mtimes[p] = mtime
                            print(f"[Watcher] Detected live update in {p} from whatsapp_service!")
                            for acc_id in list(self.profile_info.keys()):
                                count = self.import_ecourt_history(acc_id, p)
                                if count > 0:
                                    self.merge_contacts_groups(acc_id)
                                    self.broadcast("contacts_updated", acc_id, {})
                                    top_contacts = self.get_contacts(acc_id)
                                    if top_contacts:
                                        top_c = top_contacts[0]
                                        msgs = self.get_messages(acc_id, top_c["jid"])
                                        if msgs:
                                            self.broadcast("message", acc_id, {
                                                "chat_jid": top_c["jid"],
                                                "message": msgs[-1]
                                            })
                    except Exception:
                        pass
        threading.Thread(target=_watcher, daemon=True, name="external_history_watcher").start()

    def get_listeners(self):
        return self.listeners

    def register_listener(self) -> queue.Queue:
        q = queue.Queue()
        self.listeners.append(q)
        return q

    def unregister_listener(self, q: queue.Queue):
        if q in self.listeners:
            self.listeners.remove(q)

    def broadcast(self, event_type: str, account_id: str, data: Any):
        payload = {
            "event": event_type,
            "account_id": account_id,
            "data": data
        }
        # Debug: print outgoing SSE payload for troubleshooting
        try:
            print(f"[Manager][{account_id}] Broadcasting event: {event_type} -> {payload}")
        except Exception:
            pass
        for q in list(self.listeners):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    def load_accounts(self):
        with _lock:
            if os.path.exists(ACCOUNTS_FILE):
                try:
                    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                        accounts = json.load(f)
                        for acc in accounts:
                            acc_id = acc["id"]
                            self.statuses[acc_id] = "Disconnected"
                            self.profile_info[acc_id] = {
                                "id": acc_id,
                                "name": acc.get("name", "Account " + acc_id),
                                "jid": acc.get("jid", ""),
                                "phone": acc.get("phone", "")
                            }
                except Exception as e:
                    print(f"[Manager] Error loading accounts: {e}")
            else:
                with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)

    def save_accounts(self):
        with _lock:
            accounts_data = []
            for acc_id, info in self.profile_info.items():
                accounts_data.append({
                    "id": acc_id,
                    "name": info.get("name", ""),
                    "jid": info.get("jid", ""),
                    "phone": info.get("phone", ""),
                    "status": self.statuses.get(acc_id, "Disconnected")
                })
            try:
                with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(accounts_data, f, indent=2)
            except Exception as e:
                print(f"[Manager] Error saving accounts.json: {e}")

    def start_all(self):
        # Auto-start previously configured accounts
        acc_ids = list(self.profile_info.keys())
        print(f"[Manager] Auto-starting {len(acc_ids)} accounts: {acc_ids}")
        for acc_id in acc_ids:
            self.start_account(acc_id)

    def start_account(self, account_id: str) -> bool:
        if account_id in self.clients:
            print(f"[Manager] Account {account_id} already running.")
            return True

        self.statuses[account_id] = "Connecting"
        self.broadcast("status", account_id, {"status": "Connecting"})

        def run():
            db_path = f"accounts/{account_id}.db"
            print(f"[Manager] Thread starting for account {account_id} with db {db_path}")
            try:
                client = NewClient(db_path, uuid=account_id)
                self.clients[account_id] = client

                @client.qr
                def on_qr(c, qr_data: bytes):
                    print(f"[Manager][{account_id}] QR Code received ({len(qr_data)} bytes)")
                    try:
                        qr = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr.add_data(qr_data)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        
                        buffered = io.BytesIO()
                        img.save(buffered, format="PNG")
                        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
                        self.statuses[account_id] = "Waiting for Scan"
                        self.qr_codes[account_id] = qr_base64
                        
                        self.broadcast("status", account_id, {"status": "Waiting for Scan"})
                        self.broadcast("qr", account_id, {"qr": qr_base64})
                    except Exception as qr_err:
                        print(f"[Manager][{account_id}] QR generate error: {qr_err}")

                @client.event(ConnectedEv)
                def on_connected(c, connected_ev):
                    print(f"[Manager][{account_id}] Connected!")
                    self.statuses[account_id] = "Connected"
                    self.qr_codes[account_id] = ""
                    
                    # Fetch profile info
                    own_jid = ""
                    name = "WhatsApp Account"
                    phone = ""
                    try:
                        me = client.get_me()
                        if me and hasattr(me, 'JID'):
                            own_jid = f"{me.JID.User}@{me.JID.Server}"
                            phone = me.JID.User
                            name = getattr(me, 'Pushname', '') or getattr(me, 'PushName', '') or name
                    except Exception as me_err:
                        print(f"[Manager][{account_id}] Error fetching get_me(): {me_err}")
                    
                    self.profile_info[account_id] = {
                        "id": account_id,
                        "name": name,
                        "jid": own_jid,
                        "phone": phone
                    }
                    self.save_accounts()
                    
                    self.broadcast("status", account_id, {
                        "status": "Connected",
                        "name": name,
                        "jid": own_jid,
                        "phone": phone
                    })
                    
                    # Load and cache groups / contacts asynchronously or update them
                    self.sync_groups(account_id)

                @client.event(HistorySyncEv)
                def on_history_sync(c, history_sync_ev):
                    self.handle_history_sync(account_id, history_sync_ev)

                @client.event(MessageEv)
                def on_message(c, message_ev):
                    self.handle_incoming_message(account_id, message_ev)

                @client.event(LoggedOutEv)
                def on_logged_out(c, logged_out_ev):
                    print(f"[Manager][{account_id}] Logged out by WhatsApp (session revoked on mobile device).")
                    self.statuses[account_id] = "Logged Out"
                    self.save_accounts()
                    self.broadcast("status", account_id, {"status": "Logged Out", "reason": "Session logged out from device"})

                @client.event(DisconnectedEv)
                def on_disconnected(c, disconnected_ev):
                    print(f"[Manager][{account_id}] Disconnected.")
                    if self.statuses.get(account_id) != "Logged Out":
                        self.statuses[account_id] = "Disconnected"
                    self.broadcast("status", account_id, {"status": self.statuses.get(account_id, "Disconnected")})

                # Connect blocks
                client.connect()
            except Exception as e:
                print(f"[Manager][{account_id}] Error in worker loop: {e}")
                self.statuses[account_id] = "Disconnected"
                self.broadcast("status", account_id, {"status": "Disconnected", "error": str(e)})
                if account_id in self.clients:
                    del self.clients[account_id]

        t = threading.Thread(target=run, daemon=True, name=f"wa_thread_{account_id}")
        self.threads[account_id] = t
        t.start()
        return True

    def stop_account(self, account_id: str) -> bool:
        print(f"[Manager] Stopping account {account_id}")
        client = self.clients.get(account_id)
        if client:
            try:
                client.disconnect()
                client.stop()
            except Exception as e:
                print(f"[Manager] Error stopping client {account_id}: {e}")
            
            # Clean up references
            if account_id in self.clients:
                del self.clients[account_id]
        
        self.statuses[account_id] = "Disconnected"
        self.qr_codes[account_id] = ""
        self.broadcast("status", account_id, {"status": "Disconnected"})
        return True

    def delete_account(self, account_id: str) -> bool:
        self.stop_account(account_id)
        
        # Delete session database files
        db_path = f"accounts/{account_id}.db"
        for ext in ["", "-wal", "-shm"]:
            fpath = db_path + ext
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception as e:
                    print(f"[Manager] Error removing db file {fpath}: {e}")
                    
        # Remove from profile info
        if account_id in self.profile_info:
            del self.profile_info[account_id]
        if account_id in self.statuses:
            del self.statuses[account_id]
        if account_id in self.qr_codes:
            del self.qr_codes[account_id]
            
        # Clean custom json files for history and contacts
        for ftype in ["history", "contacts", "groups"]:
            fpath = f"accounts/{ftype}_{account_id}.json"
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except:
                    pass

        self.save_accounts()
        self.broadcast("deleted", account_id, {})
        return True

    def load_contacts_from_db(self, account_id: str) -> List[Dict[str, Any]]:
        """Reads contacts from whatsmeow_contacts SQLite table and maps LIDs to phone numbers."""
        db_path = f"accounts/{account_id}.db"
        if not os.path.exists(db_path):
            return []
        import sqlite3
        import re
        db_contacts = []
        try:
            lid_map = self.load_lid_map(account_id)
            lid_to_pn = lid_map.get("lid_to_pn", {})
            pn_to_lid = lid_map.get("pn_to_lid", {})

            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
            c = conn.cursor()
            c.execute("SELECT their_jid, first_name, full_name, push_name, business_name FROM whatsmeow_contacts")
            
            raw_entries = {}
            for row in c.fetchall():
                jid, fn, full, push, biz = row
                jid_str = str(jid).strip() if jid else ""
                if not jid_str:
                    continue
                # Pick best human name
                name = ""
                for candidate in [full, biz, push, fn]:
                    if is_valid_name(candidate):
                        name = str(candidate).strip()
                        break
                raw_entries[jid_str] = name
            conn.close()

            # Cross-populate names between LID and Phone entries
            for lid, pn in lid_to_pn.items():
                lid_jid = f"{lid}@lid"
                pn_jid = f"{pn}@s.whatsapp.net"
                best_name = raw_entries.get(pn_jid) or raw_entries.get(lid_jid) or ""
                if best_name:
                    if not raw_entries.get(lid_jid):
                        raw_entries[lid_jid] = best_name
                    if not raw_entries.get(pn_jid):
                        raw_entries[pn_jid] = best_name

            for jid_str, name in raw_entries.items():
                clean_user = jid_str.split("@")[0]
                pn = lid_to_pn.get(clean_user) if "@lid" in jid_str else (clean_user if clean_user.isdigit() and len(clean_user) <= 15 else "")
                db_contacts.append({
                    "jid": jid_str,
                    "name": name,
                    "phone_number": pn or "",
                    "is_group": False,
                    "timestamp": 0
                })
        except Exception as e:
            print(f"[Manager][{account_id}] SQLite contact query error: {e}")
        return db_contacts

    def sync_groups(self, account_id: str):
        client = self.clients.get(account_id)
        if not client:
            return
        
        def fetch_run():
            GROUPS_FILE = f"accounts/groups_{account_id}.json"
            try:
                print(f"[Manager][{account_id}] Syncing WhatsApp groups & contacts...")
                groups = client.get_joined_groups()
                groups_data = []
                import re
                for g in groups:
                    gs = str(g)
                    jid_str = ""
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
                        pass
                    if not jid_str:
                        continue

                    # Group name
                    name = ""
                    for attr in ['Name', 'GroupName', 'Topic', 'Subject']:
                        try:
                            val = getattr(g, attr, None)
                            if val and isinstance(val, str) and val.strip():
                                name = val.strip()
                                break
                        except:
                            pass
                    if not name:
                        patterns = [r'GroupName:\s*"([^"]*)"', r'Name:\s*"([^"]*)"', r'Topic:\s*"([^"]*)"']
                        for p in patterns:
                            m = re.search(p, gs, re.IGNORECASE)
                            if m:
                                name = m.group(1).strip()
                                break
                    if not name:
                        name = jid_str

                    groups_data.append({
                        "jid": jid_str,
                        "name": name,
                        "is_group": True
                    })
                
                groups_data.sort(key=lambda x: x["name"].lower())
                with open(GROUPS_FILE, "w", encoding="utf-8") as f:
                    json.dump(groups_data, f, indent=2)

                # Fetch contacts from database
                db_contacts = self.load_contacts_from_db(account_id)
                print(f"[Manager][{account_id}] Loaded {len(db_contacts)} contacts from database.")

                # Merge contacts, groups, and history chats
                self.merge_contacts_groups(account_id, extra_contacts=db_contacts)
                self.broadcast("contacts_updated", account_id, {})
                print(f"[Manager][{account_id}] Synced {len(groups_data)} groups and {len(db_contacts)} contacts.")
            except Exception as e:
                print(f"[Manager][{account_id}] Error in sync_groups: {e}")
                
        threading.Thread(target=fetch_run, daemon=True).start()

    def handle_history_sync(self, account_id: str, history_sync_ev: Any):
        """Processes initial conversation history synced by WhatsApp upon connection."""
        def _sync_worker():
            try:
                data = getattr(history_sync_ev, 'Data', None) or history_sync_ev
                conversations = getattr(data, 'conversations', [])
                if not conversations:
                    return

                print(f"[Manager][{account_id}] Processing HistorySync with {len(conversations)} conversations...")
                HISTORY_FILE = f"accounts/history_{account_id}.json"
                history = {}
                if os.path.exists(HISTORY_FILE):
                    try:
                        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                            history = json.load(f)
                    except:
                        history = {}

                new_count = 0
                for conv in conversations:
                    cjid = getattr(conv, 'ID', '')
                    if not cjid:
                        continue
                    if cjid not in history:
                        history[cjid] = []

                    existing_ids = {m.get("id") for m in history[cjid]}
                    msgs = getattr(conv, 'messages', [])
                    for m_item in msgs:
                        try:
                            wmi = getattr(m_item, 'message', None)
                            if not wmi:
                                continue
                            key = getattr(wmi, 'key', None)
                            msg_id = getattr(key, 'ID', '') or getattr(key, 'id', '')
                            if not msg_id or msg_id in existing_ids:
                                continue

                            from_me = getattr(key, 'fromMe', False)
                            ts = int(getattr(wmi, 'messageTimestamp', 0))
                            raw_p = getattr(wmi, 'pushName', '') or ""
                            push_name = "Me" if from_me else (raw_p.strip() if is_valid_name(raw_p) else "")
                            sender = getattr(key, 'participant', '') or (cjid if not from_me else "Me")

                            inner_msg = getattr(wmi, 'message', None)
                            text = ""
                            attachment = None
                            if inner_msg:
                                attachment = self._extract_attachment(inner_msg)
                                if hasattr(inner_msg, 'conversation') and inner_msg.conversation:
                                    text = inner_msg.conversation
                                elif hasattr(inner_msg, 'extendedTextMessage') and inner_msg.extendedTextMessage:
                                    text = getattr(inner_msg.extendedTextMessage, 'text', "")
                                elif hasattr(inner_msg, 'documentWithCaptionMessage') and inner_msg.documentWithCaptionMessage:
                                    dm = getattr(inner_msg.documentWithCaptionMessage, 'message', None)
                                    if dm and hasattr(dm, 'documentMessage'):
                                        text = getattr(dm.documentMessage, 'caption', "")

                                if not text and attachment:
                                    text = attachment.get("caption") or f"[{attachment.get('type', 'attachment')}]"

                            if not text and not attachment:
                                continue

                            msg_data = {
                                "id": str(msg_id),
                                "sender": sender,
                                "sender_name": push_name,
                                "chat_jid": cjid,
                                "body": text,
                                "timestamp": ts,
                                "is_outgoing": from_me
                            }
                            if attachment:
                                msg_data["attachment"] = attachment

                            history[cjid].append(msg_data)
                            existing_ids.add(msg_id)
                            new_count += 1
                        except Exception:
                            continue

                    history[cjid] = sorted(history[cjid], key=lambda x: x.get("timestamp", 0))[-150:]

                with _lock:
                    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                        json.dump(history, f, indent=2)

                print(f"[Manager][{account_id}] HistorySync: saved {new_count} historical messages.")
                self.merge_contacts_groups(account_id)
                self.broadcast("contacts_updated", account_id, {})
            except Exception as e:
                print(f"[Manager][{account_id}] HistorySync error: {e}")

        threading.Thread(target=_sync_worker, daemon=True).start()

    def download_media_async(self, account_id: str, client: Any, msg_obj: Any, msg_id: str, att_type: str, chat_jid: str):
        """Asynchronously downloads media (image, audio, video, document) and saves to static/media."""
        def _dl():
            try:
                media_dir = os.path.join("static", "media", account_id)
                os.makedirs(media_dir, exist_ok=True)
                ext_map = {"image": ".jpg", "audio": ".ogg", "video": ".mp4", "document": ".pdf", "sticker": ".webp"}
                ext = ext_map.get(att_type, ".dat")
                filepath = os.path.join(media_dir, f"{msg_id}{ext}")
                local_url = f"/static/media/{account_id}/{msg_id}{ext}"
                
                if not os.path.exists(filepath):
                    data = client.download_any(msg_obj)
                    if data:
                        with open(filepath, "wb") as f:
                            f.write(data)
                        print(f"[Manager][{account_id}] Downloaded media {msg_id}: {len(data)} bytes ({att_type})")

                # Update history JSON with local_url
                HISTORY_FILE = f"accounts/history_{account_id}.json"
                with _lock:
                    if os.path.exists(HISTORY_FILE):
                        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                            history = json.load(f)
                        if chat_jid in history:
                            for m in history[chat_jid]:
                                if m.get("id") == msg_id and "attachment" in m:
                                    m["attachment"]["local_url"] = local_url
                            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                                json.dump(history, f, indent=2)
                
                # Broadcast media ready event to UI
                self.broadcast("media_ready", account_id, {
                    "chat_jid": chat_jid,
                    "msg_id": msg_id,
                    "local_url": local_url,
                    "type": att_type
                })
            except Exception as e:
                print(f"[Manager][{account_id}] Media download error: {e}")
        threading.Thread(target=_dl, daemon=True).start()

    def handle_message_revoke(self, account_id: str, chat_jid: str, target_id: str, sender: str):
        """
        Anti-Delete Safeguard: When someone deletes a message ('Delete for Everyone'),
        we DO NOT delete it! We preserve the original text & media and mark it as revoked/deleted.
        """
        HISTORY_FILE = f"accounts/history_{account_id}.json"
        with _lock:
            history = {}
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except:
                    history = {}

            target_msg = None
            target_chat = chat_jid
            if chat_jid in history:
                for m in history[chat_jid]:
                    if m.get("id") == target_id:
                        target_msg = m
                        break
            if not target_msg:
                for cjid, msgs in history.items():
                    for m in msgs:
                        if m.get("id") == target_id:
                            target_msg = m
                            target_chat = cjid
                            break
                    if target_msg:
                        break

            now_ts = int(time.time())
            if target_msg:
                # Mark as deleted but preserve the body and attachments!
                target_msg["is_deleted"] = True
                target_msg["deleted_at"] = now_ts
                target_msg["deleted_by"] = sender
                print(f"[Anti-Delete][{account_id}] Preserved deleted message {target_id}: '{target_msg.get('body', '')}'")
            else:
                target_msg = {
                    "id": target_id,
                    "sender": sender,
                    "sender_name": sender.split("@")[0],
                    "chat_jid": chat_jid,
                    "body": "🚫 This message was deleted by sender",
                    "timestamp": now_ts,
                    "is_outgoing": False,
                    "is_deleted": True,
                    "deleted_at": now_ts,
                    "deleted_by": sender
                }
                if target_chat not in history:
                    history[target_chat] = []
                history[target_chat].append(target_msg)

            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2)
            except Exception as e:
                print(f"[Manager] Error saving history on revoke: {e}")

        # Broadcast update to web app UI
        self.broadcast("message_revoked", account_id, {
            "chat_jid": target_chat,
            "target_id": target_id,
            "message": target_msg
        })

        # Dispatch external webhook event
        try:
            from api_service import dispatch_webhook_event
            dispatch_webhook_event("message_revoked", account_id, {
                "chat_jid": target_chat,
                "target_id": target_id,
                "message": target_msg
            })
        except Exception:
            pass

        # Log to Safety Audit Logs
        from datetime import datetime
        incident = {
            "id": f"inc_del_{now_ts}_{int(time.time()*1000)%1000}",
            "account_id": account_id,
            "timestamp": now_ts,
            "datetime": datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d %H:%M:%S"),
            "chat_jid": target_chat,
            "sender": sender,
            "sender_name": sender.split("@")[0],
            "is_outgoing": False,
            "direction": "Incoming",
            "message": target_msg.get("body", "[Deleted Message]"),
            "detection_type": "Anti-Delete Safeguard",
            "severity": "High",
            "reason": f"Sender attempted to delete message: '{target_msg.get('body', '')[:60]}'",
            "details": {"target_id": target_id, "deleted_by": sender}
        }
        self.monitor.append_audit_log(account_id, incident)
        self.broadcast("security_alert", account_id, incident)

    def _extract_attachment(self, msg: Any) -> Optional[Dict[str, Any]]:
        if not msg:
            return None

        # Unwrap common wrapper fields
        if hasattr(msg, "Message") and getattr(msg, "Message", None):
            inner = getattr(msg, "Message")
            if inner and not isinstance(inner, str):
                msg = inner
        elif hasattr(msg, "message") and getattr(msg, "message", None):
            inner = getattr(msg, "message")
            if inner and not isinstance(inner, str):
                msg = inner

        # Determine which attachment field is present safely without WhichOneof
        message_type = None
        for candidate in ("imageMessage", "videoMessage", "documentMessage", "audioMessage", "stickerMessage"):
            try:
                if hasattr(msg, "HasField") and msg.HasField(candidate):
                    message_type = candidate
                    break
                elif hasattr(msg, candidate) and getattr(msg, candidate, None):
                    sub = getattr(msg, candidate)
                    if hasattr(sub, "ByteSize") and sub.ByteSize() > 0:
                        message_type = candidate
                        break
            except Exception:
                pass

        if not message_type:
            try:
                if hasattr(msg, "HasField") and msg.HasField("documentWithCaptionMessage"):
                    sub_m = getattr(msg.documentWithCaptionMessage, "message", None)
                    if sub_m and hasattr(sub_m, "HasField") and sub_m.HasField("documentMessage"):
                        msg = sub_m
                        message_type = "documentMessage"
            except Exception:
                pass

        if not message_type:
            return None

        attachment = {
            "type": message_type.replace("Message", "").lower(),
            "mime_type": "",
            "url": "",
            "direct_path": "",
            "file_name": "",
            "caption": "",
            "duration": None,
            "preview": None
        }

        def _encode_preview(data: Any, mime_type: str = "jpeg") -> Optional[str]:
            if not data:
                return None
            try:
                return f"data:image/{mime_type};base64,{base64.b64encode(data).decode('utf-8')}"
            except Exception:
                return None

        try:
            if message_type == "imageMessage":
                image = getattr(msg, "imageMessage", None)
                if image:
                    attachment.update({
                        "mime_type": getattr(image, "mimetype", "") or "",
                        "url": getattr(image, "URL", "") or getattr(image, "url", "") or "",
                        "direct_path": getattr(image, "directPath", "") or "",
                        "caption": getattr(image, "caption", "") or ""
                    })
                    attachment["preview"] = _encode_preview(getattr(image, "JPEGThumbnail", None), "jpeg")
            elif message_type == "videoMessage":
                video = getattr(msg, "videoMessage", None)
                if video:
                    attachment.update({
                        "mime_type": getattr(video, "mimetype", "") or "",
                        "url": getattr(video, "URL", "") or getattr(video, "url", "") or "",
                        "direct_path": getattr(video, "directPath", "") or "",
                        "caption": getattr(video, "caption", "") or "",
                        "duration": getattr(video, "seconds", None)
                    })
                    attachment["preview"] = _encode_preview(getattr(video, "JPEGThumbnail", None), "jpeg")
            elif message_type == "documentMessage":
                document = getattr(msg, "documentMessage", None)
                if document:
                    attachment.update({
                        "mime_type": getattr(document, "mimetype", "") or "",
                        "url": getattr(document, "URL", "") or getattr(document, "url", "") or "",
                        "direct_path": getattr(document, "directPath", "") or "",
                        "file_name": getattr(document, "fileName", "") or getattr(document, "title", "") or "",
                        "caption": getattr(document, "caption", "") or ""
                    })
                    attachment["preview"] = _encode_preview(getattr(document, "JPEGThumbnail", None), "jpeg")
            elif message_type == "audioMessage":
                audio = getattr(msg, "audioMessage", None)
                if audio:
                    attachment.update({
                        "mime_type": getattr(audio, "mimetype", "") or "",
                        "url": getattr(audio, "URL", "") or getattr(audio, "url", "") or "",
                        "direct_path": getattr(audio, "directPath", "") or "",
                        "duration": getattr(audio, "seconds", None)
                    })
            elif message_type == "stickerMessage":
                sticker = getattr(msg, "stickerMessage", None)
                if sticker:
                    attachment.update({
                        "mime_type": getattr(sticker, "mimetype", "") or "",
                        "url": getattr(sticker, "URL", "") or getattr(sticker, "url", "") or "",
                        "direct_path": getattr(sticker, "directPath", "") or "",
                        "file_name": "sticker"
                    })
                    attachment["preview"] = _encode_preview(getattr(sticker, "pngThumbnail", None), "png")
        except Exception as e:
            print(f"[Manager] Error extracting attachment properties: {e}")

        return attachment

    def handle_incoming_message(self, account_id: str, message_ev: Any):
        client = self.clients.get(account_id)
        if not client:
            return
            
        try:
            info = getattr(message_ev, 'Info', None) or getattr(message_ev, 'info', None) or message_ev
            if not info:
                return
            
            # Extract JIDs
            ms = getattr(info, 'MessageSource', None)
            sender = "Unknown"
            chat_jid = "Unknown"
            
            if ms:
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

            # Normalize sender / chat JID
            if sender == "Unknown" or not "@" in sender:
                for attr in ['Sender', 'sender', 'Source', 'source']:
                    val = getattr(info, attr, None)
                    if val:
                        sender = str(val)
                        break

            import re
            for jid_val in [sender, chat_jid]:
                if "User:" in jid_val and "@" not in jid_val:
                    u = re.search(r'User:\s*"([^"]+)"', jid_val)
                    s = re.search(r'Server:\s*"([^"]+)"', jid_val)
                    if u and s:
                        if jid_val == sender:
                            sender = f"{u.group(1)}@{s.group(2)}"
                        else:
                            chat_jid = f"{u.group(1)}@{s.group(2)}"

            if chat_jid == "Unknown" and sender != "Unknown":
                chat_jid = sender

            # Pushname
            raw_push = getattr(info, 'Pushname', "") or getattr(info, 'PushName', "") or ""
            push_name = raw_push.strip() if is_valid_name(raw_push) else ""
            
            # Message body and attachments: Look on message_ev FIRST!
            msg = getattr(message_ev, 'Message', None) or getattr(message_ev, 'message', None) or getattr(message_ev, 'Raw', None)
            if not msg:
                for attr in ('Message', 'message', 'Raw', 'raw'):
                    try:
                        candidate = getattr(info, attr, None)
                    except Exception:
                        candidate = None
                    if candidate:
                        msg = candidate
                        break

            # Fallback: check if info or message_ev itself has message attributes
            if not msg:
                for obj in (message_ev, info):
                    if obj and (hasattr(obj, 'WhichOneof') or any(hasattr(obj, a) for a in ('conversation', 'extendedTextMessage', 'imageMessage', 'videoMessage', 'documentMessage', 'stickerMessage'))):
                        msg = obj
                        break

            # Check for Revoke or other protocol messages
            if msg and hasattr(msg, 'protocolMessage') and msg.protocolMessage:
                pm = msg.protocolMessage
                is_revoke = False
                try:
                    if getattr(pm, 'type', None) == 0 or str(getattr(pm, 'type', '')).upper() == 'REVOKE':
                        is_revoke = True
                except:
                    pass

                if is_revoke:
                    key = getattr(pm, 'key', None)
                    target_id = getattr(key, 'ID', '') or getattr(key, 'id', '')
                    remote_jid = getattr(key, 'remoteJID', '') or chat_jid
                    if target_id:
                        print(f"[Anti-Delete][{account_id}] Detected message revoke for ID {target_id} in {remote_jid}")
                        self.handle_message_revoke(account_id, remote_jid, target_id, sender)
                        return
                else:
                    # Non-chat protocol message (e.g. HISTORY_SYNC_NOTIFICATION, PEER_BROADCAST) — do not save as chat
                    return

            attachment = self._extract_attachment(msg)
            text = ""
            if msg:
                if hasattr(msg, 'conversation') and msg.conversation:
                    text = msg.conversation
                elif hasattr(msg, 'extendedTextMessage') and msg.extendedTextMessage:
                    text = getattr(msg.extendedTextMessage, 'text', "")
                elif hasattr(msg, 'documentWithCaptionMessage') and msg.documentWithCaptionMessage:
                    dm = getattr(msg.documentWithCaptionMessage, 'message', None)
                    if dm and hasattr(dm, 'documentMessage'):
                        text = getattr(dm.documentMessage, 'caption', "")

            if not text:
                if attachment and attachment.get("caption"):
                    text = attachment.get("caption", "")
                elif attachment:
                    att_type = attachment.get("type", "attachment")
                    text = "[" + att_type[:1].upper() + att_type[1:] + "]"
                else:
                    text = ""

            if not text and not attachment:
                return

            print(f"[Manager][{account_id}] Live message from {sender} ({push_name}) in {chat_jid}: '{text[:45]}'")

            # Check if outgoing (IsFromMe from WhatsApp protobuf is canonical)
            own_info = self.profile_info.get(account_id, {})
            own_jid = own_info.get("jid", "")
            own_phone = own_info.get("phone", "")
            is_outgoing = False

            if ms and getattr(ms, "IsFromMe", False):
                is_outgoing = True
            elif getattr(info, "IsFromMe", False) or getattr(message_ev, "IsFromMe", False):
                is_outgoing = True
            elif own_jid and (sender == own_jid or (sender.split("@")[0] == own_jid.split("@")[0])):
                is_outgoing = True
            elif own_phone and (sender.startswith(own_phone) or (sender.split("@")[0] == own_phone)):
                is_outgoing = True

            if is_outgoing:
                push_name = "Me"
            elif not push_name:
                # Look up saved contact name
                sender_u = sender.split("@")[0] if "@" in sender else sender
                lid_m = self.load_lid_map(account_id)
                pn = lid_m.get("lid_to_pn", {}).get(sender_u, "") or (sender_u if sender_u.isdigit() and len(sender_u) <= 15 else "")
                cached_contacts = self.get_contacts(account_id)
                for c in cached_contacts:
                    if is_valid_name(c.get("name")) and (c["jid"] == sender or (pn and c.get("phone_number") == pn)):
                        push_name = c["name"]
                        break

            # Create message structure
            # Neonize Timestamp may be in milliseconds — normalize to seconds
            raw_ts = int(getattr(info, 'Timestamp', int(time.time())))
            ts_seconds = raw_ts // 1000 if raw_ts > 1_000_000_000_000 else raw_ts

            msg_data = {
                "id": str(getattr(info, 'ID', str(time.time()))),
                "sender": sender,
                "sender_name": push_name,
                "chat_jid": chat_jid,
                "body": text,
                "timestamp": ts_seconds,
                "is_outgoing": is_outgoing
            }
            if attachment:
                msg_data["attachment"] = attachment
            
            # Save to message history
            self.save_message(account_id, chat_jid, msg_data)
            
            # Save contact
            if not is_outgoing:
                is_group = "@g.us" in chat_jid
                self.save_contact(account_id, chat_jid, push_name, is_group=is_group)

            # Update contacts cache so sidebar has latest message & timestamp
            self.merge_contacts_groups(account_id)
            
            # Resolve alt_jid if LID or Phone
            alt_jid = ""
            clean_u = chat_jid.split("@")[0] if "@" in chat_jid else chat_jid
            lid_map = self.load_lid_map(account_id)
            if "@lid" in chat_jid or clean_u in lid_map.get("lid_to_pn", {}):
                pn = lid_map.get("lid_to_pn", {}).get(clean_u)
                if pn:
                    alt_jid = f"{pn}@s.whatsapp.net"
            elif "@s.whatsapp.net" in chat_jid or clean_u in lid_map.get("pn_to_lid", {}):
                lid = lid_map.get("pn_to_lid", {}).get(clean_u)
                if lid:
                    alt_jid = f"{lid}@lid"

            # Broadcast to web app UI
            self.broadcast("message", account_id, {
                "chat_jid": chat_jid,
                "alt_jid": alt_jid,
                "message": msg_data
            })
            self.broadcast("contacts_updated", account_id, {})

            # Asynchronously download media (image, audio, video, document)
            if attachment and client:
                att_type = attachment.get("type", "attachment")
                self.download_media_async(account_id, client, msg, msg_data["id"], att_type, chat_jid)

            # Trigger external webhooks
            try:
                from api_service import dispatch_webhook_event
                dispatch_webhook_event("message_received", account_id, msg_data)
            except Exception:
                pass
            
            # Safety & Moderation Inspection (Keyword + Gemini AI)
            if text and not text.startswith("["):
                self.monitor.inspect_message(
                    account_id=account_id,
                    chat_jid=chat_jid,
                    sender=sender,
                    sender_name=push_name,
                    body=text,
                    is_outgoing=is_outgoing,
                    on_flagged_callback=lambda acc_id, inc: self.broadcast("security_alert", acc_id, inc)
                )

            print(f"[Manager][{account_id}] Msg: {push_name} -> {chat_jid}: {text[:40]}")
        except Exception as err:
            print(f"[Manager][{account_id}] Error parsing message: {err}")
            try:
                # Attempt to dump useful debug info about the protobuf message
                print(f"[Manager][{account_id}] message_ev type: {type(message_ev)}")
                # Print raw repr
                try:
                    print(f"[Manager][{account_id}] message_ev repr: {message_ev}")
                except Exception:
                    pass

                # If protobuf object supports ListFields(), enumerate populated fields
                lf = getattr(message_ev, 'ListFields', None)
                if callable(lf):
                    pairs = message_ev.ListFields()
                    print(f"[Manager][{account_id}] ListFields count: {len(pairs)}")
                    for fd, val in pairs:
                        try:
                            print(f"[Manager][{account_id}] field: {fd.name} -> {val}")
                        except Exception:
                            print(f"[Manager][{account_id}] field: {fd.name} -> (unprintable)")
                else:
                    # Fallback: try attributes
                    attrs = [a for a in dir(message_ev) if not a.startswith('_')][:50]
                    print(f"[Manager][{account_id}] message_ev attrs sample: {attrs}")
            except Exception as dump_err:
                print(f"[Manager][{account_id}] Failed to dump message_ev: {dump_err}")

    def save_message(self, account_id: str, chat_jid: str, msg_data: Dict[str, Any]):
        HISTORY_FILE = f"accounts/history_{account_id}.json"
        with _lock:
            history = {}
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except:
                    pass
            
            if chat_jid not in history:
                history[chat_jid] = []
                
            history[chat_jid].append(msg_data)
            history[chat_jid] = history[chat_jid][-150:] # Limit history per contact to 150 messages
            
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2)
            except Exception as e:
                print(f"[Manager] Error saving history: {e}")

    def save_contact(self, account_id: str, jid: str, name: str, is_group: bool = False, phone_number: str = ""):
        CONTACTS_FILE = f"accounts/contacts_{account_id}.json"
        with _lock:
            contacts = []
            if os.path.exists(CONTACTS_FILE):
                try:
                    with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                        contacts = json.load(f)
                except:
                    pass
            
            clean_name = name.strip() if name and is_valid_name(name) else ""
            if not phone_number:
                lid_map = self.load_lid_map(account_id)
                clean_u = jid.split("@")[0] if "@" in jid else jid
                phone_number = lid_map.get("lid_to_pn", {}).get(clean_u, "") or (clean_u if clean_u.isdigit() and len(clean_u) <= 15 and not "@lid" in jid else "")

            # Update or insert
            found = False
            for c in contacts:
                if c["jid"] == jid:
                    if clean_name:
                        c["name"] = clean_name
                    elif not is_valid_name(c.get("name")):
                        c["name"] = ""
                    if phone_number and not c.get("phone_number"):
                        c["phone_number"] = phone_number
                    c["timestamp"] = int(time.time())
                    found = True
                    break
            
            if not found:
                contacts.append({
                    "jid": jid,
                    "name": clean_name,
                    "phone_number": phone_number,
                    "is_group": is_group,
                    "timestamp": int(time.time())
                })
                
            contacts.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            try:
                with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(contacts, f, indent=2)
            except Exception as e:
                print(f"[Manager] Error saving contact: {e}")

    def merge_contacts_groups(self, account_id: str, extra_contacts: List[Dict[str, Any]] = None):
        """Merges SQLite contacts, joined groups, and history chats into contacts list with rich previews."""
        CONTACTS_FILE = f"accounts/contacts_{account_id}.json"
        GROUPS_FILE = f"accounts/groups_{account_id}.json"
        HISTORY_FILE = f"accounts/history_{account_id}.json"
        
        contacts_map = {}

        # 1. Existing contacts in file
        if os.path.exists(CONTACTS_FILE):
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                    for c in json.load(f):
                        contacts_map[c["jid"]] = c
            except:
                pass

        # 2. Database contacts (all WhatsApp phone contacts)
        db_contacts = extra_contacts or self.load_contacts_from_db(account_id)
        for c in db_contacts:
            jid = c["jid"]
            if jid not in contacts_map:
                contacts_map[jid] = c
            else:
                if c.get("name") and is_valid_name(c["name"]) and not is_valid_name(contacts_map[jid].get("name")):
                    contacts_map[jid]["name"] = c["name"]
                if c.get("phone_number") and not contacts_map[jid].get("phone_number"):
                    contacts_map[jid]["phone_number"] = c["phone_number"]

        # 3. Joined Groups
        if os.path.exists(GROUPS_FILE):
            try:
                with open(GROUPS_FILE, "r", encoding="utf-8") as f:
                    for g in json.load(f):
                        jid = g["jid"]
                        g_name = g.get("name", "") if is_valid_name(g.get("name")) else ""
                        if jid not in contacts_map:
                            contacts_map[jid] = {
                                "jid": jid,
                                "name": g_name,
                                "is_group": True,
                                "timestamp": 0
                            }
                        else:
                            contacts_map[jid]["is_group"] = True
                            if g_name:
                                contacts_map[jid]["name"] = g_name
            except:
                pass

        # 4. Chat History: Extract last message snippet and active timestamps
        lid_map = self.load_lid_map(account_id)
        lid_to_pn = lid_map.get("lid_to_pn", {})
        pn_to_lid = lid_map.get("pn_to_lid", {})

        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    for chat_jid, msgs in history.items():
                        if not msgs or chat_jid == "status@broadcast":
                            continue
                        last_m = msgs[-1]
                        last_ts = last_m.get("timestamp", 0)

                        # Determine snippet text & icon
                        if last_m.get("is_deleted"):
                            last_body = "🚫 This message was deleted"
                        elif last_m.get("attachment"):
                            atype = last_m["attachment"].get("type", "attachment")
                            icons = {
                                "image": "📷 Photo",
                                "audio": "🎵 Voice note",
                                "video": "🎥 Video",
                                "document": "📄 Document",
                                "sticker": "✨ Sticker"
                            }
                            caption = last_m["attachment"].get("caption", "").strip()
                            last_body = icons.get(atype, f"[{atype}]") + (f" {caption}" if caption else "")
                        else:
                            last_body = last_m.get("body", "")

                        # Match with contacts_map via exact JID, LID-to-phone, or local user
                        clean_user = chat_jid.split("@")[0] if "@" in chat_jid else chat_jid
                        pn = lid_to_pn.get(clean_user, "") or (clean_user if clean_user.isdigit() and len(clean_user) <= 15 and not "@lid" in chat_jid else "")

                        target_key = None
                        if chat_jid in contacts_map:
                            target_key = chat_jid
                        elif clean_user in lid_to_pn:
                            p_num = lid_to_pn[clean_user]
                            for alt in [f"{p_num}@s.whatsapp.net", f"{p_num}@c.us", p_num]:
                                if alt in contacts_map:
                                    target_key = alt
                                    break
                        elif clean_user in pn_to_lid:
                            lid = pn_to_lid[clean_user]
                            if f"{lid}@lid" in contacts_map:
                                target_key = f"{lid}@lid"

                        if not target_key:
                            for c_k in contacts_map.keys():
                                if c_k.split("@")[0] == clean_user:
                                    target_key = c_k
                                    break

                        # Extract any valid human sender_name from recent history messages
                        hist_sender_name = ""
                        for m in reversed(msgs):
                            s_name = m.get("sender_name")
                            if is_valid_name(s_name) and s_name != "Me":
                                hist_sender_name = s_name.strip()
                                break

                        is_group = chat_jid.endswith("@g.us")
                        if target_key:
                            existing = contacts_map[target_key]
                            existing["timestamp"] = max(existing.get("timestamp", 0), last_ts)
                            existing["last_message"] = last_body
                            if pn and not existing.get("phone_number"):
                                existing["phone_number"] = pn
                            # Update name if current name is invalid or missing
                            if not is_valid_name(existing.get("name")):
                                if hist_sender_name:
                                    existing["name"] = hist_sender_name
                                else:
                                    existing["name"] = ""
                            if target_key != chat_jid:
                                existing["alt_jid"] = chat_jid
                        else:
                            c_name = hist_sender_name if not is_group else ""
                            contacts_map[chat_jid] = {
                                "jid": chat_jid,
                                "name": c_name,
                                "phone_number": pn,
                                "is_group": is_group,
                                "timestamp": last_ts,
                                "last_message": last_body
                            }
            except Exception as e:
                print(f"[Manager] Error in merge_contacts_groups: {e}")

        with _lock:
            # Active chats with messages appear first (sorted by newest message timestamp)
            active_chats = [c for c in contacts_map.values() if c.get("timestamp", 0) > 0 and c.get("jid") != "status@broadcast"]
            inactive_chats = [c for c in contacts_map.values() if c.get("timestamp", 0) == 0 and c.get("jid") != "status@broadcast"]

            # Filter out inactive duplicate entries if an active chat already exists for that contact
            active_phones = {c.get("phone_number") for c in active_chats if c.get("phone_number")}
            active_clean_users = {c["jid"].split("@")[0] for c in active_chats}

            deduped_inactive = []
            for c in inactive_chats:
                pn = c.get("phone_number")
                cu = c["jid"].split("@")[0]
                if pn and pn in active_phones:
                    continue
                if cu in active_clean_users:
                    continue
                deduped_inactive.append(c)

            active_chats.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            deduped_inactive.sort(key=lambda x: str(x.get("name", "")).lower())

            merged = active_chats + deduped_inactive
            try:
                with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(merged, f, indent=2)
            except Exception as e:
                print(f"[Manager] Error writing merged contacts: {e}")

    def load_lid_map(self, account_id: str) -> Dict[str, Dict[str, str]]:
        """Reads whatsmeow_lid_map from SQLite session database for two-way LID <-> Phone translation."""
        if hasattr(self, 'lid_maps') and account_id in self.lid_maps:
            return self.lid_maps[account_id]
        
        db_path = f"accounts/{account_id}.db"
        lid_to_pn = {}
        pn_to_lid = {}
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whatsmeow_lid_map';")
                if cursor.fetchone():
                    cursor.execute("SELECT lid, pn FROM whatsmeow_lid_map;")
                    for r in cursor.fetchall():
                        if len(r) >= 2 and r[0] and r[1]:
                            lid_str = str(r[0]).strip()
                            pn_str = str(r[1]).strip()
                            lid_to_pn[lid_str] = pn_str
                            pn_to_lid[pn_str] = lid_str
                conn.close()
            except Exception as e:
                print(f"[Manager] Error loading LID map for {account_id}: {e}")
        
        result = {"lid_to_pn": lid_to_pn, "pn_to_lid": pn_to_lid}
        if not hasattr(self, 'lid_maps'):
            self.lid_maps = {}
        self.lid_maps[account_id] = result
        return result

    def get_contacts(self, account_id: str) -> List[Dict[str, Any]]:
        CONTACTS_FILE = f"accounts/contacts_{account_id}.json"
        
        # If contacts file is empty or only has groups, refresh from DB
        if not os.path.exists(CONTACTS_FILE):
            self.merge_contacts_groups(account_id)
        else:
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if len(cached) < 20 or all(c.get("is_group") for c in cached):
                        self.merge_contacts_groups(account_id)
            except:
                self.merge_contacts_groups(account_id)

        contacts = []
        if os.path.exists(CONTACTS_FILE):
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                    contacts = json.load(f)
            except:
                contacts = []

        return contacts

    def _find_alternate_chat_key(self, history: Dict[str, Any], chat_jid: str) -> Optional[str]:
        if not chat_jid or chat_jid in history:
            return None

        if "@s.whatsapp.net" in chat_jid:
            alt = chat_jid.replace("@s.whatsapp.net", "@lid")
            if alt in history:
                return alt
        elif "@lid" in chat_jid:
            alt = chat_jid.replace("@lid", "@s.whatsapp.net")
            if alt in history:
                return alt

        user = chat_jid.split("@")[0] if "@" in chat_jid else chat_jid
        for key in history.keys():
            if key.split("@")[0] == user:
                return key
        return None

    def get_messages(self, account_id: str, chat_jid: str) -> List[Dict[str, Any]]:
        HISTORY_FILE = f"accounts/history_{account_id}.json"
        if not os.path.exists(HISTORY_FILE):
            return []

        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            return []

        if not history or not chat_jid:
            return []

        matching_keys = set()
        if chat_jid in history:
            matching_keys.add(chat_jid)

        lid_map = self.load_lid_map(account_id)
        lid_to_pn = lid_map.get("lid_to_pn", {})
        pn_to_lid = lid_map.get("pn_to_lid", {})

        clean_user = chat_jid.split("@")[0] if "@" in chat_jid else chat_jid
        clean_user_digits = "".join(filter(str.isdigit, clean_user))

        # 1. If chat_jid is @lid, check mapped phone number
        if "@lid" in chat_jid or clean_user in lid_to_pn:
            pn = lid_to_pn.get(clean_user)
            if pn:
                for k in [f"{pn}@s.whatsapp.net", f"{pn}@c.us", pn]:
                    if k in history:
                        matching_keys.add(k)

        # 2. If chat_jid is phone (@s.whatsapp.net or digits), check mapped LID
        if "@s.whatsapp.net" in chat_jid or clean_user in pn_to_lid or clean_user_digits in pn_to_lid:
            lid = pn_to_lid.get(clean_user) or pn_to_lid.get(clean_user_digits)
            if lid:
                for k in [f"{lid}@lid", lid]:
                    if k in history:
                        matching_keys.add(k)

        # 3. Fallback: match by local user part or alternate domains
        if not matching_keys:
            alt = self._find_alternate_chat_key(history, chat_jid)
            if alt:
                matching_keys.add(alt)

        for k in history.keys():
            k_user = k.split("@")[0] if "@" in k else k
            if k_user == clean_user:
                matching_keys.add(k)

        # Gather messages from all matching keys & deduplicate
        seen_ids = set()
        messages = []
        for k in matching_keys:
            for m in history.get(k, []):
                mid = m.get("id")
                if mid and mid in seen_ids:
                    continue
                if mid:
                    seen_ids.add(mid)
                messages.append(m)

        # Auto-heal outgoing status if message was sent by this account
        own_info = self.profile_info.get(account_id, {})
        own_jid = own_info.get("jid", "")
        own_phone = own_info.get("phone", "")
        for m in messages:
            s = str(m.get("sender", ""))
            sn = str(m.get("sender_name", ""))
            if not m.get("is_outgoing"):
                if sn == "Me" or str(m.get("id", "")).startswith("out_"):
                    m["is_outgoing"] = True
                elif own_jid and (s == own_jid or s.split("@")[0] == own_jid.split("@")[0]):
                    m["is_outgoing"] = True
                elif own_phone and (s.startswith(own_phone) or s.split("@")[0] == own_phone):
                    m["is_outgoing"] = True

        # Sort chronologically
        messages.sort(key=lambda x: x.get("timestamp", 0))
        return messages

    def import_ecourt_history(self, account_id: str, ecourt_history_path: str):
        """
        Imports the old eCourt whatsapp_history.json (flat list format) into
        the per-account history file (dict keyed by chat_jid).
        Skips duplicates by checking message ID.
        """
        if not os.path.exists(ecourt_history_path):
            print(f"[Manager] eCourt history file not found: {ecourt_history_path}")
            return 0
        
        try:
            with open(ecourt_history_path, 'r', encoding='utf-8') as f:
                old_history = json.load(f)
        except Exception as e:
            print(f"[Manager] Error reading eCourt history: {e}")
            return 0

        if not isinstance(old_history, list):
            print("[Manager] eCourt history is not a list, skipping.")
            return 0

        HISTORY_FILE = f"accounts/history_{account_id}.json"
        with _lock:
            history = {}
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    pass

            imported = 0
            for msg in old_history:
                # Determine chat JID (group or direct)
                group_jid = msg.get('group_jid')
                sender_jid = str(msg.get('sender_jid', ''))
                chat_jid = group_jid if group_jid else sender_jid

                if not chat_jid or chat_jid == 'None':
                    continue

                is_ai = msg.get('is_ai', False)
                body = str(msg.get('body', ''))
                sender_name = str(msg.get('sender_name', sender_jid.split('@')[0]))

                # Normalize timestamp to seconds
                raw_ts = int(msg.get('timestamp', 0))
                ts_seconds = raw_ts // 1000 if raw_ts > 1_000_000_000_000 else raw_ts

                msg_data = {
                    "id": f"ecourt_{imported}_{ts_seconds}",
                    "sender": sender_jid,
                    "sender_name": "Me" if is_ai else sender_name,
                    "chat_jid": chat_jid,
                    "body": body,
                    "timestamp": ts_seconds,
                    "is_outgoing": is_ai
                }

                if chat_jid not in history:
                    history[chat_jid] = []

                history[chat_jid].append(msg_data)
                imported += 1

            # Trim each chat to 150 msgs
            for cjid in history:
                history[cjid] = history[cjid][-150:]

            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=2)
                print(f"[Manager] Imported {imported} messages from eCourt history.")
            except Exception as e:
                print(f"[Manager] Error writing history: {e}")
            
            return imported

    def send_whatsapp_message(self, account_id: str, target: str, body: str) -> bool:
        client = self.clients.get(account_id)
        if not client or self.statuses.get(account_id) != "Connected":
            print(f"[Manager] Account {account_id} not connected or client missing.")
            return False
            
        try:
            target = target.strip()
            # Parse JID
            if '@' in target:
                from neonize.utils.jid import JID
                user, server = target.split('@')
                jid = JID(User=user, Server=server, RawAgent=0, Device=0, Integrator=0)
            else:
                clean_phone = target.replace('+', '').replace(' ', '')
                jid = build_jid(clean_phone)
                
            # Send message
            client.send_message(jid, body)
            
            # Save outgoing message in local history
            own_info = self.profile_info.get(account_id, {})
            own_jid = own_info.get("jid", "Me")
            
            # Build clean target_str before saving
            target_str = f"{jid.User}@{jid.Server}" if hasattr(jid, 'User') else str(jid)

            msg_data = {
                "id": f"out_{int(time.time() * 1000)}",
                "sender": own_jid,
                "sender_name": "Me",
                "chat_jid": target_str,
                "body": body,
                "timestamp": int(time.time()),
                "is_outgoing": True
            }
            
            self.save_message(account_id, target_str, msg_data)
            
            # Save target to contacts
            is_group = "@g.us" in target_str
            self.save_contact(account_id, target_str, target_str.split('@')[0], is_group=is_group)
            
            # Resolve alt_jid
            alt_jid = ""
            clean_t = target_str.split("@")[0] if "@" in target_str else target_str
            lid_map = self.load_lid_map(account_id)
            if "@lid" in target_str or clean_t in lid_map.get("lid_to_pn", {}):
                pn = lid_map.get("lid_to_pn", {}).get(clean_t)
                if pn:
                    alt_jid = f"{pn}@s.whatsapp.net"
            elif "@s.whatsapp.net" in target_str or clean_t in lid_map.get("pn_to_lid", {}):
                lid = lid_map.get("pn_to_lid", {}).get(clean_t)
                if lid:
                    alt_jid = f"{lid}@lid"

            # Broadcast outgoing message to UI
            self.broadcast("message", account_id, {
                "chat_jid": target_str,
                "alt_jid": alt_jid,
                "message": msg_data
            })

            # Inspect outgoing message for safety (Keyword + Gemini AI)
            self.monitor.inspect_message(
                account_id=account_id,
                chat_jid=target_str,
                sender=own_jid,
                sender_name="Me",
                body=body,
                is_outgoing=True,
                on_flagged_callback=lambda acc_id, inc: self.broadcast("security_alert", acc_id, inc)
            )
            
            return True
        except Exception as e:
            print(f"[Manager] Error sending message: {e}")
            return False

    def disconnect_account(self, account_id: str) -> bool:
        """Logs out / disconnects the specified account session without deleting credentials."""
        return self.stop_account(account_id)

    def reconnect_account(self, account_id: str) -> bool:
        """Logs in / reconnects the specified account."""
        self.stop_account(account_id)
        self.statuses[account_id] = "Connecting"
        self.broadcast("status", account_id, {"status": "Connecting"})
        return self.start_account(account_id)

    def get_account_settings(self, account_id: str) -> Dict[str, Any]:
        """Fetches per-account settings including theme, keyword rules, and Gemini AI config."""
        return self.monitor.get_account_settings(account_id)

    def save_account_settings(self, account_id: str, settings: Dict[str, Any]) -> bool:
        """Saves per-account settings."""
        return self.monitor.save_account_settings(account_id, settings)

    def get_audit_logs(self, account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns safety violation logs for this account."""
        return self.monitor.get_audit_logs(account_id, limit)

    def clear_audit_logs(self, account_id: str) -> bool:
        """Clears safety violation logs for this account."""
        return self.monitor.clear_audit_logs(account_id)

