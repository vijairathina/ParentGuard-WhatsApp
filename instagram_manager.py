"""
ParentGuard - Instagram Manager (Instagrapi Client Engine)
Handles:
1. Multi-account Instagram sessions with Username/Password and 2FA Code verification.
2. Direct message polling & realtime monitoring, parent content safety scanning.
3. Chat list (threads) and message history fetching and sending.
4. Session persistence in accounts/ directory.
"""

import os
import json
import time
import threading
from typing import Dict, List, Any, Optional
from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    TwoFactorRequired,
    ChallengeRequired,
    FeedbackRequired,
    LoginRequired
)

class InstagramManager:
    def __init__(self, parent_manager=None):
        self.parent_manager = parent_manager
        self.clients: Dict[str, Client] = {}
        self.statuses: Dict[str, str] = {}
        self.profile_info: Dict[str, Dict[str, Any]] = {}
        self.seen_message_ids: Dict[str, set] = {}
        
        # Polling threads for watching direct messages: account_id -> threading.Event
        self.stop_events: Dict[str, threading.Event] = {}
        self.poll_threads: Dict[str, threading.Thread] = {}

    def _get_settings_path(self, account_id: str) -> str:
        return os.path.join("accounts", f"ig_{account_id}_settings.json")

    def init_account(self, account_id: str, name: str = "", username: str = ""):
        self.statuses[account_id] = "Disconnected"
        self.profile_info[account_id] = {
            "id": account_id,
            "platform": "instagram",
            "name": name or username or f"Instagram {account_id[-4:]}",
            "username": username,
            "phone": ""
        }

    # =========================================================================
    # LOGIN & 2FA WORKFLOW
    # =========================================================================

    def login(self, account_id: str, username: str, password: str) -> Dict[str, Any]:
        """Logs into Instagram using username and password."""
        username = username.strip().lstrip("@")
        cl = Client()
        cl.delay_range = [1, 3]
        settings_path = self._get_settings_path(account_id)

        try:
            cl.login(username, password)
            self._on_login_success(account_id, cl, username)
            return {"success": True, "username": username}

        except TwoFactorRequired:
            self.clients[account_id] = cl
            self.statuses[account_id] = "Waiting for 2FA"
            return {"success": False, "requires_2fa": True, "error": "Two-factor authentication code required."}

        except BadPassword:
            return {"success": False, "error": "Incorrect password. Please verify your credentials."}

        except ChallengeRequired:
            return {"success": False, "error": "Instagram security challenge required. Please log into Instagram app once."}

        except Exception as e:
            print(f"[Instagram][{account_id}] Login error: {e}")
            return {"success": False, "error": str(e)}

    def verify_2fa(self, account_id: str, code: str) -> Dict[str, Any]:
        """Submits 2FA code if account has two-factor authentication enabled."""
        cl = self.clients.get(account_id)
        if not cl:
            return {"success": False, "error": "No pending Instagram login session found. Please log in again."}

        try:
            cl.two_factor_login(code.strip())
            username = cl.username or self.profile_info.get(account_id, {}).get("username", "")
            self._on_login_success(account_id, cl, username)
            return {"success": True, "username": username}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _on_login_success(self, account_id: str, cl: Client, username: str):
        self.clients[account_id] = cl
        self.statuses[account_id] = "Connected"
        
        # Save session settings
        try:
            cl.dump_settings(self._get_settings_path(account_id))
        except Exception as e:
            print(f"[Instagram][{account_id}] Error dumping settings: {e}")

        # Fetch profile info
        display_name = username
        try:
            info = cl.user_info_by_username(username)
            if info and info.full_name:
                display_name = info.full_name
        except Exception:
            pass

        self.profile_info[account_id] = {
            "id": account_id,
            "platform": "instagram",
            "name": display_name,
            "username": username,
            "phone": ""
        }

        # Start background direct message monitoring worker
        self._start_message_watcher(account_id)

        # Notify parent manager
        if self.parent_manager:
            self.parent_manager.broadcast("status", account_id, {"status": "Connected"})
            self.parent_manager.save_accounts()

    # =========================================================================
    # REALTIME MESSAGE WATCHER & SAFETY MONITOR
    # =========================================================================

    def _start_message_watcher(self, account_id: str):
        """Starts background polling thread to watch Instagram direct messages."""
        self._stop_message_watcher(account_id)

        stop_event = threading.Event()
        self.stop_events[account_id] = stop_event

        thread = threading.Thread(
            target=self._watch_loop,
            args=(account_id, stop_event),
            daemon=True,
            name=f"InstagramWatcher-{account_id}"
        )
        self.poll_threads[account_id] = thread
        thread.start()

    def _stop_message_watcher(self, account_id: str):
        if account_id in self.stop_events:
            self.stop_events[account_id].set()
        self.stop_events.pop(account_id, None)
        self.poll_threads.pop(account_id, None)

    def _watch_loop(self, account_id: str, stop_event: threading.Event):
        """Polls Instagram inbox threads for new incoming and outgoing messages."""
        print(f"[Instagram][{account_id}] Started message monitoring worker.")
        cl = self.clients.get(account_id)
        if not cl:
            return

        if account_id not in self.seen_message_ids:
            self.seen_message_ids[account_id] = set()

        # Seed existing history IDs
        history_file = f"accounts/history_{account_id}.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    hist = json.load(f)
                    for _, msgs in hist.items():
                        for m in msgs:
                            if m.get("id"):
                                self.seen_message_ids[account_id].add(str(m.get("id")))
            except Exception:
                pass

        first_run = True
        while not stop_event.is_set():
            try:
                threads = cl.direct_threads(amount=15)
                contacts = []

                for th in threads:
                    tid = str(th.id)
                    title = th.thread_title or "Direct Message"
                    if not th.thread_title and th.users:
                        u = th.users[0]
                        title = u.full_name or u.username or tid

                    is_group = bool(th.is_group)
                    last_msg_data = None

                    # Process messages inside thread
                    if th.messages:
                        # Direct messages are ordered newest first
                        latest = th.messages[0]
                        own_user_id = str(cl.user_id) if hasattr(cl, 'user_id') else ""
                        is_out = str(latest.user_id) == own_user_id

                        last_msg_data = {
                            "text": latest.text or (f"[{latest.item_type}]" if hasattr(latest, 'item_type') else ""),
                            "timestamp": int(latest.timestamp.timestamp()) if hasattr(latest.timestamp, 'timestamp') else int(time.time()),
                            "sender": "Me" if is_out else title
                        }

                        # Check new messages
                        for m in reversed(th.messages):
                            mid = f"ig_{m.id}"
                            if mid not in self.seen_message_ids[account_id]:
                                self.seen_message_ids[account_id].add(mid)
                                
                                m_is_out = str(m.user_id) == own_user_id
                                m_text = m.text or (f"[{m.item_type}]" if hasattr(m, 'item_type') else "")
                                m_ts = int(m.timestamp.timestamp()) if hasattr(m.timestamp, 'timestamp') else int(time.time())

                                msg_obj = {
                                    "id": mid,
                                    "sender": str(m.user_id),
                                    "sender_name": "Me" if m_is_out else title,
                                    "text": m_text,
                                    "timestamp": m_ts,
                                    "is_outgoing": m_is_out,
                                    "platform": "instagram"
                                }

                                self._save_message_to_history(account_id, tid, msg_obj)

                                # If not first seeding run, check content safety and broadcast
                                if not first_run:
                                    if self.parent_manager and self.parent_manager.monitor and m_text:
                                        direction = "outgoing" if m_is_out else "incoming"
                                        alert = self.parent_manager.monitor.check_message(
                                            account_id=account_id,
                                            text=m_text,
                                            sender="Me" if m_is_out else title,
                                            recipient=title,
                                            direction=direction,
                                            timestamp=m_ts
                                        )
                                        if alert:
                                            alert["platform"] = "instagram"
                                            self.parent_manager.broadcast("security_alert", account_id, alert)

                                    if self.parent_manager:
                                        self.parent_manager.broadcast("message", account_id, {
                                            "chat_jid": tid,
                                            "chat_name": title,
                                            "message": msg_obj,
                                            "platform": "instagram"
                                        })

                    contacts.append({
                        "jid": tid,
                        "name": title,
                        "phone": "",
                        "is_group": is_group,
                        "unread_count": 0,
                        "platform": "instagram",
                        "last_message": last_msg_data
                    })

                # Save contacts cache
                contacts_file = f"accounts/contacts_{account_id}.json"
                with open(contacts_file, "w", encoding="utf-8") as f:
                    json.dump(contacts, f, indent=2)

                first_run = False

            except LoginRequired:
                print(f"[Instagram][{account_id}] Session expired, login required.")
                self.statuses[account_id] = "Disconnected"
                break
            except Exception as e:
                print(f"[Instagram][{account_id}] Polling error: {e}")

            stop_event.wait(timeout=12)

    # =========================================================================
    # HISTORY & CONTACTS CACHE
    # =========================================================================

    def _save_message_to_history(self, account_id: str, chat_id: str, msg_data: dict):
        history_file = f"accounts/history_{account_id}.json"
        history = {}
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = {}

        if chat_id not in history:
            history[chat_id] = []

        # Avoid duplicates
        for m in history[chat_id]:
            if m.get("id") == msg_data.get("id"):
                return

        history[chat_id].append(msg_data)
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"[Instagram][{account_id}] Error saving history: {e}")

    # =========================================================================
    # PUBLIC OPERATIONS (GET CONTACTS, GET MESSAGES, SEND MESSAGE, START/STOP)
    # =========================================================================

    def get_contacts(self, account_id: str) -> List[Dict[str, Any]]:
        contacts_file = f"accounts/contacts_{account_id}.json"
        if os.path.exists(contacts_file):
            try:
                with open(contacts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_messages(self, account_id: str, chat_id: str) -> List[Dict[str, Any]]:
        history_file = f"accounts/history_{account_id}.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    messages = history.get(str(chat_id), [])
                    messages.sort(key=lambda x: x.get("timestamp", 0))
                    return messages
            except Exception:
                pass
        return []

    def send_message(self, account_id: str, target: str, text: str) -> bool:
        cl = self.clients.get(account_id)
        if not cl or self.statuses.get(account_id) != "Connected":
            print(f"[Instagram][{account_id}] Cannot send: client not connected")
            return False

        try:
            # Send message to thread ID
            cl.direct_send(text, thread_ids=[target])

            ts = int(time.time())
            msg_obj = {
                "id": f"ig_out_{int(time.time()*1000)}",
                "sender": "Me",
                "sender_name": "Me",
                "text": text,
                "timestamp": ts,
                "is_outgoing": True,
                "platform": "instagram"
            }
            self._save_message_to_history(account_id, target, msg_obj)
            return True
        except Exception as e:
            print(f"[Instagram][{account_id}] Error sending direct message: {e}")
            return False

    def start_account(self, account_id: str) -> bool:
        """Restores Instagram session from settings file."""
        settings_path = self._get_settings_path(account_id)
        if not os.path.exists(settings_path):
            self.statuses[account_id] = "Disconnected"
            return False

        try:
            cl = Client()
            cl.load_settings(settings_path)
            
            # Check login
            try:
                info = cl.get_timeline_feed()
                self.clients[account_id] = cl
                self.statuses[account_id] = "Connected"
                
                username = cl.username or self.profile_info.get(account_id, {}).get("username", "")
                self.profile_info[account_id] = {
                    "id": account_id,
                    "platform": "instagram",
                    "name": username or f"Instagram {account_id[-4:]}",
                    "username": username,
                    "phone": ""
                }
                self._start_message_watcher(account_id)
                print(f"[Instagram][{account_id}] Restored session for @{username}")
                return True
            except LoginRequired:
                print(f"[Instagram][{account_id}] Saved session expired.")
                self.statuses[account_id] = "Disconnected"
                return False
        except Exception as e:
            print(f"[Instagram][{account_id}] Error restoring session: {e}")
            self.statuses[account_id] = "Disconnected"
            return False

    def delete_account(self, account_id: str) -> bool:
        """Stops watcher and deletes Instagram account files."""
        self._stop_message_watcher(account_id)
        self.clients.pop(account_id, None)
        self.statuses.pop(account_id, None)
        self.profile_info.pop(account_id, None)
        self.seen_message_ids.pop(account_id, None)

        settings_path = self._get_settings_path(account_id)
        if os.path.exists(settings_path):
            try:
                os.remove(settings_path)
            except Exception:
                pass

        for prefix in ["contacts_", "history_", "settings_", "audit_log_"]:
            fpath = f"accounts/{prefix}{account_id}.json"
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

        return True
