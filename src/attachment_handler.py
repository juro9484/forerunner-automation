"""
Attachment handling module for Forerunner Claims Automation.
Handles downloading, categorizing, and managing email attachments.
"""

import logging
import os
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
from email.message import Message
import anthropic

from config import Config


@dataclass
class AttachmentData:
    """
    Structured data for an email attachment.

    Attributes:
        filename: Original filename from email
        file_path: Path where file is saved locally
        file_size: Size in bytes
        content_type: MIME type (e.g., application/pdf, image/jpeg)
        category: AI-determined category (estimates, photos, policy, etc.)
        description: AI-generated description of the attachment
    """
    filename: str
    file_path: str
    file_size: int
    content_type: str
    category: Optional[str] = None
    description: Optional[str] = None


class AttachmentHandler:
    """
    Handles downloading and processing email attachments.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = Config.ATTACHMENTS_TEMP_DIR
        self.documents_dir = Config.DOCUMENTS_DIR

        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Claude client for categorization
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def extract_attachments(self, message: Message, email_id: str) -> List[AttachmentData]:
        """
        Extract and download all attachments from an email message.

        Args:
            message: Email message object
            email_id: Unique email identifier

        Returns:
            List of AttachmentData objects
        """
        attachments = []

        try:
            for part in message.walk():
                # Skip non-attachment parts
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue

                filename = part.get_filename()
                if not filename:
                    continue

                # Skip tiny files (likely signatures/logos)
                content = part.get_payload(decode=True)
                if not content or len(content) < 1024:  # Skip files < 1KB
                    self.logger.debug(f"Skipping tiny file: {filename}")
                    continue

                # Save to temp directory
                safe_filename = self._sanitize_filename(filename)
                temp_path = self.temp_dir / f"{email_id}_{safe_filename}"

                with open(temp_path, 'wb') as f:
                    f.write(content)

                attachment = AttachmentData(
                    filename=filename,
                    file_path=str(temp_path),
                    file_size=len(content),
                    content_type=part.get_content_type()
                )

                attachments.append(attachment)
                self.logger.info(f"Downloaded attachment: {filename} ({len(content)} bytes)")

        except Exception as e:
            self.logger.error(f"Error extracting attachments: {e}")

        return attachments

    def match_attachments_to_folders(
        self,
        attachments: List[AttachmentData],
        available_folders: List[str],
        email_summary: str
    ) -> Dict[str, str]:
        """
        Use Claude to match attachments to CRM folders.

        Args:
            attachments: List of attachment data
            available_folders: Folder names scraped from CRM
            email_summary: The email summary generated earlier (for context)

        Returns:
            Dictionary mapping filename to folder name
            Example: {"estimate.pdf": "Estimates", "photo1.jpg": "Photos"}
        """
        self.logger.info(f"Matching {len(attachments)} attachments to folders")

        # Build attachment list for prompt
        attachment_list = []
        for att in attachments:
            attachment_list.append(f"- {att.filename} (type: {att.content_type})")

        # Build prompt
        prompt = f"""You must match each attachment to exactly ONE folder from this list of available folders.

Available folders (copy these EXACTLY):
{json.dumps(available_folders, indent=2)}

Attachments to categorize:
{chr(10).join(attachment_list)}

Email context:
{email_summary[:500]}

Return ONLY valid JSON in this exact format:
{{
  "filename1.ext": "Exact Folder Name",
  "filename2.ext": "Exact Folder Name"
}}

Rules:
- Use EXACT folder name from the available list (copy it character-for-character)
- Every attachment MUST be matched to exactly one folder
- If no good match exists, choose the most general folder or one named "Other" or "Documents"
- Never invent folder names that aren't in the available list
- Common patterns:
  * PDFs with "estimate" → folders like "Estimates" or "Repair Estimates"
  * Images (jpg, png) → folders like "Photos" or "Images"
  * Invoices → folders like "Invoices" or "Billing"
  * Policies → folders like "Policy" or "Policy Documents"
  * Email correspondence → folders like "Correspondence" or "Emails"
"""

        try:
            # Call Claude - using configurable model from Config.CLAUDE_MODEL
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse response
            content = response.content[0].text.strip()

            # Extract JSON from response (might be wrapped in markdown)
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content

            matches = json.loads(json_str)

            # Validate that all folders exist
            validated_matches = {}
            for filename, folder in matches.items():
                if folder in available_folders:
                    validated_matches[filename] = folder
                    self.logger.info(f"✓ Matched {filename} → {folder}")
                else:
                    self.logger.error(f"✗ Claude returned invalid folder '{folder}' for {filename}")
                    self.logger.error(f"Available folders: {available_folders}")
                    # Try to find a fallback
                    fallback = self._find_fallback_folder(available_folders)
                    if fallback:
                        validated_matches[filename] = fallback
                        self.logger.warning(f"Using fallback folder '{fallback}' for {filename}")

            return validated_matches

        except Exception as e:
            self.logger.error(f"Error matching attachments to folders: {e}")
            # Return empty dict - caller should handle this
            return {}

    def move_to_permanent_storage(
        self,
        attachment: AttachmentData,
        claim_number: str,
        folder_name: str
    ) -> str:
        """
        Move attachment from temp to permanent storage.

        Args:
            attachment: Attachment data
            claim_number: Claim number
            folder_name: Folder/category name

        Returns:
            Path to permanent location
        """
        # Create claim directory
        claim_dir = self.documents_dir / claim_number / folder_name
        claim_dir.mkdir(parents=True, exist_ok=True)

        # Add timestamp to filename to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = self._sanitize_filename(attachment.filename)
        new_filename = f"{timestamp}_{safe_filename}"

        permanent_path = claim_dir / new_filename

        # Move file
        import shutil
        shutil.move(attachment.file_path, str(permanent_path))

        self.logger.info(f"Moved {attachment.filename} to {permanent_path}")

        return str(permanent_path)

    def cleanup_temp_file(self, file_path: str):
        """Delete a temporary file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe filesystem storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove/replace unsafe characters
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe_name = filename
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')

        return safe_name

    def _find_fallback_folder(self, available_folders: List[str]) -> Optional[str]:
        """
        Find a reasonable fallback folder from available options.

        Args:
            available_folders: List of folder names

        Returns:
            Best fallback folder name, or None
        """
        # Prefer generic folders
        preferences = ['Other', 'Documents', 'General', 'Miscellaneous', 'Files']

        for pref in preferences:
            for folder in available_folders:
                if pref.lower() in folder.lower():
                    return folder

        # If no generic folder, just use the first one
        return available_folders[0] if available_folders else None
