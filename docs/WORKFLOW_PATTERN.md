# Production Workflow Pattern

## The Golden Rule: Only Mark as Read After SUCCESS

### ❌ WRONG - Mark as Read Immediately
```python
emails = monitor.fetch_unread_emails()
for email in emails:
    monitor.mark_as_read(email.email_id)  # BAD: Marked before processing!

    try:
        summary = summarize(email)
        post_to_claim_titan(summary)
    except Exception:
        # Email is already marked read but NOT processed
        # YOU LOST IT! 💀
        pass
```

**Problem:** If processing fails, the email is gone forever.

---

### ✅ CORRECT - Mark as Read After Success Only

```python
from email_monitor import EmailMonitor
from summarizer import summarize_email
from claim_titan_bot import post_to_claim_titan
import logging

logger = logging.getLogger(__name__)

with EmailMonitor() as monitor:
    emails = monitor.process_emails()

    for email_data in emails:
        logger.info(f"Processing claim #{email_data.claim_number}")

        try:
            # Step 1: Summarize email with AI
            summary = summarize_email(email_data.email_content)

            # Step 2: Post to Claim Titan
            post_to_claim_titan(
                claim_number=email_data.claim_number,
                notes=summary
            )

            # Step 3: Mark in database as SUCCESS
            monitor.mark_email_processed(email_data, status="success")

            # Step 4: Mark as read (ONLY if everything above succeeded)
            monitor.mark_as_read(email_data.email_id)

            logger.info(f"✓ Successfully processed claim #{email_data.claim_number}")

        except Exception as e:
            # Something failed - track it but DON'T mark as read
            logger.error(f"✗ Failed to process claim #{email_data.claim_number}: {e}")

            # Mark in database as FAILED (for tracking)
            monitor.mark_email_processed(
                email_data,
                status="failed",
                error_message=str(e)
            )

            # DON'T mark as read - leave unread for retry
            # Email will be processed again next run
            continue
```

---

## Why This Works

### Scenario 1: Everything Succeeds ✓
```
1. Email arrives (unread)
2. Fetch it
3. Summarize ✓
4. Post to Claim Titan ✓
5. Mark in DB as "success" ✓
6. Mark as read ✓
7. Email disappears from unread (done!)
```

### Scenario 2: AI API Fails
```
1. Email arrives (unread)
2. Fetch it
3. Summarize ✗ FAILS
4. Mark in DB as "failed"
5. DON'T mark as read
6. Email stays unread
7. Next run: Try again ✓
```

### Scenario 3: Claim Titan Down
```
1. Email arrives (unread)
2. Fetch it
3. Summarize ✓
4. Post to Claim Titan ✗ FAILS
5. Mark in DB as "failed"
6. DON'T mark as read
7. Email stays unread
8. Next run: Try again ✓
```

### Scenario 4: Already Processed (Duplicate)
```
1. Email arrives (unread)
2. Check DB → "Already processed successfully"
3. Skip it (database prevents duplicate)
4. Mark as read (safe to mark since we know it's done)
```

---

## Database + Unread = Perfect System

### The Database Tracks:
- ✓ What we processed successfully
- ✓ What failed and why
- ✓ How many times we retried

### Unread Status = Work Queue:
- Unread = "Needs processing"
- Read = "Successfully processed"

### Together They Provide:
- **Duplicate prevention** (database check)
- **Automatic retry** (unread = try again)
- **Audit trail** (database records)
- **Idempotency** (safe to run multiple times)

---

## Handling Retry Limits

Eventually, you want to stop retrying failures:

```python
with EmailMonitor() as monitor:
    emails = monitor.process_emails()

    for email_data in emails:
        # Check how many times we've tried this email
        retry_count = monitor.db.get_retry_count(email_data.email_id)

        if retry_count >= 3:
            logger.warning(f"Email {email_data.email_id} failed {retry_count} times - giving up")

            # Mark as permanently failed and mark as read (stop retrying)
            monitor.mark_email_processed(
                email_data,
                status="failed",
                error_message="Max retries exceeded"
            )
            monitor.mark_as_read(email_data.email_id)

            # Send alert to human
            send_alert(f"Manual review needed for claim #{email_data.claim_number}")
            continue

        # Normal processing...
        try:
            process_email(email_data)
            monitor.mark_email_processed(email_data, status="success")
            monitor.mark_as_read(email_data.email_id)
        except Exception as e:
            # Increment retry count
            monitor.db.increment_retry_count(email_data.email_id)
            monitor.mark_email_processed(email_data, status="failed", error_message=str(e))
            # Leave unread for retry
```

---

## Summary

### The Pattern:
```python
try:
    # Do all processing
    result = process_everything(email)

    # SUCCESS: Mark as processed and read
    mark_email_processed(email, status="success")
    mark_as_read(email.email_id)

except Exception as e:
    # FAILURE: Mark as failed but DON'T mark as read
    mark_email_processed(email, status="failed", error=str(e))
    # Leave unread → automatic retry
```

### The Benefits:
- ✅ No lost emails (failures get retried)
- ✅ No duplicates (database tracks processed)
- ✅ Automatic retry (unread = work queue)
- ✅ Audit trail (database has history)
- ✅ Safe to run anytime (idempotent)

---

**This is the pattern we'll implement in `main.py`**
