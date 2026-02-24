# Multi-Client Deployment Guide

## Architecture Overview

You have **ONE shared codebase** that runs **multiple separate services** (one per client).

```
/opt/forerunner-automation/           ← SHARED CODE (one copy)
├── src/
│   ├── main.py
│   ├── config.py
│   ├── adapters/
│   └── utils/
├── requirements.txt
└── venv/

/opt/clients/                          ← CLIENT-SPECIFIC DATA
├── forerunner/                        ← Client 1 (Beau)
│   ├── .env                          ← Client-specific config
│   ├── logs/
│   │   └── forerunner_claims.log
│   ├── data/
│   │   └── automation.db
│   ├── screenshots/
│   └── documents/
│
├── client2/                           ← Client 2 (future)
│   ├── .env
│   ├── logs/
│   │   └── client2.log
│   ├── data/
│   │   └── automation.db
│   └── ...
│
└── client3/                           ← Client 3 (future)
    └── ...
```

---

## Why This Architecture?

### ✅ Shared Codebase (Recommended)
- **One codebase** = Deploy bug fixes/features to all clients at once
- **Less disk space** = One copy of Python dependencies
- **Easier maintenance** = Update one place, restart all services
- **Version control** = All clients run same tested version

### ❌ Separate Folders Per Client (NOT Recommended)
- Need to copy entire codebase for each client
- Bug fix requires updating N different folders
- Disk space waste (N copies of same code)
- Version drift (client1 on v1.2, client2 on v1.5)

---

## Current Setup (Single Client)

Your current server probably has:

```bash
/home/your-user/forerunner-automation/
├── src/
│   ├── main.py
│   ├── config.py
│   └── ...
├── .env                              ← Beau's credentials
├── logs/monitor_daemon.log
├── data/automation.db
└── venv/

# Service file
/etc/systemd/system/forerunner-monitor.service
```

Service looks like:
```ini
[Unit]
Description=Forerunner Claims Automation
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/forerunner-automation
ExecStart=/home/your-user/forerunner-automation/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## New Multi-Client Setup

### Step 1: Restructure Server Directories

```bash
# Move shared code to /opt (cleaner for multi-client)
sudo mkdir -p /opt/forerunner-automation
sudo cp -r ~/forerunner-automation/src /opt/forerunner-automation/
sudo cp -r ~/forerunner-automation/requirements.txt /opt/forerunner-automation/
sudo cp -r ~/forerunner-automation/venv /opt/forerunner-automation/  # Or rebuild venv

# Create client data directories
sudo mkdir -p /opt/clients/forerunner
sudo mkdir -p /opt/clients/forerunner/logs
sudo mkdir -p /opt/clients/forerunner/data
sudo mkdir -p /opt/clients/forerunner/screenshots
sudo mkdir -p /opt/clients/forerunner/documents
sudo mkdir -p /opt/clients/forerunner/temp_attachments

# Move Beau's .env and data
sudo cp ~/forerunner-automation/.env /opt/clients/forerunner/.env
sudo cp ~/forerunner-automation/data/automation.db /opt/clients/forerunner/data/ 2>/dev/null || true

# Set ownership
sudo chown -R your-user:your-user /opt/forerunner-automation
sudo chown -R your-user:your-user /opt/clients
```

### Step 2: Update Client .env File

Edit `/opt/clients/forerunner/.env`:

```bash
# Add CLIENT_ID (used for logging)
CLIENT_ID=forerunner_claims

# Existing credentials stay the same
CLAIM_TITAN_USER=beau@email.com
CLAIM_TITAN_PASS=password123
BOT_EMAIL_USER=bot@forerunner.com
BOT_EMAIL_PASS=emailpass
OPENAI_API_KEY=sk-...

# Feature flags (all enabled for Beau)
FEATURE_COMMENTS_ENABLED=true
COMMENTS_UPLOAD_ATTACHMENTS=false
FEATURE_CONTRACT_ADDITION_ENABLED=true

# Log level
LOG_LEVEL=INFO
BROWSER_HEADLESS=true
```

### Step 3: Create New Service File

Create `/etc/systemd/system/forerunner-client@.service` (template service):

```ini
[Unit]
Description=Forerunner Automation - %i
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/clients/%i
Environment="PYTHONPATH=/opt/forerunner-automation/src"
EnvironmentFile=/opt/clients/%i/.env
ExecStart=/opt/forerunner-automation/venv/bin/python /opt/forerunner-automation/src/main.py
Restart=always
RestartSec=10

StandardOutput=append:/opt/clients/%i/logs/service.log
StandardError=append:/opt/clients/%i/logs/service.log

[Install]
WantedBy=multi-user.target
```

**Key Changes:**
- `@` in filename = template service (can create instances)
- `%i` = instance name (e.g., "forerunner")
- `WorkingDirectory=/opt/clients/%i` = Client-specific directory
- `EnvironmentFile=/opt/clients/%i/.env` = Client-specific config
- `ExecStart` points to **shared code** in `/opt/forerunner-automation`

### Step 4: Enable Services

```bash
# Stop old service
sudo systemctl stop forerunner-monitor.service
sudo systemctl disable forerunner-monitor.service

# Reload systemd
sudo systemctl daemon-reload

# Enable new service for Beau
sudo systemctl enable forerunner-client@forerunner.service
sudo systemctl start forerunner-client@forerunner.service

# Check status
sudo systemctl status forerunner-client@forerunner.service

