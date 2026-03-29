"""Tests for RobustFileSystemCache — corrupt/empty file handling (GitHub #1180)."""

import struct
import time

import pytest

from app.utils.session_cache import RobustFileSystemCache


@pytest.fixture
def cache_dir(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    return d


class TestStartupCleanup:
    """_cleanup_stale_files removes corrupt files at init."""

    def test_removes_empty_files(self, cache_dir):
        # Create a 0-byte file (the exact scenario from #1180)
        (cache_dir / "empty_session").write_bytes(b"")

        cache = RobustFileSystemCache(str(cache_dir))
        assert not (cache_dir / "empty_session").exists()
        # Cache should still work after cleanup
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_removes_truncated_files(self, cache_dir):
        # File with fewer than 4 bytes (truncated header)
        (cache_dir / "truncated").write_bytes(b"\x00\x01")

        RobustFileSystemCache(str(cache_dir))
        assert not (cache_dir / "truncated").exists()

    def test_keeps_valid_files(self, cache_dir):
        # Create a valid cache file (4-byte header + pickled data)
        expires = int(time.time()) + 3600  # 1 hour from now
        header = struct.pack("I", expires)
        (cache_dir / "valid_session").write_bytes(header + b"some_data")

        RobustFileSystemCache(str(cache_dir))
        assert (cache_dir / "valid_session").exists()


class TestRemoveExpired:
    """_remove_expired deletes corrupt files instead of logging forever."""

    def test_removes_empty_file_during_expiry_check(self, cache_dir):
        cache = RobustFileSystemCache(str(cache_dir))

        # Sneak in a 0-byte file after init
        (cache_dir / "empty_after_init").write_bytes(b"")

        # Trigger expiry check
        cache._remove_expired(time.time())

        assert not (cache_dir / "empty_after_init").exists()

    def test_removes_truncated_file_during_expiry_check(self, cache_dir):
        cache = RobustFileSystemCache(str(cache_dir))

        (cache_dir / "short_header").write_bytes(b"\x00")

        cache._remove_expired(time.time())

        assert not (cache_dir / "short_header").exists()

    def test_normal_expiry_still_works(self, cache_dir):
        cache = RobustFileSystemCache(str(cache_dir), default_timeout=1)
        cache.set("ephemeral", "data")
        assert cache.get("ephemeral") == "data"

        # Wait for expiry
        time.sleep(1.5)
        cache._remove_expired(time.time())

        assert cache.get("ephemeral") is None
