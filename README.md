# 🤖 Telegram AI & Group Verification Bot

A Python-based Telegram bot combining **AI assistance** with **private user verification and administrator-controlled group joining**.

The bot is designed to support protected Telegram communities where new users must complete a verification process before an administrator approves their entry.

---

## 🚀 Features

### 🤖 AI Assistant

* Private AI chat with users
* Uses the OpenAI API
* Users can send normal text messages to receive AI responses
* AI functionality is handled separately through `ai.py`

### 🔐 Group Join Verification

New users requesting access to a protected group are kept **outside the group** while their verification is completed.

The verification flow collects:

* 👤 Full Name
* 🎂 Age
* ⚧ Gender
* 📍 Location
* 🎯 Purpose for joining
* 📸 Selfie Photo

The information is sent privately to the administrator for review.

### 👨‍💼 Administrator Approval

The administrator receives the applicant's:

* Name
* Age
* Gender
* Location
* Purpose
* Telegram username
* Telegram user ID
* Group information
* Selfie

The administrator receives two buttons:

```text
✅ APPROVE
❌ REJECT
```

#### APPROVE

The bot approves the pending Telegram join request.

The user can then enter the group.

#### REJECT

The bot declines the pending join request.

The user is not admitted to the group.

---

## 🔒 Important Verification Principle

The bot uses Telegram's **Join Request** mechanism.

A user must request to join through a verification invite link.

The user is **not automatically added to the group**.

The sequence is:

```text
User opens verification invite link
             ↓
User sends Telegram Join Request
             ↓
Telegram keeps request pending
             ↓
Bot receives Join Request
             ↓
Bot contacts user privately
             ↓
User submits verification details
             ↓
User submits selfie
             ↓
Bot sends information to Admin
             ↓
        Admin Decision
          ↙       ↘
     APPROVE      REJECT
        ↓            ↓
User admitted    User denied
```

---

# 📁 Project Structure

```text
telegram-bot/
│
├── bot.py
├── ai.py
├── .env
├── .gitignore
├── README.md
│
└── venv/
```

### `bot.py`

Main Telegram bot application.

Responsible for:

* Telegram commands
* Join requests
* Verification sessions
* User information collection
* Photo collection
* Admin notifications
* Approve / Reject buttons
* Telegram group approval
* Telegram group rejection
* AI message routing

### `ai.py`

Handles communication with the OpenAI API.

The AI functionality is separated from the main Telegram bot.

### `.env`

Contains private credentials and configuration.

**Never publish this file to GitHub.**

### `.gitignore`

Prevents sensitive and unnecessary files from being uploaded to GitHub.

### `README.md`

Project documentation and deployment instructions.

---

# 🔑 Environment Variables

Create a `.env` file in the project root.

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
ADMIN_CHAT_ID=YOUR_TELEGRAM_USER_ID
```

### BOT_TOKEN

Telegram Bot API token obtained from BotFather.

### OPENAI_API_KEY

OpenAI API key used by `ai.py`.

### ADMIN_CHAT_ID

Numeric Telegram user ID of the administrator who receives verification requests and can approve or reject users.

Example:

```env
ADMIN_CHAT_ID=123456789
```

Do not use your Telegram username here.

---

# ⚠️ Security

Never commit these values to GitHub:

```text
BOT_TOKEN
OPENAI_API_KEY
ADMIN_CHAT_ID
```

Your `.env` file should be ignored by Git.

Example `.gitignore`:

```gitignore
.env
.env.*
!.env.example

