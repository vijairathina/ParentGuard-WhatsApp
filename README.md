<p align="center">
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/WhatsApp.dark.svg" width="60" height="60" alt="WhatsApp" />
  &nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Telegram.svg" width="60" height="60" alt="Telegram" />
  &nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Instagram.svg" width="60" height="60" alt="Instagram" />
</p>

<h1 align="center">🛡️ ParentGuard - Multi-Platform Messenger Guardian</h1>

<p align="center">
  <strong>Unified Parental-Supervision & Safety Monitoring across WhatsApp, Telegram, and Instagram with Real-Time AI Content Auditing, OTP Verification, and Automated Scheduling</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://flask.palletsprojects.com/"><img src="https://img.shields.io/badge/Framework-Flask_3.x-black?logo=flask&logoColor=white" alt="Flask" /></a>
  <a href="https://aistudio.google.com/"><img src="https://img.shields.io/badge/AI-Google_Gemini-orange?logo=google&logoColor=white" alt="Gemini AI" /></a>
  <a href="https://github.com/LonamiWebs/Telethon"><img src="https://img.shields.io/badge/Telegram-Telethon_MTProto-blue?logo=telegram&logoColor=white" alt="Telethon" /></a>
  <a href="https://github.com/adw0rd/instagrapi"><img src="https://img.shields.io/badge/Instagram-Instagrapi-purple?logo=instagram&logoColor=white" alt="Instagrapi" /></a>
  <a href="https://github.com/krypton-byte/neonize"><img src="https://img.shields.io/badge/WhatsApp-Neonize_WA-brightgreen?logo=whatsapp&logoColor=white" alt="Neonize" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="License" /></a>
</p>

---

## 🌟 Overview

**ParentGuard** is a parental-control and safety-monitoring multi-account messenger client designed to supervise minor children's communication across the three most popular messaging platforms: **WhatsApp**, **Telegram**, and **Instagram Direct**.

With a single, modern **Glassmorphism Web Dashboard**, parents can monitor conversations in real time, watch for inappropriate or dangerous content using customizable keyword alerts and **Google Gemini AI**, schedule routine greetings and festival wishes, and receive instant alert notifications when suspicious activity occurs.

---

## ✨ Key Features

### 1. 🌐 Multi-Platform Live Monitoring
- **🟢 WhatsApp**:
  - Direct connection via the Neonize protocol with instant QR code scanning.
  - Full bidirectional chat history, group conversation tracking, and photo/media viewing.
- **✈️ Telegram (OTP Verification)**:
  - Frictionless connection using the child's phone number + one-time login code (OTP) received on Telegram/SMS.
  - Full support for Two-Step Cloud Verification (2FA) passwords.
  - Native MTProto protocol powered by Telethon with real-time `NewMessage` event streaming.
- **📸 Instagram Direct**:
  - Secure Instagram Direct client powered by Instagrapi.
  - Supports standard username/password login and Two-Factor Authentication (2FA) verification codes.
  - Continuous background polling and inbox thread synchronization.

### 2. 📊 Live Platform Counters & Navigation Dock
- **Top Platform Dock**: Dynamic segmented control displaying live counts of active accounts per platform:
  - `🌐 All (Total Accounts)`
  - `🟢 WhatsApp (WA Accounts)`
  - `✈️ Telegram (TG Accounts)`
  - `📸 Instagram (IG Accounts)`
- **One-Click Filtering**: Instantly filters accounts and contacts by platform with automatic UI synchronization.
- **Micro Platform Badges**: Every contact item displays a color-coded badge (`WA`, `TG`, `IG`) so guardians immediately identify where each conversation is taking place.
- **Chat Header Platform Pill**: Visual indicator (`🟢 WhatsApp`, `✈️ Telegram`, `📸 Instagram`) displayed beside the child's contact details.
- **Chat Filter Counters**: Live chat breakdown showing counts for `All`, `Chats`, and `Groups`.

### 3. 🎨 Trending Glassmorphism UI & UX
- Ultra-modern frosted glass panels with `backdrop-filter: blur(20px)` and soft 1px luminous edge highlights.
- Ambient multi-orb mesh gradient background (emerald, indigo, and cyan neon glow).
- iOS/macOS-grade pill buttons, floating glass input capsules, and glowing theme palettes (**Dark**, **Light**, **Emerald**, **Midnight OLED**, and **Guardian Shield**).

### 4. 🛡️ Parental Safety & Gemini AI Content Moderation
- **Custom Keyword Engine**: Configure restricted words (drugs, cyberbullying, weapons, harassment, passwords, adult content, etc.) per account.
- **Google Gemini AI**: Semantic analysis identifying intent, harmful context, and severity ratings (`High`, `Medium`, `Low`) with real-time reasoning explanations.
- **Real-Time Security Toasts**: Floating glass alert popups whenever a violation is detected.
- **Audit Logs & CSV Export**: Timestamped incident table with one-click export for parental records.

### 5. ⏰ Scheduled & Automated Messages
- Persistent message scheduler retained across logouts and server restarts.
- Pre-built templates for **Birthdays**, **Wedding Anniversaries**, **Daily Routine Greetings (Morning, Afternoon, Night)**, **Festivals (Diwali, New Year, Pongal, Christmas, Eid, Holi)**, and **Health Check-ins**.
- Dynamic smart variables: `{name}`, `{date}`, `{time}`, `{day}`.

