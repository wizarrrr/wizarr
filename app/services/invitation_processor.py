"""
Unified Invitation Processing System

This module provides a coherent, modular approach to handling all invitation workflows
across different media server types. It follows the app's design principles of being
modular, class-based, and easy to maintain.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from flask import session, redirect, url_for, render_template

from app.extensions import db
from app.models import Invitation, MediaServer
from app.services.invites import is_invite_valid
from app.services.media.service import get_client_for_media_server


class WorkflowType(Enum):
    """Types of invitation workflows"""
    PLEX_OAUTH = "plex_oauth"
    FORM_BASED = "form_based"  
    MIXED = "mixed"


class ProcessingStatus(Enum):
    """Processing result statuses"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    INVALID_INVITATION = "invalid_invitation"


@dataclass
class ServerResult:
    """Result of processing a single server"""
    server: MediaServer
    success: bool
    message: str
    user_created: bool = False


@dataclass
class InvitationResult:
    """Complete result of invitation processing"""
    status: ProcessingStatus
    message: str
    successful_servers: List[ServerResult]
    failed_servers: List[ServerResult]
    redirect_url: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None

    def to_flask_response(self):
        """Convert result to appropriate Flask response"""
        if self.redirect_url:
            return redirect(self.redirect_url)
        elif self.template_data:
            return render_template(**self.template_data)
        else:
            # Default error response
            return render_template("invalid-invite.html", error=self.message)


class ServerTypeDetector:
    """Detects server types and determines appropriate workflows"""
    
    FORM_BASED_SERVERS = {"jellyfin", "emby", "audiobookshelf", "romm", "kavita", "komga"}
    OAUTH_SERVERS = {"plex"}
    
    @classmethod
    def get_workflow_type(cls, servers: List[MediaServer]) -> WorkflowType:
        """Determine the appropriate workflow type for given servers"""
        if not servers:
            return WorkflowType.FORM_BASED
            
        server_types = {server.server_type for server in servers}
        
        has_oauth = bool(server_types & cls.OAUTH_SERVERS)
        has_form = bool(server_types & cls.FORM_BASED_SERVERS)
        
        if has_oauth and has_form:
            return WorkflowType.MIXED
        elif has_oauth:
            return WorkflowType.PLEX_OAUTH
        else:
            return WorkflowType.FORM_BASED
    
    @classmethod
    def get_primary_server_type(cls, servers: List[MediaServer]) -> str:
        """Get the primary server type for template rendering"""
        if not servers:
            return "jellyfin"
        
        # Prefer OAuth servers as primary for workflow routing
        oauth_servers = [s for s in servers if s.server_type in cls.OAUTH_SERVERS]
        if oauth_servers:
            return oauth_servers[0].server_type
            
        # Otherwise use first form-based server
        return servers[0].server_type


class InvitationWorkflow(ABC):
    """Abstract base class for invitation workflows"""
    
    @abstractmethod
    def process(self, invitation: Invitation, servers: List[MediaServer], form_data: Dict[str, Any]) -> InvitationResult:
        """Process the invitation workflow"""
        pass
    
    def _process_servers_batch(self, servers: List[MediaServer], form_data: Dict[str, Any], invitation_code: str) -> Tuple[List[ServerResult], List[ServerResult]]:
        """Process multiple servers and return success/failure lists"""
        successful = []
        failed = []
        
        for server in servers:
            try:
                client = get_client_for_media_server(server)
                ok, msg = client.join(
                    username=form_data.get("username", ""),
                    password=form_data.get("password", ""),
                    confirm=form_data.get("confirm_password", ""),
                    email=form_data.get("email", ""),
                    code=invitation_code,
                )
                
                result = ServerResult(
                    server=server,
                    success=ok,
                    message=msg,
                    user_created=ok
                )
                
                if ok:
                    successful.append(result)
                else:
                    failed.append(result)
                    
            except Exception as exc:
                logging.error(f"Failed to process server {server.name}: {exc}")
                failed.append(ServerResult(
                    server=server,
                    success=False,
                    message=f"Error: {exc}",
                    user_created=False
                ))
        
        return successful, failed


class PlexOAuthWorkflow(InvitationWorkflow):
    """Handles Plex OAuth invitation flow"""
    
    def process(self, invitation: Invitation, servers: List[MediaServer], form_data: Dict[str, Any]) -> InvitationResult:
        """Process Plex OAuth workflow"""
        # For Plex OAuth, we just render the Plex login template
        # The actual processing happens in the /join POST route
        return InvitationResult(
            status=ProcessingStatus.SUCCESS,
            message="Plex OAuth flow initiated",
            successful_servers=[],
            failed_servers=[],
            template_data={
                "template_name_or_list": "user-plex-login.html",
                "code": form_data.get("code")
            }
        )