venv/
__pycache__/
*.pyc
*.log
```

You can create a safe template for other developers:

### `.env.example`

```env
BOT_TOKEN=
OPENAI_API_KEY=
ADMIN_CHAT_ID=
```

The `.env.example` file contains no real credentials.

---

# 🛠️ Requirements

Recommended environment:

```text
Python 3.11+
```

The project uses:

* Python
* python-telegram-bot
* python-dotenv
* OpenAI Python SDK

Install dependencies with:

```bash
pip install python-telegram-bot python-dotenv openai
```

---

# 💻 Local Installation

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Enter the project:

```bash
cd telegram-bot
```

Create a virtual environment:

### Windows

```bat
python -m venv venv
```

Activate:

```bat
venv\Scripts\activate
```

### Linux / Ubuntu

```bash
python3 -m venv venv
```

Activate:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install --upgrade pip
pip install python-telegram-bot python-dotenv openai
```

---

# ⚙️ Configuration

Create `.env`:

```env
BOT_TOKEN=YOUR_REAL_BOT_TOKEN
OPENAI_API_KEY=YOUR_REAL_OPENAI_KEY
ADMIN_CHAT_ID=YOUR_REAL_TELEGRAM_ID
```

Do not commit `.env`.

---

# ▶️ Run the Bot

### Windows

```bat
python bot.py
```

### Linux / Ubuntu

```bash
python3 bot.py
```

When the bot starts successfully, the terminal should show an environment check similar to:

```text
ENVIRONMENT CHECK
.env exists: True
BOT_TOKEN loaded: True
OPENAI_API_KEY loaded: True
ADMIN_CHAT_ID loaded: True
```

Then:

```text
BOT CONNECTED
Starting polling...
```

---

# 🤖 Telegram Commands

The current bot supports:

```text
/start
/help
/joinlink
```

### `/start`

Starts interaction with the bot.

### `/help`

Displays available bot functionality.

### `/joinlink`

Creates a Telegram invite link configured for **join requests**.

Example:

```text
/joinlink -1001234567890
```

Replace the example group ID with the actual Telegram group/supergroup ID.

---

# 🔗 Creating the Verification Join Link

The bot administrator can use:

```text
/joinlink GROUP_ID
```

Example:

```text
/joinlink -1001234567890123
```

The bot creates an invite link where:

```text
creates_join_request=True
```

Users using this link submit a join request instead of entering immediately.

### Important

Users should be given the **verification join-request link**, not an ordinary Telegram invite link.

---

# 👥 Telegram Group Requirements

The bot must be added to the target group or supergroup.

The bot should have administrator permissions required to manage join requests.

In particular, the bot needs permission to manage/invite users.

Recommended setup:

```text
Telegram Group
      ↓
Add Bot
      ↓
Promote Bot to Administrator
      ↓
Allow required invite/join-request permission
```

---

# 🔐 Verification Process

When Telegram sends a join request:

```text
chat_join_request
```

the bot creates a verification session.

The applicant is privately asked for:

```text
1. Full Name
2. Age
3. Gender
4. Location
5. Purpose
6. Selfie
```

The bot keeps the join request pending during this process.

---

# 👨‍💼 Administrator Workflow

After the applicant submits the selfie, the administrator receives a private message containing the verification information.

Example:

```text
🔔 NEW GROUP JOIN VERIFICATION

👤 USER INFORMATION

Name: Example User
Age: 25
Gender: Male
Location: Chennai
Purpose: Community participation

📱 TELEGRAM INFORMATION

Username: @example
User ID: 123456789

👥 GROUP

Group: Example Group
Group ID: -100123456789

📸 Selfie attached.

⏳ STATUS: WAITING FOR ADMIN APPROVAL
```

The administrator can then choose:

```text
✅ APPROVE
❌ REJECT
```

---

# ✅ Approval

When the administrator clicks:

```text
✅ APPROVE
```

the bot calls Telegram's join-request approval mechanism.

The user is then permitted to join the group.

The bot also sends a confirmation message to the applicant.

---

# ❌ Rejection

When the administrator clicks:

```text
❌ REJECT
```

the bot declines the pending join request.

The user remains outside the group.

---

# 🧪 Testing

Before production deployment, test the complete workflow.

### Test 1 — Bot Startup

```bash
python bot.py
```

Confirm:

