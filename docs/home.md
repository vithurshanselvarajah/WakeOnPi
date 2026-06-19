# WakeOnPi Documentation

Welcome to the WakeOnPi project documentation. WakeOnPi is a Raspberry Pi camera service that combines motion detection, MJPEG streaming, screen control, and optional MQTT/Home Assistant integration.

## Overview

WakeOnPi is built for always-on Pi setups where you want the display and stream to react to motion without wasting power. It provides:

- **Motion Detection**: Detects motion from low-resolution camera frames
- **Live Streaming**: MJPEG stream at `/stream` endpoint
- **Snapshots**: On-demand JPEG frames via `/snapshot`
- **Display Control**: Power and brightness control through sysfs backlight paths
- **Real-time Settings UI**: WebSocket-based dashboard at `/settings`
- **MQTT Integration**: Full state publishing and command acceptance with Home Assistant discovery support
- **Recording**: Manual and motion-triggered recording capabilities

## Quick Start

1. [Installation Guide](./installation) - Get WakeOnPi up and running
2. [Configuration](./configuration) - Configure settings and MQTT
3. [API Reference](./api) - Complete API endpoint documentation
4. [Architecture](./architecture) - Understand how WakeOnPi works

## Key Features

### Motion Detection
WakeOnPi processes low-resolution frames to efficiently detect motion while minimizing CPU usage on resource-constrained Raspberry Pi devices.

### Display Management
Control display power and brightness through sysfs backlight paths, ideal for keeping screens active only when needed.

### MQTT & Home Assistant
Full integration with MQTT brokers and automatic Home Assistant discovery for seamless smart home automation.

### Recording
Both manual recording and automatic motion-triggered recording ensure you capture important events.

### Streaming
Multiple endpoints provide live MJPEG streams and snapshots for remote monitoring.

## Documentation Structure

- **[Installation](./installation)** - Dependencies, setup instructions
- **[Configuration](./configuration)** - Settings, MQTT setup, environment variables
- **[API Reference](./api)** - Complete endpoint documentation
- **[Architecture](./architecture)** - System design and component overview
- **[Development](./development)** - Contribution guidelines and development setup

## Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/settings` | GET | Settings dashboard (authenticated) |
| `/stream` | GET | MJPEG stream (authenticated) |
| `/snapshot` | GET | Single JPEG frame (authenticated) |
| `/health` | GET | Health and system stats |
| `/motion_alerts` | GET | Motion detection alerts |
| `/api/status` | GET | Full runtime status (authenticated) |
| `/api/settings` | GET/POST | Read/update settings (authenticated) |
| `/api/display` | POST | Display control (authenticated) |
| `/api/logs` | GET | Recent logs (authenticated) |
| `/ws` | WS | WebSocket for live updates (authenticated) |

## Support & Contributing

For bug reports, feature requests, or contributions, please refer to the main repository. All code contributions should follow the guidelines in the [Development](./development) documentation.

## License

See the main repository for license information.
