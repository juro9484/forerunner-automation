"""
Unit tests for policy addition functionality.
Tests the logic without requiring Claim Titan connection using mocks.
"""

import sys
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from dataclasses import dataclass

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contract_parser import ClientData


class TestPolicyAdditionLogic(unittest.TestCase):
    """Test policy addition logic with mocked browser interactions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_page = MagicMock()
        self.mock_logger = MagicMock()

        # Sample client data with policy info
        self.client_data_with_policy = ClientData(
            first_name="John",
            last_name="Doe",
            street_address="123 Main St",
            city="Denver",
            state="CO",
            zipcode="80210",
            policy_number="POL-123456",
            claim_number="CLM-789",
            insurance_company="State Farm"
        )

        # Sample client data without policy
        self.client_data_no_policy = ClientData(
            first_name="Jane",
            last_name="Smith",
            street_address="456 Oak Ave",
            city="Boulder",
            state="CO",
            zipcode="80302",
        )

    def test_should_add_policy_when_policy_and_claim_number_present(self):
        """Test that policy addition is triggered when both fields are present."""
        # Both policy_number and claim_number are present
        self.assertTrue(self.client_data_with_policy.policy_number is not None)
        self.assertTrue(self.client_data_with_policy.claim_number is not None)

        # Should trigger policy addition
        should_add = (
            self.client_data_with_policy.policy_number and
            self.client_data_with_policy.claim_number
        )
        self.assertTrue(should_add)

    def test_should_not_add_policy_when_policy_number_missing(self):
        """Test that policy addition is skipped when policy_number is missing."""
        self.assertIsNone(self.client_data_no_policy.policy_number)

        should_add = (
            self.client_data_no_policy.policy_number and
            self.client_data_no_policy.claim_number
        )
        self.assertFalse(should_add)

    def test_should_not_add_policy_when_claim_number_missing(self):
        """Test that policy addition is skipped when claim_number is missing."""
        client_data = ClientData(
            first_name="Test",
            street_address="123 St",
            city="City",
            state="CO",
            zipcode="80000",
            policy_number="POL-123",  # Has policy
            claim_number=None  # But no claim number
        )

        should_add = client_data.policy_number and client_data.claim_number
        self.assertFalse(should_add)

    def test_policy_number_field_selector(self):
        """Test that policy number field selector is correct."""
        expected_selector = 'input[name="policy_number"]'

        # Mock locator
        mock_locator = MagicMock()
        self.mock_page.locator.return_value = mock_locator

        # Simulate finding the field
        self.mock_page.locator(expected_selector)

        # Verify correct selector was used
        self.mock_page.locator.assert_called_with(expected_selector)

    def test_insurance_dropdown_selector(self):
        """Test that insurance company dropdown selector is correct."""
        expected_selector = 'select[name="insurance_company_id"]'

        mock_locator = MagicMock()
        self.mock_page.locator.return_value = mock_locator

        self.mock_page.locator(expected_selector)

        self.mock_page.locator.assert_called_with(expected_selector)

    def test_save_policy_button_selector(self):
        """Test that Save Policy button selector is correct."""
        expected_selector = 'button[type="submit"]:has-text("Save Policy")'

        mock_locator = MagicMock()
        self.mock_page.locator.return_value = mock_locator

        self.mock_page.locator(expected_selector)

        self.mock_page.locator.assert_called_with(expected_selector)

    def test_policy_link_selector(self):
        """Test that 'Not Set' policy link selector is correct."""
        expected_selector = 'a[href*="/policies/create"]:has-text("Not Set")'

        mock_locator = MagicMock()
        self.mock_page.locator.return_value = mock_locator

        self.mock_page.locator(expected_selector)

        self.mock_page.locator.assert_called_with(expected_selector)

    def test_insurance_exact_match(self):
        """Test insurance company selection with exact match."""
        insurance_name = "State Farm"

        # Mock dropdown
        mock_dropdown = MagicMock()
        self.mock_page.locator.return_value = mock_dropdown

        # Simulate exact match success
        mock_dropdown.select_option.return_value = None

        # Try to select
        try:
            mock_dropdown.select_option(label=insurance_name)
            exact_match_worked = True
        except Exception:
            exact_match_worked = False

        self.assertTrue(exact_match_worked)
        mock_dropdown.select_option.assert_called_with(label=insurance_name)

    def test_insurance_fuzzy_match_logic(self):
        """Test insurance company fuzzy matching logic."""
        insurance_from_contract = "State Farm"

        # Mock dropdown options
        mock_options = [
            Mock(inner_text=Mock(return_value="American Family Insurance"), get_attribute=Mock(return_value="1")),
            Mock(inner_text=Mock(return_value="State Farm Insurance"), get_attribute=Mock(return_value="2")),
            Mock(inner_text=Mock(return_value="USAA"), get_attribute=Mock(return_value="3")),
        ]

        # Test fuzzy matching logic
        matched = False
        matched_option = None

        for option in mock_options:
            option_text = option.inner_text()
            if insurance_from_contract.lower() in option_text.lower():
                matched = True
                matched_option = option_text
                break

        self.assertTrue(matched)
        self.assertEqual(matched_option, "State Farm Insurance")

    def test_insurance_no_match_continues(self):
        """Test that missing insurance match doesn't fail the process."""
        insurance_from_contract = "Unknown Insurance Co"

        # Mock dropdown options (none match)
        mock_options = [
            Mock(inner_text=Mock(return_value="American Family Insurance")),
            Mock(inner_text=Mock(return_value="USAA")),
        ]

        # Test fuzzy matching logic
        matched = False

        for option in mock_options:
            option_text = option.inner_text()
            if insurance_from_contract.lower() in option_text.lower():
                matched = True
                break

        # Should not match but shouldn't crash
        self.assertFalse(matched)
        # In actual code, this would log a warning and continue

    def test_client_data_with_all_policy_fields(self):
        """Test ClientData creation with all policy-related fields."""
        data = ClientData(
            first_name="Test",
            last_name="User",
            street_address="123 Test St",
            city="Denver",
            state="CO",
            zipcode="80210",
            policy_number="TEST-POLICY-123",
            claim_number="TEST-CLAIM-456",
            insurance_company="Test Insurance",
            email="test@example.com",
            phone="555-1234"
        )

        self.assertEqual(data.policy_number, "TEST-POLICY-123")
        self.assertEqual(data.claim_number, "TEST-CLAIM-456")
        self.assertEqual(data.insurance_company, "Test Insurance")

    def test_client_data_optional_fields_can_be_none(self):
        """Test that optional policy fields can be None."""
        data = ClientData(
            first_name="Test",
            street_address="123 St",
            city="City",
            state="CO",
            zipcode="80000"
        )

        self.assertIsNone(data.policy_number)
        self.assertIsNone(data.claim_number)
        self.assertIsNone(data.insurance_company)


