# Development Guide

## Contributing

Thank you for your interest in contributing to WakeOnPi! This guide will help you get started with development.

## Prerequisites

- Python 3.14
- Git
- Raspberry Pi 4/5 or Linux machine (for testing with camera)
- Docker (optional, for isolated testing)

## Setting Up Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/WakeOnPi.git
cd WakeOnPi
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### 4. Configure Environment

Create `.env.development`:

```env
FLASK_DEBUG=true
FLASK_ENV=development
AUTH_USERNAME=dev
AUTH_PASSWORD=dev
LOG_LEVEL=DEBUG
MOTION_ENABLED=false
MQTT_ENABLED=false
```

### 5. Run Development Server

```bash
python3 run.py
```

Visit `http://localhost:5000/settings`

## Project Structure

```
WakeOnPi/
├── docs/                    # Documentation (this folder)
├── wakeonpi/
│   ├── __init__.py         # Package initialization
│   ├── app.py              # Flask application
│   ├── auth.py             # Authentication
│   ├── browser.py          # Web UI
│   ├── camera.py           # Camera interface
│   ├── config.py           # Configuration
│   ├── display.py          # Display control
│   ├── logging_config.py   # Logging setup
│   ├── motion.py           # Motion detection
│   ├── mqtt.py             # MQTT integration
│   ├── overlay.py          # Stream overlay
│   ├── recorder.py         # Recording service
│   ├── state.py            # State management
│   ├── system.py           # System info
│   └── templates/          # HTML templates
├── tests/                  # Test suite
├── run.py                  # Entry point
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── pyproject.toml          # Project metadata
└── readme.md              # Main readme
```

## Code Style & Standards

### Python Style
- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use type hints where practical

### Linting

```bash
# Lint code
ruff check wakeonpi tests

# All checks
ruff check wakeonpi tests
python -m pytest --cov=wakeonpi
```

### Commit Messages

Follow conventional commits:
```
type(scope): subject

type can be: feat, fix, docs, style, refactor, test, chore
scope: module or feature name
subject: clear, concise description
```

Examples:
```
feat(motion): improve edge detection algorithm
fix(display): handle missing sysfs path gracefully
docs(api): add WebSocket examples
test(recorder): add video format validation tests
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=wakeonpi

# Run specific test file
pytest tests/test_motion.py

# Run with verbose output
pytest -v
```

### Writing Tests

Tests go in `tests/` directory with `test_` prefix:

```python
import unittest
from wakeonpi.motion import MotionDetector

class TestMotionDetector(unittest.TestCase):
    def setUp(self):
        self.detector = MotionDetector(threshold=5.0)

    def test_initialization(self):
        self.assertEqual(self.detector.threshold, 5.0)

    def test_motion_detection(self):
        # Create test frame
        result = self.detector.detect(test_frame)
        self.assertTrue(result)
```

### Test Coverage

Maintain >80% code coverage:

```bash
pytest --cov=wakeonpi --cov-report=html
open htmlcov/index.html
```

## Creating New Features

### 1. Create a Feature Branch

```bash
git checkout -b feat/my-feature
```

### 2. Implement Feature

Follow existing code patterns and architecture.

### 3. Add Tests

Write tests for new functionality.

### 4. Update Documentation

- Update [Architecture](./architecture.md) if adding new modules
- Update [API Reference](./api.md) if adding endpoints
- Update [Configuration](./configuration.md) if adding settings

### 5. Create Pull Request

- Clear description of changes
- Reference related issues
- Ensure all tests pass
- Maintain code coverage

## Debugging

### Using Python Debugger

```python
import pdb; pdb.set_trace()
```

Or with VS Code:

```python
import debugpy
debugpy.listen(("0.0.0.0", 5678))
debugpy.wait_for_client()
```

### Logging

Use the logging module:

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Motion Detection Development

Test without camera:

```python
from wakeonpi.motion import MotionDetector
import numpy as np

detector = MotionDetector()
test_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
motion_detected = detector.detect(test_frame)
```

### MQTT Testing

Use MQTT Explorer or mosquitto_pub/sub:

```bash
# Subscribe to all topics
mosquitto_sub -h localhost -t "wakeonpi/#" -v

# Publish test message
mosquitto_pub -h localhost -t "wakeonpi/command/display/on" -m ""
```

## Performance Profiling

### CPU Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
detector.detect(frame)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### Memory Profiling

```bash
pip install memory-profiler
python -m memory_profiler run.py
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit: `chore: bump version to X.Y.Z`
4. Create git tag: `git tag vX.Y.Z`
5. Push tag: `git push --tags`
6. Create GitHub Release with changelog

## Continuous Integration

GitHub Actions runs on every push:

- ✅ Tests pass
- ✅ Code coverage maintained
- ✅ Ruff linting passes

## Common Issues

### Camera not detected in tests
- Mock picamera in tests
- Use `unittest.mock` for hardware interfaces

### Motion detection too sensitive
- Increase `MOTION_THRESHOLD` in config
- Adjust `MOTION_MIN_AREA` for smaller objects

### MQTT connection failures
- Verify broker is running
- Check network connectivity
- Validate credentials in `.env`

### Display control errors
- Verify sysfs path exists
- Check user permissions
- Review system logs

## Getting Help

- Check existing [GitHub Issues](https://github.com/yourusername/WakeOnPi/issues)
- Review [Architecture Documentation](./architecture.md)
- Check [Configuration Guide](./configuration.md)
- Ask in project discussions

## Resources

- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [picamera Documentation](https://picamera.readthedocs.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [MQTT Protocol](https://mqtt.org/)
- [Home Assistant MQTT](https://www.home-assistant.io/integrations/mqtt/)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
