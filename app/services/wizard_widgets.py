"""
Wizard widget system for embedding dynamic content in wizard steps.

Widgets are inserted into markdown content using special syntax:
{{ widget:recently_added_media }}
{{ widget:recently_added_media limit=6 }}
{{ widget:button url="https://example.com" text="Click Here" }}

Cards use delimiter syntax:
|||
# Card Title
This is the card content with **markdown** support.
|||
"""

import logging
import re
from typing import Any

import markdown
from flask import render_template_string

from app.services.media.service import get_media_client


class WizardWidget:
    """Base class for wizard widgets."""

    def __init__(self, name: str, template: str):
        self.name = name
        self.template = template

    def render(self, server_type: str, _context: dict | None = None, **kwargs) -> str:
        """Render the widget with given parameters."""
        try:
            data = self.get_data(server_type, **kwargs)
            html_content = render_template_string(self.template, **data)
            # Wrap in markdown HTML block to ensure it's treated as raw HTML
            return f'\n\n<div class="widget-container">\n{html_content}\n</div>\n\n'
        except Exception:
            # Fail gracefully in wizard context
            return f'\n\n<div class="text-sm text-gray-500 italic">Widget "{self.name}" temporarily unavailable</div>\n\n'

    def get_data(self, _server_type: str, **_kwargs) -> dict[str, Any]:
        """Override this method to provide data for the widget."""
        return {}


class RecentlyAddedMediaWidget(WizardWidget):
    """Widget to show recently added media from the server."""

    def __init__(self):
        # The strip loops by holding the item list twice and sliding exactly
        # half its own width, so at the moment it resets the poster under every
        # pixel is the one that was already there. That only holds when the two
        # halves are identical in width, which is why the spacing is a right
        # margin on every item rather than a gap on the track: a flex gap is
        # drawn between items but not after the last one, so one half came out
        # a gap narrower than the other and the reset jumped.
        template = """
        {%- macro poster(item) -%}
        <div class="carousel-item">
            {% if item.thumb %}
            <img src="{{ item.thumb }}" alt="{{ item.title }}"
                 decoding="async"
                 class="w-full h-full object-cover rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300">
            {% else %}
            <div class="w-full h-full bg-gradient-to-br from-primary/20 to-primary/40 rounded-lg shadow-lg flex items-center justify-center">
                <svg class="w-8 h-8 text-primary" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"/>
                </svg>
            </div>
            {% endif %}
        </div>
        {%- endmacro -%}
        {# not-prose: the widget is injected into markdown that renders inside
           .prose, whose img rule adds a ~2em vertical margin. That was harmless
           while the poster sized itself, but the item needs a fixed height for
           the two halves to match, and the margin pushed the poster down until
           the strip clipped its bottom. #}
        <div class="media-carousel-widget not-prose my-6">
            {% if items %}
            <div class="carousel-container">
                <div class="carousel-track"
                     style="animation-duration: {{ items|length * 3 }}s">
                    {% for item in items %}{{ poster(item) }}{% endfor %}
                    {# Second copy is what makes the reset invisible. #}
                    {% for item in items %}{{ poster(item) }}{% endfor %}
                </div>
            </div>

            <style>
            .carousel-container {
                position: relative;
                overflow: hidden;
                /* Fade the ends rather than cutting a poster off square. */
                -webkit-mask-image: linear-gradient(to right, transparent, #000 3rem, #000 calc(100% - 3rem), transparent);
                mask-image: linear-gradient(to right, transparent, #000 3rem, #000 calc(100% - 3rem), transparent);
            }

            .carousel-track {
                display: flex;
                width: max-content;
                animation-name: carousel-scroll;
                animation-timing-function: linear;
                animation-iteration-count: infinite;
            }

            .carousel-item {
                flex: 0 0 auto;
                width: 8rem;            /* 128px */
                height: 12rem;          /* 2:3, a poster's own aspect ratio */
                margin-right: 0.75rem;  /* on every item, including the last */
            }

            .carousel-item > img,
            .carousel-item > div {
                margin: 0;
                display: block;
            }

            @keyframes carousel-scroll {
                from { transform: translateX(0); }
                to   { transform: translateX(-50%); }
            }

            .carousel-container:hover .carousel-track {
                animation-play-state: paused;
            }

            @media (prefers-reduced-motion: reduce) {
                .carousel-track { animation: none; }
                .carousel-container { overflow-x: auto; }
            }
            </style>
            {% else %}
            <div class="text-center py-8 text-gray-500 dark:text-gray-400">
                <svg class="w-12 h-12 mx-auto mb-2 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"/>
                </svg>
                <p class="text-sm">{{ _("No recent content available") }}</p>
            </div>
            {% endif %}
        </div>
        """
        super().__init__("recently_added_media", template)

    def get_data(self, _server_type: str, **_kwargs) -> dict[str, Any]:
        """Fetch recently added media from the server."""
        server_type = _server_type
        limit = _kwargs.get("limit", 6)

        try:
            # Get media client for the server type
            from app.models import MediaServer

            server = MediaServer.query.filter_by(server_type=server_type).first()

            if not server:
                # Try to get any server if none match the exact type
                server = MediaServer.query.first()

            if not server:
                return {"items": [], "limit": limit}

            client = get_media_client(server.server_type, server)

            if not client:
                return {"items": [], "limit": limit}

            # Get recently added items
            recent_items = self._get_recent_items(client, limit)

            return {"items": recent_items, "limit": limit}

        except Exception:
            # Return empty data on any error to fail gracefully
            return {"items": [], "limit": limit}

    def _get_recent_items(self, client, limit: int):
        """Extract recent items from media client."""
        try:
            # Use the new get_recent_items method if available
            if hasattr(client, "get_recent_items"):
                return client.get_recent_items(limit=limit)

            # Fallback: try to get recent content from libraries
            libraries = client.libraries()
            recent_items = []

            # For each library, try to get recent content
            for library in libraries[:3]:  # Limit to first 3 libraries
                try:
                    if hasattr(client, "get_recent_items"):
                        items = client.get_recent_items(library.get("id"), limit=2)
                        recent_items.extend(items)
                except Exception as exc:
                    logging.debug(
                        f"Failed to get recent items for library {library.get('id')}: {exc}"
                    )
                    continue

            return recent_items[:limit]

        except Exception:
            return []


