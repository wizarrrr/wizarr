# Wizarr API Documentation

This document provides comprehensive documentation for the Wizarr API endpoints, including authentication, request/response formats, and usage examples.

## Table of Contents

- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
  - [Status](#status)
  - [Users](#users)
  - [Invitations](#invitations)
  - [Libraries](#libraries)
  - [Servers](#servers)
  - [API Keys](#api-keys)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Authentication

All API endpoints require authentication using an API key. API keys can be created through the Wizarr web interface under Settings → API Keys.

### API Key Header

Include your API key in the request headers:

```
X-API-Key: your_api_key_here
```

### Example Request

```bash
curl -H "X-API-Key: your_api_key_here" https://your-wizarr-instance.com/api/status
```

## API Endpoints

### Status

Get overall statistics about your Wizarr instance.

#### GET `/api/status`

Returns basic statistics about users and invitations.

**Response:**
```json
{
  "users": 15,
  "invites": 8,
  "pending": 3,
  "expired": 2
}
```

**Example:**
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/status
```

---

### Users

Manage users across all configured media servers.

#### GET `/api/users`

List all users across all media servers.

**Response:**
```json
{
  "users": [
    {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com",
      "server": "Main Plex Server",
      "server_type": "plex",
      "expires": "2024-08-28T12:00:00Z",
      "created": "2024-07-28T12:00:00Z"
    }
  ],
  "count": 1
}
```

**Example:**
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/users
```

#### DELETE `/api/users/{user_id}`

Delete a specific user by ID.

**Parameters:**
- `user_id` (integer) - The ID of the user to delete

**Response:**
```json
{
  "message": "User john_doe deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE \
     -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/users/1
```

#### POST `/api/users/{user_id}/extend`

Extend a user's expiry date.

**Parameters:**
- `user_id` (integer) - The ID of the user
- `days` (integer, optional) - Number of days to extend (default: 30)

**Request Body:**
```json
{
  "days": 14
}
```

**Response:**
```json
{
  "message": "User john_doe expiry extended by 14 days",
  "new_expiry": "2024-09-11T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{"days": 14}' \
     https://your-wizarr-instance.com/api/users/1/extend
```

---

### Invitations

Manage invitation codes for new users.

#### GET `/api/invitations`

List all invitations with their current status and server information.

**Response:**
```json
{
  "invitations": [
    {
      "id": 1,
      "code": "ABC123",
      "status": "pending",
      "created": "2024-07-28T12:00:00Z",
      "expires": "2024-08-04T12:00:00Z",
      "used_at": null,
      "used_by": null,
      "duration": "30",
      "unlimited": false,
      "specific_libraries": null,
      "display_name": "My Jellyfin Server",
      "server_names": ["My Jellyfin Server"],
      "uses_global_setting": false
    },
    {
      "id": 2,
      "code": "DEF456", 
      "status": "pending",
      "created": "2024-07-28T13:00:00Z",
      "expires": "2024-08-04T13:00:00Z",
      "used_at": null,
      "used_by": null,
      "duration": "unlimited",
      "unlimited": true,
      "specific_libraries": null,
      "display_name": "Plex Server, Jellyfin Server",
      "server_names": ["Plex Server", "Jellyfin Server"],
      "uses_global_setting": false
    }
  ],
  "count": 2
}
```

**Response Fields:**
- `display_name` (string) - The resolved display name for the invitation (either global setting or server names)
- `server_names` (array) - List of individual server names associated with the invitation
- `uses_global_setting` (boolean) - Whether the display name comes from global setting or server names

**Status Values:**
- `pending` - Invitation is active and can be used
- `used` - Invitation has been used
- `expired` - Invitation has expired

**Example:**
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/invitations
```

#### POST `/api/invitations`

Create a new invitation.

**Request Body:**
```json
{
  "expires_in_days": 7,
  "duration": "30",
  "unlimited": false,
  "library_ids": [1, 2],
  "allow_downloads": false,
  "allow_live_tv": false,
  "allow_mobile_uploads": false
}
```

**Parameters:**
- `expires_in_days` (integer, optional) - Days until invitation expires (1, 7, 30, or null for never)
- `duration` (string, optional) - User access duration in days or "unlimited" (default: "unlimited")
- `unlimited` (boolean, optional) - Whether user access is unlimited (default: true)
- `library_ids` (array, optional) - Array of library IDs to grant access to
- `allow_downloads` (boolean, optional) - Allow user downloads (default: false)
- `allow_live_tv` (boolean, optional) - Allow live TV access (default: false)
- `allow_mobile_uploads` (boolean, optional) - Allow mobile uploads (default: false)

**Response:**
```json
{
  "message": "Invitation created successfully",
  "invitation": {
    "id": 2,
    "code": "DEF456",
    "expires": "2024-08-04T12:00:00Z",
    "duration": "30",
    "unlimited": false,
    "display_name": "My Jellyfin Server",
    "server_names": ["My Jellyfin Server"],
    "uses_global_setting": false
  }
}
```

**Response Fields:**
- `display_name` (string) - The resolved display name for the invitation (either global setting or server names)
- `server_names` (array) - List of individual server names associated with the invitation
- `uses_global_setting` (boolean) - Whether the display name comes from global setting or server names

**Example:**
```bash
curl -X POST \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "expires_in_days": 7,
       "duration": "30",
       "unlimited": false,
       "library_ids": [1, 2]
     }' \
     https://your-wizarr-instance.com/api/invitations
```

#### DELETE `/api/invitations/{invitation_id}`

Delete a specific invitation.

**Parameters:**
- `invitation_id` (integer) - The ID of the invitation to delete

**Response:**
```json
{
  "message": "Invitation ABC123 deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE \
     -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/invitations/1
```

---

### Libraries

Get information about available media libraries.

#### GET `/api/libraries`

List all available libraries across all servers.

**Response:**
```json
{
  "libraries": [
    {
      "id": 1,
      "name": "Movies",
      "server_id": 1
    },
    {
      "id": 2,
      "name": "TV Shows",
      "server_id": 1
    }
  ],
  "count": 2
}
```

**Example:**
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/libraries
```

---

### Servers

Get information about configured media servers.

#### GET `/api/servers`

List all configured media servers.

**Response:**
```json
{
  "servers": [
    {
      "id": 1,
      "name": "Main Plex Server",
      "server_type": "plex",
      "server_url": "http://localhost:32400",
      "external_url": "https://plex.example.com",
      "verified": true,
      "allow_downloads": false,
      "allow_live_tv": true,
      "allow_mobile_uploads": false,
      "created_at": "2024-07-28T12:00:00Z"
    },
    {
      "id": 2,
      "name": "Jellyfin Server",
      "server_type": "jellyfin",
      "server_url": "http://localhost:8096",
      "external_url": null,
      "verified": true,
      "allow_downloads": true,
      "allow_live_tv": false,
      "allow_mobile_uploads": true,
      "created_at": "2024-07-28T13:00:00Z"
    }
  ],
  "count": 2
}
```

**Example:**
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/servers
```

---

### API Keys

Manage API keys programmatically (useful for automation and administrative tasks).

#### GET `/api/api-keys`

List all active API keys (excluding the actual key values for security).

**Response:**
```json
{
  "api_keys": [
    {
      "id": 1,
      "name": "Production API Key",
      "created_at": "2024-07-28T12:00:00Z",
      "last_used_at": "2024-07-28T14:30:00Z",
      "created_by": "admin"
    },
    {
      "id": 2,
      "name": "Development Key",
      "created_at": "2024-07-28T13:00:00Z",
      "last_used_at": null,
      "created_by": "admin"
    }
  ],
  "count": 2
}
```

**Example:**
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/api-keys
```

#### DELETE `/api/api-keys/{key_id}`

Delete a specific API key (soft delete - marks as inactive).

**Parameters:**
- `key_id` (integer) - The ID of the API key to delete

**Response:**
```json
{
  "message": "API key 'Development Key' deleted successfully"
}
```

**Security Note:** You cannot delete the API key that is currently being used for the request.

**Example:**
```bash
curl -X DELETE \
     -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/api-keys/2
```

---

## Error Handling

The API uses standard HTTP status codes to indicate success or failure of requests.

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Invalid or missing API key
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
  "error": "Error message describing what went wrong"
}
```

### Common Error Examples

**Missing API Key:**
```json
{
  "error": "API key required"
}
```

**Invalid API Key:**
```json
{
  "error": "Invalid API key"
}
```

**Resource Not Found:**
```json
{
  "error": "User not found"
}
```

---

## Rate Limiting

Currently, there are no explicit rate limits on the API endpoints. However, it's recommended to make requests responsibly to avoid overwhelming the server.

---

## Examples

### Complete User Management Workflow

#### 1. Check System Status
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/status
```

#### 2. List All Users
```bash
curl -H "X-API-Key: your_api_key" \
     https://your-wizarr-instance.com/api/users
```

#### 3. Create an Invitation
```bash
curl -X POST \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "expires_in_days": 7,
       "duration": "30",
       "unlimited": false
     }' \
     https://your-wizarr-instance.com/api/invitations
```

#### 4. Extend User Access
```bash
curl -X POST \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{"days": 30}' \
     https://your-wizarr-instance.com/api/users/1/extend
```

### Python Example

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://your-wizarr-instance.com/api"

headers = {"X-API-Key": API_KEY}

# Get status
response = requests.get(f"{BASE_URL}/status", headers=headers)
status_data = response.json()
print(f"Total users: {status_data['users']}")

# Create invitation
invitation_data = {
    "expires_in_days": 7,
    "duration": "30",
    "unlimited": False
}

response = requests.post(
    f"{BASE_URL}/invitations", 
    headers={**headers, "Content-Type": "application/json"},
    json=invitation_data
)

if response.status_code == 201:
    invitation = response.json()
    print(f"Created invitation: {invitation['invitation']['code']}")
```

### JavaScript Example

```javascript
const API_KEY = 'your_api_key_here';
const BASE_URL = 'https://your-wizarr-instance.com/api';

const headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
};

// Get all users
fetch(`${BASE_URL}/users`, { headers })
    .then(response => response.json())
    .then(data => {
        console.log(`Found ${data.count} users`);
        data.users.forEach(user => {
            console.log(`- ${user.username} (${user.server})`);
        });
    });

// Create invitation
const invitationData = {
    expires_in_days: 7,
    duration: "30",
    unlimited: false
};

fetch(`${BASE_URL}/invitations`, {
    method: 'POST',
    headers,
    body: JSON.stringify(invitationData)
})
.then(response => response.json())
.then(data => {
    if (data.invitation) {
        console.log(`Created invitation: ${data.invitation.code}`);
    }
});
```

---

## API Key Management

### Creating API Keys

1. Log into your Wizarr web interface
2. Navigate to Settings → API Keys
3. Click "Create API Key"
4. Enter a descriptive name
5. Copy the generated API key (it will only be shown once)

### Security Best Practices

- Store API keys securely and never commit them to version control
- Use different API keys for different applications or environments
- Rotate API keys regularly
- Delete unused API keys
- Monitor API key usage through the web interface

### API Key Permissions

Currently, all API keys have full access to all endpoints. Future versions may include granular permissions.

---

## Changelog

- **v2.2.1** - Initial API documentation
  - Added comprehensive endpoint documentation
  - Fixed API key deletion UI glitch
  - Improved error handling and response formats
  - Added comprehensive test coverage