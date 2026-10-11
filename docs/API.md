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

## Interactive Testing

Visit `/api/docs/` on your Wizarr instance to:
- Browse all available endpoints
- Test API calls directly in your browser
- View detailed request/response examples
- Download the OpenAPI specification

The Swagger UI provides the most up-to-date and complete API documentation.