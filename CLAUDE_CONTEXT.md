# Claude Context - Forerunner Claims Automation

**Last Updated:** February 23, 2026
**Production Status:** ✅ Live with 1 client (Beau/Forerunner Claims)
**Server:** Google Cloud VM `roakprod-first`

---

## What This Project Does

Automates claims processing for Public Adjusters (PAs):

1. **Monitors email inbox** (Outlook/Office365 with OAuth)
2. **Extracts claim numbers** from emails using regex patterns
3. **Summarizes emails** with Claude AI (Anthropic API)
4. **Posts notes** to claims in Claim Titan CRM (Playwright browser automation)
5. **Processes contracts** - Parses PDFs with Claude Vision and creates new claims
6. **Tracks everything** in SQLite database

**Business Value:** Saves ~4-5 hours/day per adjuster by automating email processing and CRM data entry.

---

## Architecture (Post-Refactor - Feb 2026)

### Adapter Pattern
```
src/
├── main.py                          # Orchestrator (runs once, processes emails, exits)
├── config.py                        # Centralized configuration
├── adapters/
│   ├── email/
│   │   └── outlook/
│   │       └── adapter.py           # OutlookAdapter - IMAP + OAuth email monitoring
│   └── crm/
│       └── claim_titan/
│           ├── adapter.py           # ClaimTitanAdapter - Browser automation, login, search
│           ├── exceptions.py        # Custom exceptions
│           └── features/
│               ├── comments.py      # CommentsFeature - Posts notes to claims
│               └── contract_addition.py  # ContractAdditionFeature - Creates new claims
├── utils/
│   └── browser_pool.py              # BrowserPool - Parallel browser sessions (not yet used)
└── [shared utilities]
    ├── summarizer.py                # EmailSummarizer - Claude AI summarization
    ├── contract_parser.py           # ContractParser - Claude Vision PDF parsing
    ├── attachment_handler.py        # AttachmentHandler - File downloads/uploads
    ├── email_database.py            # EmailDatabase - SQLite tracking
    ├── oauth_helper.py              # OAuthHelper - Azure OAuth tokens
    ├── health_checker.py            # HealthChecker - System health monitoring
    └── metrics_tracker.py           # MetricsTracker - Success rate tracking
```

### Key Design Decisions

**1. Adapter Pattern**
- **Email adapters** are swappable (currently: Outlook, future: Gmail)
- **CRM adapters** are swappable (currently: Claim Titan, future: Xactimate)
- Each adapter has **features** that can be enabled/disabled per client

**2. Feature Flags (per client)**
```python
FEATURE_COMMENTS_ENABLED = true/false           # Post notes to claims
COMMENTS_UPLOAD_ATTACHMENTS = true/false        # Upload email attachments
FEATURE_CONTRACT_ADDITION_ENABLED = true/false  # Create claims from contracts
```

**3. Multi-Client Support**
- Each client has separate `.env` file with `CLIENT_ID`
- Logs go to `logs/{CLIENT_ID}.log`
- Separate database, screenshots, attachments per client
- One server can run multiple clients (separate systemd services)

**4. Run Model**
- `main.py` runs **once** → processes emails → exits with code 0
- Systemd restarts it every 10 seconds (`Restart=always`, `RestartSec=10`)
- Better than long-running daemon (no memory leaks, cleaner process isolation)

---

## Current Deployment

### Production Server
```
VM: roakprod-first (Google Cloud, e2-medium)
User: juanrod2000
Path: /home/juanrod2000/forerunner-automation/
Service: forerunner-monitor.service
Status: Active (activating/auto-restart loop - this is NORMAL)
```

### Client: Beau (Forerunner Claims)
```
CLIENT_ID: forerunner_claims
Email: support@forerunnerclaims.com (OAuth)
CRM: Claim Titan
Log: logs/forerunner_claims.log
Database: data/automation.db
Features: Comments (yes), Attachments (no), Contract Addition (yes)
```

### Service File Location
```bash
/etc/systemd/system/forerunner-monitor.service

Key settings:
- ExecStart: /home/juanrod2000/forerunner-automation/venv/bin/python3 src/main.py
- WorkingDirectory: /home/juanrod2000/forerunner-automation
- Restart: always
- RestartSec: 10
```

---

## Important Files & Paths