---

## 🏗️ Architecture

```
                 ┌────────────────────────────────────────────────────────┐
                 │                   ParentGuard Engine                   │
                 └──────────────────────────┬─────────────────────────────┘
                                            │
           ┌────────────────────────────────┼────────────────────────────────┐
           │                                │                                │
           ▼                                ▼                                ▼
  [ WhatsApp Manager ]             [ Telegram Manager ]            [ Instagram Manager ]
   Neonize WA Protocol              Telethon MTProto API             Instagrapi Direct API
  (QR Code Authentication)         (Phone Number + OTP)             (Username / Password / 2FA)
           │                                │                                │
           └────────────────────────────────┼────────────────────────────────┘
                                            │
                                            ▼
                                  [ Content Safety Engine ]
                                  ├── Regex Keyword Monitor
                                  └── Google Gemini AI Scanner
                                            │
                                            ▼
                                  [ Unified Flask REST & SSE ]
                                            │
                                            ▼
                                  [ Glassmorphism Web UI ]
                                  ├── Live Platform Counts Dock
                                  ├── Unified Contacts & Chat Area
                                  └── Realtime Toast & Audit Logs
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- **Python 3.10+**
- **Git**

### 2. Clone the Repository
```bash
git clone https://github.com/vijairathina/ParentGuard-WhatsApp.git
cd ParentGuard-WhatsApp
```

### 3. Set Up Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` to configure your settings (optional):
```env
# Google Gemini AI (Optional - get free key from https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram MTProto (Optional - default client credentials provided)
TELEGRAM_API_ID=2040
TELEGRAM_API_HASH=b18441a1ff607e10a989891a5462e627

# Server Port
FLASK_PORT=5003
```

### 6. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://localhost:5003
```

---

## 📱 How to Connect Accounts

### 🟢 1. WhatsApp (QR Code)
1. Click the **`+`** (Add Account) button in the top left header.
2. Select the **🟢 WhatsApp (QR)** tab.
3. Open WhatsApp on the monitored phone &rarr; **Settings** &rarr; **Linked Devices** &rarr; **Link a Device**.
4. Scan the on-screen QR code. Connection will be established instantly.

### ✈️ 2. Telegram (OTP Code)
1. Click the **`+`** (Add Account) button.
2. Select the **✈️ Telegram (OTP)** tab.
3. Enter the phone number with country code (e.g., `+91 99447 70544` or `+1 234 567 8900`) and click **Send Telegram OTP Code**.
4. Enter the 5-digit verification code sent to the Telegram app or SMS.
5. If the account has Two-Step Cloud Verification enabled, enter the 2FA password.
6. Click **Verify & Connect Telegram**.

### 📸 3. Instagram Direct
1. Click the **`+`** (Add Account) button.
2. Select the **📸 Instagram** tab.
3. Enter the Instagram **Username** and **Password** and click **Connect Instagram Account**.
4. If Two-Factor Authentication is enabled, enter the 6-digit 2FA security code when prompted.
5. Direct message inbox threads and contacts will sync automatically.

---

## 🛠️ API & Webhooks (v1)

ParentGuard exposes an external REST API for home automation systems, parental dashboards, and alert webhooks:

| Endpoint | Method | Description |
|---|---|---|
| `/api/platform_counts` | `GET` | Live account, chat, and unread counts per platform |
| `/api/accounts` | `GET` | List all configured accounts, platforms, and statuses |
| `/api/accounts/add` | `POST` | Register a new WhatsApp, Telegram, or Instagram account |
| `/api/accounts/delete` | `POST` | Delete an account session and wipe stored credentials |
| `/api/telegram/send_code` | `POST` | Request an OTP code for Telegram login |
| `/api/telegram/verify_code` | `POST` | Verify Telegram OTP and 2FA password |
| `/api/instagram/login` | `POST` | Authenticate an Instagram account |
| `/api/instagram/verify_2fa` | `POST` | Submit Instagram 2FA security code |
| `/api/accounts/<id>/contacts` | `GET` | Retrieve conversations list for the specified account |
| `/api/accounts/<id>/messages` | `GET` | Fetch message history for a specific contact or thread |
| `/api/accounts/<id>/send` | `POST` | Send message via WhatsApp, Telegram, or Instagram |
| `/api/schedules` | `GET / POST` | Manage automated and scheduled messages |
| `/api/events` | `GET` | SSE stream for real-time messages and security alerts |

---

## 🔒 Privacy & Local Security

- **100% Local Storage**: All chat histories, session tokens, and incident logs are stored on your local machine under the `accounts/` directory.
- **No Cloud Tracking**: No message content is ever uploaded to external servers except when an optional Gemini AI moderation check is requested by the parent.
- **Git Protection**: The `.gitignore` prevents local session databases (`*.db`, `*.session`, `*.json`) from ever being committed to GitHub.

---

## ⚖️ Ethical & Legal Disclaimer

*ParentGuard is created exclusively for lawful parental supervision of minor children, family safety, or educational and accessibility research across accounts owned or authorized by the user. Do not use this tool to monitor individuals without their explicit legal knowledge and consent in full compliance with local, state, and federal privacy regulations.*

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
