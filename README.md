# AI Scrum Master

An intelligent task creation and management system that converts TDD/PRD documents into actionable GitHub issues using LLM technology.

## Overview

AI Scrum Master automates the process of converting Technical Design Documents (TDD) and Product Requirements Documents (PRD) into well-structured, prioritized GitHub issues. It leverages Large Language Models (LLMs) to enhance task extraction, generate comprehensive issue descriptions, and manage dependencies between tasks.

## Features

- **Document Parsing**: Extract structured information from TDD and PRD documents
- **Intelligent Task Extraction**: Convert requirements into actionable tasks with acceptance criteria
- **Priority Analysis**: Automatically assign priorities based on keywords and dependencies
- **Dependency Resolution**: Create and validate task dependency graphs
- **Batch Issue Creation**: Efficiently create multiple GitHub issues with error recovery
- **LLM Enhancement**: Use AI to generate detailed issue titles and descriptions
- **Fallback Mechanisms**: Graceful degradation when external services are unavailable

## Quick Start

### Prerequisites

- Python 3.13+
- GitHub account with personal access token
- OpenAI API key (or compatible LLM provider)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-scrum-master.git
cd ai-scrum-master

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Basic Usage

```python
from src.agents.tdd_prd_agent import TDDPRDIssueGenerationAgent
from src.models.documents import DocumentInput

# Initialize the agent
agent = TDDPRDIssueGenerationAgent()

# Create input with TDD content
input_data = DocumentInput(
    tdd_content="""
    # User Authentication TDD
    
    ## Test Cases
    1. User Registration
       - Test email validation
       - Test password strength
       - Test duplicate prevention
    
    ## Implementation Requirements
    - Use bcrypt for hashing
    - JWT for sessions
    """,
    repo_owner="your-org",
    repo_name="your-repo"
)

# Generate and create issues
result = agent.execute(input_data)
print(f"Created {len(result.created_issues)} issues")
print(f"Success rate: {result.success_rate * 100}%")
```

## Architecture

The system follows a modular, pipeline-based architecture:

```
Document Input → Parser → Task Extractor → Priority Analyzer → 
Dependency Resolver → Issue Mapper → GitHub Creator → Output
```

### Core Components

- **DocumentParser**: Extracts structured sections from documents
- **TaskExtractor**: Converts sections into task objects
- **PriorityAnalyzer**: Assigns priorities based on content analysis
- **DependencyResolver**: Manages task dependencies and ordering
- **IssueMapper**: Formats tasks as GitHub issue templates
- **BatchIssueCreator**: Creates issues via GitHub API

## Configuration

Create a `.env` file with the following variables:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_personal_access_token

# Optional
LLM_MODEL_NAME=gpt-4  # Default: gpt-4
DEFAULT_LABELS=ai-generated,scrum  # Default: ai-generated
MAX_RETRY_ATTEMPTS=3  # Default: 3
LOG_LEVEL=INFO  # Default: INFO
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Development Guide](docs/development.md)
- [Testing Guide](docs/testing.md)
- [Deployment Guide](docs/deployment.md)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_document_parser.py
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

Based on architectural patterns from the [avanti-agent-base](https://github.com/avanti-ai/avanti-agent-base) project.