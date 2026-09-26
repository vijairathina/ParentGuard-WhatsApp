"""
ParentGuard WhatsApp - Content Safety & AI Moderation Engine
Supports:
1. Keyword and phrase matching (custom lists per account).
2. Google Gemini AI content moderation for illegal, harmful, harassment, or unwanted speech.
3. Incident logging with timestamps, severity levels, and reasoning.
"""

import os
import json
import time
import re
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests

# Default keywords to monitor for parental safety
DEFAULT_KEYWORDS = [
    "illegal", "drugs", "weed", "cocaine", "weapon", "gun", "knife",
    "kill", "murder", "suicide", "hurt myself", "threat", "bomb",
    "password", "credit card", "bank account", "otp", "pin number",
    "cheat", "exam leak", "gambling", "betting", "porn", "xxx", "hack"
]

DEFAULT_SETTINGS = {
    "theme": "dark",
    "monitoring": {
        "enabled": True,
        "direction": "all",  # "all", "incoming", "outgoing"
        "keywords_enabled": True,
        "keywords": DEFAULT_KEYWORDS,
        "gemini_enabled": False,
        "gemini_api_key": "",
        "gemini_model": "gemini-1.5-flash",
        "gemini_sensitivity": "moderate",  # "strict", "moderate"
        "notify_on_violation": True
    }
}

_lock = threading.Lock()

