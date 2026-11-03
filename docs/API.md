# Wizarr API Documentation

Wizarr provides a comprehensive REST API with **automatic OpenAPI/Swagger documentation**.

## Interactive Documentation

- **📖 Swagger UI**: `http://your-wizarr-instance/api/docs/`
- **📋 OpenAPI Spec**: `http://your-wizarr-instance/api/swagger.json`

The interactive documentation provides:
- Real-time API testing interface  
- Complete request/response schemas
- Authentication examples
- Error code explanations

## Quick Start

### Authentication

All API endpoints require authentication using an API key:

```bash
curl -H "X-API-Key: your_api_key_here" \
     http://your-wizarr-instance/api/status
```

### API Key Management

1. Log into your Wizarr web interface
2. Navigate to **Settings → API Keys**
3. Click **"Create API Key"**
4. Copy the generated key (shown only once)

### Available Endpoints

The API is organized into the following sections:

- **Status**: System statistics
- **Version**: The installed Wizarr version
- **Users**: User management across media servers
- **Invitations**: Invitation creation and management
- **Libraries**: Media library information
- **Servers**: Configured media server details
- **API Keys**: API key management
- **Activity**: Playback statistics from the Activity tab

### Example Usage

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "http://your-wizarr-instance/api"
headers = {"X-API-Key": API_KEY}

# Get system status
response = requests.get(f"{BASE_URL}/status", headers=headers)
print(response.json())

# Create invitation
data = {"server_ids": [1], "expires_in_days": 7, "duration": "30", "unlimited": False}

response = requests.post(
    f"{BASE_URL}/invitations",
    headers={**headers, "Content-Type": "application/json"},
    json=data,
)

if response.status_code == 201:
    invitation = response.json()
    print(f"Invitation URL: {invitation['invitation']['url']}")
```

### Invitation revocation (Emby)

`DELETE /api/invitations/{id}` still deletes the invitation **without revoking existing
accounts**. Its response also contains `operation_id`; durable join provenance and
retired codes survive deletion. Retired codes cannot be reused.

To explicitly revoke access:

- `POST /api/invitations/{id}/revoke`: commit an irreversible join cutoff, then try
  to disable all known Emby identities.
- `GET /api/invitations/revocations/{operation_id}`: read persisted status only.
- `POST /api/invitations/revocations/{operation_id}`: explicitly commit/retry the
  same cutoff, including after invitation deletion or a lost response/restart.

All require `X-API-Key`. No request body or implicit account deletion is involved.
POST returns `200` only for `state: "revoked"`; otherwise `202` with `state: "pending"`.
Status includes `operation_id`, `barrier_committed`, `in_flight_joins`,
`account_ids_complete`, and `accounts` (join-attempt ID, server ID, local user ID if
available, actual `remote_user_id`, and `remote_state: "disabled" | "unconfirmed"`).
No credentials, passwords, API keys, or generic user `token` fields are exported.

The cutoff is serialized through SQLite against **each** Emby join write, including
the legacy password route, not a process-local lock. A remote request already holding
the writer lock finishes before the cutoff can commit; its returned identity is
committed under that same lock. Requests may therefore wait for an ongoing remote
write or fail with a database/network error; such errors do not confirm a barrier.
Admitted joins remain counted until they finish. After cutoff, later create/policy
writes are rejected and known accounts are reconciled. Disable requires an exact-ID
remote policy readback showing `IsDisabled: true`; failure never falls back to DELETE.
A local missing user, an Emby 404 (documented as not found **or unavailable**), a changed
server endpoint, or a removed server does not prove revocation.

**Limits:** This is an Emby invitation-join contract, not protection against deliberate
external/admin re-enabling or a guarantee for LDAP, Plex, companion services, or other
backends. Unsupported configurations remain incomplete. All invitations present at
migration time remain identity-incomplete, even if marked unused: old workers did not
register attempts. No name/email/legacy-token guessing or automatic legacy recovery
is performed. Run only upgraded workers; mixed-version operation is not supported.

[Emby's documented create request](https://dev.emby.media/reference/RestAPI/UserService/postUsersNew.html)
exposes `Name`, `CopyFromUserId`, and `UserCopyOptions`, not a documented idempotency key
or direct disabled-creation contract. This implementation **does not claim atomic
disabled creation**. A crash/lost response after remote creation but before identity
commit can leave an active unidentified account. The committed uncertain attempt stays
pending across restarts, prevents blind create retries on that invitation/server, and
never reports complete identities or terminal revocation. Operator investigation is
required; there is no automatic recovery/lease expiry that pretends the attempt finished.
Known-ID failures can be retried with POST; GET does not perform remote reconciliation.

The schema migration is additive and leaves existing invitation/user/credential rows
unchanged. Downgrade removes the new safety state; quiesce joins and resolve operations
before rolling back. The migration targets current main. A schema-only probe against
`v2026.10.1` is **not** a tested application backport or a production rollout approval.

### Activity Statistics

Three endpoints give the playback statistics of the **Activity** tab:

- `GET /api/activity/stats`: the totals of the dashboard (sessions, users, watch time and average session length)
- `GET /api/activity/users`: the sessions and the watch time of each user
- `GET /api/activity/content`: the plays and the watch time of each movie or series

All three accept these query parameters:

| Parameter | Description |
| --- | --- |
| `days` | Days back from now. The default is `30`. Use `0` for all time. |
| `start`, `end` | A period, as ISO 8601 dates or date-times (for example `2026-09-01`). Values without a time zone are UTC. A date in `end` includes the whole day. Do not use them together with `days`. |
| `server_id` | Count only the sessions on this media server. |
| `username` | Count only the sessions of this user. |
| `limit` | `users` and `content` only. The maximum number of rows, from 1 to 1000. The default is `100`. |

Durations are in seconds. Watch time counts only the sessions that have stopped. Like the dashboard, the statistics do not include sessions with an Unknown user, title or device.

```bash
curl -H "X-API-Key: your_api_key_here" \
     "http://your-wizarr-instance/api/activity/stats?start=2026-09-01&end=2026-09-30"
```

```json
{
  "start": "2026-09-01T00:00:00+00:00",
  "end": "2026-10-01T00:00:00+00:00",
  "total_sessions": 843,
  "unique_users": 11,
  "total_watch_time_seconds": 1850401,
  "avg_session_length_seconds": 2044
}
```

### Version

`GET /api/version` gives the installed Wizarr version. Update monitors, for example Argus, can read it. A local build without a release version gives `"dev"`.

```bash
curl -H "X-API-Key: your_api_key_here" \
     "http://your-wizarr-instance/api/version"
```

```json
{
  "version": "v2026.10.0"
}
```

## Interactive Testing

Visit `/api/docs/` on your Wizarr instance to:
- Browse all available endpoints
- Test API calls directly in your browser
- View detailed request/response examples
- Download the OpenAPI specification

The Swagger UI provides the most up-to-date and complete API documentation.