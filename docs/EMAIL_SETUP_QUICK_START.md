# Email Monitor Quick Start Guide

## Step 1: Create/Configure Email Account

### Option A: Gmail (Recommended)

1. **Use existing or create new Gmail account**
   - Example: `forerunner.bot@gmail.com`

2. **Enable 2-Factor Authentication** (required for App Passwords)
   - Go to: https://myaccount.google.com/security
   - Click "2-Step Verification"
   - Follow the setup wizard

3. **Generate App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it: "Forerunner Claims Bot"
   - Copy the 16-character password (example: `abcd efgh ijkl mnop`)
   - Remove spaces: `abcdefghijklmnop`

4. **Enable IMAP**
   - Gmail Settings → Forwarding and POP/IMAP
   - Enable IMAP
   - Save changes

## Step 2: Configure .env File

Edit your `.env` file (in the root directory):

```bash
# Email Configuration
BOT_EMAIL_USER=your_bot_email@gmail.com
BOT_EMAIL_PASS=abcdefghijklmnop
BOT_EMAIL_IMAP_SERVER=imap.gmail.com
BOT_EMAIL_IMAP_PORT=993

# You can leave these empty for now (needed later)
CLAIM_TITAN_USER=Beau@forerunnerclaims.com
CLAIM_TITAN_PASS=YOUR_CLAIM_TITAN_PASSWORD
CLAIM_TITAN_URL=https://claimtitan.com/welcome

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AI_PROVIDER=openai
```

## Step 3: Send Test Email

From any email account, send an email TO your bot email with:

**Subject:** `Test claim #12345 - Customer inquiry`

**Body:**
```
Hi team,

Customer John Doe called about his water damage claim. He wants to know:
1. Status of his claim
2. When the adjuster will visit
3. Timeline for payment

Please update the claim notes.

Thanks,
Sarah
```

## Step 4: Run the Test Script

```bash
cd /Users/juanrodriguez/Downloads/forerunner-automation
python3 tests/test_email_monitor.py
```

## What You Should See

### Successful Connection:
```
2024-01-12 16:50:00 - INFO - Connecting to IMAP server: imap.gmail.com:993
2024-01-12 16:50:01 - INFO - IMAP connection established
2024-01-12 16:50:01 - INFO - Authenticating as forerunner.bot@gmail.com
2024-01-12 16:50:02 - INFO - Authentication successful
2024-01-12 16:50:02 - INFO - Selected INBOX
2024-01-12 16:50:02 - INFO - Found 1 unread email(s)
2024-01-12 16:50:02 - INFO - Extracted claim number: 12345
2024-01-12 16:50:02 - INFO - Parsed email from sender@example.com with claim #12345

================================================================================
Found 1 email(s) with claim numbers
================================================================================

Email #1:
  Claim Number: #12345
  From: Sarah Smith <sarah@example.com>
  Subject: Test claim #12345 - Customer inquiry
  Timestamp: 2024-01-12 16:45:00
  Email ID: 12345
  Content Preview:
    Hi team,

    Customer John Doe called about his water damage claim. He wants to know:
    1. Status of his claim
    2. When the adjuster will visit
    3. Timeline for payment
    ...

Mark these emails as read? (y/n):
```

### If No Emails Found:
```
2024-01-12 16:50:00 - INFO - Connecting to IMAP server: imap.gmail.com:993
2024-01-12 16:50:01 - INFO - Authentication successful
2024-01-12 16:50:02 - INFO - No unread emails found
```

This is normal - just send yourself a test email!

## Common Issues

### Authentication Failed
**Error:** `IMAP authentication failed: [AUTHENTICATIONFAILED]`

**Fix:**
- Use App Password, not your regular Gmail password
- Ensure 2FA is enabled
- Check for typos in .env file

### Connection Refused
**Error:** `Failed to connect to email server`

**Fix:**
- Check internet connection
- Verify IMAP is enabled in Gmail settings
- Check firewall settings

### No Claim Number Found
If email shows up but no claim number extracted:
- Ensure subject has `#` followed by 4-6 digits
- Valid: `#1234`, `#12345`, `#123456`
- Invalid: `1234` (no #), `#123` (too short), `#1234567` (too long)

## Testing Checklist

- [ ] Email account created/configured
- [ ] 2FA enabled
- [ ] App password generated
- [ ] IMAP enabled
- [ ] .env file configured with credentials
- [ ] Test email sent with claim number in subject
- [ ] Test script runs without errors
- [ ] Email parsed and claim number extracted
- [ ] Can mark email as read successfully

Once all checks pass, your email monitor is working!
