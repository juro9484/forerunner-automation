"""
Test script for the email summarizer module.
Tests Claude AI integration and summary generation.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config
from email_monitor import EmailData
from summarizer import EmailSummarizer


def setup_logging():
    """Configure logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_with_sample_email():
    """Test the summarizer with a sample insurance email."""
    print("\n" + "="*70)
    print("TEST 1: Sample Insurance Claim Email")
    print("="*70 + "\n")

    # Create sample email data (similar to real examples)
    sample_email = EmailData(
        claim_number="23-456",
        email_content="""
        Hi Sly,

        Following up on the repair estimate and demand letter we submitted on August 27th.

        State Farm is required to respond within 15 days under CA Regulation 2695.5(b),
        which has now lapsed.

        Can you confirm:
        - New adjuster assignment
        - Supervisor contact info per Insurance Code Section 14047
        - Contractor name, report, and photos from prior inspection (withholding violates CA Insurance Code 2071)

        Also concerned about the unauthorized property visit. We need the contractor present
        at the scheduled reinspection on October 7th.

        Thanks,
        Beau
        Forerunner Claims
        """,
        sender="beau@forerunnerclaims.com",
        recipient="sly@statefarm.com",
        subject="Re: Claim 23-456 - Follow up on pending response",
        timestamp=datetime(2025, 9, 12, 10, 30),
        email_id="msg_001"
    )

    try:
        # Initialize summarizer
        print("Initializing EmailSummarizer with Claude...")
        summarizer = EmailSummarizer()

        # Generate summary
        print(f"Sending email to Claude API for summarization...")
        print(f"Claim Number: {sample_email.claim_number}")
        print(f"From: {sample_email.sender}")
        print(f"Subject: {sample_email.subject}\n")

        summary = summarizer.summarize_email(sample_email)

        # Display results
        print("\n" + "="*70)
        print("SUMMARY GENERATED SUCCESSFULLY")
        print("="*70 + "\n")

        print("CRM NOTE FORMAT:")
        print("-" * 70)
        print(summarizer.format_for_crm(summary))
        print("-" * 70)

        print("\n" + "="*70)
        print("METADATA")
        print("="*70)
        print(f"Claim Number: {summary.claim_number}")
        print(f"Model Used: {summary.model_used}")
        print(f"Generated: {summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nTitle: {summary.title}")
        print(f"\nDescription Length: {len(summary.description)} characters")

        print("\n✅ TEST PASSED\n")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        logging.exception("Test failed with exception:")
        return False


def test_with_detailed_email():
    """Test with a detailed email with multiple questions and amounts."""
    print("\n" + "="*70)
    print("TEST 2: Detailed Email with Multiple Questions")
    print("="*70 + "\n")

    short_email = EmailData(
        claim_number="24-789",
        email_content="""
        Hi Beau,

        I'll deposit the checks and pay your invoice.

        What does the $20,000 for "misc cleaning items changes" cover?

        The $4,579 HVAC cleaning payment is about $30,000 short of what's needed to replace
        the ducts and units for proper remediation. What's State Farm's reasoning?

        FYI - the $20,000 advance was used for clothes and rent. Was the $10,873 payment
        for Dylan's work? My calculation shows $9,127 still owed for his fees.

        Also need reimbursement for $5,280 brush clearing and $800 pool draining.

        I've attached an updated personal property spreadsheet and receipt links.
        Still waiting on ALE payments.

        Dorothy
        """,
        sender="dorothy@email.com",
        recipient="beau@forerunnerclaims.com",
        subject="Re: Claim 24-789 - Payment questions",
        timestamp=datetime(2025, 10, 27, 15, 20),
        email_id="msg_002"
    )

    try:
        print("Initializing EmailSummarizer...")
        summarizer = EmailSummarizer()

        print(f"Generating summary for claim {short_email.claim_number}...\n")
        summary = summarizer.summarize_email(short_email)

        print("\nCRM NOTE FORMAT:")
        print("-" * 70)
        print(summarizer.format_for_crm(summary))
        print("-" * 70)

        print("\n✅ TEST PASSED\n")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        logging.exception("Test failed with exception:")
        return False


def test_config_validation():
    """Test that configuration is properly set up."""
    print("\n" + "="*70)
    print("TEST 0: Configuration Validation")
    print("="*70 + "\n")

    print("Checking configuration...")
    print(f"AI Provider: {Config.AI_PROVIDER}")
    print(f"Anthropic API Key: {'✓ Set' if Config.ANTHROPIC_API_KEY else '✗ Missing'}")

    if Config.AI_PROVIDER != "anthropic":
        print(f"\n⚠️  WARNING: AI_PROVIDER is set to '{Config.AI_PROVIDER}'")
        print("    Should be 'anthropic' to use Claude")
        print("    Update your .env file: AI_PROVIDER=anthropic\n")
        return False

    if not Config.ANTHROPIC_API_KEY or Config.ANTHROPIC_API_KEY == "sk-ant-your-anthropic-key":
        print(f"\n❌ ERROR: ANTHROPIC_API_KEY not configured properly")
        print("    Please set a valid API key in your .env file\n")
        return False

    print("\n✅ Configuration valid\n")
    return True


def main():
    """Run all tests."""
    setup_logging()

    print("\n" + "="*70)
    print("EMAIL SUMMARIZER TEST SUITE")
    print("="*70)

    # Run tests
    results = []

    # Test 0: Config validation
    results.append(("Configuration", test_config_validation()))

    if not results[0][1]:
        print("\n❌ Configuration test failed. Fix configuration before running other tests.\n")
        return

    # Test 1: Sample email
    results.append(("Sample Email Test", test_with_sample_email()))

    # Test 2: Detailed email
    results.append(("Detailed Email Test", test_with_detailed_email()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    print("="*70 + "\n")

    if total_passed == total_tests:
        print("🎉 All tests passed! The summarizer is ready to use.\n")
    else:
        print("⚠️  Some tests failed. Check the error messages above.\n")


if __name__ == "__main__":
    main()
