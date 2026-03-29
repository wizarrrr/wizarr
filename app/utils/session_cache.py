"""
Robust session cache wrapper that handles corrupt and stale session files gracefully.

Addresses:
- 0-byte cache files left by interrupted container restarts (GitHub #1180)
- Stale file handle errors (errno 116) from network storage / container restarts
"""

import contextlib
import logging
import struct
from pathlib import Path

from cachelib.file import FileSystemCache


class RobustFileSystemCache(FileSystemCache):
    """
    A FileSystemCache wrapper that automatically removes corrupt or stale
    session files instead of logging warnings indefinitely.
    """

    def __init__(self, cache_dir, **kwargs):
        self.cache_dir = cache_dir
        super().__init__(cache_dir, **kwargs)
        self._cleanup_stale_files()

    def _handle_stale_file_error(
        self, operation_name: str, filename: str, error: OSError
    ):
        """Handle stale file handle errors by logging and attempting recovery."""
        if error.errno == 116:  # Stale file handle
            logging.warning(
                f"Stale file handle in session cache during {operation_name}: {filename}. "
                f"This typically happens after container restarts or network storage issues. "
                f"Attempting to continue..."
            )
            try:
                # Try to remove the problematic file
                if Path(filename).exists():
                    Path(filename).unlink()
                    logging.info(f"Removed stale session file: {filename}")
            except OSError as cleanup_error:
                logging.warning(
                    f"Could not cleanup stale file {filename}: {cleanup_error}"
                )
        else:
            # Re-raise non-stale file handle errors
            raise error

    def set(self, key, value, timeout=None, mgmt_element=False):
        """Set a cache value with stale file handle error recovery."""
        try:
            return super().set(key, value, timeout, mgmt_element=mgmt_element)
        except OSError as e:
            filename = self._get_filename(key)
            self._handle_stale_file_error("set", filename, e)
            # Retry once after cleanup
            try:
                return super().set(key, value, timeout, mgmt_element=mgmt_element)
            except OSError as retry_error:
                if retry_error.errno == 116:
                    logging.error(
                        f"Session cache set failed twice for {key}. "
                        f"Consider switching to a different session backend."
                    )
                    return False
                raise retry_error

    def get(self, key):
        """Get a cache value with stale file handle error recovery."""
        try:
            return super().get(key)
        except OSError as e:
            filename = self._get_filename(key)
            self._handle_stale_file_error("get", filename, e)
            # Return None for stale file handle errors (session will be recreated)
            return None

    def delete(self, key, mgmt_element=False):
        """Delete a cache value with stale file handle error recovery."""
        try:
            return super().delete(key, mgmt_element=mgmt_element)
        except OSError as e:
            filename = self._get_filename(key)
            self._handle_stale_file_error("delete", filename, e)
            # Consider delete successful for stale files (they're gone anyway)
            return True

    def _remove_expired(self, now: float) -> None:
        """Remove expired cache files, deleting corrupt/empty files instead of
        logging warnings forever (fixes GitHub #1180)."""
        for fname in self._list_dir():
            try:
                with self._safe_stream_open(fname, "rb") as f:
                    header = f.read(4)
                if len(header) < 4:
                    # Corrupt or empty file — remove it silently
                    Path(fname).unlink()
                    self._update_count(delta=-1)
                    continue
                expires = struct.unpack("I", header)[0]
                if expires != 0 and expires < now:
                    Path(fname).unlink()
                    self._update_count(delta=-1)
            except FileNotFoundError:
                pass
            except OSError as e:
                if e.errno == 116:  # Stale file handle
                    self._try_remove(fname)
                else:
                    logging.warning(
                        "Exception raised while handling cache file '%s'",
                        fname,
                        exc_info=True,
                    )
            except (EOFError, struct.error):
                # Corrupt file — remove it
                self._try_remove(fname)

    @staticmethod
    def _try_remove(fname: str) -> None:
        """Best-effort removal of a cache file."""
        with contextlib.suppress(OSError):
            Path(fname).unlink()

    def _cleanup_stale_files(self) -> None:
        """Clean up stale or corrupt session files at startup."""
        try:
            session_dir = Path(self.cache_dir)
            if not session_dir.exists():
                return

            bad_files: list[Path] = []
            for cache_file in session_dir.glob("*"):
                if not cache_file.is_file():
                    continue
                try:
                    # Empty files are corrupt — the header is a 4-byte struct
                    if cache_file.stat().st_size < 4:
                        bad_files.append(cache_file)
                        continue
                    with cache_file.open("rb") as f:
                        f.read(4)
                except OSError as e:
                    if e.errno == 116:  # Stale file handle
                        bad_files.append(cache_file)

            if bad_files:
                logging.info(
                    "Found %d corrupt/stale session files at startup, cleaning up...",
                    len(bad_files),
                )
                for bad_file in bad_files:
                    try:
                        bad_file.unlink()
                    except OSError as cleanup_error:
                        logging.warning(
                            "Could not cleanup session file %s: %s",
                            bad_file,
                            cleanup_error,
                        )

        except Exception as e:
            logging.warning("Session cache startup cleanup failed: %s", e)
