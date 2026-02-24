"""
Exceptions for Claim Titan adapter.
"""


class ClaimTitanError(Exception):
    """Base exception for Claim Titan adapter errors."""
    pass


class LoginError(ClaimTitanError):
    """Error during login process."""
    pass


class SearchError(ClaimTitanError):
    """Error during claim search."""
    pass


class PostError(ClaimTitanError):
    """Error during note posting."""
    pass


class BrowserError(ClaimTitanError):
    """Error with browser automation."""
    pass