class CardWidget(WizardWidget):
    """Widget to create a card - not used with standard widget syntax, rendered via delimiter."""

    def __init__(self):
        # Placeholder - cards are handled by process_card_delimiters
        super().__init__("card", "")

    def render(self, server_type: str, _context: dict | None = None, **kwargs) -> str:  # noqa: ARG002
        """Cards should use delimiter syntax instead."""
        return '\n\n<div class="text-sm text-yellow-500 italic">Use ||| delimiter syntax for cards instead</div>\n\n'


class ButtonWidget(WizardWidget):
    """Widget to create a standard Wizarr button with a link."""

    def __init__(self):
        # Empty template since we'll override render
        super().__init__("button", "")

    def render(self, server_type: str, _context: dict | None = None, **kwargs) -> str:  # noqa: ARG002
        """Render the button widget with direct HTML generation."""
        try:
            import html

            url = kwargs.get("url", "")
            text = kwargs.get("text", "Click Here")
            context = _context or kwargs.pop("context", {}) or {}

            # If URL is a Jinja variable name (no protocol and no slashes), try to resolve it from context
            if (
                url
                and not url.startswith(("http://", "https://", "//", "{{"))
                and "/" not in url
            ):
                # First try to get it from context directly
                if url in context:
                    url = context[url]
                else:
                    # Try to render it as a Jinja variable
                    try:
                        from flask_babel import gettext as _translate

                        render_ctx = context.copy()
                        render_ctx["_"] = _translate
                        url = render_template_string(f"{{{{ {url} }}}}", **render_ctx)
                    except Exception as exc:
                        # If rendering fails, keep original value
                        logging.debug(f"Failed to render URL template '{url}': {exc}")

            # If text contains translation function call, render it first
            text_str = str(text)

            if "_(" in text_str:
                try:
                    # Import gettext to make it available in the template context
                    from flask_babel import gettext as _translate

                    # Wrap _("...") in {{ }} to make it a Jinja expression
                    template_str = f"{{{{ {text_str} }}}}"
                    text = render_template_string(template_str, _=_translate)
                except Exception as exc:
                    # If rendering fails, use the text as-is
                    logging.debug(
                        f"Failed to render text translation '{text_str}': {exc}"
                    )
            elif "{{" in text_str:
                # Already has Jinja syntax, render as-is
                try:
                    from flask_babel import gettext as _translate

                    text = render_template_string(text_str, _=_translate)
                except Exception as exc:
                    # If rendering fails, use the text as-is
                    logging.debug(f"Failed to render text template '{text_str}': {exc}")

            # Ensure URL has proper protocol if missing
            if url and not url.startswith(("http://", "https://", "//")) and "." in url:
                # If it looks like a domain, prepend https://
                url = f"https://{url}"

            # Validate required parameters after processing
            if not url:
                # Empty URL means server not configured - hide button gracefully
                return ""

            if not text:
                return '\n\n<div class="text-sm text-red-500 italic">Button widget requires text parameter</div>\n\n'

            # Escape for safety
            escaped_text = html.escape(text)
            escaped_url = html.escape(url)

            # Generate button HTML
            return f'''
<div class="flex justify-center w-full my-6">
<div class="inline-flex">
    <a href="{escaped_url}" class="inline-flex items-center px-6 py-3 text-base font-medium text-white bg-primary rounded-lg hover:bg-primary-hover focus:ring-4 focus:ring-primary-300 dark:bg-primary-600 dark:hover:bg-primary dark:focus:ring-primary-800 transition-colors duration-200" style="text-decoration: none;" target="_blank" rel="noopener noreferrer">
        {escaped_text}
    </a>
</div>
</div>
'''

        except Exception as e:
            return f'\n\n<div class="text-sm text-gray-500 italic">Button widget error: {e}</div>\n\n'


