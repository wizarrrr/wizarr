# Wizard Architecture Documentation

> **Version:** 3.3 - Two-Phase Wizard System with Bundles and Modular Interactions
> **Last Updated:** 2025-12-17

## Overview

The Wizarr wizard is a mobile-first, app-like onboarding system with:
- **Two-phase flow** (pre-invite and post-invite steps)
- **Fixed UI chrome** (progress bar + navigation buttons)
- **Smooth content transitions** (slide animations)
- **Swipe gesture support**
- **Zero UI duplication** (HTMX partial swaps)
- **Phase-aware routing** (separate endpoints for each phase)

---

## Two-Phase Wizard System

### Phase Overview

The wizard operates in two distinct phases:

1. **Pre-Invite Phase** (`/pre-wizard`)
   - Shown **before** user accepts invitation
   - No authentication required (invite code in session)
   - Validates invite code on each request
   - Completes with redirect to join page
   - Use cases: Terms of service, requirements, welcome messages

2. **Post-Invite Phase** (`/post-wizard`)
   - Shown **after** user accepts invitation
   - Requires authentication or `wizard_access` session
   - Completes with redirect to completion page
   - Use cases: App setup, library selection, feature tours

### User Flow

```
User clicks invite link
    ↓
[Invite code stored in session]
    ↓
Pre-Invite Steps (if configured)
    ↓
Join Page (accept invitation)
    ↓
[Account created]
    ↓
Post-Invite Steps (if configured)
    ↓
Completion Page
```

---

## Architecture

### File Structure

```
app/templates/wizard/
├── frame.html          # Initial page load wrapper
├── steps.html          # UI chrome (progress + buttons + WizardController JS)
└── _content.html       # Content-only partial (HTMX swaps)

app/templates/partials/
└── _interaction_config.html  # Interaction configuration UI component

app/blueprints/wizard/
└── routes.py           # Flask routes with phase-aware template selection

app/blueprints/wizard_admin/
└── routes.py           # Admin routes for wizard step CRUD operations (/settings/wizard)

app/services/
├── invite_code_manager.py  # Session management for invite codes
├── wizard_seed.py          # Seed database with bundled markdown steps
├── wizard_reset.py         # Reset wizard steps to defaults
├── wizard_export_import.py # Export/import wizard configurations
├── wizard_migration.py     # Database migrations for wizard steps
├── wizard_presets.py       # Preset templates for common integrations
├── wizard_widgets.py       # Dynamic content widgets for wizard steps
└── invitation_flow/        # Invitation processing pipeline
    ├── __init__.py         # Module exports (public API)
    ├── manager.py          # InvitationFlowManager - main orchestrator
    ├── workflows.py        # Workflow classes (FormBasedWorkflow, PlexOAuthWorkflow, MixedWorkflow)
    ├── strategies.py       # Authentication strategies (FormBasedStrategy, PlexOAuthStrategy, HybridStrategy)
    ├── results.py          # InvitationResult, AuthResult, and ProcessingStatus
    ├── errors.py           # Error classes for invitation flow exceptions
    └── server_registry.py  # ServerIntegrationRegistry for server type management

app/forms/
└── wizard.py           # WTForms for wizard step CRUD operations

app/models.py           # WizardStep, WizardBundle, WizardBundleStep models
app/interactions.py     # Modular interaction type definitions

app/static/js/
├── interaction-config.js   # Interaction configuration form handling
└── wizard-interactions.js  # Client-side interaction validation

wizard_steps/           # Legacy bundled markdown files (repository root)
├── plex/               # Plex server steps
├── jellyfin/           # Jellyfin server steps
├── emby/               # Emby server steps
├── audiobookshelf/     # Audiobookshelf server steps
├── kavita/             # Kavita server steps
├── komga/              # Komga server steps
└── romm/               # Romm server steps
```

### Routing Structure

