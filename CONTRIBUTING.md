# Contributing to AI Scrum Master

Thank you for your interest in contributing to AI Scrum Master! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, please include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- System information (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- A clear and descriptive title
- Detailed description of the proposed functionality
- Any possible alternatives you've considered
- Examples of how the feature would be used

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature-name`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Update documentation as needed
7. Commit your changes (`git commit -m 'Add some feature'`)
8. Push to your branch (`git push origin feature/your-feature-name`)
9. Open a Pull Request

## Development Setup

1. Clone your fork:
```bash
git clone https://github.com/your-username/ai-scrum-master.git
cd ai-scrum-master
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up pre-commit hooks:
```bash
pre-commit install
```

5. Create `.env` file from example:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use meaningful variable and function names

## Testing

- Write tests for all new functionality
- Maintain or increase code coverage
- Run tests before submitting PR:
```bash
pytest
pytest --cov=src tests/
```

## Documentation

- Update README.md if adding new features
- Add docstrings to new functions and classes
- Update architecture documentation for significant changes
- Include examples for new functionality

## Commit Messages

- Use clear and meaningful commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issue numbers when applicable

Example:
```
Add task priority analysis feature (#123)

- Implement keyword-based priority detection
- Add dependency impact analysis
- Update documentation with new feature
```

## Code Review Process

1. All submissions require review
2. Reviewers will provide feedback
3. Address all feedback or discuss alternatives
4. Once approved, maintainers will merge your PR

## Community Guidelines

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Assume good intentions

## Questions?

Feel free to open an issue for any questions about contributing!