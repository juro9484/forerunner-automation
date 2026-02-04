#!/bin/bash
# Server Configuration Script for Forerunner Automation
# Run this on your VM to ensure proper service configuration
# (auto-restart, log rotation, cron jobs, backups)

set -e  # Exit on any error

echo "=========================================="
echo "Forerunner Automation - Server Config"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Working directory: $SCRIPT_DIR"
echo ""

# ==========================================
# 1. Check systemd service configuration
# ==========================================
echo "==== [1/5] Checking systemd service configuration ===="

SERVICE_FILE="/etc/systemd/system/forerunner-monitor.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}✗ Service file not found: $SERVICE_FILE${NC}"
    echo "  You need to create the systemd service first!"
    exit 1
fi

echo "✓ Service file exists: $SERVICE_FILE"

# Check if Restart=always is configured
if grep -q "Restart=always" "$SERVICE_FILE"; then
    echo -e "${GREEN}✓ Auto-restart is enabled (Restart=always)${NC}"
else
    echo -e "${YELLOW}⚠ Auto-restart is NOT configured${NC}"
    echo "  To enable, add 'Restart=always' to the [Service] section"
fi

# Check if service is enabled on boot
if systemctl is-enabled forerunner-monitor.service &>/dev/null; then
    echo -e "${GREEN}✓ Service is enabled on boot${NC}"
else
    echo -e "${YELLOW}⚠ Service is NOT enabled on boot${NC}"
    echo -n "  Enable service to start on boot? [y/N]: "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo systemctl enable forerunner-monitor.service
        echo -e "${GREEN}✓ Service enabled on boot${NC}"
    fi
fi

echo ""

# ==========================================
# 2. Setup log rotation
# ==========================================
echo "==== [2/5] Setting up log rotation ===="

LOGROTATE_FILE="/etc/logrotate.d/forerunner-automation"

if [ -f "$LOGROTATE_FILE" ]; then
    echo -e "${YELLOW}⚠ Log rotation config already exists${NC}"
    echo "  Location: $LOGROTATE_FILE"
    echo -n "  Overwrite with new configuration? [y/N]: "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "  Skipping log rotation setup"
        echo ""
        SKIP_LOGROTATE=true
    else
        sudo rm "$LOGROTATE_FILE"
        SKIP_LOGROTATE=false
    fi
else
    SKIP_LOGROTATE=false
fi

if [ "$SKIP_LOGROTATE" = false ]; then
    echo "Creating log rotation configuration..."

    sudo tee "$LOGROTATE_FILE" > /dev/null <<EOF
# Forerunner Automation Log Rotation
# Rotates logs weekly, keeps 12 weeks (3 months)
$SCRIPT_DIR/logs/*.log {
    su $(whoami) $(whoami)
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) $(whoami)
    dateext
    dateformat -%Y%m%d
}
EOF

    echo -e "${GREEN}✓ Log rotation configured (weekly, 12 weeks retention)${NC}"
    echo "  Location: $LOGROTATE_FILE"
fi

echo ""

# ==========================================
# 3. Setup cron jobs
# ==========================================
echo "==== [3/5] Setting up cron jobs ===="

# Create a temporary file for crontab
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

CRON_MODIFIED=false

# Check if screenshot cleanup is already configured
if grep -q "forerunner-automation/screenshots" "$TEMP_CRON"; then
    echo -e "${YELLOW}⚠ Screenshot cleanup cron job already exists${NC}"
else
    echo "Adding monthly screenshot cleanup (keeps last 90 days)..."
    echo "" >> "$TEMP_CRON"
    echo "# Forerunner: Clean old screenshots monthly (1st of month at 2 AM)" >> "$TEMP_CRON"
    echo "0 2 1 * * find $SCRIPT_DIR/screenshots/ -name '*.png' -mtime +90 -delete" >> "$TEMP_CRON"
    echo -e "${GREEN}✓ Screenshot cleanup cron added (monthly, 90 days retention)${NC}"
    CRON_MODIFIED=true
fi

# Check if database backup is already configured
if grep -q "automation.db.backup" "$TEMP_CRON"; then
    echo -e "${YELLOW}⚠ Database backup cron job already exists${NC}"
else
    echo "Adding daily database backup..."
    echo "" >> "$TEMP_CRON"
    echo "# Forerunner: Backup database daily at 3 AM" >> "$TEMP_CRON"
    echo "0 3 * * * cp $SCRIPT_DIR/data/automation.db $SCRIPT_DIR/data/automation.db.backup-\$(date +\\%Y\\%m\\%d)" >> "$TEMP_CRON"
    echo "# Forerunner: Clean old database backups (keep 30 days)" >> "$TEMP_CRON"
    echo "0 4 * * * find $SCRIPT_DIR/data/ -name 'automation.db.backup-*' -mtime +30 -delete" >> "$TEMP_CRON"
    echo -e "${GREEN}✓ Database backup cron added (daily, 7 days retention)${NC}"
    CRON_MODIFIED=true
fi

# Install the new crontab if modified
if [ "$CRON_MODIFIED" = true ]; then
    crontab "$TEMP_CRON"
    echo -e "${GREEN}✓ Crontab updated${NC}"
fi

rm "$TEMP_CRON"

echo ""

# ==========================================
# 4. Create backup directories
# ==========================================
echo "==== [4/5] Ensuring directory structure ===="

mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/screenshots"
mkdir -p "$SCRIPT_DIR/temp_attachments"
mkdir -p "$SCRIPT_DIR/documents"

echo -e "${GREEN}✓ All directories exist${NC}"
echo ""

# ==========================================
# 5. Test log rotation
# ==========================================
echo "==== [5/5] Testing log rotation ===="

if [ -f "$LOGROTATE_FILE" ]; then
    echo -n "Test log rotation configuration? [y/N]: "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Running logrotate dry-run test..."
        sudo logrotate -d "$LOGROTATE_FILE"
        echo ""
        echo -e "${GREEN}✓ Log rotation test complete (dry run)${NC}"
    fi
else
    echo "Log rotation not configured, skipping test"
fi

echo ""

# ==========================================
# Summary
# ==========================================
echo "=========================================="
echo "Configuration Complete!"
echo "=========================================="
echo ""
echo "Configuration Summary:"
echo "  • Log rotation: Weekly (keeps 12 weeks)"
echo "  • Screenshot cleanup: Monthly (keeps 90 days)"
echo "  • Database backups: Daily (keeps 30 days)"
echo ""
echo "Active cron jobs:"
crontab -l 2>/dev/null | grep -i forerunner || echo "  (none found)"
echo ""
echo "Next steps:"
echo "  1. Verify service is running:"
echo "     sudo systemctl status forerunner-monitor"
echo ""
echo "  2. View current logs:"
echo "     tail -f $SCRIPT_DIR/logs/monitor_daemon.log"
echo ""
echo "  3. Check disk usage:"
echo "     df -h"
echo ""
echo "To apply service configuration changes (if modified):"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart forerunner-monitor"
echo ""
echo -e "${GREEN}✓ All done!${NC}"
echo ""