```
/wizard/                                  # Legacy entry point (redirects based on context)
/wizard/pre-wizard                        # Pre-invite phase entry (idx=0)
/wizard/pre-wizard/<idx>                  # Pre-invite phase steps
/wizard/pre-wizard/complete               # Pre-invite completion (redirects to join page)
/wizard/post-wizard                       # Post-invite phase entry (idx=0)
/wizard/post-wizard/<idx>                 # Post-invite phase steps
/wizard/complete                          # Post-invite completion page
/wizard/<server>/<idx>                    # Preview mode (admin/testing)
/wizard/combo/<category>                  # Multi-server invitations (category entry)
/wizard/combo/<category>/<idx>            # Multi-server invitations with step index
/wizard/bundle/<idx>                      # Bundle-specific wizard steps
/wizard/bundle-preview/<bundle_id>/<idx>  # Admin preview for custom bundles
```

**Note:** Routes use `/wizard/` prefix (defined in blueprint). The `<category>` parameter
in combo routes is `pre_invite` or `post_invite`.

### Request Flow

1. **Initial Page Load**
   - User visits `/pre-wizard` or `/post-wizard/<idx>`
   - Flask returns `frame.html`
   - `frame.html` includes `steps.html`
   - `steps.html` includes `_content.html`
   - **Result:** Full page with UI chrome + initial content

2. **HTMX Navigation**
   - User clicks button or swipes
   - HTMX sends request with `HX-Request` header
   - Flask detects header and returns `_content.html` ONLY
   - HTMX swaps `#wizard-content` element
   - JavaScript updates progress bars and button states
   - **Result:** Content slides in, UI chrome stays static

3. **Phase Completion**
   - **Pre-invite:** Redirects to join page (`/invite/<code>`)
   - **Post-invite:** Redirects to completion page (`/wizard/complete`)

---

## State Management

### Server → Client Communication

Flask sends custom headers on HTMX requests:

```python
resp.headers['X-Wizard-Idx'] = str(idx)
resp.headers['X-Require-Interaction'] = 'true' | 'false'
resp.headers['X-Wizard-Step-Phase'] = 'pre' | 'post' | ''
resp.headers['X-Interactions'] = json.dumps(interactions_config)  # When interactions configured
```

**Note:** The `X-Interactions` header is only sent when the step has interaction requirements
configured in the `interactions` JSON column. It contains the serialized interaction config.

### Client State Storage

The `#wizard-wrapper` element stores:

```html
<div id="wizard-wrapper"
     x-data="wizardSwipe()"
     data-current-idx="0"
     data-max-idx="5"
     data-server-type="plex"
     data-phase="pre|post|preview"
     data-step-phase="pre|post"
     data-completion-url="/wizard/pre-wizard/complete"
     data-completion-label="Continue to Invite"
     data-next-label="Next"
     data-phase-label-pre="Before Invitation"
     data-phase-label-post="After Invitation">
```

**Phase Attributes:**
- `data-phase`: Overall wizard phase context (pre, post, or preview)
- `data-step-phase`: Current step's specific phase (for mixed-phase flows)
- `data-completion-url`: URL to redirect when completing this phase
- `data-completion-label`: Button text for completion action
- `data-next-label`: Default "Next" button label (i18n)
- `data-phase-label-pre`: Label for pre-invite phase badge (i18n)
- `data-phase-label-post`: Label for post-invite phase badge (i18n)

### JavaScript Controller

`WizardController` handles all UI updates (defined in `steps.html`):

