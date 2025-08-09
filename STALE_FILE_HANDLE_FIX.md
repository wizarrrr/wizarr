# Session Cache Stale File Handle Fix

## Problem
Users were experiencing `OSError: [Errno 116] Stale file handle` errors in the session cache, particularly after:
- Docker container restarts/updates from Watchtower
- Network storage issues (NFS, etc.)
- Filesystem I/O problems

## Root Cause
The Flask session storage was using `FileSystemCache` which can encounter stale file handles when:
1. The application tries to access session files after a container restart
2. Network storage becomes temporarily unavailable
3. File descriptors become invalid due to system changes

## Solution Implemented

### 1. Robust Session Cache Wrapper (`app/utils/session_cache.py`)
- Created `RobustFileSystemCache` that extends `FileSystemCache`
- Handles `OSError errno 116` gracefully by:
  - Logging the issue with context
  - Attempting to remove stale files
  - Retrying operations once
  - Continuing gracefully if cleanup fails

### 2. Enhanced Configuration (`app/config.py`)
- Added better cache parameters:
  - `threshold=1000` - automatic cleanup
  - `default_timeout=86400` - 24-hour session timeout  
  - `mode=0o600` - restricted file permissions
- Startup cleanup of existing stale files

### 3. Startup Stale File Cleanup
- Automatically detects and removes stale session files on application startup
- Prevents accumulation of problematic session files
- Logs cleanup activities for monitoring

## Expected Outcome
- Users will no longer see stale file handle errors in logs
- Session handling becomes more robust in containerized environments
- Graceful recovery from filesystem issues
- Improved reliability after container restarts

## Alternative Solutions (if needed)
If file-based sessions continue to cause issues, consider:
1. **Redis session backend** - More reliable for containerized apps
2. **Database-backed sessions** - Use existing SQLAlchemy connection
3. **Memory-only sessions** - For single-container deployments

## Testing
To verify the fix:
1. Monitor logs after container restarts - should see cleanup messages instead of errors
2. Check that sessions work normally after Watchtower updates
3. Verify session files are properly managed in `/data/database/sessions/`

## Deployment Notes
- This fix is backward compatible
- No migration required
- Existing session files will be cleaned up automatically
- Users may need to re-login after the first restart (expected)