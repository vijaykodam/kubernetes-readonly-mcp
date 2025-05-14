# Contributing to Kubernetes Read-Only MCP Server

Thank you for your interest in contributing to the Kubernetes Read-Only MCP Server! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with the following information:

- A clear, descriptive title
- A detailed description of the issue
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Any relevant logs or error messages
- Your environment (OS, Python version, Kubernetes version, etc.)

### Suggesting Features

If you have an idea for a new feature, please create an issue on GitHub with the following information:

- A clear, descriptive title
- A detailed description of the feature
- Why this feature would be useful
- Any potential implementation details

### Pull Requests

1. Fork the repository
2. Create a new branch for your changes
3. Make your changes
4. Add or update tests as necessary
5. Ensure all tests pass
6. Update documentation as necessary
7. Submit a pull request

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/vijaykodam/kubernetes-readonly-mcp.git
   cd kubernetes-readonly-mcp
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest
   ```

4. Check code style:
   ```bash
   black src tests
   isort src tests
   flake8 src tests
   ```

## Code Style

This project follows the Black code style. Please ensure your code is formatted with Black before submitting a pull request.

## Testing

Please add tests for any new functionality. We use pytest for testing.

## Documentation

Please update the documentation when adding or modifying functionality.

## License

By contributing to this project, you agree that your contributions will be licensed under the project's Apache 2.0 license.