```javascript
WizardController = {
    init()                          // Initialize controller, attach HTMX listeners
    getCurrentIdx()                 // Get current step index from wrapper
    getMaxIdx()                     // Get max step index from wrapper
    getServerType()                 // Get server type (plex, jellyfin, combo, bundle, etc.)
    getPhase()                      // Get overall phase (pre, post, preview)
    getStepPhase()                  // Get current step's phase
    getCompletionUrl()              // Get completion redirect URL
    getCompletionLabel()            // Get completion button text
    getDefaultNextLabel()           // Get default "Next" label (i18n)
    updateUI(xhr)                   // Main update handler after HTMX swap
      → updatePhaseBadges(phase)    // Update phase indicator badges
      → updateProgress(idx, maxIdx) // Animate progress bars and text
      → updateButtons(...)          // Update nav button URLs & visibility
}

// Swipe gesture handler (Alpine.js component)
wizardSwipe()
    onTouchStart(e)                 // Record touch start position
    onTouchMove(e)                  // Track touch movement
    onTouchEnd(e)                   // Trigger navigation if threshold met
```

---

## Mobile Experience

### Layout Structure

```
┌─────────────────────────────┐
│  Fixed Progress Bar (top)   │  ← position: fixed, z-index: 40
├─────────────────────────────┤
│                             │
│   Scrollable Content Area   │  ← overflow-y: auto, flex: 1
│   (only this scrolls)       │
│                             │
├─────────────────────────────┤
│  Fixed Nav Buttons (bottom) │  ← position: fixed, z-index: 40
│   [←]              [→]      │     (circular, gradient)
└─────────────────────────────┘
```

### CSS Classes

- `.wizard-container` - Fixed viewport height container
- `.wizard-progress-mobile` - Fixed progress bar
- `.wizard-content-mobile` - Scrollable content area
- `.wizard-nav-mobile` - Fixed button container
- `.wizard-btn-mobile` - Circular gradient buttons

### Swipe Gestures

- **Swipe Left** → Navigate to next step
- **Swipe Right** → Navigate to previous step
- **Threshold:** 75px
- Respects disabled states and boundaries

---

## Template Logic

### Flask Route Pattern

All wizard routes follow this pattern:

```python
def _serve_wizard(server: str, idx: int, steps: list, phase: str,
                  *, completion_url: str | None = None,
                  completion_label: str | None = None,
                  current_step_phase: str | None = None):
    # ... build HTML content ...

    # Extract interaction requirements from step
    require_interaction = False
    interactions_config = None
    try:
        require_interaction = bool(
            getattr(post, "get", lambda _k, _d=None: None)("require", False)
        )
        interactions_config = getattr(post, "get", lambda _k, _d=None: None)(
            "interactions", None
        )
    except Exception:
        require_interaction = False
        interactions_config = None

    # Smart template selection
    if not request.headers.get("HX-Request"):
        page = "wizard/frame.html"        # Initial load
    else:
        page = "wizard/_content.html"     # HTMX swap

    response = render_template(
        page,
        body_html=html,
        idx=idx,
        max_idx=len(steps) - 1,
        server_type=server,
        phase=phase,                      # Phase context
        step_phase=display_phase,         # Current step phase
        completion_url=completion_url,    # Completion redirect
        completion_label=completion_label,# Completion button text
        require_interaction=require_interaction,
        interactions_config=interactions_config
    )

    # Add headers for HTMX requests
    if request.headers.get("HX-Request"):
        resp = make_response(response)
        resp.headers['X-Wizard-Idx'] = str(idx)
        resp.headers['X-Require-Interaction'] = 'true' if require_interaction else 'false'
        resp.headers['X-Wizard-Step-Phase'] = display_phase or ''
        # Include interactions config for frontend handlers
        if interactions_config:
            resp.headers['X-Interactions'] = json.dumps(interactions_config)
        return resp

    return response
```

### Phase-Specific Routes

**Pre-Wizard Route:**
```python
@wizard_bp.route("/pre-wizard/<int:idx>")
def pre_wizard(idx: int = 0):
    # Validate invite code
    invite_code = InviteCodeManager.get_invite_code()
    # ... validation logic ...

    # Get pre-invite steps
    steps = _steps(server_type, cfg, category="pre_invite")

    # Render with pre-phase context
    return _serve_wizard(
        server_type, idx, steps, "pre",
        completion_url=url_for("wizard.pre_wizard_complete"),
        completion_label=_("Continue to Invite")
    )
```

