# Wizard Architecture Documentation

> **Version:** 3.0 - Two-Phase Wizard System
> **Last Updated:** 2025-10-04

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
├── steps.html          # UI chrome (progress + buttons)
└── _content.html       # Content-only partial (HTMX swaps)

app/blueprints/wizard/
└── routes.py           # Flask routes with phase-aware template selection

app/services/
└── invite_code_manager.py  # Session management for invite codes
```

### Routing Structure

```
/wizard/                    # Legacy entry point (redirects based on context)
/pre-wizard/<idx>          # Pre-invite phase steps
/pre-wizard/complete       # Pre-invite completion (redirects to join page)
/post-wizard/<idx>         # Post-invite phase steps
/wizard/complete           # Post-invite completion page
/wizard/<server>/<idx>     # Preview mode (admin/testing)
/wizard/combo/<idx>        # Multi-server invitations
```

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
```

### Client State Storage

The `#wizard-wrapper` element stores:

```html
<div id="wizard-wrapper"
     data-current-idx="0"
     data-max-idx="5"
     data-server-type="plex"
     data-phase="pre|post|preview"
     data-step-phase="pre|post"
     data-completion-url="/pre-wizard/complete"
     data-completion-label="Continue to Invite">
```

**Phase Attributes:**
- `data-phase`: Overall wizard phase context (pre, post, or preview)
- `data-step-phase`: Current step's specific phase (for mixed-phase flows)
- `data-completion-url`: URL to redirect when completing this phase
- `data-completion-label`: Button text for completion action

### JavaScript Controller

`WizardController` handles all UI updates:

```javascript
WizardController.updateUI(xhr)
  → updateProgress(idx, maxIdx)       // Animate progress bars
  → updateButtons(idx, maxIdx, ...)   // Update URLs & visibility (phase-aware)
  → updatePhaseIndicator(phase)       // Update phase badge
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
        phase=phase,                      # NEW: Phase context
        step_phase=display_phase,         # NEW: Current step phase
        completion_url=completion_url,    # NEW: Completion redirect
        completion_label=completion_label # NEW: Completion button text
    )

    # Add headers for HTMX requests
    if request.headers.get("HX-Request"):
        resp = make_response(response)
        resp.headers['X-Wizard-Idx'] = str(idx)
        resp.headers['X-Require-Interaction'] = 'true' | 'false'
        resp.headers['X-Wizard-Step-Phase'] = display_phase or ''  # NEW
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

Buttons dynamically update their `hx-get` attribute based on phase:

```javascript
// Phase-aware URL generation
if (phase === 'pre') {
    btn.setAttribute('hx-get', `/pre-wizard/${targetIdx}`);
} else if (phase === 'post') {
    btn.setAttribute('hx-get', `/post-wizard/${targetIdx}`);
} else {
    btn.setAttribute('hx-get', `/wizard/${serverType}/${targetIdx}`);
}
htmx.process(wrapper);  // Reinitialize HTMX
```

### Step Filtering by Category

The `_steps()` function filters steps by category:

```python
def _steps(server: str, cfg: dict, category: str = "post_invite"):
    """Return ordered wizard steps for server and category.

    Args:
        server: Server type (plex, jellyfin, etc.)
        cfg: Configuration dictionary
        category: 'pre_invite' or 'post_invite' (default: 'post_invite')

    Returns:
        List of wizard steps filtered by category
    """
    db_rows = (
        WizardStep.query
        .filter_by(server_type=server, category=category)
        .order_by(WizardStep.position)
        .all()
    )
    # ... fallback to legacy markdown files (post_invite only) ...
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
- Redirects to `/pre-wizard/complete`
- Completion endpoint redirects to join page (`/invite/<code>`)
- Marks pre-wizard as complete in session

**Session Management:**
```python
InviteCodeManager.get_invite_code()           # Retrieve invite code
InviteCodeManager.validate_invite_code(code)  # Validate invite code
InviteCodeManager.mark_pre_wizard_complete()  # Mark phase complete
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

    return redirect(url_for("public.index"))
```

---

## Future Enhancements

- [ ] Keyboard navigation (arrow keys)
- [ ] Accessibility improvements (ARIA live regions)
- [ ] Progress persistence (localStorage)
- [ ] Prefetch next step for instant navigation
- [ ] Step validation hooks
- [ ] Custom step transitions
- [ ] Phase-specific analytics tracking
- [ ] Conditional phase skipping based on invitation settings

---

## Testing Checklist

### Core Functionality
- [ ] Initial page load shows all UI chrome
- [ ] Navigation updates only content area
- [ ] Progress bar animates smoothly
- [ ] Previous button hidden on first step
- [ ] Next button hidden on last step
- [ ] Swipe gestures work correctly
- [ ] Required interaction blocks navigation
- [ ] Mobile layout fits single viewport
- [ ] Desktop layout stays centered
- [ ] Dark mode works correctly

### Phase-Specific Tests
- [ ] Pre-wizard validates invite code on each request
- [ ] Pre-wizard redirects to home if invite code invalid
- [ ] Pre-wizard completion redirects to join page
- [ ] Post-wizard requires authentication
- [ ] Post-wizard completion clears session data
- [ ] Post-wizard completion shows success message
- [ ] Legacy `/wizard/` route redirects correctly
- [ ] Multi-server invitations show correct phase steps
- [ ] Phase badges display correctly
- [ ] Completion buttons show correct labels
