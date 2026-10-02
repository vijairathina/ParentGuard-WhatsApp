"""
ParentGuard WhatsApp - Advanced Scheduled & Automated Messages Engine
Provides persistent, rule-based scheduling for:
1. Birthday Wishes (Annual by date or contact)
2. Wedding Anniversary Wishes (Annual by date)
3. Daily Routine Greetings (Good Morning, Good Afternoon, Good Night)
4. Festival & Holiday Wishes (Diwali, New Year, Pongal, Christmas, Eid, Holi)
5. Routine Check-ins & Reminders (Hydration, Health, Weekend Greetings)

Key Features:
- Persistent storage in accounts/scheduled_messages.json (retained across logouts/restarts).
- Background engine with auto-retry and queueing when WhatsApp sessions are temporarily offline.
- Dynamic variable placeholders ({name}, {date}, {time}, {day}).
- One-click sample templates catalog.
"""

import os
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

SCHEDULES_FILE = "accounts/scheduled_messages.json"
_sched_lock = threading.Lock()

# Curated pre-packaged sample templates with emojis and heartfelt messages
SAMPLE_TEMPLATES = {
    "birthday": {
        "title": "🎂 Birthday Wishes",
        "category": "birthday",
        "default_type": "annual",
        "default_time": "09:00",
        "templates": [
            {
                "id": "bday_1",
                "name": "Warm & Joyful Celebration",
                "text": "🎂 Happy Birthday, {name}! 🎉 Wishing you a magnificent year filled with boundless happiness, radiant health, and outstanding achievements! Have a wonderful celebration! 🎈✨"
            },
            {
                "id": "bday_2",
                "name": "Blessing & Endless Success",
                "text": "Happy Birthday {name}! 🌟 May your special day bring countless reasons to smile and may the year ahead be your most successful and fulfilling one yet! 🎁🎂"
            },
            {
                "id": "bday_3",
                "name": "Heartfelt & Sweet",
                "text": "Wishing you the happiest of birthdays, {name}! Hope your day is as wonderful, bright, and inspiring as you are! 🥳🎉🥂"
            }
        ]
    },
    "anniversary": {
        "title": "💍 Wedding Anniversary",
        "category": "anniversary",
        "default_type": "annual",
        "default_time": "10:00",
        "templates": [
            {
                "id": "anni_1",
                "name": "Elegant Milestone Celebration",
                "text": "💍 Happy Wedding Anniversary, {name}! Wishing you both a lifetime of enduring love, deepest joy, and wonderful adventures together! Cheers to your beautiful journey! 🥂❤️"
            },
            {
                "id": "anni_2",
                "name": "Heartfelt Love & Respect",
                "text": "Happy Anniversary, {name}! May the love, harmony, and mutual respect you share continue to grow stronger and blossom with each passing year! 💐✨"
            },
            {
                "id": "anni_3",
                "name": "Inspiring Couple Blessing",
                "text": "Warmest anniversary wishes to an inspiring couple, {name}! May your home always be blessed with laughter, prosperity, and lifelong companionship! 🥂🎉"
            }
        ]
    },
    "morning": {
        "title": "🌅 Good Morning Greeting",
        "category": "morning",
        "default_type": "daily",
        "default_time": "07:30",
        "templates": [
            {
                "id": "morn_1",
                "name": "Positive Energy & Focus",
                "text": "🌅 Good morning, {name}! Rise and shine! May your day be filled with positive energy, sharp focus, and pleasant surprises! ☀️💪"
            },
            {
                "id": "morn_2",
                "name": "Peaceful & Blessed Morning",
                "text": "Good morning, {name}! ☕ Wishing you a calm mind, joyful heart, and smooth sailing through all your tasks today! Have a blessed day ahead! 🌿✨"
            },
            {
                "id": "morn_3",
                "name": "Motivational Inspiration",
                "text": "Every morning is a clean canvas! Make today count with confidence and determination. Good morning, {name}! 🌄🎯"
            }
        ]
    },
    "afternoon": {
        "title": "☀️ Good Afternoon Greeting",
        "category": "afternoon",
        "default_type": "daily",
        "default_time": "13:30",
        "templates": [
            {
                "id": "aft_1",
                "name": "Mindful Check-in & Break",
                "text": "☀️ Good afternoon, {name}! Hope your day is progressing smoothly. Remember to take a nourishing lunch break, stay hydrated, and keep up the great momentum! 🥗🥪"
            },
            {
                "id": "aft_2",
                "name": "Refreshing Energy Boost",
                "text": "Good afternoon, {name}! Half the day is conquered—wishing you sustained energy and a refreshing second half of the day! 🌿✨"
            }
        ]
    },
    "night": {
        "title": "🌙 Good Night Greeting",
        "category": "night",
        "default_type": "daily",
        "default_time": "21:30",
        "templates": [
            {
                "id": "night_1",
                "name": "Peaceful Rest & Sweet Dreams",
                "text": "🌙 Good night, {name}! Let go of today's worries and rest well. Wishing you deep, restorative sleep and sweet dreams! See you tomorrow! 😴⭐"
            },
            {
                "id": "night_2",
                "name": "Gratitude & Recharge",
                "text": "Good night, {name}! Take time to recharge and reflect on the positive moments today. Tomorrow brings fresh possibilities! Sleep peacefully! 🌌🛏️"
            }
        ]
    },
    "festival": {
        "title": "🪔 Festivals & Holidays",
        "category": "festival",
        "default_type": "once",
        "default_time": "08:30",
        "templates": [
            {
                "id": "fest_diwali",
                "name": "Diwali / Deepavali",
                "text": "🪔 Happy Diwali, {name}! May the divine festival of lights illuminate your life with joy, good health, peace, and prosperous abundance! Wishing you and your family a safe and glittering Deepavali! 🎆✨"
            },
            {
                "id": "fest_newyear",
                "name": "New Year Celebration",
                "text": "🎉 Happy New Year, {name}! May the coming year unlock incredible new opportunities, radiant wellness, and prosperity for you and your family! Here's to a fantastic 365 days ahead! 🥳🥂"
            },
            {
                "id": "fest_pongal",
                "name": "Pongal / Makar Sankranti",
                "text": "🌾 Happy Pongal & Makar Sankranti, {name}! May the harvest festival shower your life with happiness, sweet prosperity, and success in all your endeavors! 🪁☀️"
            },
            {
                "id": "fest_christmas",
                "name": "Merry Christmas",
                "text": "🎄 Merry Christmas, {name}! May the spirit of Christmas bring peace to your home, warmth to your heart, and joyful moments to your family! 🎅⭐"
            },
            {
                "id": "fest_eid",
                "name": "Eid Mubarak",
                "text": "🌙 Eid Mubarak, {name}! Wishing you and your loved ones peace, harmony, divine blessings, and immense joy on this auspicious occasion! ✨"
            },
            {
                "id": "fest_holi",
                "name": "Holi Colors Festival",
                "text": "🎨 Happy Holi, {name}! May your life be painted with the vibrant colors of happiness, laughter, good friendship, and prosperity! Have a joyful celebration! 🌈"
            }
        ]
    },
    "reminder": {
        "title": "💧 Wellness & Routine Reminders",
        "category": "reminder",
        "default_type": "daily",
        "default_time": "11:00",
        "templates": [
            {
                "id": "rem_water",
                "name": "Hydration & Health Check",
                "text": "💧 Friendly reminder, {name}: Pause for a moment, drink a refreshing glass of water, and stretch your body! Your wellness comes first! 🏃‍♂️🌿"
            },
            {
                "id": "rem_weekend",
                "name": "Weekend Vibes & Relaxation",
                "text": "Happy Weekend, {name}! 🌴 Wishing you a relaxing, fun-filled weekend surrounded by the people you love. Enjoy and recharge! 🍹☀️"
            }
        ]
    }
}


