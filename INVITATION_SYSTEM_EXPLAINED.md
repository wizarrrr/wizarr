# Wizarr Invitation System - Complete Guide

## Overview

The Wizarr invitation system has been completely redesigned with a clean, object-oriented architecture that supports multiple media server types and authentication methods while maintaining the simple `/j/<code>` user experience.

## 🧭 What We Removed (Cleanup)

### Overcomplicated Components Removed:
- **`app/services/invitation_flow/`** (old complex system) - Complex system with metrics, migrations, CLI tools
- **`app/cli/`** - Entire CLI directory with invitation management commands  
- **`app/services/invitation_processor.py`** - Old monolithic processor
- **`app/blueprints/public/routes_simple.py`** - Example file
- **`app/blueprints/public/routes_new.py`** - Unused new routes file

### What Remains (Clean & Simple):
- **`app/services/invitation_flow/`** - Advanced system with clean architecture
- **`app/blueprints/public/routes.py`** - Updated to use new system
- **`app/templates/hybrid-password-form.html`** - Template for mixed auth scenarios
- **`tests/invitation_flow/`** - Comprehensive test suite

## 🧪 Testing Suite

### Test Coverage
The invitation flow system includes comprehensive testing:

- **Unit Tests** (`test_*.py`):
  - `test_manager.py` - InvitationFlowManager tests
  - `test_strategies.py` - Authentication strategy tests
  - `test_workflows.py` - Workflow execution tests
  - `test_server_registry.py` - Server integration tests
  - `test_results.py` - Result object tests

- **Integration Tests** (`test_integration.py`):
  - Complete flow testing
  - Multi-server scenarios
  - Error recovery testing
  - Session management

- **End-to-End Tests** (`test_routes.py`):
  - HTTP request/response testing
  - Route security testing
  - Session handling
  - Error scenarios

### Running Tests
```bash
# Run all tests
pytest tests/invitation_flow/

# Run specific test categories
python tests/invitation_flow/test_runner.py unit
python tests/invitation_flow/test_runner.py integration
python tests/invitation_flow/test_runner.py routes

# Run with coverage
python tests/invitation_flow/test_runner.py coverage
```

### Test Features
- **Comprehensive Mocking** - All external dependencies mocked
- **Database Integration** - Real database testing with cleanup
- **Session Testing** - Flask session management verification
- **Error Scenarios** - Extensive error condition testing
- **Performance Testing** - Basic performance characteristics
- **Security Testing** - XSS, CSRF, and injection protection


## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                              │
│                     GET /j/<code>                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                InvitationFlowManager                            │
│            (Central Orchestrator)                               │
│  • process_invitation_display()                                 │
│  • process_invitation_submission()                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────▼───────────┐
          │   Server Detection    │
          │   & Workflow Choice   │
          └───────────┬───────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │        Authentication             │
    │         Strategies                │
    │  ┌─────────────────────────────┐  │
    │  │  FormBasedStrategy          │  │
    │  │  PlexOAuthStrategy          │  │
    │  │  HybridStrategy             │  │
    │  └─────────────────────────────┘  │
    └─────────────────┬─────────────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │           Workflows               │
    │  ┌─────────────────────────────┐  │
    │  │  FormBasedWorkflow          │  │
    │  │  PlexOAuthWorkflow          │  │
    │  │  MixedWorkflow              │  │
    │  └─────────────────────────────┘  │
    └─────────────────┬─────────────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │        User Account              │
    │        Provisioning              │
    │  ┌─────────────────────────────┐  │
    │  │  Media Server Clients       │  │
    │  │  (Plex, Jellyfin, Emby,     │  │
    │  │   AudiobookShelf, etc.)     │  │
    │  └─────────────────────────────┘  │
    └─────────────────┬─────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Response                                     │
│  • Flask Response (template or redirect)                       │
│  • Session data for wizard access                              │
│  • User accounts created on servers                            │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. InvitationFlowManager (`manager.py`)
**Purpose**: Central orchestrator for all invitation processing