**Post-Wizard Route:**
```python
@wizard_bp.route("/post-wizard/<int:idx>")
def post_wizard(idx: int = 0):
    # Check authentication
    if not current_user.is_authenticated and not session.get("wizard_access"):
        return redirect(url_for("auth.login"))

    # Get post-invite steps
    steps = _steps(server_type, cfg, category="post_invite")

    # Render with post-phase context
    return _serve_wizard(server_type, idx, steps, "post")
```

### Button URL Updates

Buttons dynamically update their `hx-get` attribute based on phase and server type:

```javascript
// Phase and server-type aware URL generation
if (serverType === 'combo') {
    // Combo wizard uses path-based category routing
    const category = phase === 'pre' ? 'pre_invite' : 'post_invite';
    newUrl = `/wizard/combo/${category}/${targetIdx}`;
} else if (serverType === 'bundle') {
    newUrl = `/wizard/bundle/${targetIdx}`;
} else if (phase === 'pre') {
    newUrl = `/wizard/pre-wizard/${targetIdx}`;
} else if (phase === 'post') {
    newUrl = `/wizard/post-wizard/${targetIdx}`;
} else {
    newUrl = `/wizard/${serverType}/${targetIdx}`;
}
htmx.process(wrapper);  // Reinitialize HTMX
```

### Step Filtering by Category

The `_steps()` function filters steps by category:

```python
def _steps(server: str, _cfg: dict, category: str = "post_invite"):
    """Return ordered wizard steps for server and category filtered by eligibility.

    Args:
        server: Server type (plex, jellyfin, etc.)
        _cfg: Configuration dictionary (used for settings-based filtering)
        category: 'pre_invite' or 'post_invite' (default: 'post_invite')

    Preference order:
        1. Rows from the wizard_step table (if any exist for server_type and category)
        2. Legacy markdown files shipped in wizard_steps/ (fallback, post_invite only)

    Returns:
        List of wizard steps (frontmatter.Post or _RowAdapter objects)
    """
    db_rows = (
        WizardStep.query
        .filter_by(server_type=server, category=category)
        .order_by(WizardStep.position)
        .all()
    )
    # ... filter by requires settings, return adapted rows ...

    # Fallback to bundled markdown files (post_invite only)
    if category == "post_invite":
        files = sorted((BASE_DIR / server).glob("*.md"))
        return [frontmatter.load(str(f)) for f in files]
```

---

## Database Models

### WizardStep

Stores wizard step content in the database (replaces legacy markdown files):

```python
class WizardStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_type = db.Column(db.String, nullable=False)   # plex, jellyfin, etc.
    category = db.Column(db.String, nullable=False,      # pre_invite | post_invite
                         default="post_invite", server_default="post_invite")
    position = db.Column(db.Integer, nullable=False)     # Sort order (0-indexed)
    title = db.Column(db.String, nullable=True)          # Optional title
    markdown = db.Column(db.Text, nullable=False)        # Step content
    requires = db.Column(db.JSON, nullable=True)         # Settings requirements

    # DEPRECATED: Legacy boolean for backward compatibility
    # Use `interactions` JSON column for new interaction configurations
    require_interaction = db.Column(db.Boolean, default=False, nullable=True)

    # Flexible interaction configuration stored as JSON
    # Each key (click, time, tos, text_input, quiz) is optional
    # See "Modular Interaction System" section for details
    interactions = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False)  # Auto-set on creation
    updated_at = db.Column(db.DateTime, nullable=False)  # Auto-updated on change

    # Unique constraint: (server_type, category, position)

    # ── Interaction helpers ──
    @property
    def step_interactions(self) -> StepInteractions:
        """Get typed interaction configuration from JSON."""
        return StepInteractions.from_dict(self.interactions)

    @step_interactions.setter
    def step_interactions(self, value: StepInteractions):
        """Set interaction configuration from typed object."""
        self.interactions = value.to_dict() if value else None

    def has_interactions(self) -> bool:
        """Check if step requires any interactions.

        Checks both the new `interactions` JSON and legacy `require_interaction`
        boolean for backward compatibility.
        """
        if self.interactions:
            return self.step_interactions.has_any_interaction()
        return bool(self.require_interaction)

    def to_dict(self) -> dict:
        """Return serializable representation (for JSON responses)."""
        return {
            "id": self.id,
            "server_type": self.server_type,
            "category": self.category,
            "position": self.position,
            "title": self.title,
            "markdown": self.markdown,
            "requires": self.requires or [],
            "interactions": self.interactions,
            "require_interaction": self.has_interactions(),  # Backward compat
        }
```

