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

    # Application Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"

    # Email Processing Configuration
    # Matches: #12345, #12-345, 12345, 12-345 (keeps hyphens)
    CLAIM_NUMBER_PATTERN: str = r"#?(\d{2,3}-?\d{3,4})"
    EMAIL_CHECK_INTERVAL: int = 300  # 5 minutes in seconds
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    SCREENSHOTS_DIR: Path = PROJECT_ROOT / "screenshots"
    DATA_DIR: Path = PROJECT_ROOT / "data"
    DATABASE_PATH: Path = DATA_DIR / "automation.db"

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
