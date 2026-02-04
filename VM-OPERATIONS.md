# VM Operations Guide - RoakProdFirst

Quick reference for managing your Forerunner automation on Google Cloud VM.

---

## 🔌 Connecting & Disconnecting

### Connect to VM
**From Google Cloud Console (Easiest):**
1. Go to: https://console.cloud.google.com
2. Navigate to: Compute Engine → VM Instances
3. Click "SSH" button next to "roakprod-first"
4. Browser terminal opens automatically

**From Your Computer (Mac/Linux):**
```bash
gcloud compute ssh roakprod-first
```

### Disconnect from VM
Just close the SSH window or type:
```bash
exit
```

**Don't worry - the service keeps running after you disconnect!**

---

## 📊 Checking Status

### Is the service running?
```bash
sudo systemctl status forerunner-monitor
```
Look for: **"active (running)"** in green = Good ✅

### View live logs (see what's happening right now)
```bash
tail -f ~/forerunner-automation/logs/monitor_daemon.log
```
Press `Ctrl+C` to stop watching

### View recent activity (last 50 lines)
```bash
tail -50 ~/forerunner-automation/logs/monitor_daemon.log
```

### Check today's metrics
```bash
cat ~/forerunner-automation/logs/metrics.txt
```

---

## 🔄 Service Management

### Start the service
```bash
sudo systemctl start forerunner-monitor
```

### Stop the service
```bash
sudo systemctl stop forerunner-monitor
```

### Restart the service (after code updates)
```bash
sudo systemctl restart forerunner-monitor
```

### View service logs
```bash
sudo journalctl -u forerunner-monitor -n 100
```

---

## 🚀 Updating Code (After GitHub Push)

When you push new code to GitHub and want to deploy it:

```bash
# 1. SSH into VM
gcloud compute ssh roakprod-first

# 2. Navigate to project
cd ~/forerunner-automation

# 3. Pull latest code
git pull origin main

# 4. Activate virtual environment
source venv/bin/activate

# 5. Install any new dependencies
pip install -r requirements.txt

# 6. Restart service
sudo systemctl restart forerunner-monitor

# 7. Check it started successfully
sudo systemctl status forerunner-monitor

# 8. Watch logs to verify
tail -f logs/monitor_daemon.log
```
Press `Ctrl+C` when done watching

---

## 📸 Viewing Screenshots (When Errors Occur)

### List all screenshots
```bash
ls -lh ~/forerunner-automation/screenshots/
```

### Download screenshot to your computer
**Option 1: Via Google Cloud Console**
1. Go to VM Instances page
2. Click SSH dropdown → "Download file"
3. Enter path: `/home/juanrod2000/forerunner-automation/screenshots/error_XXXXX.png`

**Option 2: Via Command (from your Mac)**
```bash
gcloud compute scp roakprod-first:~/forerunner-automation/screenshots/error_*.png ~/Downloads/
```

---

## 🛠️ Troubleshooting

### Service won't start
```bash
# Check what went wrong
sudo journalctl -u forerunner-monitor -n 50

# Check if port is in use
sudo lsof -i :993

# Force kill any stuck processes
pkill -9 -f monitor_daemon.py

# Try starting again
sudo systemctl start forerunner-monitor
```

### Service keeps restarting
```bash
# View error logs
tail -100 ~/forerunner-automation/logs/service-error.log

# Check credentials are correct
nano ~/.env  # Don't forget to save with Ctrl+X, Y, Enter
```

### Out of disk space
```bash
# Check disk usage
df -h

# Clean old logs (be careful!)
rm ~/forerunner-automation/logs/*.log.old
rm ~/forerunner-automation/screenshots/error_*.png  # After reviewing them
```

---

## 💰 Cost Management

### Check VM is actually running
```bash
gcloud compute instances list
```

### Stop VM (to save money when not needed)
```bash
gcloud compute instances stop roakprod-first
```
**Warning:** Automation stops when VM is stopped!

### Start VM (after stopping)
```bash
gcloud compute instances start roakprod-first
```

### Current monthly cost estimate
- **Running 24/7:** ~$25-30/month (e2-medium)
- **With $300 free credits:** Free for ~3 months!

---

## 📝 Important File Locations

| File/Folder | Path | Purpose |
|------------|------|---------|
| Main logs | `~/forerunner-automation/logs/monitor_daemon.log` | See what's happening |
| Error logs | `~/forerunner-automation/logs/service-error.log` | Debug issues |
| Screenshots | `~/forerunner-automation/screenshots/` | Error screenshots |
| Metrics | `~/forerunner-automation/logs/metrics.txt` | Success rates |
| Credentials | `~/forerunner-automation/.env` | Passwords & API keys |
| Database | `~/forerunner-automation/email_processing.db` | Processed emails |

---

## 🆘 Emergency Commands

### Everything is broken - restart from scratch
```bash
# Stop service
sudo systemctl stop forerunner-monitor

# Delete database (forces reprocessing)
rm ~/forerunner-automation/email_processing.db

# Restart service
sudo systemctl start forerunner-monitor
```

### Check if VM has internet
```bash
ping -c 3 google.com
```

### Check if emails are accessible
```bash
telnet outlook.office365.com 993
# Press Ctrl+] then type 'quit'
```

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Connect | `gcloud compute ssh roakprod-first` |
| Disconnect | `exit` |
| Status | `sudo systemctl status forerunner-monitor` |
| Logs | `tail -f ~/forerunner-automation/logs/monitor_daemon.log` |
| Restart | `sudo systemctl restart forerunner-monitor` |
| Update code | `cd ~/forerunner-automation && git pull` |

---

## 💡 Best Practices

1. **Check logs daily** (just tail the last 50 lines)
2. **Monitor email alerts** (you'll get notified of failures)
3. **Update regularly** (pull latest code weekly)
4. **Back up .env file** (save credentials somewhere safe)
5. **Test after updates** (restart service, check logs)
6. **Keep screenshots** (review before deleting)

---

**Need help? Check the logs first - they usually tell you what went wrong!**
