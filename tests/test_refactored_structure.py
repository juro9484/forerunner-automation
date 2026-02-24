#!/usr/bin/env python3
"""
Unit tests for refactored structure.
Tests the new adapter pattern, feature loading, and module organization.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestImports(unittest.TestCase):
    """Test that all new modules can be imported."""

    def test_import_outlook_adapter(self):
        """Test importing OutlookAdapter."""
        from adapters.email.outlook.adapter import OutlookAdapter, EmailData
        self.assertIsNotNone(OutlookAdapter)
        self.assertIsNotNone(EmailData)

    def test_import_claim_titan_adapter(self):
        """Test importing ClaimTitanAdapter."""
        from adapters.crm.claim_titan.adapter import ClaimTitanAdapter
        self.assertIsNotNone(ClaimTitanAdapter)

    def test_import_exceptions(self):
        """Test importing exceptions."""
        from adapters.crm.claim_titan.exceptions import (
            ClaimTitanError, LoginError, SearchError, PostError, BrowserError
        )
        self.assertIsNotNone(ClaimTitanError)
        self.assertIsNotNone(LoginError)
        self.assertIsNotNone(SearchError)
        self.assertIsNotNone(PostError)
        self.assertIsNotNone(BrowserError)

    def test_import_features(self):
        """Test importing features."""
        from adapters.crm.claim_titan.features.comments import CommentsFeature
        from adapters.crm.claim_titan.features.contract_addition import ContractAdditionFeature
        self.assertIsNotNone(CommentsFeature)
        self.assertIsNotNone(ContractAdditionFeature)

    def test_import_browser_pool(self):
        """Test importing BrowserPool."""
        from utils.browser_pool import BrowserPool
        self.assertIsNotNone(BrowserPool)

    def test_import_main(self):
        """Test importing main module."""
        import main
        self.assertIsNotNone(main)
        self.assertTrue(hasattr(main, 'main'))
        self.assertTrue(hasattr(main, 'setup_logging'))


class TestConfig(unittest.TestCase):
    """Test configuration and feature flags."""

    def test_config_has_client_id(self):
        """Test that Config has CLIENT_ID."""
        from config import Config
        self.assertTrue(hasattr(Config, 'CLIENT_ID'))
        self.assertIsNotNone(Config.CLIENT_ID)

    def test_config_has_feature_flags(self):
        """Test that Config has all feature flags."""
        from config import Config
        self.assertTrue(hasattr(Config, 'FEATURE_COMMENTS_ENABLED'))
        self.assertTrue(hasattr(Config, 'COMMENTS_UPLOAD_ATTACHMENTS'))
        self.assertTrue(hasattr(Config, 'FEATURE_CONTRACT_ADDITION_ENABLED'))

    def test_feature_flags_are_boolean(self):
        """Test that feature flags are boolean."""
        from config import Config
        self.assertIsInstance(Config.FEATURE_COMMENTS_ENABLED, bool)
        self.assertIsInstance(Config.COMMENTS_UPLOAD_ATTACHMENTS, bool)
        self.assertIsInstance(Config.FEATURE_CONTRACT_ADDITION_ENABLED, bool)


class TestClaimTitanFeatureLoading(unittest.TestCase):
    """Test ClaimTitanAdapter feature loading."""

    @patch('adapters.crm.claim_titan.adapter.sync_playwright')
    def test_adapter_loads_comments_feature_when_enabled(self, mock_playwright):
        """Test that adapter loads CommentsFeature when enabled."""
        from adapters.crm.claim_titan.adapter import ClaimTitanAdapter
        from config import Config

        # Create mock config with comments enabled
        mock_config = Mock()
        mock_config.FEATURE_COMMENTS_ENABLED = True
        mock_config.COMMENTS_UPLOAD_ATTACHMENTS = False
        mock_config.FEATURE_CONTRACT_ADDITION_ENABLED = False
        mock_config.CLAIM_TITAN_USER = "test"
        mock_config.CLAIM_TITAN_PASS = "test"
        mock_config.CLAIM_TITAN_URL = "https://test.com"
        mock_config.BROWSER_HEADLESS = True

        # Mock playwright
        mock_playwright.return_value.start.return_value.chromium.launch.return_value = Mock()

        # Create adapter (don't actually connect)
        adapter = ClaimTitanAdapter.__new__(ClaimTitanAdapter)
        adapter.config = mock_config
        adapter.features = {}
        adapter.logger = Mock()  # Add mock logger
        adapter._load_features()

        # Check that comments feature was loaded
        self.assertIn('comments', adapter.features)

    @patch('adapters.crm.claim_titan.adapter.sync_playwright')
    def test_adapter_loads_contract_feature_when_enabled(self, mock_playwright):
        """Test that adapter loads ContractAdditionFeature when enabled."""
        from adapters.crm.claim_titan.adapter import ClaimTitanAdapter

        # Create mock config with contract addition enabled
        mock_config = Mock()
        mock_config.FEATURE_COMMENTS_ENABLED = False
        mock_config.FEATURE_CONTRACT_ADDITION_ENABLED = True
        mock_config.CLAIM_TITAN_USER = "test"
        mock_config.CLAIM_TITAN_PASS = "test"
        mock_config.CLAIM_TITAN_URL = "https://test.com"
        mock_config.BROWSER_HEADLESS = True

        # Create adapter (don't actually connect)
        adapter = ClaimTitanAdapter.__new__(ClaimTitanAdapter)
        adapter.config = mock_config
        adapter.features = {}
        adapter.logger = Mock()  # Add mock logger
        adapter._load_features()

        # Check that contract addition feature was loaded
        self.assertIn('contract_addition', adapter.features)

    @patch('adapters.crm.claim_titan.adapter.sync_playwright')
    def test_adapter_skips_disabled_features(self, mock_playwright):
        """Test that adapter doesn't load disabled features."""
        from adapters.crm.claim_titan.adapter import ClaimTitanAdapter

        # Create mock config with all features disabled
        mock_config = Mock()
        mock_config.FEATURE_COMMENTS_ENABLED = False
        mock_config.FEATURE_CONTRACT_ADDITION_ENABLED = False
        mock_config.CLAIM_TITAN_USER = "test"
        mock_config.CLAIM_TITAN_PASS = "test"
        mock_config.CLAIM_TITAN_URL = "https://test.com"
        mock_config.BROWSER_HEADLESS = True

        # Create adapter (don't actually connect)
        adapter = ClaimTitanAdapter.__new__(ClaimTitanAdapter)
        adapter.config = mock_config
        adapter.features = {}
        adapter.logger = Mock()  # Add mock logger
        adapter._load_features()

        # Check that no features were loaded
        self.assertEqual(len(adapter.features), 0)

    @patch('adapters.crm.claim_titan.adapter.sync_playwright')
    def test_get_feature_returns_loaded_feature(self, mock_playwright):
        """Test that get_feature() returns loaded features."""
        from adapters.crm.claim_titan.adapter import ClaimTitanAdapter

        # Create mock config
        mock_config = Mock()
        mock_config.FEATURE_COMMENTS_ENABLED = True
        mock_config.COMMENTS_UPLOAD_ATTACHMENTS = False
        mock_config.FEATURE_CONTRACT_ADDITION_ENABLED = False
        mock_config.CLAIM_TITAN_USER = "test"
        mock_config.CLAIM_TITAN_PASS = "test"
        mock_config.CLAIM_TITAN_URL = "https://test.com"
        mock_config.BROWSER_HEADLESS = True

        # Create adapter
        adapter = ClaimTitanAdapter.__new__(ClaimTitanAdapter)
        adapter.config = mock_config
        adapter.features = {}
        adapter.logger = Mock()  # Add mock logger
        adapter._load_features()

        # Test get_feature
        comments_feature = adapter.get_feature('comments')
        self.assertIsNotNone(comments_feature)

        # Test non-existent feature
        fake_feature = adapter.get_feature('nonexistent')
        self.assertIsNone(fake_feature)