def get_default_samples() -> List[Dict[str, Any]]:
    """Returns initial built-in sample schedules showcasing all categories."""
    cur_year = datetime.now().year
    return [
        {
            "id": "sched_sample_morning",
            "title": "🌅 Daily Good Morning Greeting",
            "category": "morning",
            "schedule_type": "daily",
            "time_of_day": "08:00",
            "account_id": "any",
            "recipients": [],
            "message_template": "🌅 Good morning, {name}! Rise and shine! May your day be filled with positive energy, sharp focus, and pleasant surprises! ☀️💪",
            "enabled": False,
            "created_at": int(time.time()),
            "last_status": "Sample Template (Add recipient & enable)"
        },
        {
            "id": "sched_sample_bday",
            "title": "🎂 Birthday Wishes (Annual)",
            "category": "birthday",
            "schedule_type": "annual",
            "annual_month": 10,
            "annual_day": 15,
            "time_of_day": "09:00",
            "account_id": "any",
            "recipients": [],
            "message_template": "🎂 Happy Birthday, {name}! 🎉 Wishing you a magnificent year filled with boundless happiness, radiant health, and outstanding achievements! Have a wonderful celebration! 🎈✨",
            "enabled": False,
            "created_at": int(time.time()),
            "last_status": "Sample Template (Set date & recipient)"
        },
        {
            "id": "sched_sample_anni",
            "title": "💍 Wedding Anniversary Wishes (Annual)",
            "category": "anniversary",
            "schedule_type": "annual",
            "annual_month": 11,
            "annual_day": 20,
            "time_of_day": "10:00",
            "account_id": "any",
            "recipients": [],
            "message_template": "💍 Happy Wedding Anniversary, {name}! Wishing you both a lifetime of enduring love, deepest joy, and wonderful adventures together! Cheers to your beautiful journey! 🥂❤️",
            "enabled": False,
            "created_at": int(time.time()),
            "last_status": "Sample Template (Set date & recipient)"
        },
        {
            "id": "sched_sample_aft",
            "title": "☀️ Afternoon Refresh & Lunch Check-in",
            "category": "afternoon",
            "schedule_type": "daily",
            "time_of_day": "13:30",
            "account_id": "any",
            "recipients": [],
            "message_template": "☀️ Good afternoon, {name}! Hope your day is going smoothly. Remember to take a nourishing lunch break, stay hydrated, and keep up the great momentum! 🥗🥪",
            "enabled": False,
            "created_at": int(time.time()),
            "last_status": "Sample Template (Add recipient & enable)"
        },
        {
            "id": "sched_sample_night",
            "title": "🌙 Good Night Peaceful Rest",
            "category": "night",
            "schedule_type": "daily",
            "time_of_day": "21:30",
            "account_id": "any",
            "recipients": [],
            "message_template": "🌙 Good night, {name}! Let go of today's worries and rest well. Wishing you deep, restorative sleep and sweet dreams! See you tomorrow! 😴⭐",
            "enabled": False,
            "created_at": int(time.time()),
            "last_status": "Sample Template (Add recipient & enable)"
        },
        {
            "id": "sched_sample_diwali",
            "title": "🪔 Diwali / Deepavali Festival Wishes",
            "category": "festival",
            "schedule_type": "once",
            "scheduled_datetime": f"{cur_year}-11-01 08:30",
            "time_of_day": "08:30",
            "account_id": "any",
            "recipients": [],
            "message_template": "🪔 Happy Diwali, {name}! May the divine festival of lights illuminate your life with joy, good health, peace, and prosperous abundance! Wishing you and your family a safe and glittering Deepavali! 🎆✨",
            "enabled": False,
            "created_at": int(time.time()),
            "last_status": "Sample Template (Pick recipient & enable)"
        }
    ]