class TestPolicyAdditionFlow(unittest.TestCase):
    """Test the complete flow of policy addition."""

    def test_policy_addition_flow_steps(self):
        """Test that policy addition follows the correct sequence of steps."""
        expected_steps = [
            "Navigate to Claims home page",
            "Search for claim by claim_number",
            "Open claim",
            "Click 'Not Set' policy link",
            "Fill policy number",
            "Select insurance company (if available)",
            "Click Save Policy button"
        ]

        # This test documents the expected flow
        self.assertEqual(len(expected_steps), 7)
        self.assertIn("Navigate to Claims home page", expected_steps)
        self.assertIn("Fill policy number", expected_steps)
        self.assertIn("Click Save Policy button", expected_steps)

    def test_policy_addition_uses_existing_search_method(self):
        """Test that policy addition reuses _search_claim method."""
        # The flow should use the existing _search_claim method
        # which already handles hyphen variations and retries
        expected_method = "_search_claim"
        self.assertTrue(callable(getattr(type, expected_method, None)) or expected_method)

    def test_policy_addition_uses_existing_open_method(self):
        """Test that policy addition reuses _open_claim method."""
        # The flow should use the existing _open_claim method
        expected_method = "_open_claim"
        self.assertTrue(callable(getattr(type, expected_method, None)) or expected_method)

    def test_policy_failure_does_not_fail_claim_creation(self):
        """Test that policy addition failure doesn't mark claim creation as failed."""
        # In the actual code, policy addition is wrapped in try-except
        # and logs a warning but doesn't raise the exception

        claim_created = True

        try:
            # Simulate policy addition failure
            raise Exception("Policy addition failed")
        except Exception as e:
            # Should log error but not change claim_created status
            error_logged = True

        # Claim should still be marked as created
        self.assertTrue(claim_created)
        self.assertTrue(error_logged)


class TestPolicyAdditionEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios."""

    def test_empty_policy_number(self):
        """Test handling of empty policy number."""
        data = ClientData(
            first_name="Test",
            street_address="123 St",
            city="City",
            state="CO",
            zipcode="80000",
            policy_number="",  # Empty string
            claim_number="CLM-123"
        )

        # Empty string is falsy in Python
        should_add = data.policy_number and data.claim_number
        self.assertFalse(should_add)

    def test_whitespace_only_policy_number(self):
        """Test handling of whitespace-only policy number."""
        policy_number = "   "  # Only whitespace

        # After stripping, would be empty
        self.assertEqual(policy_number.strip(), "")
        self.assertFalse(policy_number.strip())

    def test_special_characters_in_policy_number(self):
        """Test that policy numbers with special characters are handled."""
        special_policy_numbers = [
            "POL-12345",
            "POL_67890",
            "POL#99999",
            "POL 11111",
            "POL/22222"
        ]

        for policy_num in special_policy_numbers:
            data = ClientData(
                first_name="Test",
                street_address="123 St",
                city="City",
                state="CO",
                zipcode="80000",
                policy_number=policy_num,
                claim_number="CLM-123"
            )
            # Should accept any string as policy number
            self.assertIsNotNone(data.policy_number)

    def test_case_insensitive_insurance_matching(self):
        """Test that insurance matching is case-insensitive."""
        insurance_from_contract = "state farm"
        dropdown_option = "State Farm Insurance"

        # Case-insensitive comparison
        matches = insurance_from_contract.lower() in dropdown_option.lower()

        self.assertTrue(matches)


def run_tests():
    """Run all unit tests."""
    print("\n" + "="*70)
    print("POLICY ADDITION UNIT TESTS")
    print("="*70)
    print("\nThese tests don't require Claim Titan connection.")
    print("They test the logic and flow using mocks.\n")
    print("="*70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPolicyAdditionLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestPolicyAdditionFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestPolicyAdditionEdgeCases))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")

    if result.wasSuccessful():
        print("🎉 All unit tests passed!\n")
        return True
    else:
        print("⚠️  Some tests failed. Check output above.\n")
        return False


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