class ContentMonitor:
    def __init__(self, accounts_dir: str = "accounts"):
        self.accounts_dir = accounts_dir
        os.makedirs(self.accounts_dir, exist_ok=True)

    def get_settings_path(self, account_id: str) -> str:
        return os.path.join(self.accounts_dir, f"settings_{account_id}.json")

    def get_logs_path(self, account_id: str) -> str:
        return os.path.join(self.accounts_dir, f"audit_log_{account_id}.json")

    def get_account_settings(self, account_id: str) -> Dict[str, Any]:
        """Loads per-account settings or returns defaults."""
        path = self.get_settings_path(account_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # Merge with default settings to ensure all keys exist
                    merged = dict(DEFAULT_SETTINGS)
                    merged.update(saved)
                    if "monitoring" in saved:
                        monitoring = dict(DEFAULT_SETTINGS["monitoring"])
                        monitoring.update(saved["monitoring"])
                        merged["monitoring"] = monitoring
                    return merged
            except Exception as e:
                print(f"[Monitor] Error reading settings for {account_id}: {e}")
        return json.loads(json.dumps(DEFAULT_SETTINGS))

    def save_account_settings(self, account_id: str, settings: Dict[str, Any]) -> bool:
        """Saves per-account settings."""
        path = self.get_settings_path(account_id)
        with _lock:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2)
                return True
            except Exception as e:
                print(f"[Monitor] Error saving settings for {account_id}: {e}")
                return False

    def get_audit_logs(self, account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns flagged message incidents for an account."""
        path = self.get_logs_path(account_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    return sorted(logs, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]
            except Exception as e:
                print(f"[Monitor] Error reading logs for {account_id}: {e}")
        return []

    def append_audit_log(self, account_id: str, incident: Dict[str, Any]):
        """Records a safety incident to the account audit log."""
        path = self.get_logs_path(account_id)
        with _lock:
            logs = []
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                except Exception:
                    logs = []

            logs.append(incident)
            # Retain last 300 incidents per account
            logs = logs[-300:]

            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)
            except Exception as e:
                print(f"[Monitor] Error writing audit log for {account_id}: {e}")

    def clear_audit_logs(self, account_id: str) -> bool:
        """Clears all audit logs for an account."""
        path = self.get_logs_path(account_id)
        with _lock:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
                return True
            except Exception as e:
                print(f"[Monitor] Error clearing audit log for {account_id}: {e}")
                return False

    def inspect_message(self, account_id: str, chat_jid: str, sender: str, 
                        sender_name: str, body: str, is_outgoing: bool, 
                        on_flagged_callback=None):
        """
        Asynchronously inspects a message using both keyword matching and Gemini AI.
        Invokes on_flagged_callback(account_id, incident) if flagged.
        """
        if not body or not body.strip():
            return

        settings = self.get_account_settings(account_id)
        mon = settings.get("monitoring", {})
        if not mon.get("enabled", True):
            return

        direction_setting = mon.get("direction", "all")
        if direction_setting == "outgoing" and not is_outgoing:
            return
        if direction_setting == "incoming" and is_outgoing:
            return

        # Start inspection in background thread so WhatsApp event pipeline stays fast
        threading.Thread(
            target=self._run_inspection,
            args=(account_id, chat_jid, sender, sender_name, body, is_outgoing, settings, on_flagged_callback),
            daemon=True
        ).start()

    def _run_inspection(self, account_id: str, chat_jid: str, sender: str, 
                        sender_name: str, body: str, is_outgoing: bool, 
                        settings: Dict[str, Any], on_flagged_callback):
        mon = settings.get("monitoring", {})
        now_ts = int(time.time())
        time_str = datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d %H:%M:%S")
        direction_label = "Outgoing (Sent)" if is_outgoing else "Incoming (Received)"

        # 1. Non-AI Keyword Matching
        if mon.get("keywords_enabled", True):
            keywords = mon.get("keywords", DEFAULT_KEYWORDS)
            text_lower = body.lower()
            matched_keywords = []

            for kw in keywords:
                kw_clean = kw.strip().lower()
                if not kw_clean:
                    continue
                # Match word boundaries or substring
                pattern = r'\b' + re.escape(kw_clean) + r'\b'
                if re.search(pattern, text_lower) or kw_clean in text_lower:
                    matched_keywords.append(kw_clean)

            if matched_keywords:
                incident = {
                    "id": f"inc_kw_{now_ts}_{int(time.time()*1000)%1000}",
                    "account_id": account_id,
                    "timestamp": now_ts,
                    "datetime": time_str,
                    "chat_jid": chat_jid,
                    "sender": sender,
                    "sender_name": sender_name,
                    "is_outgoing": is_outgoing,
                    "direction": direction_label,
                    "message": body,
                    "detection_type": "Keyword Match",
                    "severity": "Medium",
                    "reason": f"Matched sensitive keywords: {', '.join(matched_keywords)}",
                    "details": {"keywords": matched_keywords}
                }
                print(f"[Monitor][Alert] Keyword match for {account_id}: {matched_keywords}")
                self.append_audit_log(account_id, incident)
                if on_flagged_callback:
                    on_flagged_callback(account_id, incident)

        # 2. Gemini AI Moderation (if enabled)
        if mon.get("gemini_enabled", False):
            api_key = mon.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                print(f"[Monitor] Gemini AI enabled but no API key provided for {account_id}")
                return

            ai_result = self._call_gemini_moderation(body, api_key, mon.get("gemini_model", "gemini-1.5-flash"))
            if ai_result and ai_result.get("flagged"):
                incident = {
                    "id": f"inc_ai_{now_ts}_{int(time.time()*1000)%1000}",
                    "account_id": account_id,
                    "timestamp": now_ts,
                    "datetime": time_str,
                    "chat_jid": chat_jid,
                    "sender": sender,
                    "sender_name": sender_name,
                    "is_outgoing": is_outgoing,
                    "direction": direction_label,
                    "message": body,
                    "detection_type": "Gemini AI Safety",
                    "severity": ai_result.get("severity", "High"),
                    "category": ai_result.get("category", "Inappropriate Content"),
                    "reason": ai_result.get("reason", "Flagged by Gemini AI Safety Guardian"),
                    "details": ai_result
                }
                print(f"[Monitor][Alert] Gemini AI flagged message for {account_id}: {ai_result.get('reason')}")
                self.append_audit_log(account_id, incident)
                if on_flagged_callback:
                    on_flagged_callback(account_id, incident)

    def _call_gemini_moderation(self, text: str, api_key: str, model: str = "gemini-1.5-flash") -> Optional[Dict[str, Any]]:
        """Calls Gemini API to moderate chat content for parental and legal safety."""
        prompt = (
            "You are an AI Safety and Parental Supervision Content Moderator. "
            "Analyze the following WhatsApp message to determine if it contains or promotes:\n"
            "- Illegal activities (substance abuse, drugs, piracy, cybercrime, fraud, scams)\n"
            "- Harassment, bullying, threats, or hate speech\n"
            "- Severe profanity, sexually explicit or inappropriate adult content\n"
            "- Dangerous behavior, violence, or self-harm\n"
            "- Unwanted disclosures (confidential passwords, bank account info, credentials)\n\n"
            "Message to analyze: \"\"\"\n"
            f"{text}\n"
            "\"\"\"\n\n"
            "Return ONLY a valid JSON object with this exact structure (no markdown formatting, no backticks):\n"
            "{\n"
            '  "flagged": true or false,\n'
            '  "severity": "Low" or "Medium" or "High",\n'
            '  "category": "Illegal Activity" or "Harassment" or "Adult Content" or "Violence" or "Sensitive Data" or "None",\n'
            '  "reason": "Brief 1-sentence reason explaining why it was flagged or why it is safe."\n'
            "}"
        )

        # Models to try (fallback to 1.5-flash or 2.0-flash if needed)
        models_to_try = [model, "gemini-1.5-flash", "gemini-2.0-flash"]
        for m in dict.fromkeys(models_to_try):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 200,
                    "responseMimeType": "application/json"
                }
            }
            try:
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_json = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        # Clean backticks if any
                        if raw_json.startswith("```"):
                            raw_json = re.sub(r"^```(?:json)?\n?", "", raw_json)
                            raw_json = re.sub(r"\n?```$", "", raw_json)
                        result = json.loads(raw_json)
                        return result
                else:
                    print(f"[Monitor] Gemini API returned {resp.status_code}: {resp.text[:120]}")
            except Exception as e:
                print(f"[Monitor] Gemini API request exception ({m}): {e}")

        return None
