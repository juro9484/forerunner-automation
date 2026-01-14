# Production Readiness Checklist

## Current Status: Development/MVP ⚠️

The email monitor works for testing but needs these enhancements for production deployment.

## Critical Features Needed for Production

### 1. Duplicate Detection ⚠️ HIGH PRIORITY
**Current State:** None - will reprocess emails if script runs twice
**Needed:**
- Track processed email IDs in a persistent store
- Prevent duplicate processing of same email
- Handle script crashes/restarts gracefully

**Implementation:**
- SQLite database to track processed emails
- Store: email_id, claim_number, processed_timestamp, status
- Check before processing each email

### 2. Retry Logic with Exponential Backoff ⚠️ HIGH PRIORITY
**Current State:** Single attempt, fails immediately
**Needed:**
- Retry on connection failures (network issues)
- Exponential backoff (1s, 2s, 4s, 8s, etc.)
- Max retry limit
- Don't retry on authentication errors (permanent failures)

**Implementation:**
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        connect()
        break
    except ConnectionError:
        if attempt < max_retries - 1:
            sleep(2 ** attempt)  # exponential backoff
```

### 3. Email Filtering/Allowlist ⚠️ MEDIUM PRIORITY
**Current State:** Processes ALL emails with claim numbers
**Needed:**
- Filter by sender domain (only process emails from specific clients)
- Filter by sender email address
- Configurable allowlist/blocklist

**Why Important:** Security - prevents spam/phishing from triggering automation

**Implementation:**
```python
ALLOWED_DOMAINS = ["forerunnerclaims.com", "trustedpartner.com"]
ALLOWED_SENDERS = ["claims@partner.com"]
```

### 4. Connection Management ⚠️ MEDIUM PRIORITY
**Current State:** Create new connection each time
**Needed:**
- Connection keepalive for long-running processes
- Detect stale connections and reconnect
- Connection timeout settings

### 5. Error Recovery & Alerting ⚠️ HIGH PRIORITY
**Current State:** Logs errors, but no alerts
**Needed:**
- Email/SMS alerts on critical failures
- Distinguish transient vs permanent errors
- Automatic recovery from transient errors
- Graceful degradation (mark email for manual review)

**Implementation:**
- Send alert email if connection fails > 3 times
- Log errors to monitoring service
- Create "failed_processing" folder for problematic emails

### 6. Rate Limiting ⚠️ LOW PRIORITY
**Current State:** None
**Needed:**
- Limit API calls to Claim Titan (avoid overwhelming their server)
- Throttle email processing (e.g., max 10/minute)

**Why Important:** Be a good citizen, avoid getting IP blocked

### 7. Processed Email Tracking Database ⚠️ HIGH PRIORITY

**Schema:**
```sql
CREATE TABLE processed_emails (
    email_id TEXT PRIMARY KEY,
    claim_number TEXT NOT NULL,
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    received_timestamp DATETIME NOT NULL,
    processed_timestamp DATETIME NOT NULL,
    status TEXT NOT NULL,  -- 'success', 'failed', 'pending'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);
```

### 8. Configuration Enhancements ⚠️ MEDIUM PRIORITY

Add to `config.py`:
```python
# Email filtering
ALLOWED_SENDER_DOMAINS: List[str] = ["forerunnerclaims.com"]
ALLOWED_SENDERS: List[str] = []  # Specific email addresses
BLOCKED_SENDERS: List[str] = []

# Processing limits
MAX_EMAILS_PER_RUN: int = 50  # Don't process more than 50 at once
MAX_RETRIES: int = 3
RETRY_DELAY_BASE: int = 2  # seconds (exponential backoff)

# Connection settings
IMAP_TIMEOUT: int = 30  # seconds
CONNECTION_KEEPALIVE: bool = True

# Database
DATABASE_PATH: Path = PROJECT_ROOT / "data" / "automation.db"

# Alerting
ALERT_EMAIL: Optional[str] = None  # Send alerts here
ALERT_ON_FAILURE_COUNT: int = 3  # Alert after N consecutive failures
```

### 9. Monitoring & Metrics ⚠️ MEDIUM PRIORITY

**Track:**
- Emails processed per hour/day
- Processing success rate
- Average processing time
- Connection failures count
- Current backlog size

**Implementation:**
- Log metrics to file/database
- Dashboard for monitoring (optional)
- Daily summary email

### 10. Email Folder Management ⚠️ LOW PRIORITY
**Current State:** Only monitors INBOX
**Needed:**
- Move processed emails to "Processed" folder
- Move failed emails to "Failed" folder
- Configurable folder names

### 11. Security Enhancements ⚠️ MEDIUM PRIORITY

**Current State:** Basic IMAP SSL
**Needed:**
- Validate email sender (SPF/DKIM checks)
- Sanitize email content (remove scripts, dangerous content)
- Log all access for audit trail
- Encrypt database with processed email data

### 12. Logging Improvements ⚠️ HIGH PRIORITY

**Current State:** Basic logging
**Needed:**
- Structured logging (JSON format)
- Log rotation (don't fill disk)
- Different log levels for different components
- Performance metrics in logs

**Implementation:**
```python
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    'logs/automation.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## Quick Wins for Production (Minimum Viable Production)

These are the MUST-HAVES before going live:

1. **Duplicate Detection** - SQLite database to track processed emails
2. **Retry Logic** - Handle transient network failures
3. **Email Filtering** - Only process emails from approved senders
4. **Error Alerting** - Send email/SMS when system fails
5. **Log Rotation** - Prevent disk space issues

Estimated time: 3-4 hours to implement all 5

## Nice-to-Haves (Can add later)

- Advanced monitoring/metrics
- Email folder management
- Connection pooling
- Rate limiting
- Dashboard

## Current MVP Limitations

**Do NOT use current code in production without:**
- Duplicate detection (will reprocess same emails)
- Email filtering (security risk)
- Retry logic (fails on network blips)
- Error alerts (silent failures)

## Next Steps

1. **Test current MVP** - Make sure basic functionality works
2. **Add duplicate detection** - Critical for reliability
3. **Add retry logic** - Critical for stability
4. **Add email filtering** - Critical for security
5. **Add error alerting** - Critical for monitoring
6. **Deploy to ZBook** - Test in production environment
7. **Add monitoring** - Track performance over time

---

**Recommendation:** Implement the "Quick Wins" features before deploying to production. The current code is suitable for testing and development only.
