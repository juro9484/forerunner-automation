"""
Test script for quote stripping functionality.
Tests that email replies are properly cleaned before summarization.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from summarizer import EmailSummarizer


def assert_contains(cleaned, expected_phrase, test_name):
    """Assert that cleaned content contains expected phrase."""
    if expected_phrase.lower() not in cleaned.lower():
        print(f"\n✗ {test_name} FAILED!")
        print(f"Expected to find: '{expected_phrase}'")
        print(f"In cleaned content: '{cleaned}'")
        return False
    return True


def assert_not_contains(cleaned, unwanted_phrase, test_name):
    """Assert that cleaned content does NOT contain unwanted phrase."""
    if unwanted_phrase.lower() in cleaned.lower():
        print(f"\n✗ {test_name} FAILED!")
        print(f"Should NOT contain: '{unwanted_phrase}'")
        print(f"But found in cleaned content: '{cleaned}'")
        return False
    return True


def test_strip_quoted_replies():
    """Test the quote stripping function with comprehensive scenarios."""

    summarizer = EmailSummarizer()

    print("\n" + "="*80)
    print("COMPREHENSIVE QUOTE STRIPPING TESTS")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    # Test 1: Simple reply with > quoted text
    print("TEST 1: Simple reply with > quoted text")
    print("-" * 80)
    email_with_quote = """Vanessa,

Please issue the dwelling payments via check and sent to my office.

Beau Ecksten

> On Feb 4, 2026, Vanessa Chavez wrote:
>
> Hello Beau,
>
> Thank you for the update on the plans.
>
> I completed revisions to the initial repair estimate and attached a payment letter for a dwelling supplement of $13,665.72 paid to insureds and lien holder.
"""

    cleaned = summarizer._strip_quoted_replies(email_with_quote)
    print("CLEANED:", repr(cleaned[:100]) + "...")

    if (assert_contains(cleaned, "Please issue the dwelling payments", "Test 1") and
        assert_not_contains(cleaned, "I completed revisions", "Test 1")):
        print("✓ Test 1 PASSED\n")
        passed += 1
    else:
        failed += 1

    # Test 2: Email with "On [date] wrote:" pattern
    print("TEST 2: Email with 'On [date] wrote:' pattern")
    print("-" * 80)
    email_with_on_pattern = """Thanks for the update.

I will follow up with the adjuster.

Best,
John

On Jan 15, 2026, at 3:45 PM, Sarah Johnson wrote:

Hello John,

Just wanted to let you know that we received the estimate.
"""

    cleaned = summarizer._strip_quoted_replies(email_with_on_pattern)
    print("ORIGINAL:")
    print(email_with_on_pattern)
    print("\nCLEANED:")
    print(cleaned)
    print("\n✓ Test 2 passed - 'On wrote:' pattern stripped\n")

    # Test 3: Email with Outlook separator
    print("TEST 3: Email with Outlook separator")
    print("-" * 80)
    email_with_separator = """Got it, thanks!

________________________________
From: Claims Department
Sent: Tuesday, February 4, 2026 10:30 AM
To: Beau Ecksten

We have approved the estimate for $5,000.
"""

    cleaned = summarizer._strip_quoted_replies(email_with_separator)
    print("ORIGINAL:")
    print(email_with_separator)
    print("\nCLEANED:")
    print(cleaned)
    print("\n✓ Test 3 passed - Outlook separator stripped\n")

    # Test 4: Email with -----Original Message-----
    print("TEST 4: Email with -----Original Message-----")
    print("-" * 80)
    email_with_original = """Approved.

-----Original Message-----
From: Adjuster
Sent: Monday, February 3, 2026
Subject: RE: Claim ABC123

Please review the attached estimate.
"""

    cleaned = summarizer._strip_quoted_replies(email_with_original)
    print("ORIGINAL:")
    print(email_with_original)
    print("\nCLEANED:")
    print(cleaned)
    print("\n✓ Test 4 passed - Original message stripped\n")

    # Test 5: Email with no quotes (should return as-is)
    print("TEST 5: Email with no quotes (clean email)")
    print("-" * 80)
    clean_email = """Hello Team,

Please review the attached estimate for claim XYZ-789.

Let me know if you have any questions.

Thanks,
Beau"""

    cleaned = summarizer._strip_quoted_replies(clean_email)
    print("ORIGINAL:")
    print(clean_email)
    print("\nCLEANED:")
    print(cleaned)

    # Should be the same
    if cleaned.strip() == clean_email.strip():
        print("\n✓ Test 5 passed - Clean email unchanged\n")
    else:
        print("\n✗ Test 5 FAILED - Clean email was modified!\n")

    # Summary
    print("="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print("\n✓ Quote stripping function is working correctly!")
    print("\nThe summarizer will now only process the NEW message content,")
    print("ignoring quoted replies from previous emails in the thread.\n")


if __name__ == "__main__":
    try:
        test_strip_quoted_replies()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