### WizardBundle

Named collection of wizard steps for custom flows:

```python
class WizardBundle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    steps = db.relationship("WizardBundleStep", ...)  # Ordered steps
```

### WizardBundleStep

Association table linking bundles to steps with ordering:

```python
class WizardBundleStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey("wizard_bundle.id"))
    step_id = db.Column(db.Integer, db.ForeignKey("wizard_step.id"))
    position = db.Column(db.Integer, nullable=False)

    # Unique constraint: (bundle_id, position)
```

---

## Modular Interaction System

The modular interaction system (`app/interactions.py`) provides strongly-typed, combinable
interaction requirements that users must satisfy before proceeding to the next wizard step.
This replaces the legacy `require_interaction` boolean with a flexible JSON-based configuration.

### Interaction Types

| Type | Description | Key Attributes |
|------|-------------|----------------|
| `ClickInteraction` | User must click a link/button in content | `enabled`, `target_selector`, `description` |
| `TimeInteraction` | User must wait N seconds (countdown) | `enabled`, `duration_seconds`, `show_countdown` |
| `TosInteraction` | User must accept Terms of Service | `enabled`, `content_markdown`, `checkbox_label`, `require_scroll`, `version` |
| `TextInputInteraction` | User must answer correctly | `enabled`, `question`, `answers[]`, `case_sensitive`, `placeholder`, `error_message` |
| `QuizInteraction` | Multi-question quiz | `enabled`, `questions[]`, `pass_threshold`, `shuffle_questions`, `shuffle_answers`, `show_explanations` |

### StepInteractions Container

The `StepInteractions` dataclass aggregates all interaction types for a single step:

```python
@dataclass(slots=True)
class StepInteractions:
    """Container for all interaction configurations on a wizard step.

    Presence of a non-None interaction with enabled=True indicates it is active.
    All enabled interactions must be satisfied for the user to proceed.
    """
    click: ClickInteraction | None = None
    time: TimeInteraction | None = None
    tos: TosInteraction | None = None
    text_input: TextInputInteraction | None = None
    quiz: QuizInteraction | None = None

    def has_any_interaction(self) -> bool:
        """Check if any interaction type is enabled."""
        ...

    def get_enabled_types(self) -> list[InteractionType]:
        """Get list of enabled interaction types."""
        ...

    def to_dict(self) -> dict[str, Any] | None:
        """Serialize all enabled interactions to JSON-compatible dict.
        Returns None if no interactions are enabled."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Self:
        """Deserialize from JSON dict."""
        ...

    def validate(self) -> list[str]:
        """Validate all enabled interactions."""
        ...
```

### JSON Structure Examples

The `interactions` column in `WizardStep` stores JSON like:

**Click + Time Combined:**
```json
{
  "click": {
    "enabled": true,
    "target_selector": "a, button",
    "description": "Click the download link to continue"
  },
  "time": {
    "enabled": true,
    "duration_seconds": 30,
    "show_countdown": true
  }
}
```

