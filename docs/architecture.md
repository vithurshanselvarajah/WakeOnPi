# Architecture Overview

## System Architecture

WakeOnPi is a modular Python application designed to run on Raspberry Pi with minimal resource overhead. The system is built around a Flask web server with async motion detection and MQTT integration.

```
┌─────────────────────────────────────────────────────────┐
│               Web Interface (/settings)                  │
├─────────────────────────────────────────────────────────┤
│                    Flask App                             │
│  ┌──────────────────────────────────────────────────┐   │
│  │ HTTP Endpoints:                                   │   │
│  │  - /stream (MJPEG)                                │   │
│  │  - /snapshot (JPEG)                               │   │
│  │  - /api/* (REST API)                              │   │
│  │  - /ws (WebSocket)                                │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                 Core Services Layer                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │   Motion     │ │   Display    │ │   Recording  │   │
│  │  Detection   │ │   Control    │ │   Service    │   │
│  └──────────────┘ └──────────────┘ └──────────────┘   │
├─────────────────────────────────────────────────────────┤
│               Hardware & External Integration            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │   Camera     │ │   Display    │ │    MQTT      │   │
│  │   (picamera)│ │   (sysfs)    │ │    Broker    │   │
│  └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Module Breakdown

### Core Modules

#### `app.py` - Flask Application
Main web server and request handling. Handles:
- HTTP endpoint routing
- WebSocket connections
- Session management
- Authentication

#### `camera.py` - Camera Interface
Wrapper around `picamera` library. Responsibilities:
- Frame capture and streaming
- Resolution management
- Rotation and flip settings

#### `motion.py` - Motion Detection Engine
Low-overhead motion detection. Implements:
- Frame downsampling for efficiency
- Background subtraction algorithms
- Motion event debouncing
- Sensitivity threshold configuration

#### `display.py` - Display Control
Manages Raspberry Pi display power and brightness:
- sysfs interface to backlight
- Power state management
- Brightness level control
- Auto-off timeout implementation

#### `recorder.py` - Video Recording
Handles manual and motion-triggered recording:
- H.264 video encoding
- File management
- Quality configuration
- Storage optimization

#### `mqtt.py` - MQTT Integration
Manages MQTT broker communication:
- State publishing
- Command subscription
- Home Assistant discovery
- Connection management

#### `state.py` - Application State
Thread-safe state management:
- Display state
- Motion detection status
- Recording state
- System metrics

#### `browser.py` - Web UI
Frontend assets and templates:
- Settings dashboard (HTML/CSS/JS)
- Real-time WebSocket client
- Live stream viewer

#### `overlay.py` - Stream Overlay
Adds visual information to MJPEG stream:
- Motion detection indicators
- Recording status display
- Timestamp overlay

#### `config.py` - Configuration
Environment variable management:
- Settings loading
- Validation
- Default values

#### `system.py` - System Information
Collects system metrics:
- CPU usage and temperature
- Memory statistics
- Uptime tracking

#### `auth.py` - Authentication
Handles HTTP Basic Auth:
- Credential validation
- Session token management
- Access control

#### `logging_config.py` - Logging Setup
Configures application logging:
- Log level management
- File/console output
- Log formatting

### External Integration

#### Camera Input
- **Interface**: picamera library (Raspberry Pi specific)
- **Resolution**: Configurable (default 1280x720)
- **Output**: Raw frames for motion detection, MJPEG stream

#### Display Control
- **Interface**: sysfs backlight paths
- **Typical Path**: `/sys/class/backlight/rpi_backlight/brightness`
- **Control**: Power on/off, brightness level (0-255)

#### MQTT Integration
- **Client Library**: paho-mqtt
- **Topics**: Configurable prefix with standardized suffixes
- **Discovery**: Home Assistant MQTT Discovery protocol
- **Commands**: Display control, recording management

#### Web UI
- **Frontend**: HTML/CSS/JavaScript
- **Real-time**: WebSocket for live updates
- **Streaming**: MJPEG via HTTP

## Data Flow

### Motion Detection Pipeline
```
Camera Frame → Capture → Downsampling → Background Subtraction → Threshold Check → Event
```

1. Camera captures frame at configured framerate
2. Frame is downsampled to reduce processing
3. Background subtraction identifies changes
4. Motion area compared against threshold
5. Motion event fired if threshold exceeded
6. Debounce prevents rapid toggles

### Display Control Flow
```
Motion Detected → Display Event → Control sysfs → Physical Output
```

1. Motion detection module fires event
2. Display control module updates state
3. sysfs files written to control hardware
4. Physical display responds

### MQTT Publishing Flow
```
State Change → MQTT Module → Broker → Subscribers (HA, etc.)
```

1. Any state change (display, motion, recording) triggers update
2. MQTT module formats and publishes message
3. Broker distributes to subscribed clients
4. Home Assistant receives discovery/status messages

### WebSocket Update Flow
```
State Change → WebSocket Module → Connected Clients
```

1. State change detected
2. Message formatted as JSON
3. Sent to all connected WebSocket clients
4. Frontend updates UI in real-time

## Performance Considerations

### CPU Optimization
- Motion detection uses downsampled frames (100x100 pixels)
- Frame processing is rate-limited
- Heavy operations run in separate threads

### Memory Management
- Streaming buffer limited to prevent memory growth
- Frame caching disabled by default
- MQTT message queue bounded

### Power Efficiency
- Camera FPS adjustable for Pi Zero/Zero 2 compatibility
- Display auto-off timeout reduces backlight usage
- Motion detection sleep mode for idle periods

## Thread Management

WakeOnPi uses threading for concurrent operations:

- **Main Thread**: Flask web server
- **Motion Thread**: Continuous frame processing
- **MQTT Thread**: Broker communication
- **Recording Thread**: Video encoding (if active)
- **WebSocket Thread**: Client management

Thread-safe state updates through `state.py` module with locks.

## Configuration Flow

```
Environment Variables → config.py → State Module → Services
                    ↓
                 settings.html (runtime updates)
```

1. Startup: Environment variables loaded into config
2. Runtime: Settings can be modified via web UI
3. Persistence: Settings saved to disk
4. Broadcast: Changes sent to MQTT and WebSocket clients

## Security Architecture

- **First-Connection Setup**: On first launch, all routes redirect to `/setup` until an admin account is created
- **Authentication**: Session-based cookie auth for WebUI; HTTP Basic Auth for stream endpoints
- **Password Storage**: Salted PBKDF2 hashes (never stored in plaintext)
- **HTTPS**: Support via reverse proxy (nginx/Caddy)
- **MQTT**: Optional username/password and topic ACLs
- **Isolation**: Runs with minimal required permissions

## Error Handling & Recovery

- **Graceful Degradation**: Individual component failures don't crash app
- **Reconnection**: MQTT auto-reconnects on connection loss
- **Fallbacks**: Continue operation if optional features fail
- **Logging**: All errors logged with context for debugging

## Extensibility

The modular design allows:
- Custom motion detection algorithms (override `motion.py`)
- Additional hardware integration (extend `display.py`)
- Custom streaming formats (extend `browser.py`)
- Alternative state backends (replace `state.py`)

## Deployment Variants

### Development
- Python virtual environment
- Flask debug mode
- Local testing without display/camera

### Production (systemd service)
- Runs as service on startup
- Restarts on failure
- Integrated logging
- Resource limits applied
