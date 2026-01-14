# Deployment Guide - Windows HP ZBook

## Quick Setup (Get Running Tonight)

### Prerequisites
- HP ZBook with Windows
- Internet connection
- Access to GitHub repo

---

## Step 1: Install Python 3.11+

Download and install Python:
1. Go to: https://www.python.org/downloads/
2. Download **Python 3.11** or newer
3. **IMPORTANT:** Check "Add Python to PATH" during installation
4. Install

Verify installation:
```cmd
python --version
```

Or try:
```cmd
python3 --version
```

---

## Step 2: Clone Repository

Open **Command Prompt** or **PowerShell**:

```cmd
cd C:\Users\YourUsername\Desktop
git clone https://github.com/YOUR_USERNAME/forerunner-automation.git
cd forerunner-automation
```

If git isn't installed:
- Download from: https://git-scm.com/download/win
- Or just download ZIP from GitHub and extract

---

## Step 3: Install Dependencies

```cmd
python -m pip install -r requirements.txt
```

If you get an error, try:
```cmd
python3 -m pip install -r requirements.txt
```

---

## Step 4: Configure Environment Variables

Create `.env` file in the project root:

```cmd
copy .env.example .env
notepad .env
```

**Add these values:**
```bash
# Email Configuration
BOT_EMAIL_USER=support@forerunnerclaims.com
BOT_EMAIL_PASS=YOUR_EMAIL_PASSWORD
BOT_EMAIL_IMAP_SERVER=outlook.office365.com
BOT_EMAIL_IMAP_PORT=993

# OAuth Configuration
USE_OAUTH=true
AZURE_CLIENT_ID=YOUR_AZURE_CLIENT_ID
AZURE_CLIENT_SECRET=YOUR_AZURE_CLIENT_SECRET
AZURE_TENANT_ID=YOUR_AZURE_TENANT_ID

# Claim Titan (for later)
CLAIM_TITAN_USER=beau@forerunnerclaims.com
CLAIM_TITAN_PASS=YOUR_CLAIM_TITAN_PASSWORD
CLAIM_TITAN_URL=https://claimtitan.com/welcome

# AI (leave empty for now)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AI_PROVIDER=openai

# Settings
LOG_LEVEL=INFO
BROWSER_HEADLESS=true
MAX_RETRIES=3
```

Save and close Notepad.

---

## Step 5: Test the Setup

```cmd
python tests\test_email_monitor.py
```

**Expected output:**
- ✓ Connects to email
- ✓ OAuth authentication successful
- ✓ Fetches emails (if any)

---

## Step 6: Start Continuous Monitoring

### Option A: Run in Command Prompt Window

```cmd
python monitor_daemon.py
```

**To stop:** Press `Ctrl+C`

**Logs:** Check `logs\monitor_daemon.log`

---

### Option B: Run as Background Task (Windows Task Scheduler)

**Create a scheduled task to run at startup:**

1. Open **Task Scheduler** (search in Start menu)
2. Click **"Create Basic Task"**
3. Name: `Forerunner Email Monitor`
4. Trigger: **"When the computer starts"**
5. Action: **"Start a program"**
6. Program/script:
   ```
   python
   ```
7. Add arguments:
   ```
   C:\Users\YourUsername\Desktop\forerunner-automation\monitor_daemon.py
   ```
8. Start in:
   ```
   C:\Users\YourUsername\Desktop\forerunner-automation
   ```
9. Check **"Run whether user is logged on or not"**
10. Click **Finish**

---

### Option C: Run Hidden in Background (Best for ZBook)

Create a batch file to run hidden:

**Create `start_monitor.bat`:**
```batch
@echo off
cd /d C:\Users\YourUsername\Desktop\forerunner-automation
pythonw monitor_daemon.py
```

**Double-click to start** (no window appears)

**To stop:**
```cmd
taskkill /F /IM pythonw.exe
```

---

## Step 7: Verify It's Working

### Send Test Email

From any email, send to `support@forerunnerclaims.com`:

**Subject:** `Test claim #12345`
**Body:** `Test email for monitoring`

**Alternative formats that work:**
- `#12-345` (with hyphen)
- `12345` (without #)

### Check Logs

```cmd
type logs\monitor_daemon.log

REM Or watch live (PowerShell):
Get-Content logs\monitor_daemon.log -Wait -Tail 50
```

---

## Step 8: Keep ZBook Running 24/7

### Prevent Sleep:

1. **Settings** → **System** → **Power & sleep**
2. Set **"When plugged in, PC goes to sleep after"**: **Never**
3. Set screen to turn off after 15 mins (saves power)

### Keep Network Alive:

1. **Control Panel** → **Network and Sharing**
2. Click your network adapter
3. **Properties** → **Configure** → **Power Management**
4. **Uncheck** "Allow computer to turn off this device to save power"

---

## Monitoring Schedule

Checks every **5 minutes** automatically.

---

## Troubleshooting

### Issue: Python not found

**Fix:**
- Reinstall Python with "Add to PATH" checked
- Or use full path: `C:\Python311\python.exe`

### Issue: Permission Denied

**Fix:**
- Run Command Prompt as Administrator
- Right-click → "Run as administrator"

### Issue: Monitor Stops Overnight

**Check:**
- Power settings (no sleep)
- Network adapter (don't turn off)
- Task Scheduler task is configured correctly

### Issue: Can't Find Logs

**Location:**
```
C:\Users\YourUsername\Desktop\forerunner-automation\logs\monitor_daemon.log
```

---

## Production Checklist

- [ ] Python installed correctly
- [ ] All dependencies installed
- [ ] `.env` file configured
- [ ] Test script runs successfully
- [ ] Monitor runs in background
- [ ] ZBook power settings configured
- [ ] Network stays connected
- [ ] Can view logs
- [ ] Test email gets processed

---

## File Locations (Windows)

```
C:\Users\YourUsername\Desktop\forerunner-automation\
├── .env                          ← Your credentials
├── monitor_daemon.py             ← Main script
├── data\
│   └── automation.db             ← Database
├── logs\
│   └── monitor_daemon.log        ← Logs
└── src\                          ← Source code
```

---

## Common Windows Commands

```cmd
REM Check if running
tasklist | findstr python

REM View logs
type logs\monitor_daemon.log

REM Stop monitoring
taskkill /F /IM python.exe

REM Restart monitoring
python monitor_daemon.py

REM Test without daemon
python tests\test_email_monitor.py
```

---

## Estimated Setup Time: 30 Minutes

1. Install Python: 5 mins
2. Clone repo: 2 mins
3. Install dependencies: 5 mins
4. Configure .env: 5 mins
5. Test: 5 mins
6. Start monitoring: 2 mins
7. Configure Task Scheduler: 5 mins

**You should be monitoring tonight!**
