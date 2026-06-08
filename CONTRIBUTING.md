# Contributing to WakeOnPi

Thank you for your interest in contributing to WakeOnPi! We welcome contributions from the community. This document provides guidelines for contributing.

## Code of Conduct

Be respectful and constructive in all interactions. We're committed to providing a welcoming and inclusive environment.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a feature branch for your work
4. Make your changes
5. Submit a pull request

## Development Setup

See the [Development Guide](docs/development.md) for detailed setup instructions.

## Pull Request Process

1. **Create a feature branch**: `git checkout -b feat/my-feature`
2. **Make your changes**: Follow code style guidelines
3. **Add tests**: Ensure new functionality has test coverage
4. **Run tests**: `pytest` with coverage
5. **Update documentation**: If adding features or changing behavior
6. **Commit with conventional commits**: `feat(module): description`
7. **Push and create PR**: Provide clear description of changes

## Code Style

- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use type hints where practical
- Run Ruff for linting: `ruff check wakeonpi tests`

## Testing

- Write tests for new features
- Maintain test coverage above 80%
- Run: `pytest --cov=wakeonpi`
- Tests should be in `tests/` directory with `test_` prefix

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

Body (optional, explaining what and why)

Footer (optional, referencing issues)
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(motion): add adaptive threshold detection`
- `fix(display): handle missing sysfs path gracefully`
- `docs(api): add WebSocket examples`

## Reporting Issues

- Check existing issues to avoid duplicates
- Include steps to reproduce
- Provide environment details (Pi model, OS version, Python version)
- Include relevant logs or error messages

## Questions?

- Check [Documentation](docs/home.md)
- Review existing [Issues](https://github.com/yourusername/WakeOnPi/issues)
- Create a new discussion or issue

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

Thank you for contributing!