def load_schedules() -> List[Dict[str, Any]]:
    """Loads all scheduled message configurations from disk. Seeds samples on first run."""
    if os.path.exists(SCHEDULES_FILE):
        with _sched_lock:
            try:
                with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                print(f"[Scheduler] Error reading {SCHEDULES_FILE}: {e}")

    # Seed initial samples
    defaults = get_default_samples()
    for s in defaults:
        s["next_run"] = compute_next_run(s)
    save_schedules(defaults)
    return defaults


def save_schedules(schedules: List[Dict[str, Any]]) -> bool:
    """Persists all scheduled message configurations to disk."""
    os.makedirs(os.path.dirname(SCHEDULES_FILE) or "accounts", exist_ok=True)
    with _sched_lock:
        try:
            with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
                json.dump(schedules, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Scheduler] Error saving {SCHEDULES_FILE}: {e}")
            return False


def compute_next_run(sched: Dict[str, Any]) -> Optional[int]:
    """
    Computes the upcoming Unix epoch timestamp for a schedule rule.
    Returns None if the schedule is one-time and already executed.
    """
    sched_type = sched.get("schedule_type", "once")
    time_str = sched.get("time_of_day", "09:00")
    
    try:
        hour, minute = [int(p) for p in time_str.split(":")]
    except Exception:
        hour, minute = 9, 0

    now = datetime.now()

    # 1. ONE-TIME SCHEDULE
    if sched_type == "once":
        dt_str = sched.get("scheduled_datetime")
        if not dt_str:
            return None
        try:
            # Handle format "YYYY-MM-DDTHH:MM" or "YYYY-MM-DD HH:MM"
            cleaned_str = dt_str.replace("T", " ")
            dt = datetime.strptime(cleaned_str, "%Y-%m-%d %H:%M")
            return int(dt.timestamp())
        except Exception as e:
            print(f"[Scheduler] Invalid datetime for once schedule: {e}")
            return None

    # 2. DAILY SCHEDULE
    elif sched_type == "daily":
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return int(target.timestamp())

    # 3. WEEKLY SCHEDULE
    elif sched_type == "weekly":
        # days_of_week: [0=Mon, 1=Tue, ..., 6=Sun]
        days = sched.get("days_of_week", [0])
        if not days:
            days = [0]
        
        candidates = []
        for d in days:
            days_ahead = (d - now.weekday()) % 7
            target = now + timedelta(days=days_ahead)
            target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=7)
            candidates.append(target)
        if candidates:
            return int(min(candidates).timestamp())
        return None

    # 4. ANNUAL SCHEDULE (Birthdays, Anniversaries, Annual Festivals)
    elif sched_type == "annual":
        month = int(sched.get("annual_month", 1))
        day = int(sched.get("annual_day", 1))
        
        try:
            target = now.replace(year=now.year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target = target.replace(year=now.year + 1)
            return int(target.timestamp())
        except ValueError:
            # Handle leap year Feb 29
            target = now.replace(year=now.year + 1, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            return int(target.timestamp())

    return None


def format_template_message(template: str, contact_name: str = "") -> str:
    """Renders dynamic placeholders in message content."""
    now = datetime.now()
    clean_name = contact_name.strip() if contact_name else "there"
    
    rendered = template.replace("{name}", clean_name)
    rendered = rendered.replace("{date}", now.strftime("%d %b %Y"))
    rendered = rendered.replace("{time}", now.strftime("%I:%M %p"))
    rendered = rendered.replace("{day}", now.strftime("%A"))
    return rendered


class SchedulerEngine:
    """
    Background worker that monitors scheduled messages and triggers sends
    via connected WhatsApp accounts. Even if an account is disconnected or logged out,
    schedules are retained and marked as queued until reconnect.
    """
    def __init__(self, manager: Any):
        self.manager = manager
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ParentGuard_SchedulerEngine")
        self._thread.start()
        print("[Scheduler] Scheduled messages engine started.")

    def stop(self):
        self.running = False

    def _run_loop(self):
        # Initial brief sleep to let accounts connect
        time.sleep(6)
        while self.running:
            try:
                self._check_and_dispatch_due_schedules()
            except Exception as e:
                print(f"[Scheduler] Loop error: {e}")
            time.sleep(20)  # Check every 20 seconds

    def _check_and_dispatch_due_schedules(self):
        schedules = load_schedules()
        if not schedules:
            return

        now_ts = int(time.time())
        updated = False

        for sched in schedules:
            if not sched.get("enabled", True):
                continue

            next_run = sched.get("next_run")
            if next_run is None:
                next_run = compute_next_run(sched)
                sched["next_run"] = next_run
                updated = True

            # Check if this schedule is due
            if next_run and now_ts >= next_run:
                account_id = sched.get("account_id")
                # If specific account not set, try the first connected account
                if not account_id or account_id == "any":
                    for acc_id, status in self.manager.statuses.items():
                        if status == "Connected":
                            account_id = acc_id
                            break

                is_connected = bool(account_id and self.manager.statuses.get(account_id) == "Connected")

                if not is_connected:
                    # Account currently offline / logged out: KEEP CONFIG! Mark as queued!
                    if sched.get("last_status") != "Queued (Waiting for WhatsApp session reconnect)":
                        sched["last_status"] = "Queued (Waiting for WhatsApp session reconnect)"
                        updated = True
                    continue

                # Account is Connected: Dispatch message!
                recipients = sched.get("recipients", [])
                template_text = sched.get("message_template", "")
                
                success_all = True
                delivered_count = 0

                for rec in recipients:
                    target_jid = rec.get("jid") or rec.get("phone") or ""
                    target_name = rec.get("name") or ""
                    
                    if not target_jid:
                        continue

                    rendered_body = format_template_message(template_text, target_name)
                    ok = self.manager.send_whatsapp_message(account_id, target_jid, rendered_body)
                    if ok:
                        delivered_count += 1
                        print(f"[Scheduler] Sent scheduled message to {target_name or target_jid}: {sched.get('title')}")
                    else:
                        success_all = False
                        print(f"[Scheduler] Failed sending scheduled message to {target_jid}")

                # Update schedule metadata
                sched["last_sent_at"] = now_ts
                sched["sent_count"] = sched.get("sent_count", 0) + delivered_count
                sched["last_status"] = "Sent" if success_all else "Partially Sent"
                
                # Advance or complete
                if sched.get("schedule_type") == "once":
                    sched["enabled"] = False
                    sched["next_run"] = None
                    sched["last_status"] = "Completed"
                else:
                    sched["next_run"] = compute_next_run(sched)

                updated = True

                # Broadcast live event to UI
                self.manager.broadcast("scheduled_message_sent", account_id or "", {
                    "schedule_id": sched.get("id"),
                    "title": sched.get("title"),
                    "last_sent_at": now_ts,
                    "next_run": sched.get("next_run"),
                    "status": sched.get("last_status")
                })

        if updated:
            save_schedules(schedules)