# Widget registry
WIDGET_REGISTRY = {
    "recently_added_media": RecentlyAddedMediaWidget(),
    "button": ButtonWidget(),
}


def process_card_delimiters(content: str) -> str:
    """
    Process card delimiters (|||) and convert to styled cards.

    Example:
    |||
    # Card Title
    This is content
    |||
    """

    def replace_card(match):
        card_content = match.group(1).strip()

        if not card_content:
            return '<div class="text-sm text-red-500 italic">Empty card content</div>'

        try:
            # Convert markdown to HTML
            html_content = markdown.markdown(
                card_content, extensions=["extra", "nl2br"]
            )

            # Wrap in card styling with extra bottom margin for spacing between cards
            return f"""<div class="card-widget my-6 mb-8 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 p-5 sm:p-6">
    <div class="prose prose-sm dark:prose-invert max-w-none">
        {html_content}
    </div>
</div>"""

        except Exception as e:
            return f'<div class="text-sm text-red-500 italic">Card rendering error: {e}</div>'

    # Match ||| ... ||| patterns
    pattern = r"\|\|\|\s*\n(.*?)\n\s*\|\|\|"
    return re.sub(pattern, replace_card, content, flags=re.DOTALL)


def process_widget_placeholders(
    content: str, server_type: str, context: dict | None = None
) -> str:
    """
    Process widget placeholders in markdown content.

    Supports syntax like:
    {{ widget:recently_added_media }}
    {{ widget:recently_added_media limit=6 }}
    {{ widget:button url="https://example.com" text="Click Here" }}
    """
    context = context or {}

    def replace_widget(match):
        full_match = match.group(0)
        widget_call = match.group(1).strip()

        # Parse widget call
        if not widget_call.startswith("widget:"):
            return full_match

        # Remove 'widget:' prefix
        widget_spec = widget_call[7:]  # len('widget:') = 7

        # Split on first space to separate widget name from parameters
        parts = widget_spec.split(None, 1)
        widget_name = parts[0]

        # Parse parameters if present
        params = {}
        if len(parts) > 1:
            param_string = parts[1]

            # Match key="value" or key=_("value") or key=value patterns
            # This regex handles:
            # 1. Quoted values: key="value with spaces"
            # 2. Function calls with quoted args: key=_("translated text")
            # 3. Unquoted values: key=123
            param_pattern = r'(\w+)=(?:"([^"]*)"|(\w+\([^)]+\))|(\S+))'

            for param_match in re.finditer(param_pattern, param_string):
                key = param_match.group(1)
                # Use quoted value if present, otherwise function call, otherwise unquoted value
                value = (
                    param_match.group(2)
                    if param_match.group(2) is not None
                    else param_match.group(3)
                    if param_match.group(3) is not None
                    else param_match.group(4)
                )

                # Try to convert to int if possible
                from contextlib import suppress

                with suppress(ValueError):
                    value = int(value)

                params[key] = value

        # Get widget and render
        widget = WIDGET_REGISTRY.get(widget_name)
        if widget:
            return widget.render(server_type, _context=context, **params)
        return f'<div class="text-sm text-red-500">Unknown widget: {widget_name}</div>'

    # Match {{ widget:... }} patterns specifically (not other {{ }} expressions)
    pattern = r"\{\{\s*(widget:[^}]+)\s*\}\}"
    return re.sub(pattern, replace_widget, content)
