"""
OAuth authentication helper for Office 365 IMAP access.
Uses Microsoft Authentication Library (MSAL) for token acquisition.
"""

import logging
import base64
from typing import Optional
import msal

from config import Config


class OAuthHelper:
    """
    Handles OAuth token acquisition for Office 365 IMAP access.
    Uses client credentials flow with Application permissions.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize OAuth helper.

        Args:
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
            tenant_id: Azure AD tenant ID
        """
        self.client_id = client_id or Config.AZURE_CLIENT_ID
        self.client_secret = client_secret or Config.AZURE_CLIENT_SECRET
        self.tenant_id = tenant_id or Config.AZURE_TENANT_ID
        self.logger = logging.getLogger(__name__)

        # Validate configuration
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError(
                "OAuth credentials missing. Need AZURE_CLIENT_ID, "
                "AZURE_CLIENT_SECRET, and AZURE_TENANT_ID in .env"
            )

        # MSAL authority URL
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        # Scopes for IMAP access
        # For Application permissions, use .default scope
        self.scopes = ["https://outlook.office365.com/.default"]

    def get_access_token(self) -> str:
        """
        Acquire OAuth access token using client credentials flow.

        Returns:
            Access token string

        Raises:
            Exception: If token acquisition fails
        """
        try:
            self.logger.info("Acquiring OAuth access token...")

            # Create confidential client application
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
            )

            # Acquire token for application (client credentials flow)
            result = app.acquire_token_for_client(scopes=self.scopes)

            if "access_token" in result:
                self.logger.info("Successfully acquired OAuth access token")
                return result["access_token"]
            else:
                error = result.get("error", "Unknown error")
                error_description = result.get("error_description", "")
                error_msg = f"OAuth token acquisition failed: {error} - {error_description}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            self.logger.error(f"Error acquiring OAuth token: {e}")
            raise

    def generate_oauth_string(self, user_email: str, access_token: str) -> bytes:
        """
        Generate XOAUTH2 authentication string for IMAP.

        Args:
            user_email: Email address to authenticate as
            access_token: OAuth access token

        Returns:
            XOAUTH2 auth string as bytes (not base64-encoded for IMAP)
        """
        # Format: user=<email>\x01auth=Bearer <token>\x01\x01
        auth_string = f"user={user_email}\x01auth=Bearer {access_token}\x01\x01"

        # Return as bytes (IMAP's authenticate will handle base64 encoding)
        return auth_string.encode()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try:
        oauth = OAuthHelper()
        token = oauth.get_access_token()
        print(f"✓ Successfully acquired OAuth token")
        print(f"Token (first 50 chars): {token[:50]}...")

        # Generate auth string
        auth_string = oauth.generate_oauth_string(
            Config.BOT_EMAIL_USER, token
        )
        print(f"✓ Generated XOAUTH2 auth string")

    except Exception as e:
        print(f"✗ OAuth test failed: {e}")
