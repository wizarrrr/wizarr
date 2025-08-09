"""
Robust session cache wrapper that handles stale file handle errors gracefully.
"""

import logging
import os
from pathlib import Path

from cachelib.file import FileSystemCache


class RobustFileSystemCache(FileSystemCache):
    """
    A FileSystemCache wrapper that handles OSError errno 116 (stale file handle)
    by recreating the cache directory and continuing operation.
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
                if os.path.exists(filename):
                    os.unlink(filename)
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

    def delete(self, key):
        """Delete a cache value with stale file handle error recovery."""
        try:
            return super().delete(key)
        except OSError as e:
            filename = self._get_filename(key)
            self._handle_stale_file_error("delete", filename, e)
            # Consider delete successful for stale files (they're gone anyway)
            return True

    def _cleanup_stale_files(self):
        """Clean up any stale session files at startup."""
        try:
            session_dir = Path(self.cache_dir)
            if not session_dir.exists():
                return

            stale_files = []
            for cache_file in session_dir.glob("*"):
                if cache_file.is_file():
                    try:
                        # Try to access file stats to detect stale handles
                        cache_file.stat()
                        # Try to open/read the file briefly
                        with cache_file.open("rb") as f:
                            f.read(1)
                    except OSError as e:
                        if e.errno == 116:  # Stale file handle
                            stale_files.append(cache_file)

            if stale_files:
                logging.info(
                    f"Found {len(stale_files)} stale session files at startup, cleaning up..."
                )
                for stale_file in stale_files:
                    try:
                        stale_file.unlink()
                        logging.debug(f"Removed stale session file: {stale_file}")
                    except OSError as cleanup_error:
                        logging.warning(
                            f"Could not cleanup stale session file {stale_file}: {cleanup_error}"
                        )

        except Exception as e:
            logging.warning(f"Session cache startup cleanup failed: {e}")
