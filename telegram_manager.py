"""
ParentGuard - Telegram Manager (Telethon Client Engine)
Handles:
1. Multi-account Telegram sessions with Phone + OTP Code verification (+ 2FA password support).
2. Real-time message streaming, listening for new messages, parent content safety scanning.
3. Chat list (dialogs) and message history fetching and sending.
4. Session persistence in accounts/ directory.
"""

import os
import json
import time
import asyncio
import threading
from typing import Dict, List, Any, Optional
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

# Default Telegram API credentials (official client dev ID/Hash, customizable via ENV)
DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"

class TelegramManager:
    def __init__(self, parent_manager=None):
        self.parent_manager = parent_manager
        self.api_id = int(os.getenv("TELEGRAM_API_ID", DEFAULT_API_ID))
        self.api_hash = os.getenv("TELEGRAM_API_HASH", DEFAULT_API_HASH)
        
        # Dedicated background asyncio event loop for Telethon
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True, name="TelegramEventLoop")
        self.loop_thread.start()
        
        # Active clients: account_id -> TelegramClient
        self.clients: Dict[str, TelegramClient] = {}
        # Pending login requests: account_id -> {"phone": ..., "phone_code_hash": ..., "client": ...}
        self.pending_logins: Dict[str, Dict[str, Any]] = {}
        self.statuses: Dict[str, str] = {}
        self.profile_info: Dict[str, Dict[str, Any]] = {}

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _run_coro(self, coro, timeout=30):
        """Safely executes an async coroutine inside the background asyncio event loop."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def _get_session_path(self, account_id: str) -> str:
        return os.path.join("accounts", f"tg_{account_id}")

    def init_account(self, account_id: str, name: str = "", phone: str = ""):
        self.statuses[account_id] = "Disconnected"
        self.profile_info[account_id] = {
            "id": account_id,
            "platform": "telegram",
            "name": name or f"Telegram {account_id[-4:]}",
            "phone": phone,
            "username": ""
        }

    # =========================================================================
    # LOGIN WORKFLOW (PHONE NUMBER -> OTP CODE -> OPTIONAL 2FA PASSWORD)
    # =========================================================================

    def request_otp(self, account_id: str, phone: str) -> Dict[str, Any]:
        """
        Step 1 of Telegram login: Sends an OTP code to the user's phone via Telegram app or SMS.
        """
        phone = phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = "+" + phone

        session_path = self._get_session_path(account_id)
        
        async def _send():
            client = TelegramClient(session_path, self.api_id, self.api_hash, loop=self.loop)
            await client.connect()
            
            # Check if session is already authorized
            if await client.is_user_authorized():
                me = await client.get_me()
                self.clients[account_id] = client
                self.statuses[account_id] = "Connected"
                self._setup_event_listeners(account_id, client)
                
                name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or phone
                self.profile_info[account_id] = {
                    "id": account_id,
                    "platform": "telegram",
                    "name": name,
                    "phone": me.phone or phone,
                    "username": me.username or ""
                }
                return {"success": True, "already_authorized": True, "name": name, "phone": phone}

            sent = await client.send_code_request(phone)
            self.pending_logins[account_id] = {
                "client": client,
                "phone": phone,
                "phone_code_hash": sent.phone_code_hash
            }
            self.statuses[account_id] = "Waiting for OTP"
            return {
                "success": True,
                "already_authorized": False,
                "phone": phone,
                "phone_code_hash": sent.phone_code_hash
            }

        try:
            res = self._run_coro(_send(), timeout=30)
            return res
        except Exception as e:
            print(f"[Telegram][{account_id}] Error requesting OTP: {e}")
            return {"success": False, "error": str(e)}

    def verify_otp(self, account_id: str, code: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Step 2 of Telegram login: Verifies the received OTP code and optional 2FA cloud password.
        """
        pending = self.pending_logins.get(account_id)
        if not pending:
            return {"success": False, "error": "No pending login session found. Please request OTP again."}

        client: TelegramClient = pending["client"]
        phone: str = pending["phone"]
        phone_code_hash: str = pending["phone_code_hash"]

        async def _verify():
            try:
                try:
                    await client.sign_in(phone=phone, code=code.strip(), phone_code_hash=phone_code_hash)
                except SessionPasswordNeededError:
                    if not password:
                        return {"success": False, "requires_2fa": True, "error": "Two-step verification password required."}
                    await client.sign_in(password=password.strip())

                if await client.is_user_authorized():
                    me = await client.get_me()
                    self.clients[account_id] = client
                    self.statuses[account_id] = "Connected"
                    self._setup_event_listeners(account_id, client)
                    
                    name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or phone
                    self.profile_info[account_id] = {
                        "id": account_id,
                        "platform": "telegram",
                        "name": name,
                        "phone": me.phone or phone,
                        "username": me.username or ""
                    }
                    
                    if account_id in self.pending_logins:
                        del self.pending_logins[account_id]

                    # Trigger initial dialogs sync
                    asyncio.create_task(self._sync_dialogs(account_id, client))

                    # Broadcast connected status
                    if self.parent_manager:
                        self.parent_manager.broadcast("status", account_id, {"status": "Connected"})
                        self.parent_manager.save_accounts()

                    return {"success": True, "name": name, "phone": phone, "username": me.username or ""}
                else:
                    return {"success": False, "error": "Authorization failed."}

            except PhoneCodeInvalidError:
                return {"success": False, "error": "The verification code entered is incorrect."}
            except PhoneCodeExpiredError:
                return {"success": False, "error": "The verification code has expired. Please request a new one."}
            except Exception as ex:
                return {"success": False, "error": str(ex)}

        try:
            res = self._run_coro(_verify(), timeout=35)
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # REALTIME EVENT LISTENERS & MESSAGE MONITORING
    # =========================================================================

    def _setup_event_listeners(self, account_id: str, client: TelegramClient):
        """Sets up Telethon NewMessage listener for real-time monitoring."""
        @client.on(events.NewMessage)
        async def on_new_message(event):
            try:
                msg = event.message
                chat = await event.get_chat()
                sender = await event.get_sender()
                
                chat_id = str(event.chat_id)
                sender_id = str(msg.sender_id or "")
                
                # Determine sender name
                sender_name = "Contact"
                if sender:
                    sender_name = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
                    if not sender_name:
                        sender_name = getattr(sender, 'username', '') or getattr(sender, 'title', '') or sender_id

                chat_name = "Chat"
                if chat:
                    chat_name = getattr(chat, 'title', None) or f"{getattr(chat, 'first_name', '') or ''} {getattr(chat, 'last_name', '') or ''}".strip() or getattr(chat, 'username', None) or chat_id

                is_outgoing = bool(msg.out)
                text = msg.text or (f"[{msg.media.__class__.__name__}]" if msg.media else "")
                ts = int(msg.date.timestamp()) if msg.date else int(time.time())

                msg_data = {
                    "id": f"tg_{msg.id}",
                    "sender": sender_id,
                    "sender_name": "Me" if is_outgoing else sender_name,
                    "text": text,
                    "timestamp": ts,
                    "is_outgoing": is_outgoing,
                    "platform": "telegram",
                    "media_type": "media" if msg.media else None
                }

                # Save to history & update contacts
                self._save_message_to_history(account_id, chat_id, msg_data)
                self._update_contact_last_message(account_id, chat_id, chat_name, msg_data, is_group=event.is_group)

                # Parental Content Safety Check
                if self.parent_manager and self.parent_manager.monitor and text:
                    direction = "outgoing" if is_outgoing else "incoming"
                    alert = self.parent_manager.monitor.check_message(
                        account_id=account_id,
                        text=text,
                        sender="Me" if is_outgoing else sender_name,
                        recipient=chat_name,
                        direction=direction,
                        timestamp=ts
                    )
                    if alert:
                        alert["platform"] = "telegram"
                        self.parent_manager.broadcast("security_alert", account_id, alert)

                # Broadcast live message to front-end SSE
                if self.parent_manager:
                    self.parent_manager.broadcast("message", account_id, {
                        "chat_jid": chat_id,
                        "chat_name": chat_name,
                        "message": msg_data,
                        "platform": "telegram"
                    })

            except Exception as e:
                print(f"[Telegram][{account_id}] Error in on_new_message: {e}")

    async def _sync_dialogs(self, account_id: str, client: TelegramClient):
        """Fetches initial dialogs (chats, contacts, groups) and stores them."""
        try:
            dialogs = await client.get_dialogs(limit=50)
            contacts = []
            for d in dialogs:
                cid = str(d.id)
                name = d.name or getattr(d.entity, 'username', '') or cid
                phone = getattr(d.entity, 'phone', '') or ""
                is_group = d.is_group or d.is_channel
                
                last_msg = None
                if d.message:
                    last_msg = {
                        "text": d.message.text or "",
                        "timestamp": int(d.message.date.timestamp()) if d.message.date else int(time.time()),
                        "sender": "Me" if d.message.out else "Contact"
                    }

                contacts.append({
                    "jid": cid,
                    "name": name,
                    "phone": phone,
                    "is_group": is_group,
                    "unread_count": d.unread_count or 0,
                    "platform": "telegram",
                    "last_message": last_msg
                })

            contacts_file = f"accounts/contacts_{account_id}.json"
            with open(contacts_file, "w", encoding="utf-8") as f:
                json.dump(contacts, f, indent=2)

            print(f"[Telegram][{account_id}] Synced {len(contacts)} dialogs.")
        except Exception as e:
            print(f"[Telegram][{account_id}] Error syncing dialogs: {e}")

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

        history[chat_id].append(msg_data)
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"[Telegram][{account_id}] Error saving history: {e}")

    def _update_contact_last_message(self, account_id: str, chat_id: str, chat_name: str, msg_data: dict, is_group: bool = False):
        contacts_file = f"accounts/contacts_{account_id}.json"
        contacts = []
        if os.path.exists(contacts_file):
            try:
                with open(contacts_file, "r", encoding="utf-8") as f:
                    contacts = json.load(f)
            except Exception:
                contacts = []

        found = False
        for c in contacts:
            if c.get("jid") == chat_id:
                c["last_message"] = {
                    "text": msg_data.get("text", ""),
                    "timestamp": msg_data.get("timestamp", int(time.time())),
                    "sender": msg_data.get("sender_name", "")
                }
                c["platform"] = "telegram"
                if not msg_data.get("is_outgoing"):
                    c["unread_count"] = c.get("unread_count", 0) + 1
                found = True
                break

        if not found:
            contacts.append({
                "jid": chat_id,
                "name": chat_name,
                "phone": "",
                "is_group": is_group,
                "unread_count": 0 if msg_data.get("is_outgoing") else 1,
                "platform": "telegram",
                "last_message": {
                    "text": msg_data.get("text", ""),
                    "timestamp": msg_data.get("timestamp", int(time.time())),
                    "sender": msg_data.get("sender_name", "")
                }
            })

        try:
            with open(contacts_file, "w", encoding="utf-8") as f:
                json.dump(contacts, f, indent=2)
        except Exception as e:
            print(f"[Telegram][{account_id}] Error saving contacts: {e}")

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
        client = self.clients.get(account_id)
        if not client:
            print(f"[Telegram][{account_id}] Cannot send: client not active")
            return False

        async def _send():
            try:
                # Target can be integer chat ID, username, or phone
                dest = target
                if target.lstrip("-").isdigit():
                    dest = int(target)
                msg = await client.send_message(dest, text)
                
                # Save outgoing message to local cache
                ts = int(msg.date.timestamp()) if msg.date else int(time.time())
                msg_data = {
                    "id": f"tg_{msg.id}",
                    "sender": "Me",
                    "sender_name": "Me",
                    "text": text,
                    "timestamp": ts,
                    "is_outgoing": True,
                    "platform": "telegram"
                }
                self._save_message_to_history(account_id, str(target), msg_data)
                self._update_contact_last_message(account_id, str(target), str(target), msg_data)
                return True
            except Exception as e:
                print(f"[Telegram][{account_id}] Error sending message to {target}: {e}")
                return False

        try:
            return self._run_coro(_send(), timeout=15)
        except Exception:
            return False

    def start_account(self, account_id: str) -> bool:
        """Starts an existing Telegram account session if session file exists."""
        session_path = self._get_session_path(account_id)
        if not os.path.exists(session_path + ".session"):
            self.statuses[account_id] = "Disconnected"
            return False

        async def _start():
            try:
                client = TelegramClient(session_path, self.api_id, self.api_hash, loop=self.loop)
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    self.clients[account_id] = client
                    self.statuses[account_id] = "Connected"
                    self._setup_event_listeners(account_id, client)
                    
                    name = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or me.phone or account_id
                    self.profile_info[account_id] = {
                        "id": account_id,
                        "platform": "telegram",
                        "name": name,
                        "phone": me.phone or "",
                        "username": me.username or ""
                    }
                    asyncio.create_task(self._sync_dialogs(account_id, client))
                    print(f"[Telegram][{account_id}] Successfully started authorized session for {name}")
                    return True
                else:
                    self.statuses[account_id] = "Disconnected"
                    return False
            except Exception as e:
                print(f"[Telegram][{account_id}] Error starting session: {e}")
                self.statuses[account_id] = "Disconnected"
                return False

        try:
            return self._run_coro(_start(), timeout=20)
        except Exception:
            return False

    def delete_account(self, account_id: str) -> bool:
        """Stops client and removes session files."""
        client = self.clients.pop(account_id, None)
        if client:
            async def _disc():
                try:
                    await client.disconnect()
                except Exception:
                    pass
            try:
                self._run_coro(_disc(), timeout=5)
            except Exception:
                pass

        self.statuses.pop(account_id, None)
        self.profile_info.pop(account_id, None)
        self.pending_logins.pop(account_id, None)

        session_base = self._get_session_path(account_id)
        for ext in [".session", ".session-journal"]:
            fpath = session_base + ext
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
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
