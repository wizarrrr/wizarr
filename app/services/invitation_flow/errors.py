"""
Simple exception classes for invitation flow operations.
"""


class InvitationFlowError(Exception):
    """Base exception for invitation flow errors."""


class ValidationError(InvitationFlowError):
    """Raised when invitation validation fails."""


class AuthenticationError(InvitationFlowError):
    """Raised when authentication fails."""


class ServerError(InvitationFlowError):
    """Raised when server operations fail."""


class OAuthError(AuthenticationError):
    """Raised when OAuth authentication fails."""
