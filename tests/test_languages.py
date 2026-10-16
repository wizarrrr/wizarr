"""Configured languages and their catalogs (wizarrrr/wizarr#1179 adds Estonian)."""

from pathlib import Path

import pytest

from app.config import BaseConfig
from app.extensions import _select_locale

TRANSLATIONS = Path(__file__).resolve().parents[1] / "app" / "translations"


def test_english_is_first_and_the_other_codes_are_sorted():
    codes = list(BaseConfig.LANGUAGES)

    assert codes[0] == "en"
    assert codes[1:] == sorted(codes[1:])


def test_each_language_has_a_catalog_and_each_catalog_a_language():
    catalogs = {
        path.parent.parent.name for path in TRANSLATIONS.glob("*/LC_MESSAGES/*.po")
    }

    assert catalogs == set(BaseConfig.LANGUAGES) - {"en"}


@pytest.mark.parametrize("requested", ["et", "et-EE", "ET"])
def test_estonian_can_be_selected(app, requested):
    with app.test_request_context(f"/?lang={requested}"):
        assert _select_locale() == "et"