**Key Methods**:
- `process_invitation_display(code)` - Handles GET `/j/<code>` 
- `process_invitation_submission(form_data)` - Handles POST form submissions

**How it works**:
1. Validates invitation code
2. Detects server types (Plex, Jellyfin, Emby, etc.)
3. Chooses appropriate authentication strategy
4. Delegates to workflow for processing
5. Returns unified `InvitationResult`

### 2. Authentication Strategies (`strategies.py`)
**Purpose**: Handle different authentication methods

**Strategy Pattern Implementation**:
- **`FormBasedStrategy`**: Username/password forms (Jellyfin, Emby, AudiobookShelf)
- **`PlexOAuthStrategy`**: Plex OAuth flow integration
- **`HybridStrategy`**: Mixed scenarios (Plex + local servers)

**How strategies work**:
```python
class AuthenticationStrategy:
    def authenticate(self, form_data: Dict[str, Any]) -> AuthResult:
        # Each strategy implements its own auth logic
        pass
```

### 3. Workflows (`workflows.py`)
**Purpose**: Orchestrate multi-step processes

**Workflow Types**:
- **`FormBasedWorkflow`**: Simple form → create accounts → redirect to wizard
- **`PlexOAuthWorkflow`**: Show Plex login → handle OAuth → redirect to wizard
- **`MixedWorkflow`**: Plex OAuth → password form → create local accounts → wizard

**How workflows work**:
```python
class InvitationWorkflow:
    def execute(self, invitation: Invitation, form_data: Dict[str, Any]) -> InvitationResult:
        # Each workflow implements its own process
        pass
```

### 4. Server Registry (`server_registry.py`)
**Purpose**: Manage server integrations and capabilities

**Features**:
- Maps server types to authentication methods
- Handles server-specific account creation
- Manages library permissions and access

### 5. Results System (`results.py`)
**Purpose**: Unified response handling

**Result Types**:
- **`InvitationResult`**: Main result with status, messages, and template data
- **`ProcessingStatus`**: Enum for success/failure states
- **`to_flask_response()`**: Converts results to Flask responses

## 🔄 How the System Works

### Scenario 1: Pure Jellyfin Invitation
```
User clicks: /j/ABC123
↓
Manager detects: Jellyfin server only
↓
Strategy chosen: FormBasedStrategy
↓
Workflow chosen: FormBasedWorkflow
↓
User sees: Registration form
↓
User submits: username, password, email
↓
System creates: Jellyfin account
↓
Result: Redirect to wizard
```

### Scenario 2: Pure Plex Invitation
```
User clicks: /j/XYZ789
↓
Manager detects: Plex server only
↓
Strategy chosen: PlexOAuthStrategy
↓
Workflow chosen: PlexOAuthWorkflow
↓
User sees: Plex login button
↓
User clicks: Plex OAuth flow
↓
System processes: OAuth token
↓
Result: Redirect to wizard
```

### Scenario 3: Mixed Invitation (Plex + Jellyfin)
```
User clicks: /j/MIX456
↓
Manager detects: Plex + Jellyfin servers
↓
Strategy chosen: HybridStrategy
↓
Workflow chosen: MixedWorkflow
↓
User sees: Plex login button
↓
User completes: Plex OAuth
↓
System shows: Password form for local servers
↓
User submits: password for Jellyfin
↓
System creates: Jellyfin account + links to Plex
↓
Result: Redirect to wizard
```

## 🎛️ Route Integration

### Current Routes (`app/blueprints/public/routes.py`)

```python
@public_bp.route("/j/<code>")
def invite(code):
    # Simple drop-in replacement
    manager = InvitationFlowManager()
    result = manager.process_invitation_display(code)
    return result.to_flask_response()

@public_bp.route("/invitation/process", methods=["POST"])
def process_invitation():
    # Handles all form submissions
    manager = InvitationFlowManager()
    form_data = request.form.to_dict()
    result = manager.process_invitation_submission(form_data)
    return result.to_flask_response()
```

