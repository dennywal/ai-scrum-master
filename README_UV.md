# AI Scrum Master - UV Setup Guide

## Python 3.13 with UV Package Manager

This project has been upgraded to use Python 3.13 and UV as the package manager for faster, more reliable dependency management.

## Prerequisites

- UV package manager installed (see below)
- Python 3.13+ 

## Installation

### 1. Install UV (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Add UV to your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Set up the project

```bash
# Clone the repository
git clone https://github.com/ai-scrum-master/ai-scrum-master.git
cd ai-scrum-master

# Install Python 3.13 using UV
uv python install 3.13

# Create virtual environment with Python 3.13
uv venv --python 3.13

# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows

# Install all dependencies (including dev dependencies)
uv sync --all-groups
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_task_extractor.py -v
```

### Code Quality

```bash
# Format code with Black
uv run black src tests

# Lint with Ruff
uv run ruff check src tests

# Type check with MyPy
uv run mypy src
```

### Adding Dependencies

```bash
# Add a production dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Update all dependencies
uv sync --all-groups
```

## Key Improvements with UV and Python 3.13

1. **Faster Dependency Resolution**: UV resolves and installs dependencies significantly faster than pip
2. **Built-in Virtual Environment Management**: UV handles virtual environments natively
3. **Python 3.13 Features**: 
   - Better performance (10-15% faster than Python 3.12)
   - Improved error messages
   - Enhanced type hints support
   - UTC-aware datetime by default

## Migration from pip/requirements.txt

The project has been migrated from `requirements.txt` to `pyproject.toml` with UV support:

- All dependencies are now defined in `pyproject.toml`
- Development dependencies are in the `[dependency-groups]` section
- Python version is specified in `.python-version`

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```
OPENAI_API_KEY=your_openai_key
GITHUB_TOKEN=your_github_token
```

## Troubleshooting

If you encounter issues:

1. **UV not found**: Make sure UV is in your PATH
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. **Python 3.13 not available**: Install it with UV
   ```bash
   uv python install 3.13
   ```

3. **Dependencies not installing**: Clear cache and retry
   ```bash
   uv cache clean
   uv sync --all-groups
   ```

## VS Code Integration

For VS Code users, select the Python interpreter from the UV virtual environment:
1. Open Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
2. Select "Python: Select Interpreter"
3. Choose the interpreter from `.venv/bin/python`

## CI/CD

For GitHub Actions or other CI systems, use the UV action:

```yaml
- name: Install UV
  uses: astral-sh/setup-uv@v3
  
- name: Set up Python
  run: uv python install 3.13

- name: Install dependencies
  run: uv sync --all-groups

- name: Run tests
  run: uv run pytest
```