class FormBasedWorkflow(InvitationWorkflow):
    """Handles form-based invitation workflows (Jellyfin, Emby, etc.)"""
    
    def process(self, invitation: Invitation, servers: List[MediaServer], form_data: Dict[str, Any]) -> InvitationResult:
        """Process form-based workflow"""
        # Validate required form data
        required_fields = ["username", "password", "confirm_password", "email"]
        for field in required_fields:
            if not form_data.get(field):
                return InvitationResult(
                    status=ProcessingStatus.FAILURE,
                    message=f"Missing required field: {field}",
                    successful_servers=[],
                    failed_servers=[]
                )
        
        # Process all servers
        successful, failed = self._process_servers_batch(servers, form_data, invitation.code)
        
        if successful and not failed:
            # Complete success
            session["wizard_access"] = invitation.code
            return InvitationResult(
                status=ProcessingStatus.SUCCESS,
                message="Accounts created successfully on all servers",
                successful_servers=successful,
                failed_servers=failed,
                redirect_url="/wizard/"
            )
        elif successful:
            # Partial success
            session["wizard_access"] = invitation.code
            return InvitationResult(
                status=ProcessingStatus.PARTIAL_SUCCESS,
                message=f"Accounts created on {len(successful)} of {len(servers)} servers",
                successful_servers=successful,
                failed_servers=failed,
                redirect_url="/wizard/"
            )
        else:
            # Complete failure - create a proper form object with error data
            from app.forms.join import JoinForm
            form = JoinForm()
            # Populate form with submitted data
            if 'username' in form_data:
                form.username.data = form_data['username']
            if 'email' in form_data:
                form.email.data = form_data['email']
            if 'code' in form_data:
                form.code.data = form_data['code']
            
            error_messages = [f"{result.server.name}: {result.message}" for result in failed]
            return InvitationResult(
                status=ProcessingStatus.FAILURE,
                message="; ".join(error_messages),
                successful_servers=successful,
                failed_servers=failed,
                template_data={
                    "template_name_or_list": "welcome-jellyfin.html",
                    "form": form,  # Now passing the actual form object
                    "server_type": ServerTypeDetector.get_primary_server_type(servers),
                    "error": "; ".join(error_messages)
                }
            )


class MixedWorkflow(InvitationWorkflow):
    """Handles mixed Plex + other servers workflow"""
    
    def process(self, invitation: Invitation, servers: List[MediaServer], form_data: Dict[str, Any]) -> InvitationResult:
        """Process mixed workflow - starts with Plex OAuth"""
        # For mixed workflows, we start with Plex OAuth
        # The form-based servers will be processed later in the password prompt flow
        return InvitationResult(
            status=ProcessingStatus.SUCCESS,
            message="Mixed workflow initiated with Plex OAuth",
            successful_servers=[],
            failed_servers=[],
            template_data={
                "template_name_or_list": "user-plex-login.html",
                "code": invitation.code
            }
        )


class InvitationProcessor:
    """Central processor for all invitation workflows"""
    
    def __init__(self):
        self.workflows = {
            WorkflowType.PLEX_OAUTH: PlexOAuthWorkflow(),
            WorkflowType.FORM_BASED: FormBasedWorkflow(),
            WorkflowType.MIXED: MixedWorkflow()
        }
    
    def process_invitation_display(self, code: str) -> InvitationResult:
        """Process invitation display (GET /j/<code>)"""
        # Validate invitation
        valid, msg = is_invite_valid(code)
        if not valid:
            return InvitationResult(
                status=ProcessingStatus.INVALID_INVITATION,
                message=msg,
                successful_servers=[],
                failed_servers=[],
                template_data={
                    "template_name_or_list": "invalid-invite.html",
                    "error": msg
                }
            )
        
        # Get invitation and servers
        invitation = Invitation.query.filter(
            db.func.lower(Invitation.code) == code.lower()
        ).first()
        
        servers = self._get_invitation_servers(invitation)
        workflow_type = ServerTypeDetector.get_workflow_type(servers)
        
        # For display, we show the appropriate template based on workflow type
        if workflow_type == WorkflowType.PLEX_OAUTH:
            return InvitationResult(
                status=ProcessingStatus.SUCCESS,
                message="Plex invitation display",
                successful_servers=[],
                failed_servers=[],
                template_data={
                    "template_name_or_list": "user-plex-login.html",
                    "code": code
                }
            )
        else:
            # Form-based or mixed (which starts with form)
            from app.forms.join import JoinForm
            form = JoinForm()
            form.code.data = code
            
            return InvitationResult(
                status=ProcessingStatus.SUCCESS,
                message="Form-based invitation display",
                successful_servers=[],
                failed_servers=[],
                template_data={
                    "template_name_or_list": "welcome-jellyfin.html",
                    "form": form,
                    "server_type": ServerTypeDetector.get_primary_server_type(servers)
                }
            )
    
    def process_invitation_submission(self, form_data: Dict[str, Any]) -> InvitationResult:
        """Process invitation form submission"""
        code = form_data.get("code")
        if not code:
            return InvitationResult(
                status=ProcessingStatus.FAILURE,
                message="Missing invitation code",
                successful_servers=[],
                failed_servers=[]
            )
        
        # Validate invitation
        valid, msg = is_invite_valid(code)
        if not valid:
            return InvitationResult(
                status=ProcessingStatus.INVALID_INVITATION,
                message=msg,
                successful_servers=[],
                failed_servers=[]
            )
        
        # Get invitation and servers
        invitation = Invitation.query.filter(
            db.func.lower(Invitation.code) == code.lower()
        ).first()
        
        servers = self._get_invitation_servers(invitation)
        workflow_type = ServerTypeDetector.get_workflow_type(servers)
        
        # Process with appropriate workflow
        workflow = self.workflows[workflow_type]
        return workflow.process(invitation, servers, form_data)
    
    def _get_invitation_servers(self, invitation: Invitation) -> List[MediaServer]:
        """Get all servers associated with an invitation"""
        if invitation.servers:
            return list(invitation.servers)
        elif invitation.server:
            return [invitation.server]
        else:
            # Fallback to first available server
            default_server = MediaServer.query.first()
            return [default_server] if default_server else []