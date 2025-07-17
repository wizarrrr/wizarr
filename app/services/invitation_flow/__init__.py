"""
Advanced Invitation Flow System

A clean, modular invitation flow system that integrates seamlessly with existing routes
while providing advanced features for multiple server types and authentication methods.
"""

from .manager import InvitationFlowManager
from .results import AuthResult, InvitationResult, ProcessingStatus
from .server_registry import ServerIntegrationRegistry
from .strategies import (
    AuthenticationStrategy,
    FormBasedStrategy,
    HybridStrategy,
    PlexOAuthStrategy,
)
from .workflows import FormBasedWorkflow, MixedWorkflow, PlexOAuthWorkflow

__all__ = [
    "InvitationFlowManager",
    "AuthenticationStrategy",
    "FormBasedStrategy",
    "PlexOAuthStrategy",
    "HybridStrategy",
    "FormBasedWorkflow",
    "PlexOAuthWorkflow",
    "MixedWorkflow",
    "ServerIntegrationRegistry",
    "InvitationResult",
    "ProcessingStatus",
    "AuthResult",
]
