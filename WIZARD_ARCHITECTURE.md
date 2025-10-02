# Wizard Architecture Documentation

> **Version:** 2.0 - Modular App-Like Experience
> **Last Updated:** 2025-10-02

## Overview

The Wizarr wizard is a mobile-first, app-like onboarding system with:
- **Fixed UI chrome** (progress bar + navigation buttons)
- **Smooth content transitions** (slide animations)
- **Swipe gesture support**
- **Zero UI duplication** (HTMX partial swaps)

---

## Architecture

### File Structure

```
app/templates/wizard/
├── frame.html          # Initial page load wrapper
├── steps.html          # UI chrome (progress + buttons)
└── _content.html       # Content-only partial (HTMX swaps)

app/blueprints/wizard/
└── routes.py           # Flask routes with smart template selection
```

### Request Flow

1. **Initial Page Load**
   - User visits `/wizard` or `/wizard/<server>/<idx>`
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

---

## State Management

### Server → Client Communication

Flask sends custom headers on HTMX requests:

```python
resp.headers['X-Wizard-Idx'] = str(idx)
resp.headers['X-Require-Interaction'] = 'true' | 'false'
```

### Client State Storage

The `#wizard-wrapper` element stores:

```html
<div id="wizard-wrapper"
     data-current-idx="0"
     data-max-idx="5"
     data-server-type="plex">
```

### JavaScript Controller

`WizardController` handles all UI updates:

```javascript
WizardController.updateUI(xhr)
  → updateProgress(idx, maxIdx)       // Animate progress bars
  → updateButtons(idx, maxIdx, ...)   // Update URLs & visibility
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
def _serve(server: str, idx: int):
    # ... build HTML content ...

    # Smart template selection
    if not request.headers.get("HX-Request"):
        page = "wizard/frame.html"        # Initial load
    else:
        page = "wizard/_content.html"     # HTMX swap

    response = render_template(page, ...)

    # Add headers for HTMX requests
    if request.headers.get("HX-Request"):
        resp = make_response(response)
        resp.headers['X-Wizard-Idx'] = str(idx)
        resp.headers['X-Require-Interaction'] = 'true' | 'false'
        return resp

    return response
```

### Button URL Updates

Buttons dynamically update their `hx-get` attribute:

```javascript
btn.setAttribute('hx-get', `/wizard/${serverType}/${targetIdx}`);
htmx.process(wrapper);  // Reinitialize HTMX
```

---

## Key Design Decisions

### ✅ DO

- Only swap `#wizard-content`
- Update progress/buttons via JavaScript
- Use `_content.html` for HTMX responses
- Send state via custom headers
- Validate all indices before updates

### ❌ DON'T

- Never swap `#wizard-wrapper` (causes duplication)
- Never return `steps.html` for HTMX requests
- Never modify progress bars via HTMX swaps
- Never skip header validation

---

## Debugging

### Console Logging

The wizard logs key events:

```
WizardController initialized
✅ Wizard update: { newIdx: 1, maxIdx: 5, serverType: 'plex', requireInteraction: false }
Button wizard-prev-btn: URL=/wizard/plex/0, visible=true
Button wizard-next-btn: URL=/wizard/plex/2, visible=true
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Duplicate progress bars | Swapping wrapper instead of content | Check Flask returns `_content.html` for HTMX |
| Button URLs don't update | HTMX not reprocessed | Ensure `htmx.process(wrapper)` is called |
| Content doesn't scroll | Container height wrong | Verify `.wizard-container` has `height: 100vh` |
| Buttons behind blur | Z-index issue | Ensure `.wizard-btn-mobile` has `z-index: 50` |

---

## Future Enhancements

- [ ] Keyboard navigation (arrow keys)
- [ ] Accessibility improvements (ARIA live regions)
- [ ] Progress persistence (localStorage)
- [ ] Prefetch next step for instant navigation
- [ ] Step validation hooks
- [ ] Custom step transitions

---

## Testing Checklist

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