# View logs
tail -f /opt/clients/forerunner/logs/forerunner_claims.log
```

---

## Adding New Clients

When you get a new client (e.g., "acme-adjusters"):

### 1. Create client directory
```bash
sudo mkdir -p /opt/clients/acme
sudo mkdir -p /opt/clients/acme/{logs,data,screenshots,documents,temp_attachments}
sudo chown -R your-user:your-user /opt/clients/acme
```

### 2. Create client .env
```bash
cat > /opt/clients/acme/.env << 'EOF'
# Client ID
CLIENT_ID=acme_adjusters

# Credentials
CLAIM_TITAN_USER=acme@email.com
CLAIM_TITAN_PASS=password456
BOT_EMAIL_USER=bot@acme.com
BOT_EMAIL_PASS=emailpass2
OPENAI_API_KEY=sk-...

# Features (maybe they don't want contract addition)
FEATURE_COMMENTS_ENABLED=true
COMMENTS_UPLOAD_ATTACHMENTS=true
FEATURE_CONTRACT_ADDITION_ENABLED=false

LOG_LEVEL=INFO
BROWSER_HEADLESS=true
EOF
```

### 3. Start service
```bash
sudo systemctl enable forerunner-client@acme.service
sudo systemctl start forerunner-client@acme.service
sudo systemctl status forerunner-client@acme.service
```

**That's it!** No code duplication.

---

## Updating Code (All Clients)

When you update the code:

```bash
# Pull latest code
cd /opt/forerunner-automation
git pull

# Restart ALL clients
sudo systemctl restart forerunner-client@forerunner.service
sudo systemctl restart forerunner-client@acme.service
sudo systemctl restart forerunner-client@client3.service
# ... etc

# Or restart all at once
sudo systemctl restart 'forerunner-client@*'
```

---

## Service Management Commands

```bash
# List all running clients
sudo systemctl list-units 'forerunner-client@*'

# Status of specific client
sudo systemctl status forerunner-client@forerunner.service

# View logs
journalctl -u forerunner-client@forerunner.service -f
tail -f /opt/clients/forerunner/logs/forerunner_claims.log

# Restart specific client
sudo systemctl restart forerunner-client@forerunner.service

# Stop specific client
sudo systemctl stop forerunner-client@acme.service

# View all client logs
tail -f /opt/clients/*/logs/*.log
```

---

## Client Isolation

Each client has:
- ✅ **Separate .env** (credentials, feature flags)
- ✅ **Separate database** (`data/automation.db`)
- ✅ **Separate logs** (`logs/{CLIENT_ID}.log`)
- ✅ **Separate screenshots** (`screenshots/`)
- ✅ **Shared codebase** (same Python code)
- ✅ **Shared dependencies** (same venv)

---

## Changes to Your Code

### Already Done ✅
The refactored code already supports this:

**config.py** reads `CLIENT_ID` from .env:
```python
CLIENT_ID: str = os.getenv("CLIENT_ID", "forerunner_claims")
```

**main.py** creates client-specific logs:
```python
client_id = getattr(Config, 'CLIENT_ID', 'forerunner_claims')
log_file = Config.LOGS_DIR / f"{client_id}.log"
```

**config.py** paths are relative to WorkingDirectory:
```python
PROJECT_ROOT: Path = Path(__file__).parent.parent  # /opt/forerunner-automation
LOGS_DIR: Path = PROJECT_ROOT / "logs"              # /opt/clients/{client}/logs (via WorkingDirectory)
```

Wait... that won't work! Let me fix that.

---

## Fix Required: Paths in config.py

**Problem:** config.py uses `Path(__file__).parent.parent` which will be `/opt/forerunner-automation`, not `/opt/clients/{client}`.

**Solution:** Use `os.getcwd()` for data directories (respects WorkingDirectory from systemd):

Update `src/config.py`:

```python
# Paths
PROJECT_ROOT: Path = Path(__file__).parent.parent  # Code location (/opt/forerunner-automation)
DATA_ROOT: Path = Path(os.getcwd())  # Working directory (/opt/clients/{client})

LOGS_DIR: Path = DATA_ROOT / "logs"
SCREENSHOTS_DIR: Path = DATA_ROOT / "screenshots"
DATA_DIR: Path = DATA_ROOT / "data"
DATABASE_PATH: Path = DATA_DIR / "automation.db"
ATTACHMENTS_TEMP_DIR: Path = DATA_ROOT / "temp_attachments"
DOCUMENTS_DIR: Path = DATA_ROOT / "documents"
```

This way:
- Code reads from `/opt/forerunner-automation/src/`
- Data writes to `/opt/clients/{client}/logs`, `/opt/clients/{client}/data`, etc.

---

## Summary

### Current (Single Client)
```
/home/user/forerunner-automation/
├── src/
├── .env
├── logs/
├── data/
└── venv/

systemctl start forerunner-monitor.service
```

### New (Multi-Client)
```
/opt/forerunner-automation/      ← Code
├── src/
├── requirements.txt
└── venv/

/opt/clients/                    ← Data (one folder per client)
├── forerunner/.env
├── forerunner/logs/
├── forerunner/data/
├── acme/.env
├── acme/logs/
└── acme/data/

systemctl start forerunner-client@forerunner.service
systemctl start forerunner-client@acme.service
```

**No code duplication. Easy to add clients. Easy to update all clients at once.**
