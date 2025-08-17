# Wizarr Testing Documentation

This directory contains comprehensive tests for the Wizarr invitation system.

## Test Structure

### Core Test Files

- **`test_invitation_comprehensive.py`** - Complete invitation workflow tests with API simulation
- **`test_invitation_performance.py`** - Performance and load testing
- **`e2e/test_invitation_e2e.py`** - End-to-end tests using Playwright
- **`mocks/media_server_mocks.py`** - Mock implementations for media server APIs

### Mock System

The mock system simulates various media server APIs (Jellyfin, Plex, Audiobookshelf) without requiring actual server instances:

```python
from tests.mocks import create_mock_client, setup_mock_servers

# Setup
setup_mock_servers()

# Create mock client
mock_client = create_mock_client("jellyfin", server_id=1)

# Simulate failures
simulate_server_failure()
simulate_user_creation_failure(["problematic_username"])
```

## Test Categories

### 1. Unit Tests
- **Invitation validation** - Test `is_invite_valid()` logic
- **Expiry calculations** - Test duration and expiry date handling
- **Library assignment** - Test invitation-specific library restrictions

### 2. Integration Tests  
- **Single-server invitations** - Test complete workflow for one server
- **Multi-server invitations** - Test cross-server invitation processing
- **Error handling** - Test rollback and error recovery
- **Identity linking** - Test user identity linking across servers

### 3. End-to-End Tests
- **Complete user journey** - From invitation link to account creation
- **Form validation** - Test UI validation and error handling
- **Multi-server UI flow** - Test UI for complex invitation scenarios
- **Accessibility** - Test keyboard navigation and screen reader support

### 4. Performance Tests
- **Single invitation timing** - Ensure <1s processing time
- **Concurrent processing** - Test multiple simultaneous invitations
- **Database performance** - Test with large datasets (500+ invitations)
- **Memory usage** - Ensure no memory leaks during processing

## Running Tests

### All Tests
```bash
uv run pytest tests/ -v
```

### Specific Test Categories
```bash
# Unit and integration tests
uv run pytest tests/test_invitation_comprehensive.py -v

# Performance tests
uv run pytest tests/test_invitation_performance.py -v

# End-to-end tests
uv run pytest tests/e2e/test_invitation_e2e.py -v
```

### With Coverage
```bash
uv run pytest tests/ --cov=app/services/invitation_manager --cov=app/services/invites --cov-report=html
```

## Test Scenarios Covered

### Happy Path Scenarios
- ✅ Single server invitation (Jellyfin, Plex, Audiobookshelf)
- ✅ Multi-server invitation with all servers succeeding
- ✅ Unlimited invitation reuse
- ✅ Library-specific invitations
- ✅ User expiry date calculation

### Error Scenarios
- ✅ Expired invitations
- ✅ Already used limited invitations
- ✅ Invalid invitation codes
- ✅ Server connection failures
- ✅ User creation failures
- ✅ Multi-server partial failures
- ✅ Complete multi-server failures

### Edge Cases
- ✅ Password mismatch validation
- ✅ Email format validation
- ✅ Concurrent invitation processing
- ✅ Database transaction rollbacks
- ✅ Identity linking for same invitation code

### Performance Cases
- ✅ Single invitation processing time (<1s)
- ✅ 10 concurrent invitations (<5s)
- ✅ Multi-server invitation (<3s)
- ✅ Large dataset queries (500+ records)
- ✅ Memory usage under load

## Mock API Behavior

The mock system simulates realistic API behavior:

### Jellyfin Mock
```python
# Success response
{
    "Id": "user-uuid",
    "Name": "username", 
    "Primary": "email@example.com",
    "Policy": {"EnableDownloads": True}
}

# Library assignment
client._set_specific_folders(user_id, ["lib1", "lib2"])

# Error simulation
simulate_user_creation_failure(["problematic_user"])
```

### Plex Mock
```python
# Uses email as primary identifier
# Automatically assigns all libraries
# Supports OAuth flow simulation
```

### State Management
```python
from tests.mocks import get_mock_state

# Check created users
state = get_mock_state()
print(f"Created {len(state.users)} users")

# Reset for clean tests
state.reset()
```

## Configuration

### Test Database
Tests use SQLite in-memory database by default. Configure via `conftest.py`.

### Mock Server URLs
- Jellyfin: `http://localhost:8096`  
- Plex: `http://localhost:32400`
- Audiobookshelf: `http://localhost:13378`

### Test Data
Mock servers come with predefined libraries:
- `lib1` - Movies
- `lib2` - TV Shows  
- `lib3` - Music
- `movies_4k` - Movies 4K
- `anime` - Anime
- `audiobooks` - Audiobooks

## Best Practices

### Writing New Tests
1. Use `setup_mock_servers()` in test setup
2. Create realistic test data using the models
3. Use `@patch('app.services.media.service.get_client_for_media_server')` for API mocking
4. Test both success and failure scenarios
5. Verify database state after operations
6. Check mock state for API calls

### Debugging Failed Tests
1. Check mock state: `get_mock_state().users`
2. Examine database records: `User.query.all()`
3. Review error messages in test output
4. Use `-s` flag to see print statements: `pytest -s`

### Performance Testing
1. Use `time.time()` for timing measurements
2. Set reasonable performance thresholds
3. Test with realistic data volumes
4. Monitor memory usage for long-running tests

## Future Enhancements

- [ ] Add visual regression tests for invitation pages
- [ ] Test invitation email notifications
- [ ] Add API rate limiting tests  
- [ ] Test invitation analytics and metrics
- [ ] Add security penetration tests
- [ ] Test invitation QR code generation