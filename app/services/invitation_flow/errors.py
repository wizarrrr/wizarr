"""
Simple exception classes for invitation flow operations.
"""


class InvitationFlowError(Exception):
    """Base exception for invitation flow errors."""

    pass


class ValidationError(InvitationFlowError):
    """Raised when invitation validation fails."""

    pass


class AuthenticationError(InvitationFlowError):
    """Raised when authentication fails."""

    pass


class ServerError(InvitationFlowError):
    """Raised when server operations fail."""

    pass


class OAuthError(AuthenticationError):
    """Raised when OAuth authentication fails."""

    pass