### Configuration
- `.env` - Credentials, API keys, feature flags (NEVER commit to git)
- `src/config.py` - Loads from .env, provides Config class

### Logs
- `logs/forerunner_claims.log` - Application logs (main activity)
- `logs/service.log` - Systemd stdout
- `logs/service-error.log` - Systemd stderr

### Data
- `data/automation.db` - SQLite database (processed emails tracking)
- `screenshots/` - Error screenshots from browser automation
- `temp_attachments/` - Temporary email attachment downloads
- `documents/` - Processed documents

### Documentation
- `README.md` - Quick start guide
- `ARCHITECTURE.md` - System architecture deep dive
- `DEPLOYMENT_GUIDE.md` - Multi-client deployment guide
- `VM-OPERATIONS.md` - Server management commands
- `THIS FILE` - Context for future Claude instances

---

## Environment Variables (.env)

### Required for All Clients
```bash
# Client identification
CLIENT_ID=forerunner_claims

# Claim Titan CRM
CLAIM_TITAN_USER=email@example.com
CLAIM_TITAN_PASS=password
CLAIM_TITAN_URL=https://claimtitan.com/welcome

# Email (Outlook/Office365 with OAuth)
BOT_EMAIL_USER=support@forerunnerclaims.com
BOT_EMAIL_PASS=app_password
BOT_EMAIL_IMAP_SERVER=outlook.office365.com
BOT_EMAIL_IMAP_PORT=993

# Azure OAuth (for Office365 email)
USE_OAUTH=true
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx
AZURE_TENANT_ID=xxx

# AI Provider
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx  # Optional fallback

# Claude Models
CLAUDE_MODEL=claude-3-5-sonnet-20241022  # Default for summarization
CLAUDE_VISION_MODEL=claude-opus-4-5-20251101  # For PDF/image processing

# Feature Flags
FEATURE_COMMENTS_ENABLED=true
COMMENTS_UPLOAD_ATTACHMENTS=false
FEATURE_CONTRACT_ADDITION_ENABLED=true

# Settings
LOG_LEVEL=INFO
BROWSER_HEADLESS=true
MAX_RETRIES=3
```

---

## Code Flow (main.py)

```python
1. setup_logging()           # Create client-specific log file
2. Config.validate()         # Check all required env vars present
3. Initialize components:
   - OutlookAdapter()        # Email monitoring
   - ClaimTitanAdapter()     # CRM automation (loads features based on config)
   - EmailSummarizer()       # AI summarization
   - ContractParser()        # AI contract parsing
   - EmailDatabase()         # SQLite tracking
   - HealthChecker()         # Health monitoring
   - MetricsTracker()        # Success metrics

4. with email_adapter:
   - Connect to IMAP (OAuth)
   - Fetch unread emails (last 30 days)
   - Parse claim numbers from subject/body

5. with crm_adapter:
   - Launch Playwright browser
   - Login to Claim Titan

   For each email:
     if "contract" in subject:
       # Process as contract
       - Parse PDF with Claude Vision
       - Extract client data
       - contract_feature.process() → creates new claim
     else:
       # Process as regular email
       - Summarize with Claude AI
       - comments_feature.process() → posts note to claim

     - Mark as processed in database
     - Mark as read in email
     - Record metrics

6. Exit with code 0 (success)
7. Systemd restarts after 10 seconds
```

---

## Common Tasks

### Server Access
```bash
# SSH into server
gcloud compute ssh roakprod-first

# Navigate to project
cd ~/forerunner-automation
```

### Check Status
```bash
# Service status (will show "activating" - this is NORMAL)
sudo systemctl status forerunner-monitor

# View live logs
tail -f logs/forerunner_claims.log

# Recent activity
tail -50 logs/forerunner_claims.log

# Check for errors
grep -i error logs/forerunner_claims.log
```

### Deploy Updates
```bash
# On server
cd ~/forerunner-automation
git pull origin main
sudo systemctl restart forerunner-monitor
tail -f logs/forerunner_claims.log  # Watch for errors
```

### Update Service File
```bash
# Edit service
sudo nano /etc/systemd/system/forerunner-monitor.service

# After editing, ALWAYS:
sudo systemctl daemon-reload
sudo systemctl restart forerunner-monitor
```