**Terms of Service:**
```json
{
  "tos": {
    "enabled": true,
    "content_markdown": "# Terms of Service\n\nBy using this service...",
    "checkbox_label": "I agree to the Terms of Service",
    "require_scroll": true,
    "version": "1.0"
  }
}
```

**Text Input Verification:**
```json
{
  "text_input": {
    "enabled": true,
    "question": "What is the server name?",
    "answers": ["Plex", "plex", "PLEX"],
    "case_sensitive": false,
    "placeholder": "Enter the server name",
    "error_message": "Incorrect. Hint: It starts with 'P'"
  }
}
```

Multiple interaction types can be combined - all enabled types must be satisfied before
the user can proceed to the next step.

---

## Wizard Presets

The `app/services/wizard_presets.py` module provides preset templates for common integrations,
allowing administrators to quickly add wizard steps through the Multi-Action create button.

### Available Presets

| Preset ID | Name | Description |
|-----------|------|-------------|
| `discord_community` | Discord Community | Embeds a Discord server widget for community invitations |
| `overseerr_requests` | Overseerr/Ombi Requests | Links to request system for media requests |

### Usage

```python
from app.services.wizard_presets import get_available_presets, create_step_from_preset, get_preset_title

# Get all available presets
presets = get_available_presets()  # Returns list[WizardPreset]

# Create step content from a preset (returns rendered markdown string)
markdown_content = create_step_from_preset("discord_community", discord_id="YOUR_SERVER_ID")

# Get the default title for a preset
title = get_preset_title("discord_community")
```

Presets include placeholder variables (e.g., `{discord_id}`, `{overseerr_url}`) that
are replaced with values passed as keyword arguments when calling `create_step_from_preset()`.

---

## Wizard Widgets

The `app/services/wizard_widgets.py` module enables embedding dynamic content in wizard steps
using a special syntax. Widgets are processed during markdown rendering.

### Widget Syntax

```markdown
{{ widget:widget_name param1="value1" param2="value2" }}
```

### Available Widgets

| Widget | Description | Parameters |
|--------|-------------|------------|
| `recently_added_media` | Carousel of recently added items | `limit` (default: 6) |
| `button` | Styled action button | `url`, `text` (required) |

### Card Delimiter Syntax

Cards use a special delimiter syntax for styled content blocks:

```markdown
|||
# Card Title
This is card content with **markdown** support.
|||
```

### Example Usage

```markdown
## Welcome to Your Media Library

Here's what's been added recently:

{{ widget:recently_added_media limit=6 }}

|||
### Getting Started
Click the button below to open the app.

{{ widget:button url="https://app.example.com" text="🎬 Open App" }}
|||
```

---

## Key Design Decisions

### ✅ DO

- Only swap `#wizard-content`
- Update progress/buttons via JavaScript
- Use `_content.html` for HTMX responses
- Send state via custom headers (including phase)
- Validate all indices before updates
- Filter steps by category (`pre_invite` vs `post_invite`)
- Validate invite codes on each pre-wizard request
- Use phase-specific completion URLs

### ❌ DON'T

- Never swap `#wizard-wrapper` (causes duplication)
- Never return `steps.html` for HTMX requests
- Never modify progress bars via HTMX swaps
- Never skip header validation
- Never mix pre-invite and post-invite steps in the same phase
- Never allow pre-wizard access without valid invite code
- Never hardcode server types in fallback logic

---

## Debugging

### Console Logging

The wizard logs key events:

