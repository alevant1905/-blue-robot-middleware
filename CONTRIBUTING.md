# Contributing to Blue Robot Middleware

Thank you for your interest in contributing to Blue Robot Middleware! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Adding New Tools](#adding-new-tools)
- [Testing](#testing)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/blue-robot-middleware.git
   cd blue-robot-middleware
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/originalowner/blue-robot-middleware.git
   ```

## Development Setup

1. **Install Python 3.8 or higher**
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Install development dependencies**:
   ```bash
   pip install pytest black mypy flake8
   ```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/blue-robot-middleware/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS
   - Relevant logs or screenshots

### Suggesting Features

1. Check if the feature has been suggested in [Issues](https://github.com/yourusername/blue-robot-middleware/issues)
2. Create a new issue with:
   - Clear use case description
   - Why this feature would be useful
   - Possible implementation approach

### Submitting Changes

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** following the coding standards
3. **Test your changes** thoroughly
4. **Commit your changes** with clear messages:
   ```bash
   git commit -m "Add feature: brief description"
   ```
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create a Pull Request** on GitHub

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use **4 spaces** for indentation (no tabs)
- Maximum line length: **120 characters**
- Use **type hints** where appropriate
- Format code with **Black**:
  ```bash
  black blue/
  ```

### Code Organization

- Keep functions focused and single-purpose
- Use descriptive variable and function names
- Add docstrings to all public functions and classes
- Group related functionality into modules

### Documentation

- Add docstrings to all public functions:
  ```python
  def my_function(param1: str, param2: int) -> bool:
      """
      Brief description of what the function does.

      Args:
          param1: Description of param1
          param2: Description of param2

      Returns:
          Description of return value
      """
  ```
- Update README.md if adding major features
- Add examples to docstrings where helpful

## Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**:
   ```bash
   pytest
   ```
4. **Format code**:
   ```bash
   black blue/
   ```
5. **Check type hints**:
   ```bash
   mypy blue/
   ```
6. **Update CHANGELOG.md** with your changes
7. **Submit PR** with clear description:
   - What changes were made
   - Why these changes were needed
   - How to test the changes

### PR Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, your PR will be merged

## Adding New Tools

Blue Robot Middleware is designed to be extensible. Here's how to add a new tool:

### 1. Create Tool File

Create a new file in `blue/tools/` (e.g., `my_tool.py`):

```python
"""
My Tool - Brief description
"""
import sqlite3
import os
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import json

# Database path
MY_TOOL_DB = os.path.join("data", "my_tool.db")

@dataclass
class MyDataModel:
    """Data model for my tool"""
    id: str
    name: str
    # ... other fields

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MyToolManager:
    """Manager class for my tool functionality"""

    def __init__(self, db_path: str = MY_TOOL_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS my_table (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    # Add your methods here...

# Singleton instance
_manager: Optional[MyToolManager] = None

def get_my_tool_manager() -> MyToolManager:
    """Get or create singleton manager instance"""
    global _manager
    if _manager is None:
        _manager = MyToolManager()
    return _manager

# Command functions
def my_command_cmd(param1: str) -> str:
    """
    Command function that can be called by users.

    Args:
        param1: Description

    Returns:
        JSON string with result
    """
    manager = get_my_tool_manager()
    # ... implementation
    return json.dumps({"status": "success", "data": result})
```

### 2. Update Tool Exports

Add your tool to `blue/tools/__init__.py`:

```python
from .my_tool import (
    MyToolManager,
    get_my_tool_manager,
    my_command_cmd,
    # ... other exports
)
```

### 3. Add Intent Detection

Update `blue/tool_selector.py` to recognize commands for your tool:

```python
def _detect_my_tool_intents(self, msg_lower: str, context: Dict) -> List[ToolIntent]:
    """Detect intents related to my tool"""
    intents = []

    if any(keyword in msg_lower for keyword in ["my", "tool", "command"]):
        intents.append(ToolIntent(
            tool_name="my_tool",
            function_name="my_command_cmd",
            confidence=0.8,
            suggested_params={}
        ))

    return intents
```

Then add to `_detect_all_intents`:

```python
def _detect_all_intents(self, message: str, context: List[Dict]) -> List[ToolIntent]:
    # ... existing detectors
    intents.extend(self._detect_my_tool_intents(msg_lower, context_dict))
    return intents
```

### 4. Add Tests

Create tests in a test file:

```python
def test_my_tool():
    from blue.tools.my_tool import my_command_cmd
    result = my_command_cmd("test")
    assert "status" in result
```

### 5. Document Your Tool

Add documentation to `ENHANCEMENTS.md` describing:
- What the tool does
- How to use it
- Example commands
- API reference

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_my_tool.py

# Run with coverage
pytest --cov=blue tests/
```

### Writing Tests

- Test each command function
- Test edge cases and error handling
- Mock external dependencies (APIs, databases)
- Use fixtures for common setup

Example:

```python
import pytest
from blue.tools.my_tool import MyToolManager

@pytest.fixture
def manager():
    return MyToolManager(db_path=":memory:")

def test_my_function(manager):
    result = manager.my_function("test")
    assert result is not None
```

## Database Guidelines

- Use SQLite for persistent storage
- Create databases in `data/` directory
- Use parameterized queries to prevent SQL injection
- Always close database connections
- Add database schema documentation

## Commit Message Guidelines

Use clear, descriptive commit messages:

```
Add feature: brief description

More detailed explanation of what changed and why.
Include any breaking changes or migration notes.
```

Examples:
- `Add weather forecasting to weather tool`
- `Fix: Handle None values in contact search`
- `Docs: Update README with new features`
- `Refactor: Simplify email template rendering`

## Getting Help

- Check the [documentation](README.md)
- Search [existing issues](https://github.com/yourusername/blue-robot-middleware/issues)
- Join discussions in [GitHub Discussions](https://github.com/yourusername/blue-robot-middleware/discussions)

## License

By contributing to Blue Robot Middleware, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Blue Robot Middleware!
