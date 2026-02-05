"""
ROBUST test script for quote stripping functionality.
Tests complex real-world scenarios with nested replies and edge cases.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from summarizer import EmailSummarizer


def assert_contains(cleaned, expected_phrase, test_name):
    """Assert that cleaned content contains expected phrase."""
    if expected_phrase.lower() not in cleaned.lower():
        print(f"  ✗ FAILED: Expected to find '{expected_phrase}'")
        return False
    return True


def assert_not_contains(cleaned, unwanted_phrase, test_name):
    """Assert that cleaned content does NOT contain unwanted phrase."""
    if unwanted_phrase.lower() in cleaned.lower():
        print(f"  ✗ FAILED: Should NOT contain '{unwanted_phrase}'")
        return False
    return True


def run_test(test_num, description, email_text, should_contain, should_not_contain, summarizer):
    """Run a single test case."""
    print(f"\nTEST {test_num}: {description}")
    print("-" * 80)

    cleaned = summarizer._strip_quoted_replies(email_text)

    # Show cleaned result (truncated)
    preview = cleaned.replace('\n', ' ')[:120]
    print(f"Cleaned: {preview}{'...' if len(cleaned) > 120 else ''}")

    # Validate
    success = True
    for phrase in should_contain:
        if not assert_contains(cleaned, phrase, f"Test {test_num}"):
            success = False

    for phrase in should_not_contain:
        if not assert_not_contains(cleaned, phrase, f"Test {test_num}"):
            success = False

    if success:
        print(f"✓ Test {test_num} PASSED")
        return True
    else:
        print(f"✗ Test {test_num} FAILED")
        print(f"\nFull cleaned content:\n{cleaned}\n")
        return False


def test_comprehensive_quote_stripping():
    """Run comprehensive quote stripping tests."""

    summarizer = EmailSummarizer()

    print("\n" + "="*80)
    print("COMPREHENSIVE QUOTE STRIPPING TESTS")
    print("="*80)

    passed = 0
    total = 0

    # TEST 1: Simple reply with > quotes
    total += 1
    if run_test(
        1,
        "Simple reply with > quoted text",
        """Please issue payments via check.

Thanks,
Beau

> On Feb 4, Vanessa wrote:
> I completed revisions to the estimate.
> Payment letter attached for $13,665.72.""",
        should_contain=["Please issue payments", "Beau"],
        should_not_contain=["I completed revisions", "13,665.72"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 2: Multiple levels of nesting (reply to reply to reply)
    total += 1
    if run_test(
        2,
        "Multiple nested replies (3 levels deep)",
        """Got it, will do.

> On Feb 5, John wrote:
> Thanks for clarifying.
>
> > On Feb 4, Sarah wrote:
> > Please confirm the amount.
> >
> > > On Feb 3, Mike wrote:
> > > The estimate is $5,000.""",
        should_contain=["Got it, will do"],
        should_not_contain=["Thanks for clarifying", "Please confirm", "estimate is $5,000"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 3: Very short reply
    total += 1
    if run_test(
        3,
        "Very short reply (one word)",
        """Approved.

> On Feb 4, Claims Dept wrote:
> Please review and approve the estimate for $10,000.
> Timeline: 2 weeks.
> Let me know if you have questions.""",
        should_contain=["Approved"],
        should_not_contain=["review and approve", "$10,000", "Timeline"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 4: Outlook "On [date] wrote:" pattern
    total += 1
    if run_test(
        4,
        "Outlook 'On [date] wrote:' format",
        """I'll follow up with the adjuster tomorrow.

Best,
John

On Jan 15, 2026, at 3:45 PM, Sarah Johnson <sarah@example.com> wrote:

Hello John,

We received the estimate and are reviewing it now.
Should have feedback by end of week.

Thanks,
Sarah""",
        should_contain=["I'll follow up", "adjuster tomorrow", "John"],
        should_not_contain=["We received the estimate", "end of week", "Sarah"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 5: Outlook separator (_____)
    total += 1
    if run_test(
        5,
        "Outlook horizontal separator",
        """Confirmed, I will send the invoice.