```
WizardController initialized
✅ Wizard update: { newIdx: 1, maxIdx: 5, serverType: 'plex', phase: 'pre', requireInteraction: false }
Button wizard-prev-btn: URL=/pre-wizard/0, visible=true
Button wizard-next-btn: URL=/pre-wizard/2, visible=true
Phase indicator updated: pre
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Duplicate progress bars | Swapping wrapper instead of content | Check Flask returns `_content.html` for HTMX |
| Button URLs don't update | HTMX not reprocessed | Ensure `htmx.process(wrapper)` is called |
| Content doesn't scroll | Container height wrong | Verify `.wizard-container` has `height: 100vh` |
| Buttons behind blur | Z-index issue | Ensure `.wizard-btn-mobile` has `z-index: 50` |
| Wrong phase steps shown | Category filter incorrect | Verify `_steps()` receives correct `category` parameter |
| Pre-wizard accessible without invite | Session validation missing | Check `InviteCodeManager.validate_invite_code()` is called |
| Completion redirects to wrong page | Phase-specific completion URL not set | Verify `completion_url` parameter in `_serve_wizard()` |

---

## Phase-Specific Behavior

### Pre-Invite Phase

**Access Control:**
- Requires valid invite code in session
- No authentication required
- Validates invite code on each request
- Redirects to home page if invite code is invalid/expired

**Completion:**
- Final step shows "Continue to Invite" button
- Redirects to `/wizard/pre-wizard/complete`
- Completion endpoint redirects to join page (`/invite/<code>`)
- Marks pre-wizard as complete in session

**Session Management:**
```python
InviteCodeManager.store_invite_code(code)     # Store invite code in session
InviteCodeManager.get_invite_code()           # Retrieve stored invite code
InviteCodeManager.validate_invite_code(code)  # Validate invite code (returns tuple)
InviteCodeManager.mark_pre_wizard_complete()  # Mark pre-wizard phase complete
InviteCodeManager.is_pre_wizard_complete()    # Check if pre-wizard is complete
InviteCodeManager.clear_invite_data()         # Clear all invite-related session data
```

### Post-Invite Phase

**Access Control:**
- Requires authentication OR `wizard_access` session
- User must have accepted invitation
- No invite code validation needed

**Completion:**
- Final step shows "Next" button (or custom label)
- Redirects to `/wizard/complete`
- Completion endpoint clears all session data
- Shows success message and redirects to app

**Session Cleanup:**
```python
InviteCodeManager.clear_invite_data()  # Clear invite-related data
session.pop("wizard_access", None)     # Clear wizard access flag
session.pop("wizard_server_order", None)
session.pop("wizard_bundle_id", None)
```

### Multi-Server Invitations (Combo Wizard)

For invitations linked to multiple media servers, the combo wizard concatenates
steps from all servers in session-defined order:

```python
@wizard_bp.route("/combo/<category>/<int:idx>")
def combo(category: str, idx: int = 0):
    """Combined wizard for multi-server invites with category support.

    Args:
        category: 'pre_invite' or 'post_invite'
        idx: Current step index across all servers
    """
    order = session.get("wizard_server_order")  # e.g., ["plex", "jellyfin"]

    # Concatenate steps from all servers for the category
    steps = []
    for server_type in order:
        steps.extend(_steps(server_type, cfg, category=category))
```

**Session Keys:**
- `wizard_server_order`: List of server types in order
- `wizard_bundle_id`: Optional bundle ID for custom step flows

### Bundle Wizard

For custom step sequences defined via `WizardBundle`:

```python
@wizard_bp.route("/bundle/<int:idx>")
def bundle_view(idx: int):
    """Bundle-specific wizard with custom step sequence."""
    bundle_id = session.get("wizard_bundle_id")

    # Load steps from bundle association table, filtered by current phase
    ordered = WizardBundleStep.query.filter_by(bundle_id=bundle_id)
        .order_by(WizardBundleStep.position).all()
```

### Backward Compatibility

The `/wizard/` endpoint provides backward compatibility:

```python
@wizard_bp.route("/")
def start():
    """Redirect to appropriate wizard based on context."""
    if current_user.is_authenticated or session.get("wizard_access"):
        return redirect(url_for("wizard.post_wizard"))

    invite_code = InviteCodeManager.get_invite_code()
    if invite_code:
        return redirect(url_for("wizard.pre_wizard"))

    return redirect(url_for("public.root"))
```
