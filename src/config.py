"""
Configuration module for Forerunner Claims Automation.
Loads all settings from environment variables and provides centralized access.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """
    Centralized configuration class.
    All sensitive credentials are loaded from environment variables.
    """

    # Claim Titan Configuration
    CLAIM_TITAN_USER: str = os.getenv("CLAIM_TITAN_USER", "")
    CLAIM_TITAN_PASS: str = os.getenv("CLAIM_TITAN_PASS", "")
    CLAIM_TITAN_URL: str = os.getenv("CLAIM_TITAN_URL", "https://claimtitan.com/welcome")

    # Bot Email Configuration
    BOT_EMAIL_USER: str = os.getenv("BOT_EMAIL_USER", "")
    BOT_EMAIL_PASS: str = os.getenv("BOT_EMAIL_PASS", "")
    BOT_EMAIL_IMAP_SERVER: str = os.getenv("BOT_EMAIL_IMAP_SERVER", "imap.gmail.com")
    BOT_EMAIL_IMAP_PORT: int = int(os.getenv("BOT_EMAIL_IMAP_PORT", "993"))

    # OAuth Configuration
    USE_OAUTH: bool = os.getenv("USE_OAUTH", "false").lower() == "true"
    AZURE_CLIENT_ID: Optional[str] = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET: Optional[str] = os.getenv("AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID: Optional[str] = os.getenv("AZURE_TENANT_ID")

    # AI Provider Configuration
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai").lower()
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # Claude Model Configuration (with automatic fallback)
    # Primary model to use - can be overridden via CLAUDE_MODEL env var
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    # Vision model for PDF/image processing - can be overridden via CLAUDE_VISION_MODEL env var
    # Defaults to Opus 4.5 which has superior vision capabilities
    CLAUDE_VISION_MODEL: str = os.getenv("CLAUDE_VISION_MODEL", "claude-opus-4-5-20251101")

    # Fallback models if primary fails (tries in order)
    CLAUDE_FALLBACK_MODELS: list = [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
    ]

    # Application Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"

    # Email Processing Configuration
    # Matches: #12345, 12-345, CACHO-8192398023, 75-79F3-75F, etc.
    # Very permissive pattern: any uppercase alphanumeric 5+ chars with optional hyphens
    # Case-insensitive to handle lowercase in emails (will be normalized to uppercase)
    CLAIM_NUMBER_PATTERN: str = r"(?i)#?([A-Z0-9-]{5,})"
    EMAIL_CHECK_INTERVAL: int = 300  # 5 minutes in seconds
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Paths
    # PROJECT_ROOT = where the code lives (e.g., /opt/forerunner-automation)
    PROJECT_ROOT: Path = Path(__file__).parent.parent

    # DATA_ROOT = where client data lives (e.g., /opt/clients/forerunner)
    # Uses current working directory, which systemd sets via WorkingDirectory
    DATA_ROOT: Path = Path(os.getcwd())

    # All data directories use DATA_ROOT so each client has separate data
    LOGS_DIR: Path = DATA_ROOT / "logs"
    SCREENSHOTS_DIR: Path = DATA_ROOT / "screenshots"
    DATA_DIR: Path = DATA_ROOT / "data"
    DATABASE_PATH: Path = DATA_DIR / "automation.db"
    ATTACHMENTS_TEMP_DIR: Path = DATA_ROOT / "temp_attachments"
    DOCUMENTS_DIR: Path = DATA_ROOT / "documents"
    UPLOAD_ATTACHMENTS_TO_CRM: bool = os.getenv("UPLOAD_ATTACHMENTS_TO_CRM", "false").lower() == "true"

    # Client identification (for multi-client deployments)
    CLIENT_ID: str = os.getenv("CLIENT_ID", "forerunner_claims")

    # Feature Flags - enable/disable features per client
    FEATURE_COMMENTS_ENABLED: bool = os.getenv("FEATURE_COMMENTS_ENABLED", "true").lower() == "true"
    COMMENTS_UPLOAD_ATTACHMENTS: bool = os.getenv("COMMENTS_UPLOAD_ATTACHMENTS", "false").lower() == "true"
    FEATURE_CONTRACT_ADDITION_ENABLED: bool = os.getenv("FEATURE_CONTRACT_ADDITION_ENABLED", "true").lower() == "true"
    FEATURE_CHECK_DEPOSIT_ENABLED: bool = os.getenv("FEATURE_CHECK_DEPOSIT_ENABLED", "true").lower() == "true"

    # Email Notification Configuration
    NOTIFICATIONS_ENABLED: bool = os.getenv("NOTIFICATIONS_ENABLED", "false").lower() == "true"
    NOTIFICATION_SMTP_SERVER: str = os.getenv("NOTIFICATION_SMTP_SERVER", "smtp.gmail.com")
    NOTIFICATION_SMTP_PORT: int = int(os.getenv("NOTIFICATION_SMTP_PORT", "587"))
    NOTIFICATION_FROM_EMAIL: str = os.getenv("NOTIFICATION_FROM_EMAIL", "")
    NOTIFICATION_FROM_PASSWORD: str = os.getenv("NOTIFICATION_FROM_PASSWORD", "")
    NOTIFICATION_TO_EMAILS: list = os.getenv(
        "NOTIFICATION_TO_EMAILS",
        "juanrod2000@gmail.com,juan@roaksystems.com,support@roaksystems.com,leif@roaksystems.com"
    ).split(",")

    # Healthchecks.io Configuration
    HEALTHCHECKS_ENABLED: bool = os.getenv("HEALTHCHECKS_ENABLED", "false").lower() == "true"
    HEALTHCHECKS_PING_URL: str = os.getenv("HEALTHCHECKS_PING_URL", "")

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration values are present.

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        required_fields = [
            ("CLAIM_TITAN_USER", cls.CLAIM_TITAN_USER),
            ("CLAIM_TITAN_PASS", cls.CLAIM_TITAN_PASS),
            ("BOT_EMAIL_USER", cls.BOT_EMAIL_USER),
            ("BOT_EMAIL_PASS", cls.BOT_EMAIL_PASS),
        ]

        missing_fields = []
        for field_name, field_value in required_fields:
            if not field_value:
                missing_fields.append(field_name)

        if missing_fields:
            logging.error(f"Missing required configuration: {', '.join(missing_fields)}")
            return False

        # Validate AI provider configuration
        if cls.AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            logging.error("OPENAI_API_KEY is required when AI_PROVIDER is 'openai'")
            return False
        elif cls.AI_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            logging.error("ANTHROPIC_API_KEY is required when AI_PROVIDER is 'anthropic'")
            return False

        return True

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.SCREENSHOTS_DIR.mkdir(exist_ok=True)
        cls.DATA_DIR.mkdir(exist_ok=True)


# Initialize directories on module load
Config.ensure_directories()