```text
BOT CONNECTED
Starting polling...
```

### Test 2 — Private AI

Send:

```text
Hi
```

to the bot.

Confirm that the AI response is returned.

### Test 3 — Join Request

Generate:

```text
/joinlink GROUP_ID
```

Open the generated link from a test Telegram account.

Submit a join request.

### Test 4 — Verification

Confirm the bot privately asks for:

```text
Name
Age
Gender
Location
Purpose
Selfie
```

### Test 5 — Admin

Confirm the administrator receives:

```text
Applicant details
+
Selfie
+
APPROVE
+
REJECT
```

### Test 6 — Approval

Click:

```text
APPROVE
```

Confirm that the pending join request is approved.

### Test 7 — Rejection

Repeat with another test account.

Click:

```text
REJECT
```

Confirm that the user is not admitted.

---

# 🌐 Production / Live Deployment

For 24/7 operation, the bot should run on an always-on server rather than inside a normal Windows CMD window.

Recommended production architecture:

```text
                 GitHub
                   │
                   ↓
            Bot Source Code
                   │
                   ↓
             Linux VPS
                   │
        ┌──────────┴──────────┐
        │                     │
     Python                systemd
        │                     │
        └──────────┬──────────┘
                   ↓
             Telegram API
                   │
        ┌──────────┴──────────┐
        ↓                     ↓
      Users                 Admin
```

Recommended server:

```text
Ubuntu Linux
Python 3
Virtual Environment
systemd
Git
```

---

# 📦 Deployment from GitHub

On the production server:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Enter the project:

```bash
cd telegram-bot
```

Create the virtual environment:

```bash
python3 -m venv venv
```

