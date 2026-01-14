# Email Monitor Setup Guide

This guide will help you set up and test the email monitoring component of the Forerunner Claims Automation system.

## Prerequisites

- Python 3.11 or higher
- Git (already configured)
- An email account for the bot (Gmail recommended for testing)

## Step 1: Install Dependencies

First, install all required Python packages:

```bash
# Activate your virtual environment if not already activated
source venv/bin/activate  # On macOS/Linux
# OR
.\venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (needed later for Claim Titan automation)
playwright install chromium
```

## Step 2: Configure Email Account

### Option A: Gmail (Recommended for Testing)

1. **Create or use an existing Gmail account** for the bot
2. **Enable 2-Factor Authentication** (required for App Passwords)
   - Go to: https://myaccount.google.com/security
   - Click "2-Step Verification" and follow setup

3. **Generate App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Forerunner Bot"
   - Copy the 16-character password (spaces don't matter)

4. **Enable IMAP** (if not already enabled):
   - Gmail Settings → Forwarding and POP/IMAP
   - Enable IMAP
   - Save changes

### Option B: Other Email Provider

- Ensure IMAP is enabled
- Get IMAP server address and port
- Use account password or app-specific password

## Step 3: Configure Environment Variables

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your credentials:
   ```bash
   # Required for email monitoring
   BOT_EMAIL_USER=your_bot_email@gmail.com
   BOT_EMAIL_PASS=your_16_char_app_password
   BOT_EMAIL_IMAP_SERVER=imap.gmail.com
   BOT_EMAIL_IMAP_PORT=993

   # Required for Claim Titan (add when ready)
   CLAIM_TITAN_USER=Beau@forerunnerclaims.com
   CLAIM_TITAN_PASS=YOUR_CLAIM_TITAN_PASSWORD
   CLAIM_TITAN_URL=https://claimtitan.com/welcome

   # Required for AI (add when ready)
   OPENAI_API_KEY=sk-your-key-here
   # OR
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   AI_PROVIDER=openai
   ```

3. **Save the file** (never commit this to git!)

## Step 4: Test Email Monitor

### Quick Test

Run the standalone test script:

```bash
python test_email_monitor.py
```

This will:
- Connect to your email account
- Fetch unread emails
- Look for claim numbers in subject lines (format: #1234, #12345, etc.)
- Display parsed email data
- Ask if you want to mark emails as read

### Send Test Email

To properly test, send yourself an email with:
- **Subject**: "Test claim #12345 update"
- **Body**: "This is a test email for the claim automation system. Please add this to the claim notes."

Then run the test script again to see it get picked up.

### Manual Test in Python

You can also test interactively:

```python
import sys
sys.path.insert(0, 'src')

from email_monitor import EmailMonitor
import logging

logging.basicConfig(level=logging.INFO)

# Test connection
with EmailMonitor() as monitor:
    emails = monitor.process_emails()
    for email in emails:
        print(f"Claim #{email.claim_number}: {email.subject}")
```

## Step 5: Verify Everything Works

### Expected Output

```
2024-01-12 10:30:15 - Connecting to IMAP server: imap.gmail.com:993
2024-01-12 10:30:16 - IMAP connection established
2024-01-12 10:30:16 - Authenticating as your_bot_email@gmail.com
2024-01-12 10:30:17 - Authentication successful
2024-01-12 10:30:17 - Selected INBOX
2024-01-12 10:30:17 - Found 1 unread email(s)
2024-01-12 10:30:17 - Extracted claim number: 12345
2024-01-12 10:30:17 - Parsed email from sender@example.com with claim #12345

Email #1:
  Claim Number: #12345
  From: sender@example.com
  Subject: Test claim #12345 update
  Content Preview:
    This is a test email for the claim automation system...
```

## Troubleshooting

### Authentication Failed

**Error**: `IMAP authentication failed`

**Solutions**:
- Verify email/password in `.env` file
- For Gmail, use App Password (not regular password)
- Check 2FA is enabled (required for App Passwords)
- Ensure no extra spaces in credentials

### Connection Refused

**Error**: `Failed to connect to email server`

**Solutions**:
- Check internet connection
- Verify IMAP server address and port
- Check firewall allows IMAP (port 993)
- For Gmail, ensure IMAP is enabled in settings

### No Emails Found

**Possible causes**:
- No unread emails in inbox
- No emails with claim numbers in subject
- Claim number format doesn't match pattern `#1234` (4-6 digits)

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'dotenv'`

**Solution**:
```bash
pip install -r requirements.txt
```

## Email Format Requirements

The email monitor looks for claim numbers in the subject line using this pattern:

```
#NNNN   or   #NNNNN   or   #NNNNNN
```

Valid examples:
- "Claim #1234 update"
- "RE: #98765 - Additional info"
- "FW: Claim update #123456"

Invalid examples:
- "Claim 1234" (missing #)
- "#123" (less than 4 digits)
- "#1234567" (more than 6 digits)

## Next Steps

Once email monitoring works:

1. **Build Claim Titan Bot** (`claim_titan_bot.py`)
   - Web automation with Playwright
   - Login, search, post notes

2. **Build AI Summarizer** (`summarizer.py`)
   - Integrate OpenAI or Anthropic API
   - Generate email summaries

3. **Wire Everything Together** (`main.py`)
   - Orchestrate full workflow
   - Add scheduling/looping

4. **Deploy to ZBook**
   - Test in production environment
   - Set up Windows Task Scheduler

## Security Notes

- Never commit `.env` file to git
- Use app-specific passwords, not main account passwords
- Rotate credentials periodically
- Monitor logs for suspicious activity
- Keep dependencies updated for security patches

## Support

If you encounter issues:
1. Check logs in `logs/test_email_monitor.log`
2. Enable DEBUG logging in test script
3. Verify all configuration in `.env`
4. Test with simple email first

---

**Status**: Email Monitor Complete ✓
**Next**: Build Claim Titan Bot