### Debugging
```bash
# See actual Python errors
sudo journalctl -u forerunner-monitor -n 100

# Test imports manually
source venv/bin/activate
python3 -c "import sys; sys.path.insert(0, 'src'); import main; print('OK')"

# Check database
sqlite3 data/automation.db "SELECT * FROM processed_emails ORDER BY received_timestamp DESC LIMIT 10;"
```

---

## Known Issues & Quirks

### 1. Bridge Pattern in Features
**Current State:** `CommentsFeature` and `ContractAdditionFeature` use a "bridge pattern" - they delegate to methods in the old `claim_titan_bot.py` file.

**Why:** Full extraction of 400+ lines of UI automation code was too large for one refactor.

**Files:**
- `src/claim_titan_bot.py` - OLD file, still in use via bridge
- `src/email_monitor.py` - OLD file, still in use via bridge

**Future:** Extract all methods into the feature classes, then delete old files.

### 2. Browser Pool Not Used Yet
`src/utils/browser_pool.py` exists but isn't integrated. It's ready for when we need parallel processing (3+ claims at once).

### 3. Service Shows "activating"
**This is normal!** The service runs, processes, exits, then restarts. Status will always show "activating (auto-restart)" not "active (running)".

### 4. Exit Code 0 = Success
If you see "Main process exited, code=exited, status=0/SUCCESS" in journalctl - that's GOOD. It means the script ran successfully.

### 5. Claim Number Regex is Permissive
```python
CLAIM_NUMBER_PATTERN = r"(?i)#?([A-Z0-9-]{5,})"
```
Very permissive - matches any 5+ alphanumeric string with optional hyphens. This catches claim numbers like:
- `#12345`
- `75-79F3-75F`
- `CACHO-8192398023`

But may have false positives. Monitor logs if issues arise.

---

## Testing

### Unit Tests
```bash
# Run refactored structure tests (22 tests)
python3 tests/test_refactored_structure.py
```

**Coverage:**
- Import tests (all modules load)
- Config tests (feature flags present and boolean)
- Feature loading tests (adapter loads features based on config)
- Exception tests (proper inheritance)
- Package structure tests (all __init__.py files work)

### Manual Testing
```bash
# Test email connection
python3 -c "
import sys; sys.path.insert(0, 'src')
from adapters.email.outlook.adapter import OutlookAdapter
adapter = OutlookAdapter()
with adapter:
    emails = adapter.fetch_unread_emails()
    print(f'Found {len(emails)} emails')
"

# Test CRM connection
python3 -c "
import sys; sys.path.insert(0, 'src')
from adapters.crm.claim_titan.adapter import ClaimTitanAdapter
from config import Config
adapter = ClaimTitanAdapter(config=Config)
print('CRM adapter created successfully')
"
```

---

## Git Workflow

### Branch: main
**This is production.** Anything merged here goes live immediately after `git pull` on server.

### Making Changes
```bash
# Make changes locally
git add .
git commit -m "Description"
git push origin main

# Deploy to server
gcloud compute ssh roakprod-first
cd ~/forerunner-automation
git pull origin main
sudo systemctl restart forerunner-monitor
tail -f logs/forerunner_claims.log
```

### What's in .gitignore
- `.env` files (credentials)
- `logs/` (log files)
- `data/` (databases)
- `screenshots/` (error screenshots)
- `venv/` (Python virtual environment)
- `*.db` (SQLite databases)

---

## Adding New Clients (Future)

### Option A: Simple (Separate Folders)
```bash
# On server
cd ~
git clone <repo> client2-automation
cd client2-automation
./setup.sh

# Create .env with CLIENT_ID=client2
nano .env

# Create service
sudo cp /etc/systemd/system/forerunner-monitor.service \
        /etc/systemd/system/forerunner-monitor-client2.service

# Edit service to point to client2-automation folder
sudo nano /etc/systemd/system/forerunner-monitor-client2.service

# Start
sudo systemctl enable forerunner-monitor-client2
sudo systemctl start forerunner-monitor-client2
```

### Option B: Advanced (Shared Codebase)
See `DEPLOYMENT_GUIDE.md` for full multi-client architecture with shared code in `/opt/forerunner-automation/`.

---

## Cost & Infrastructure

### Google Cloud VM
- **Type:** e2-medium (2 vCPU, 4GB RAM)
- **Region:** us-west1
- **Cost:** ~$25-30/month
- **Storage:** 10GB disk
- **Network:** External IP for SSH

