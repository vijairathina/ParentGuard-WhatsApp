<p align="center">
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/WhatsApp.dark.svg" width="80" height="80" alt="ParentGuard WhatsApp" />
</p>

<h1 align="center">🛡️ ParentGuard WhatsApp</h1>

<p align="center">
  <strong>Parental-Supervised Multi-Session WhatsApp Monitor with Google Gemini AI Safety & Content Auditing</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://flask.palletsprojects.com/"><img src="https://img.shields.io/badge/Framework-Flask_3.x-black?logo=flask&logoColor=white" alt="Flask" /></a>
  <a href="https://aistudio.google.com/"><img src="https://img.shields.io/badge/AI-Google_Gemini-orange?logo=google&logoColor=white" alt="Gemini AI" /></a>
  <a href="https://github.com/krypton-byte/neonize"><img src="https://img.shields.io/badge/Engine-Neonize_WA-brightgreen" alt="Neonize" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="License" /></a>
</p>

---

## 🌟 Overview

**ParentGuard WhatsApp** is a parental-control and safety-monitoring multi-session WhatsApp Web client. It allows parents or guardians to manage and oversee multiple WhatsApp accounts simultaneously in real time, with an integrated **Google Gemini AI content moderation engine** and **customizable keyword safety rules**.

Whenever inappropriate, dangerous, or illegal content (substances, cyberbullying, harassment, leaked passwords, self-harm, etc.) is detected in incoming or outgoing messages, **ParentGuard** instantly flags and logs the incident with exact timestamps, sender details, severity ratings, and AI explanations.

---

## ✨ Key Features

- **🛡️ Gemini AI Safety Guardian**:
  - Semantic content inspection detecting illegal acts, harassment, explicit adult content, threats, and confidential data disclosures.
  - Returns classification category, severity rating (`High`, `Medium`, `Low`), and reasoning in real time.
- **🔍 Non-AI Keyword & Phrase Rules**:
  - Fast, regex-backed keyword filtering per account.
  - Monitors outgoing, incoming, or bidirectional chat messages.
- **📑 Live Incident Audit Logs**:
  - Timestamped record of every safety violation.
  - Filterable incident table with one-click **CSV Report Export** for parental review.
  - Real-time slide-in security toast alerts on your screen.
- **👥 Multi-Account Support**:
  - Connect and manage multiple independent WhatsApp accounts concurrently via QR code scanning.
  - Per-account login and logout lifecycle without losing credentials.
- **💬 Enhanced Chat History & Visual Separation**:
  - High-contrast, clean message bubble hierarchy:
    - **Outgoing (Sender)**: Right-aligned, emerald green bubble with status double-checks.
    - **Incoming (Receiver)**: Left-aligned, slate dark bubble.
    - **Group Chats**: Distinct sender participant tags.
- **🎨 5 Per-Account Custom Themes**:
  - **WhatsApp Dark** (classic dark mode)
  - **WhatsApp Light** (crisp clean daylight mode)
  - **Emerald Night** (deep forest green)
  - **Midnight OLED** (pitch black for AMOLED screens)
  - **ParentGuard Shield** (navy blue and gold security palette)
- **⏰ Advanced Scheduled & Automated Messages**:
  - Rule-based message scheduler with persistent storage (retained across logouts & server restarts).
  - Built-in rich templates for **Birthday Wishes**, **Wedding Anniversaries**, **Daily Routine Greetings (Morning, Afternoon, Night)**, **Festivals (Diwali, New Year, Pongal, Christmas, Eid, Holi)**, and **Health Check-ins**.
  - Dynamic template variables: `{name}`, `{date}`, `{time}`, `{day}`.
  - Automatic queueing when WhatsApp sessions are temporarily offline with auto-dispatch on reconnect.
- **⚡ SSE Realtime Updates**:
  - Live server-sent events for instant message delivery, status changes, and safety incident alerts without manual polling.

---

## 🏗️ Architecture

```
[ WhatsApp Network ]
        │ (Neonize Protocol)
        ▼
[ whatsapp_manager.py ] ───► [ content_monitor.py ]
        │                               │
        │                  ┌────────────┴────────────┐
        │                  ▼                         ▼
        │         [ Keyword Engine ]        [ Google Gemini AI ]
        │                  │                         │
        │                  └────────────┬────────────┘
        │                               ▼
        │                    [ accounts/audit_log.json ]
        ▼                               │
  [ Flask API (app.py) ] ◄──────────────┘
        │
   (SSE / REST)
        │
        ▼
 [ Web UI (app.js + style.css) ]
  ├── Distinct Sender/Receiver Chat Panel
  ├── Per-Account Settings & Themes
  └── Security Alert Toast & Audit Table
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/parentguard-whatsapp.git
cd parentguard-whatsapp
```

### 3. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

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
Edit `.env` and set your Google Gemini API Key (obtain free from [Google AI Studio](https://aistudio.google.com/)):
```env
GEMINI_API_KEY=your_gemini_api_key_here
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

## 📱 How to Use

1. **Link WhatsApp Session**:
   - Click the **`+`** button in the top left header.
   - Open WhatsApp on the phone &rarr; **Linked Devices** &rarr; **Link a Device**.
   - Scan the on-screen QR code.
2. **Configure Parental Safety Rules**:
   - Click the **Settings (Gear)** icon in the header.
   - Go to the **Keyword Filter** tab to customize restricted words and direction (incoming/outgoing/both).
   - Go to the **Gemini AI Safety** tab, toggle AI moderation on, paste your Gemini API key, and test it with a sample sentence.
   - Select your preferred **Theme** for the account.
   - Click **Save Changes**.
3. **Review Flagged Incidents**:
   - Click the **Shield Alert** icon in the header to view the **Audit Incident Logs**.
   - Review flagged messages with dates, severity ratings, and reasons.
   - Click **Export CSV** to download a report.

---

## 🔒 Security & Privacy Practices

- **Zero Third-Party Cloud Data**: All chat databases, contacts, and audit logs are stored locally on your machine under `accounts/`.
- **Git Safety**: The included `.gitignore` prevents session credentials (`*.db`), chat history, audit logs, and secret keys from ever being committed to version control.
- **Asynchronous Moderation**: Message parsing and AI moderation run in background worker threads to guarantee zero lag in chat delivery.

---

## ⚖️ Ethical & Legal Disclaimer

*ParentGuard WhatsApp is intended solely for legal parental supervision of minor children, educational experimentation, or personal productivity across accounts owned and authorized by the user. Do not use this tool to monitor individuals without their knowledge and legal consent in accordance with applicable regional and federal laws.*

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
