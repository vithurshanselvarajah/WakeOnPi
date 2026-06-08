# API Reference

## Overview

WakeOnPi exposes a RESTful API for programmatic control and monitoring. Most endpoints require authentication.

## Authentication

Authentication uses HTTP Basic Auth. Include credentials in requests:

```bash
curl -u username:password http://pi-ip:5000/api/status
```

Or set the Authorization header:

```bash
curl -H "Authorization: Basic base64(username:password)" http://pi-ip:5000/api/status
```

## Endpoints

### Display Control

#### Get Display Status
```
GET /api/status
```

Returns current display state, brightness, and system information.

**Authentication**: Required

**Response**:
```json
{
  "display": {
    "power": "on",
    "brightness": 100,
    "max_brightness": 255
  },
  "motion": {
    "detected": false,
    "last_detection": "2024-01-15T10:30:00Z"
  },
  "recording": {
    "active": false,
    "duration": 0
  },
  "system": {
    "uptime": 3600,
    "cpu_temp": 45.2,
    "cpu_usage": 15.3,
    "memory_usage": 42.1
  }
}
```

#### Set Display Power
```
POST /api/display
```

Control display power and brightness.

**Authentication**: Required

**Request Body**:
```json
{
  "power": "on",
  "brightness": 100
}
```

**Response**:
```json
{
  "success": true,
  "power": "on",
  "brightness": 100
}
```

### Motion Detection

#### Get Motion Status
```
GET /api/status
```

Included in the status response.

#### Motion Alerts (SSE Stream)
```
GET /motion_alerts
```

Server-Sent Events stream of motion detection alerts.

**Authentication**: Not required

**Response Stream**:
```
data: {"event":"motion","timestamp":"2024-01-15T10:30:00Z"}
data: {"event":"nomotion","timestamp":"2024-01-15T10:35:00Z"}
```

### Stream & Snapshots

#### MJPEG Stream
```
GET /stream
```

Live MJPEG video stream.

**Authentication**: Required

**Content-Type**: `multipart/x-mixed-replace; boundary=FRAME`

#### Snapshot
```
GET /snapshot
```

Single JPEG frame capture.

**Authentication**: Required

**Content-Type**: `image/jpeg`

### Settings

#### Get Settings
```
GET /api/settings
```

Retrieve all configurable settings.

**Authentication**: Required

**Response**:
```json
{
  "motion": {
    "enabled": true,
    "threshold": 5.0,
    "min_area": 500
  },
  "display": {
    "auto_off_timeout": 600,
    "default_brightness": 100
  },
  "recording": {
    "enabled": true,
    "quality": 23,
    "auto_on_motion": true
  }
}
```

#### Update Settings
```
POST /api/settings
```

Update configuration settings.

**Authentication**: Required

**Request Body**:
```json
{
  "motion": {
    "enabled": true,
    "threshold": 3.0
  }
}
```

**Response**:
```json
{
  "success": true,
  "settings": { /* updated settings */ }
}
```

### Recording

#### Start Recording
```
POST /api/recording/start
```

Manually start recording.

**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "recording": true,
  "filename": "recording_20240115_103000.mp4"
}
```

#### Stop Recording
```
POST /api/recording/stop
```

Manually stop recording.

**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "recording": false,
  "duration": 120,
  "filesize": 15728640
}
```

### System

#### Health Check
```
GET /health
```

Simple health status without authentication.

**Response**:
```json
{
  "status": "healthy",
  "uptime": 3600
}
```

#### System Logs
```
GET /api/logs
```

Retrieve recent application logs.

**Authentication**: Required

**Query Parameters**:
- `lines` (int): Number of log lines to retrieve (default: 100)
- `level` (string): Log level filter (DEBUG, INFO, WARNING, ERROR)

**Response**:
```json
{
  "logs": [
    {"timestamp": "2024-01-15T10:30:00Z", "level": "INFO", "message": "Motion detected"},
    {"timestamp": "2024-01-15T10:35:00Z", "level": "INFO", "message": "Display turned on"}
  ]
}
```

### WebSocket

#### Live Status Updates
```
WS /ws
```

WebSocket connection for real-time status updates and control.

**Authentication**: Required (via query param or header)

**Example Connection**:
```javascript
const ws = new WebSocket('ws://pi-ip:5000/ws?token=auth_token');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Status update:', message);
};
```

**Message Types**:
```json
{"type": "motion", "detected": true}
{"type": "display", "power": "on", "brightness": 100}
{"type": "recording", "active": true}
{"type": "status", "data": { /* full status */ }}
```

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

### Common Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `UNAUTHORIZED` | 401 | Authentication failed |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_REQUEST` | 400 | Invalid request parameters |
| `INTERNAL_ERROR` | 500 | Server error |

## Rate Limiting

API endpoints are rate-limited to 60 requests per minute per IP address.

Response headers indicate rate limit status:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705321800
```

## Examples

### Using cURL

Get status:
```bash
curl -u admin:password http://pi-ip:5000/api/status
```

Set display brightness:
```bash
curl -u admin:password \
  -X POST http://pi-ip:5000/api/display \
  -H "Content-Type: application/json" \
  -d '{"brightness": 50}'
```

### Using Python

```python
import requests
from requests.auth import HTTPBasicAuth

auth = HTTPBasicAuth('admin', 'password')
url = 'http://pi-ip:5000/api/status'

response = requests.get(url, auth=auth)
status = response.json()
print(f"Display power: {status['display']['power']}")
print(f"Motion detected: {status['motion']['detected']}")
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'http://pi-ip:5000',
  auth: {
    username: 'admin',
    password: 'password'
  }
});

// Get status
const status = await api.get('/api/status');
console.log('Motion:', status.data.motion.detected);

// Control display
await api.post('/api/display', {
  power: 'on',
  brightness: 75
});
```

## Versioning

Current API version: v1

Future versions may be accessible via `/api/v2/` endpoints with breaking changes.