Activate:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install --upgrade pip
pip install python-telegram-bot python-dotenv openai
```

Create the production `.env` manually:

```bash
nano .env
```

Add:

```env
BOT_TOKEN=YOUR_REAL_BOT_TOKEN
OPENAI_API_KEY=YOUR_REAL_OPENAI_KEY
ADMIN_CHAT_ID=YOUR_REAL_TELEGRAM_ID
```

The production `.env` should remain on the server and should not be committed to GitHub.

---

# 🔄 Running 24/7 with systemd

Create:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Example configuration:

```ini
[Unit]
Description=Telegram AI Verification Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/telegram-bot
ExecStart=/opt/telegram-bot/venv/bin/python /opt/telegram-bot/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
```

Enable automatic startup:

```bash
sudo systemctl enable telegram-bot
```

Start:

```bash
sudo systemctl start telegram-bot
```

Check status:

```bash
sudo systemctl status telegram-bot
```

Expected:

```text
Active: active (running)
```

---

# 📋 Production Logs

View live logs:

```bash
sudo journalctl -u telegram-bot -f
```

View recent logs:

```bash
sudo journalctl -u telegram-bot -n 100
```

Restart:

```bash
sudo systemctl restart telegram-bot
```

Stop:

```bash
sudo systemctl stop telegram-bot
```

Start:

```bash
sudo systemctl start telegram-bot
```

---

# 🔄 Updating the Live Bot

When code is updated on GitHub:

```bash
cd /opt/telegram-bot
```

Pull the latest code:

```bash
git pull
```

Activate the environment:

```bash
source venv/bin/activate
```

Update dependencies if required:

```bash
pip install -r requirements.txt
```

Restart the service:

```bash
sudo systemctl restart telegram-bot
```

Check:

```bash
sudo systemctl status telegram-bot
```

---

# 📄 Recommended requirements.txt

Create:

```text
requirements.txt
```

Example:

```text
python-telegram-bot
python-dotenv
openai
```

Then installation becomes:

```bash
pip install -r requirements.txt
```

---

# ⚠️ Telegram Polling

This project currently uses Telegram long polling.

Only **one active instance** of this bot should normally poll Telegram at a time.

Do not run:

```text
Windows bot
+
VPS bot
```

simultaneously with the same bot token.

Otherwise Telegram may return a conflict similar to:

```text
Conflict: terminated by other getUpdates request
```

Before moving the bot to production, stop the local Windows instance.

---

# 🧰 Troubleshooting

## Bot does not start

Check:

```bash
python bot.py
```

Look at the terminal error.

---

## `.env` not found

Confirm:

```text
.env
```

exists in the project directory.

Check:

```bash
ls -la
```

Linux or:

```bat
dir /a
```

Windows.

---

## Bot token error

Verify:

```env
BOT_TOKEN=...
```

in `.env`.

Do not add quotation marks unless required by your environment.

---

## OpenAI error

Check:

```env
OPENAI_API_KEY=...
```

and verify that the API account/key has available usage.

---

## Telegram polling conflict

Stop other running instances of the same bot.

On Windows:

```bat
taskkill /F /IM python.exe
```

Then start only one instance.

On Linux:

```bash
sudo systemctl restart telegram-bot
```

---

## Join request is not received

Check:

1. Bot is administrator of the group.
2. Bot has the required invite/join-request permission.
3. User is using the verification join-request link.
4. User has actually submitted a Telegram join request.
5. Bot is running.
6. Only one bot instance is polling.

---

## Admin APPROVE does not work

Check:

```bash
sudo journalctl -u telegram-bot -n 100
```

Also confirm that the bot has the necessary permission to manage join requests.

---

# 🔐 Production Security Recommendations

For production:

* Never publish `.env`.
* Never publish Telegram bot tokens.
* Never publish OpenAI API keys.
* Never hard-code credentials into Python source code.
* Use a dedicated production server.
* Keep Ubuntu and Python dependencies updated.
* Restrict SSH access where practical.
* Use SSH keys instead of passwords where possible.
* Keep regular backups of important application data.
* Monitor application logs.
* Do not run multiple instances of the same Telegram bot token.

---

# 🗄️ Future Development

The current architecture can be expanded with additional modules.

Planned functionality:

```text
Phase 1  → Basic Telegram Bot
Phase 2  → Database & User Profiles
Phase 3  → Group Integration
Phase 4  → Welcome & Rules
Phase 5  → Warning / Mute / Kick / Ban
Phase 6  → Anti-Spam & Filters
Phase 7  → Automated Group Activities
Phase 8  → AI Group Assistant
Phase 9  → Admin Dashboard
Phase 10 → Production 24/7 Deployment
```

Future database functionality can store:

* Telegram user ID
* Username
* Name
* Verification status
* Join-request history
* Group membership
* Warning history
* Administrative actions
* User profile information
* Other application-specific data

---

# 🏗️ Suggested Future Project Structure

As the project grows, it can be organized into:

```text
telegram-bot/
│
├── bot.py
├── ai.py
├── config.py
│
├── handlers/
│   ├── start.py
│   ├── verification.py
│   ├── admin.py
│   ├── group.py
│   └── ai.py
│
├── database/
│   ├── models.py
│   ├── database.py
│   └── migrations/
│
├── services/
│   ├── verification.py
│   ├── moderation.py
│   └── ai_service.py
│
├── utils/
│   ├── logging.py
│   └── helpers.py
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

This structure can be introduced gradually rather than moving everything at once.

---

# 📌 Important

This project is intended to automate Telegram group management and user verification.

Administrators should ensure that their verification questions, photo collection, storage practices, and group rules comply with applicable laws, Telegram's terms, and the expectations communicated to users.

Sensitive user information should be handled securely and retained only when necessary.

---

# 📜 License

Add your preferred license here.

Example:

```text
MIT License
```

or specify your organization's proprietary license.

---

# 👨‍💻 Development

This project is under active development.

The initial focus is:

```text
Telegram Bot
      +
AI Assistant
      +
Private Verification
      +
Admin Approval
      +
Protected Group Access
```

Additional group-management, database, moderation, AI, and administration features can be added progressively.