### API Costs
- **Anthropic Claude:** $3-15/day depending on email volume
- **Azure OAuth:** Free (part of Microsoft 365)

---

## Security Notes

### Credentials
- All credentials in `.env` files (never committed)
- Server `.env` is readable only by `juanrod2000` user
- OAuth tokens refresh automatically (handled by `oauth_helper.py`)

### Browser Automation
- Runs in headless mode (`BROWSER_HEADLESS=true`)
- Screenshots saved on errors for debugging
- No user interaction required

### Database
- SQLite database is local to each client
- No sensitive data stored (only email IDs, claim numbers, timestamps)
- Database backed up daily via cron (see `configure-server.sh`)

---

## Metrics & Monitoring

### Health Checks
`HealthChecker` class tracks:
- Last check timestamp
- Emails processed count
- Success/failure status
- Consecutive failure count

### Metrics
`MetricsTracker` class records:
- Notes posted (success/failure)
- Claims created (success/failure)
- Written to `logs/metrics.txt`

### Log Monitoring
User should check logs daily:
```bash
tail -50 logs/forerunner_claims.log
grep -i error logs/forerunner_claims.log
```

---

## When Things Go Wrong

### Service Won't Start
1. Check service logs: `sudo journalctl -u forerunner-monitor -n 100`
2. Check Python errors: Test imports manually
3. Check .env exists: `cat .env | grep CLIENT_ID`
4. Check file paths in service file

### Authentication Failures
1. OAuth token expired: `oauth_helper.py` should auto-refresh
2. Password changed: Update `.env`
3. Azure app registration issue: Check Azure portal

### Browser Automation Fails
1. Check screenshots: `ls -lt screenshots/ | head`
2. Download screenshot: `gcloud compute scp roakprod-first:~/forerunner-automation/screenshots/error_*.png ~/Downloads/`
3. Common issues:
   - Claim Titan UI changed
   - Slow page load (increase timeouts)
   - Element not found (selector changed)

### Database Issues
1. Corrupt database: Delete and let it rebuild
2. Disk full: Clean old logs/screenshots
3. Check database: `sqlite3 data/automation.db ".schema"`

---

## Important: What NOT to Do

❌ **DON'T** commit `.env` files
❌ **DON'T** run force push to main
❌ **DON'T** edit code directly on server (always git pull)
❌ **DON'T** stop service without restarting (emails won't process)
❌ **DON'T** delete `data/automation.db` without backup (lose processing history)
❌ **DON'T** change service file without `daemon-reload`

---

## Quick Reference Commands

```bash
# Server access
gcloud compute ssh roakprod-first

# Check status
sudo systemctl status forerunner-monitor
tail -f logs/forerunner_claims.log

# Deploy updates
cd ~/forerunner-automation && git pull && sudo systemctl restart forerunner-monitor

# View recent activity
tail -50 logs/forerunner_claims.log

# Find errors
grep -i error logs/forerunner_claims.log

# Database query
sqlite3 data/automation.db "SELECT * FROM processed_emails LIMIT 10;"

# Restart service
sudo systemctl restart forerunner-monitor
```

---

## Contact & Support

**User:** Juan Rodriguez (GitHub: juro9484)
**Repo:** https://github.com/juro9484/forerunner-automation
**Client Contact:** Beau (Forerunner Claims)

---

## Summary for New Claude Instance

You're working on a **production automation system** that processes claims emails for Public Adjusters. It's **live with 1 paying client** on a Google Cloud server. The code was **recently refactored** (Feb 2026) to use an adapter pattern for multi-client support.

**Key things to know:**
1. Server is `roakprod-first`, service is `forerunner-monitor.service`
2. Logs are at `logs/forerunner_claims.log` (not `monitor_daemon.log`)
3. Service shows "activating" not "running" - **this is normal**
4. Main file is `src/main.py` (not `monitor_daemon.py`)
5. Features use bridge pattern to old code temporarily
6. When deploying: git pull → restart service → check logs

**Most common asks:**
- Deploy updates to server
- Debug service issues
- Add new features
- Optimize performance
- Add new clients

**Start any session by asking:**
- "What's the current issue?"
- "What are you trying to accomplish?"
- "Should I check the server status first?"

Good luck! 🚀