### Template Integration
- **`user-plex-login.html`**: Plex OAuth login
- **`welcome-jellyfin.html`**: Form-based registration
- **`hybrid-password-form.html`**: Mixed auth password collection
- **`invalid-invite.html`**: Error states

## 🔐 Security Features

### Authentication Security
- **Password validation**: Minimum length, confirmation matching
- **Input sanitization**: All form data validated
- **Session management**: Secure token handling
- **OAuth integration**: Proper Plex OAuth flow

### Authorization
- **Invitation validation**: Codes checked for expiry and usage
- **Server permissions**: Library access properly configured
- **Account linking**: Plex accounts linked to local accounts

## 🚀 Extensibility

### Adding New Server Types
1. **Add server client** in `app/services/media/<server>.py`
2. **Register in form choices** in `app/forms/settings.py`
3. **Update strategy detection** in `server_registry.py`
4. **Add template support** if needed

### Adding New Authentication Methods
1. **Create strategy class** extending `AuthenticationStrategy`
2. **Register in server registry** with server type mapping
3. **Add workflow support** if multi-step process needed
4. **Create templates** for user interface

### Adding New Workflow Types
1. **Create workflow class** extending `InvitationWorkflow`
2. **Register in manager** workflow mapping
3. **Add strategy support** for workflow initiation
4. **Handle result processing** for success/failure cases

## 📊 Benefits of Current Architecture

### For Developers
- **Clean separation**: Each component has single responsibility
- **Easy testing**: Mockable interfaces and dependency injection
- **Simple extension**: New servers/auth methods easy to add
- **Readable code**: Clear flow and well-documented components

### For Users
- **Same experience**: `/j/<code>` works exactly as before
- **Better reliability**: Robust error handling and validation
- **Flexible auth**: Supports multiple server combinations
- **Smooth onboarding**: Guided through complex scenarios

### For Maintainers
- **No breaking changes**: Existing invitations continue to work
- **Less complexity**: Removed CLI, metrics, migrations
- **Clear architecture**: Easy to understand and modify
- **Future-proof**: Extensible for new requirements

## 🔧 Current File Structure

```
app/
├── services/
│   └── invitation_flow/
│       ├── __init__.py          # Package exports
│       ├── manager.py           # Central orchestrator
│       ├── strategies.py        # Authentication strategies
│       ├── workflows.py         # Process workflows
│       ├── server_registry.py   # Server integration
│       ├── results.py           # Response handling
│       └── errors.py            # Error handling
├── blueprints/
│   └── public/
│       └── routes.py            # Updated routes
├── templates/
│   ├── user-plex-login.html     # Plex OAuth
│   ├── welcome-jellyfin.html    # Form-based
│   ├── hybrid-password-form.html # Mixed auth
│   └── invalid-invite.html      # Error states
└── tests/
    └── invitation_flow/
        ├── __init__.py          # Test package
        ├── conftest.py          # Test fixtures
        ├── test_manager.py      # Manager tests
        ├── test_strategies.py   # Strategy tests
        ├── test_workflows.py    # Workflow tests
        ├── test_server_registry.py # Registry tests
        ├── test_results.py      # Results tests
        ├── test_integration.py  # Integration tests
        ├── test_routes.py       # Route tests
        └── test_runner.py       # Test runner utility
```

## ✅ System Status

The simplified invitation system is now fully operational with:
- ✅ **Advanced internal architecture** using Strategy and Workflow patterns
- ✅ **Simple external interface** maintaining `/j/<code>` compatibility
- ✅ **Clean codebase** with unnecessary complexity removed
- ✅ **Extensible design** for future server types and auth methods
- ✅ **Robust error handling** with user-friendly messages
- ✅ **Production ready** with proper validation and security

The system successfully balances advanced architecture with simplicity, providing a solid foundation for future development while maintaining the user experience you wanted.