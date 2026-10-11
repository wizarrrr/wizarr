"""
Every server type checks e-mail addresses with the same pattern.

Each client used to keep its own copy, in three flavours, so the same
address could be valid for one server type and rejected by another.
"""

import importlib

import pytest

from app.services.media import client_base

MODULES = ["audiobookshelf", "drop", "jellyfin", "kavita", "komga", "romm", "service"]


@pytest.mark.parametrize("name", MODULES)
def test_every_join_uses_the_shared_pattern(name):
    module = importlib.import_module(f"app.services.media.{name}")
    assert module.EMAIL_RE is client_base.EMAIL_RE


@pytest.mark.parametrize(
    "email", ["sam@example.com", "sam@studio.photography", "pat.lee+tv@mail.co.uk"]
)
def test_valid_addresses_pass(email):
    assert client_base.EMAIL_RE.fullmatch(email)


@pytest.mark.parametrize(
    "email", ["sam smith@example.com", "sam@example", "@example.com", "sam@@x.com"]
)
def test_invalid_addresses_fail(email):
    assert not client_base.EMAIL_RE.fullmatch(email)
