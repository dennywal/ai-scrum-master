# Agent Base Architecture

## Core Agent Framework

### BaseAgent Class
**Location**: `/src/avanti_agent_base/app/models/base_agent.py`

The `BaseAgent` class provides the foundation for all agents in the system:

```python
class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self._workflow = Workflow()
    
    def add_step(self, step: Callable):
        """Add a processing step to the workflow"""
        self._workflow.add_step(step)
    
    def execute(self, task: Any) -> Any:
        """Execute the workflow on a given task"""
        return self._workflow.execute(task)
```

### Workflow Pattern
The `Workflow` class manages a sequential pipeline of processing steps:
- Steps are callable functions
- Each step receives the output of the previous step
- Enables modular, composable agent behavior

### Agent Registration System

#### AgentRegistry
- Central registry for agent discovery
- Agents register via decorator: `@AgentRegistry.register`
- Supports dynamic agent loading
- Enables API-based agent invocation

### Configuration Management

#### ConfigManager
**Purpose**: Centralized configuration loading for all agents

**Key Features**:
- Environment variable loading via `python-dotenv`
- Secret management with `pydantic.SecretStr`
- Structured settings classes:
  - `LLMSettings`: OpenAI API configuration
  - `GitHubSettings`: GitHub token management
  - `AgentSettings`: Default agent parameters

**Configuration Schema**:
```python
LLMSettings:
  - openai_api_key: SecretStr
  - model_name: str (default: "gpt-4.1-nano")

GitHubSettings:
  - github_token: SecretStr

AgentSettings:
  - default_labels: List[str]
```

### Data Models (Pydantic)

#### Input Models
- `BriefIssueInput`: Basic issue creation input
- `DocumentInput`: TDD/PRD document input
- `IssueResolutionInput`: Issue resolution parameters

#### Task Models
- `ExtractedTask`: Parsed task from documents
- `GitHubIssueTemplate`: Issue creation template
- `GeneratedIssueContent`: LLM-generated content

#### Output Models
- `GitHubIssueOutput`: Created issue details
- `BatchIssueCreationOutput`: Batch creation results

### Exception Hierarchy

Base exception classes for consistent error handling:
- `ValidationError`: Input validation failures
- `IssueGenerationError`: General generation failures
- `LLMConnectionError`: LLM service errors
- `GitHubAuthenticationError`: GitHub auth failures
- `ConfigurationError`: Configuration issues

### Utility Modules

#### Validation Module
- `InputValidator`: Input data validation
- `ConfigValidator`: Configuration validation
- Format checking for API keys
- Business logic validation

#### Retry Utilities
- `retry_llm_operation`: LLM API retry logic
- `retry_github_operation`: GitHub API retry logic
- Exponential backoff strategies
- Rate limit handling

### Integration Patterns

#### Step-Based Processing
Agents use the step pattern for modular processing:
```python
agent = MyAgent()
agent.add_step(validate_input)
agent.add_step(process_data)
agent.add_step(generate_output)
result = agent.execute(input_data)
```

#### Error Recovery
- Fallback content generation
- Partial success handling
- Graceful degradation
- Detailed error reporting

#### Monitoring and Logging
- Structured logging with contextual data
- Performance metrics tracking
- Error categorization
- Success rate monitoring

### API Integration

#### External Services
- **OpenAI API**: LLM content generation
- **GitHub API**: Issue creation and management
- **A2A Protocol**: Agent-to-agent communication

#### Authentication
- Environment-based secrets
- Token validation
- Rate limit awareness
- Retry with backoff

### Testing Infrastructure

#### Test Patterns
- Mock-based unit testing
- Integration testing with test APIs
- End-to-end workflow testing
- Error scenario coverage

#### Test Data Models
- Fixture generation
- Mock response builders
- Test repository setup
- Validation test cases