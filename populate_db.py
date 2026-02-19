import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))

from email_monitor import EmailMonitor
from datetime import datetime, timedelta

print("Connecting to email...")
monitor = EmailMonitor()
monitor.connect()

# Select inbox
print("Selecting inbox...")
status, msg = monitor.imap_connection.select("INBOX")
if status != "OK":
    print(f"Failed to select inbox: {msg}")
    monitor.disconnect()
    exit()

print("Fetching emails from last 60 days...")
since_date = (datetime.now() - timedelta(days=60)).strftime("%d-%b-%Y")
print(f"Searching since: {since_date}")

status, message_ids = monitor.imap_connection.search(None, f'(SINCE {since_date})')
if status != "OK":
    print("Failed to search emails")
    monitor.disconnect()
    exit()

email_ids = message_ids[0].split()
print(f"Found {len(email_ids)} emails")

if len(email_ids) == 0:
    print("No emails found!")
    monitor.disconnect()
    exit()

emails = []
for email_id in email_ids:
    try:
        email_id_str = email_id.decode()
        status, msg_data = monitor.imap_connection.fetch(email_id, "(RFC822)")
        if status == "OK":
            email_data = monitor._parse_email(email_id_str, msg_data[0][1])
            if email_data:
                emails.append(email_data)
    except:
        pass

print(f"Parsed {len(emails)} emails")
emails.sort(key=lambda e: e.timestamp, reverse=True)

print(f"\nMarking {len(emails)-1} old emails as processed...")
for i, email in enumerate(emails):
    if i == 0:
        print(f"  SKIPPING: {email.email_id} - {email.subject}")
        continue
    monitor.db.mark_processed(
        email_id=email.email_id,
        claim_number=email.claim_number or "N/A",
        sender=email.sender,
        subject=email.subject,
        received_timestamp=email.timestamp,
        status="skipped"
    )
    print(f"  Marked: {email.email_id}")

print(f"\nDone!")
monitor.disconnect()
