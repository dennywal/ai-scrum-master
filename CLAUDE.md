# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Scrum Master is an intelligent task creation and management system that converts TDD (Technical Design Documents) and PRD (Product Requirements Documents) into actionable GitHub issues using LLM technology. The system follows a modular, pipeline-based architecture.

## Core Architecture

The system follows a pipeline pattern with these core components:

1. **DocumentParser**: Extracts structured sections from TDD/PRD documents
2. **TaskExtractor**: Converts document sections into task objects with acceptance criteria
3. **PriorityAnalyzer**: Assigns priorities based on keywords and dependencies
4. **DependencyResolver**: Creates and validates task dependency graphs
5. **IssueMapper**: Formats tasks as GitHub issue templates
6. **GitHubIssueCreator**: Creates issues via GitHub API with retry logic

Flow: `Document Input → Parser → Task Extractor → Priority Analyzer → Dependency Resolver → Issue Mapper → GitHub Creator → Output`

All agents inherit from `src/core/base_agent.py` which provides workflow management and error handling.

## Latest Model Updates (2025)

### OpenAI Models
- **GPT-5** (default): Most capable model with 256k context
- **GPT-5-mini**: Balanced performance and cost
- **GPT-5-nano**: Lightweight, fast responses
- **Responses API**: New API replacing Chat Completions for GPT-5

### Anthropic Models  
- **Claude Opus 4.1**: Most powerful, best for complex tasks
- **Claude Sonnet 4**: 1M token context, balanced performance

## Essential Commands

### Development Setup
```bash
# Install dependencies (Python 3.13+ required)
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Setup environment variables
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and GITHUB_TOKEN
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_task_extractor.py

# Run single test
pytest tests/test_task_extractor.py::TestTaskExtractor::test_extract_acceptance_criteria_from_description -v

# Run tests with coverage report
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code with Black
black src/ tests/

# Run linter
ruff check src/ tests/

# Fix linting issues
ruff check --fix src/ tests/

# Type checking
mypy src/
```

## Key Integration Points

### LLM Integration
- Primary: `src/integrations/llm_client.py` - Handles OpenAI/Anthropic API calls
- Prompts: `src/integrations/llm_prompt_builder.py` - Constructs prompts for task extraction
- Fallback mechanisms for when LLM is unavailable

### GitHub Integration
- Client: `src/integrations/github_client.py` - Direct GitHub API interaction
- Creator: `src/integrations/github_issue_creator.py` - Batch issue creation with retry

### Configuration
- Settings: `src/config/settings.py` - Pydantic settings management
- Environment variables loaded from `.env` file
- Required: `OPENAI_API_KEY`, `GITHUB_TOKEN`

## Testing Approach

Tests use pytest with fixtures and mocks. Key testing patterns:
- Mock external services (GitHub API, OpenAI API)
- Use `pytest.fixture` for reusable test data
- Test both success and failure cases
- Verify retry logic and fallback mechanisms

## Project Structure

```
src/
├── agents/          # Core processing agents
├── config/          # Settings and configuration
├── core/            # Base classes and exceptions
├── integrations/    # External service integrations
└── models/          # Pydantic data models

tests/               # Test files mirroring src structure
examples/            # Example usage scripts
```

## Common Development Tasks

### Adding a New Agent
1. Create new agent class inheriting from `BaseAgent` in `src/core/base_agent.py`
2. Implement required abstract methods
3. Add corresponding test file in `tests/`
4. Update the pipeline if needed

### Modifying LLM Prompts
Edit prompt templates in `src/integrations/llm_prompt_builder.py`

### Adding New Issue Fields
Update the `GitHubIssue` model in `src/models/issues.py`