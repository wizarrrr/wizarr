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
data = {
    "server_ids": [1],
    "expires_in_days": 7,
    "duration": "30",
    "unlimited": False
}

response = requests.post(
    f"{BASE_URL}/invitations",
    headers={**headers, "Content-Type": "application/json"},
    json=data
)

if response.status_code == 201:
    invitation = response.json()
    print(f"Invitation URL: {invitation['invitation']['url']}")
```

## Interactive Testing

Visit `/api/docs/` on your Wizarr instance to:
- Browse all available endpoints
- Test API calls directly in your browser
- View detailed request/response examples
- Download the OpenAPI specification

The Swagger UI provides the most up-to-date and complete API documentation.