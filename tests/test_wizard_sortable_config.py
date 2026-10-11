"""
Tests for Sortable.js configuration in wizard-steps.js.

This module tests that the Sortable.js configuration is correct and doesn't
contain whitespace in CSS class tokens, which would cause DOMException errors.
"""

import re
from pathlib import Path


def test_sortable_config_no_whitespace_in_class_tokens():
    """Test that Sortable.js configuration doesn't have whitespace in class tokens."""
    # Read the wizard-steps.js file
    js_file = Path(__file__).parent.parent / "app" / "static" / "js" / "wizard-steps.js"
    content = js_file.read_text()

    # Find the sortableConfig object
    # Look for patterns like: ghostClass: 'some-class'
    class_patterns = [
        r"ghostClass:\s*['\"]([^'\"]+)['\"]",
        r"chosenClass:\s*['\"]([^'\"]+)['\"]",
        r"dragClass:\s*['\"]([^'\"]+)['\"]",
    ]

    errors = []
    for pattern in class_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if " " in match:
                errors.append(f"Found whitespace in class token: '{match}'")

    assert not errors, (
        "Sortable.js configuration has invalid class tokens:\n" + "\n".join(errors)
    )


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


def test_css_classes_exist_in_stylesheet():
    """Test that the Sortable.js CSS classes are defined in the stylesheet."""
    css_file = Path(__file__).parent.parent / "app" / "static" / "src" / "style.css"
    content = css_file.read_text()

    required_classes = [
        ".sortable-ghost",
        ".sortable-chosen",
        ".sortable-drag",
    ]

    for css_class in required_classes:
        assert css_class in content, f"CSS class '{css_class}' not found in style.css"
