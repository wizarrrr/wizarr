"""Remove active content from wizard HTML."""

from urllib.parse import urlsplit

import nh3


def _filter_attribute(tag: str, attribute: str, value: str) -> str | None:
    if tag == "iframe" and attribute == "src":
        # Keep the built-in Discord preset. Do not embed application pages.
        try:
            url = urlsplit(value)
            if (
                url.scheme != "https"
                or url.netloc != "discord.com"
                or url.path != "/widget"
            ):
                return None
        except ValueError:
            return None
    return value


_CLEANER = nh3.Cleaner(
    tags=nh3.ALLOWED_TAGS | {"iframe", "svg", "path"},
    attributes={
        **nh3.ALLOWED_ATTRIBUTES,
        "*": {"class", "title", "style"},
        "a": {"href", "title", "target"},
        "img": {"src", "alt", "width", "height", "loading", "decoding"},
        "iframe": {"src", "width", "height", "frameborder", "allowtransparency"},
        "svg": {"viewBox", "fill", "width", "height", "aria-hidden"},
        "path": {"d", "fill"},
    },
    attribute_filter=_filter_attribute,
    set_tag_attribute_values={
        "iframe": {
            "sandbox": "allow-popups allow-same-origin allow-scripts",
            "referrerpolicy": "no-referrer",
        },
    },
    url_schemes={"https", "http", "mailto"},
    filter_style_properties={
        "color",
        "background-color",
        "width",
        "height",
        "text-align",
        "text-decoration",
    },
)


def sanitize_wizard_html(html: str) -> str:
    """Keep display markup and remove scripts and application actions."""
    return _CLEANER.clean(html)