class TestExceptions(unittest.TestCase):
    """Test exception hierarchy."""

    def test_exception_inheritance(self):
        """Test that all exceptions inherit from ClaimTitanError."""
        from adapters.crm.claim_titan.exceptions import (
            ClaimTitanError, LoginError, SearchError, PostError, BrowserError
        )

        self.assertTrue(issubclass(LoginError, ClaimTitanError))
        self.assertTrue(issubclass(SearchError, ClaimTitanError))
        self.assertTrue(issubclass(PostError, ClaimTitanError))
        self.assertTrue(issubclass(BrowserError, ClaimTitanError))

    def test_exceptions_can_be_raised(self):
        """Test that exceptions can be raised and caught."""
        from adapters.crm.claim_titan.exceptions import LoginError, ClaimTitanError

        with self.assertRaises(LoginError):
            raise LoginError("Test error")

        with self.assertRaises(ClaimTitanError):
            raise LoginError("Test error")  # Should also catch as parent class


class TestPackageStructure(unittest.TestCase):
    """Test that package structure is correct."""

    def test_adapters_package_exists(self):
        """Test that adapters package exists."""
        import adapters
        self.assertIsNotNone(adapters)

    def test_email_adapters_package_exists(self):
        """Test that email adapters package exists."""
        import adapters.email
        self.assertIsNotNone(adapters.email)

    def test_outlook_adapter_package_exists(self):
        """Test that outlook adapter package exists."""
        import adapters.email.outlook
        self.assertIsNotNone(adapters.email.outlook)

    def test_crm_adapters_package_exists(self):
        """Test that CRM adapters package exists."""
        import adapters.crm
        self.assertIsNotNone(adapters.crm)

    def test_claim_titan_package_exists(self):
        """Test that Claim Titan package exists."""
        import adapters.crm.claim_titan
        self.assertIsNotNone(adapters.crm.claim_titan)

    def test_features_package_exists(self):
        """Test that features package exists."""
        import adapters.crm.claim_titan.features
        self.assertIsNotNone(adapters.crm.claim_titan.features)

    def test_utils_package_exists(self):
        """Test that utils package exists."""
        import utils
        self.assertIsNotNone(utils)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
