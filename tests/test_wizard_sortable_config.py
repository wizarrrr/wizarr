"""
Tests for Sortable.js configuration in wizard-steps.js.

A class token with whitespace (for example 'opacity-50 bg-gray') causes a
DOMException in Sortable.js. Each class option must be one class name.
"""

import re
from pathlib import Path


def test_sortable_config_uses_single_class_names():
    """Test that Sortable.js configuration uses single CSS class names."""
    js_file = Path(__file__).parent.parent / "app" / "static" / "js" / "wizard-steps.js"
    content = js_file.read_text()

    # Expected single-token class names based on style.css
    expected_classes = {
        "ghostClass": "sortable-ghost",
        "chosenClass": "sortable-chosen",
        "dragClass": "sortable-drag",
    }

    for config_key, expected_class in expected_classes.items():
        pattern = rf"{config_key}:\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)

        # Should find at least one match
        assert matches, f"Could not find {config_key} in sortableConfig"

        # All matches should use the expected single-token class name
        for match in matches:
            assert match == expected_class, (
                f"{config_key} should be '{expected_class}', but found '{match}'"
            )