________________________________
From: Claims Department <claims@insurance.com>
Sent: Tuesday, February 4, 2026 10:30 AM
To: Beau Ecksten <beau@forerunner.com>
Subject: RE: Claim ABC123

We have approved the estimate for $5,000.
Please send your invoice.""",
        should_contain=["Confirmed", "send the invoice"],
        should_not_contain=["From: Claims", "approved the estimate", "$5,000"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 6: -----Original Message-----
    total += 1
    if run_test(
        6,
        "Outlook -----Original Message----- format",
        """Sounds good, thank you.

-----Original Message-----
From: Adjuster <adj@company.com>
Sent: Monday, February 3, 2026 9:15 AM
To: Beau Ecksten
Subject: RE: Claim XYZ789

Please review the attached estimate and let us know if you have questions.""",
        should_contain=["Sounds good, thank you"],
        should_not_contain=["Original Message", "review the attached", "let us know"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 7: Mixed quote patterns
    total += 1
    if run_test(
        7,
        "Mixed quote patterns (multiple styles)",
        """I agree with this assessment.

Beau

On Feb 4, Mike wrote:

> Thanks for the update.
>
> > On Feb 3, Sarah wrote:
> > The estimate looks good.

________________________________
From: Original Sender
Sent: Feb 2, 2026

Here is the initial estimate.""",
        should_contain=["I agree with this assessment", "Beau"],
        should_not_contain=["Thanks for the update", "estimate looks good", "initial estimate"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 8: Inline reply (person quotes specific parts and responds)
    total += 1
    if run_test(
        8,
        "Inline reply with interspersed quotes",
        """Thanks for the questions.

> What is the timeline?
Two weeks.

> What about the cost?
$5,000 total.

> When can you start?
Next Monday.

Let me know if you need anything else.

Beau""",
        should_contain=["Thanks for the questions", "Two weeks", "$5,000 total", "Next Monday", "Let me know"],
        should_not_contain=["What is the timeline", "What about the cost", "When can you start"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 9: Reply with long signature
    total += 1
    if run_test(
        9,
        "Reply with complex email signature",
        """Got it, thanks!

--
Beau Ecksten
Senior Claims Consultant
Forerunner Claims Consultants
Phone: (555) 123-4567
Email: beau@forerunner.com
www.forerunnerclaims.com

CONFIDENTIALITY NOTICE: This email may contain privileged information.

> On Feb 4, Insurance Co wrote:
> Your claim has been approved.""",
        should_contain=["Got it, thanks"],
        should_not_contain=["Senior Claims Consultant", "CONFIDENTIALITY", "claim has been approved"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 10: Clean email (no quotes at all)
    total += 1
    if run_test(
        10,
        "Clean email with no quotes (should be unchanged)",
        """Hello Team,

Please review the attached estimate for claim XYZ-789.

Key details:
- Total cost: $15,000
- Timeline: 3 weeks
- Materials included

Let me know if you have any questions.

Thanks,
Beau Ecksten""",
        should_contain=["Hello Team", "XYZ-789", "Total cost: $15,000", "Timeline: 3 weeks", "Beau Ecksten"],
        should_not_contain=[],  # Nothing should be removed
        summarizer=summarizer
    ):
        passed += 1

    # TEST 11: Reply at end of long thread
    total += 1
    if run_test(
        11,
        "New reply at end of very long thread",
        """I will handle this today.

> On Feb 5, Person D wrote:
> Can someone take care of this?
>
> > On Feb 4, Person C wrote:
> > Still waiting on response.
> >
> > > On Feb 3, Person B wrote:
> > > Following up on this.
> > >
> > > > On Feb 2, Person A wrote:
> > > > Original question about the claim.""",
        should_contain=["I will handle this today"],
        should_not_contain=["Can someone take care", "Still waiting", "Following up", "Original question"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 12: Forward with "Begin forwarded message"
    total += 1
    if run_test(
        12,
        "Forwarded email (Apple Mail style)",
        """FYI - see below.

Beau

Begin forwarded message:

From: Claims Adjuster <adjuster@ins.com>
Date: February 4, 2026 at 2:30 PM
To: Beau Ecksten
Subject: Claim Update

Your claim has been processed.""",
        should_contain=["FYI - see below", "Beau"],
        should_not_contain=["Begin forwarded", "From: Claims Adjuster", "claim has been processed"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 13: Empty/whitespace only content after stripping
    total += 1
    if run_test(
        13,
        "Email with only quoted content (edge case)",
        """> On Feb 4, Someone wrote:
> This is the entire message.
> There is nothing new.""",
        should_contain=[],  # May be empty or whitespace
        should_not_contain=["This is the entire message", "nothing new"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 14: Lines of dashes/underscores as separator
    total += 1
    if run_test(
        14,
        "Dashes as separator",
        """Thanks for the info.

----------
Previous message:
The estimate is ready.""",
        should_contain=["Thanks for the info"],
        should_not_contain=["Previous message", "estimate is ready"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 15: Mobile signature patterns
    total += 1
    if run_test(
        15,
        "Mobile email signature",
        """Sounds good!

Sent from my iPhone

> On Feb 4, 2026, at 3:00 PM, John wrote:
> Let's schedule a meeting.""",
        should_contain=["Sounds good"],
        should_not_contain=["Sent from my iPhone", "schedule a meeting"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 16: False positive prevention - "To" and "From" in regular text
    total += 1
    if run_test(
        16,
        "Don't match 'To'/'From' in regular text",
        """I sent this To John yesterday and got a response From Sarah today.

The estimate went From $5,000 To $7,000 due to additional work needed.

Let me know if you need anything else.

Beau

From: Claims Dept <claims@insurance.com>
Sent: Tuesday, February 4, 2026
To: Beau Ecksten <beau@forerunner.com>

Your claim has been approved.""",
        should_contain=["I sent this To John", "From $5,000 To $7,000", "Let me know"],
        should_not_contain=["Your claim has been approved"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 17: Strict email header detection (with actual emails)
    total += 1
    if run_test(
        17,
        "Strict detection of email headers with addresses",
        """Thanks for the update.

I will review and get back to you.

Beau

From: Adjuster Name <adjuster@insurance.com>
To: Beau Ecksten <beau@forerunner.com>
Date: Monday, February 3, 2026 at 2:30 PM
Subject: RE: Claim ABC123

Please review the attached documents.""",
        should_contain=["Thanks for the update", "I will review"],
        should_not_contain=["From: Adjuster", "Please review the attached"],
        summarizer=summarizer
    ):
        passed += 1

    # TEST 18: Newest message on top (latest reply)
    total += 1
    if run_test(
        18,
        "Newest message is at top (latest reply preserved)",
        """This is my latest reply from today.

I just reviewed everything and approve.

Beau

From: John Smith <john@company.com>
Sent: Yesterday
To: Beau

This is an older message from yesterday.
Please review when you can.""",
        should_contain=["latest reply from today", "I just reviewed", "approve"],
        should_not_contain=["older message from yesterday", "Please review when you can"],
        summarizer=summarizer
    ):
        passed += 1

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {(passed/total*100):.1f}%")
    print("="*80 + "\n")

    if passed == total:
        print("🎉 ALL TESTS PASSED!\n")
        print("The quote stripping function is robust and handles:")
        print("  ✓ Simple quotes (>)")
        print("  ✓ Multiple nested levels (3+ deep)")
        print("  ✓ Very short replies (one word)")
        print("  ✓ Outlook formats (On wrote:, separators, Original Message)")
        print("  ✓ Mixed quote patterns")
        print("  ✓ Inline replies")
        print("  ✓ Complex signatures")
        print("  ✓ Forwarded messages (Apple Mail, Outlook)")
        print("  ✓ Strict email header detection (prevents false positives)")
        print("  ✓ Latest message on top (newest reply preserved)")
        print("  ✓ Edge cases (empty content, mobile signatures)")
        print()
        return True
    else:
        print(f"⚠️  {total - passed} test(s) failed. Review output above.\n")
        return False


if __name__ == "__main__":
    try:
        success = test_comprehensive_quote_stripping()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
