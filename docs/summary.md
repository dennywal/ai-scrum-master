# AI Scrum Master - Architecture Summary

## Executive Summary

This document provides a comprehensive architecture overview for implementing the **ai-scrum-master** repository, a focused implementation of task creation and TDD/PRD to task conversion capabilities extracted from the avanti-agent-base project.

## Core Architecture Components

### 1. Task Creation System

#### TDD/PRD Document Processing Pipeline
The system follows a multi-stage pipeline for converting documents into actionable tasks:

1. **Document Parsing** (`DocumentParser`)
   - Extracts structured sections from TDD/PRD documents
   - Identifies test cases, features, requirements, and dependencies
   - Validates document structure and content

2. **Task Extraction** (`TaskExtractor`)
   - Converts parsed sections into `ExtractedTask` objects
   - Extracts acceptance criteria from descriptions
   - Maps document elements to task properties

3. **Priority Analysis** (`PriorityAnalyzer`)
   - Analyzes tasks for priority indicators
   - Considers dependencies in priority assignment
   - Uses keyword-based and dependency-based scoring

4. **Dependency Resolution** (`DependencyResolver`)
   - Creates Directed Acyclic Graph (DAG) of tasks
   - Detects circular dependencies
   - Provides topologically sorted task order

5. **Issue Mapping** (`IssueMapper`)
   - Converts tasks to GitHub issue templates
   - Formats content in Markdown
   - Adds appropriate labels and metadata

6. **Batch Creation** (`BatchIssueCreator`)
   - Creates multiple GitHub issues efficiently
   - Handles partial failures gracefully
   - Tracks success rates and errors

### 2. Issue Generation System

#### Single Issue Creation Pipeline
For individual issue creation from brief descriptions:

1. **Content Generation** (`IssueContentGenerator`)
   - Uses LLM to generate titles and bodies
   - Separate optimized prompts for each component
   - Structured Markdown output with predefined sections

2. **GitHub Integration** (`GitHubIssueCreator`)
   - Creates issues via GitHub API
   - Comprehensive error handling
   - Rate limiting and retry logic

3. **Orchestration** (`IssueGenerationAgent`)
   - Manages end-to-end workflow
   - Fallback content generation
   - Configuration management

## Technical Architecture

### Foundation Layer

#### Base Agent Framework
```python
BaseAgent
├── Workflow Management
│   ├── Step-based processing
│   ├── Sequential execution
│   └── Error propagation
├── Configuration
│   ├── Environment variables
│   ├── Secret management
│   └── Default settings
└── Execution
    ├── Input validation
    ├── Step orchestration
    └── Output generation
```

#### Data Models (Pydantic)
- **Input Models**: `BriefIssueInput`, `DocumentInput`
- **Task Models**: `ExtractedTask`, `GitHubIssueTemplate`
- **Output Models**: `GitHubIssueOutput`, `BatchIssueCreationOutput`

### Integration Layer

#### External Services
1. **OpenAI API**
   - Content generation
   - Task extraction enhancement
   - Configurable models (GPT-4, GPT-4.1-nano)

2. **GitHub API**
   - Issue creation
   - Repository access
   - Authentication via tokens

#### Configuration Management
- Environment-based configuration
- Secret value protection
- Validation of API keys
- Default value management

### Application Layer

#### Core Agents
1. **TDDPRDIssueGenerationAgent**
   - Batch task creation from documents
   - Multi-stage processing pipeline
   - Comprehensive error handling

2. **IssueGenerationAgent**
   - Single issue creation
   - LLM-powered content generation
   - Fallback mechanisms

3. **PlanDevelopmentAgent**
   - Development plan generation
   - Issue analysis
   - Version control integration

## Implementation Roadmap for ai-scrum-master

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 Project Setup
```
ai-scrum-master/
├── src/
│   ├── core/
│   │   ├── base_agent.py
│   │   ├── workflow.py
│   │   └── exceptions.py
│   ├── models/
│   │   ├── tasks.py
│   │   ├── issues.py
│   │   └── documents.py
│   ├── config/
│   │   ├── settings.py
│   │   └── validators.py
│   └── utils/
│       ├── retry.py
│       └── logging.py
├── tests/
├── docs/
└── requirements.txt
```

#### 1.2 Base Components
- Implement `BaseAgent` and `Workflow` classes
- Create Pydantic models for data structures
- Set up configuration management
- Implement exception hierarchy

### Phase 2: Document Processing (Week 2-3)

#### 2.1 Parser Implementation
```python
class DocumentParser:
    def parse_tdd_document(content: str) -> Dict
    def parse_prd_document(content: str) -> Dict
    def validate_structure(sections: Dict) -> bool
```

#### 2.2 Task Extraction
```python
class TaskExtractor:
    def extract_tasks_from_tdd(sections: Dict) -> List[ExtractedTask]
    def extract_tasks_from_prd(sections: Dict) -> List[ExtractedTask]
    def extract_acceptance_criteria(description: str) -> List[str]
```

### Phase 3: Task Analysis (Week 3-4)

#### 3.1 Priority and Dependencies
```python
class PriorityAnalyzer:
    def analyze_priority(task: ExtractedTask) -> ExtractedTask
    def analyze_priorities_batch(tasks: List[ExtractedTask]) -> List[ExtractedTask]

class DependencyResolver:
    def resolve_dependencies(tasks: List[ExtractedTask]) -> List[ExtractedTask]
    def detect_cycles(tasks: List[ExtractedTask]) -> bool
```

#### 3.2 Issue Mapping
```python
class IssueMapper:
    def map_task_to_issue(task: ExtractedTask) -> GitHubIssueTemplate
    def format_markdown_body(task: ExtractedTask) -> str
```

### Phase 4: GitHub Integration (Week 4-5)

#### 4.1 API Integration
```python
class GitHubIssueCreator:
    def create_issue(repo_owner, repo_name, template) -> GitHubIssueOutput
    def create_issues_batch(templates) -> BatchIssueCreationOutput
```

#### 4.2 Error Handling
- Implement retry mechanisms
- Add rate limiting protection
- Create fallback strategies

### Phase 5: LLM Integration (Week 5-6)

#### 5.1 Content Generation
```python
class IssueContentGenerator:
    def generate_title(description: str) -> str
    def generate_body(description: str) -> str
    def enhance_task_extraction(content: str) -> List[ExtractedTask]
```

#### 5.2 Prompting Strategies
- Implement structured prompts
- Add validation prompts
- Create fallback prompts

## Key Design Decisions

### 1. Modular Architecture
- **Rationale**: Enables independent testing and maintenance
- **Implementation**: Separate classes for each responsibility
- **Benefits**: Easy to extend and modify individual components

### 2. Step-Based Processing
- **Rationale**: Clear workflow visualization and debugging
- **Implementation**: Workflow pattern with sequential steps
- **Benefits**: Predictable execution and error handling

### 3. Comprehensive Error Handling
- **Rationale**: Robust operation in production environments
- **Implementation**: Custom exception hierarchy with detailed context
- **Benefits**: Graceful degradation and clear error reporting

### 4. LLM Abstraction
- **Rationale**: Flexibility in model selection and provider switching
- **Implementation**: Configurable model names and providers
- **Benefits**: Easy updates and experimentation

### 5. Batch Processing Support
- **Rationale**: Efficient handling of multiple tasks
- **Implementation**: Batch creation with partial failure handling
- **Benefits**: Better performance and user experience

## Configuration Requirements

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_key
GITHUB_TOKEN=your_github_token

# Optional
LLM_MODEL_NAME=gpt-4
AGENT_DEFAULT_LABELS=ai-generated,scrum
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=1
```

### Dependencies
```python
# Core
pydantic>=2.0.0
python-dotenv>=1.0.0

# LLM
openai>=1.0.0

# GitHub
PyGithub>=2.0.0

# Testing
pytest>=7.0.0
pytest-mock>=3.0.0

# Utilities
tenacity>=8.0.0  # For retry logic
structlog>=23.0.0  # For structured logging
```

## Testing Strategy

### Unit Tests
- Mock external dependencies (GitHub, OpenAI)
- Test each component in isolation
- Validate error handling paths
- Test data model validation

### Integration Tests
- Test component interactions
- Validate workflow execution
- Test with real API endpoints (test environment)
- Verify end-to-end processing

### Test Coverage Goals
- Core logic: 90%+
- Error handling: 100%
- API interactions: Mocked for unit, real for integration
- Edge cases: Comprehensive coverage

## Performance Considerations

### Optimization Points
1. **Batch Processing**: Group API calls where possible
2. **Caching**: Cache LLM responses for similar inputs
3. **Async Operations**: Use async/await for I/O operations
4. **Rate Limiting**: Implement backoff strategies
5. **Connection Pooling**: Reuse HTTP connections

### Scalability
- Horizontal scaling via multiple workers
- Queue-based task processing
- Database for task state persistence
- Webhook support for GitHub events

## Security Considerations

### API Key Management
- Environment variables only
- Never commit secrets
- Use secret management services in production
- Rotate keys regularly

### Input Validation
- Validate all user inputs
- Sanitize content before API calls
- Prevent injection attacks
- Validate webhook signatures

## Monitoring and Observability

### Logging
- Structured logging with context
- Log levels for different environments
- Performance metrics tracking
- Error aggregation

### Metrics
- Task creation success rate
- API call latency
- Error rates by type
- Processing throughput

## Future Enhancements

### Short Term (1-3 months)
1. Web UI for task management
2. Slack/Teams integration
3. Custom task templates
4. Enhanced dependency visualization

### Medium Term (3-6 months)
1. Machine learning for priority prediction
2. Automated task assignment
3. Sprint planning assistance
4. Progress tracking and reporting

### Long Term (6+ months)
1. Multi-repository support
2. Cross-team collaboration features
3. Advanced analytics and insights
4. AI-powered retrospectives

## Conclusion

The ai-scrum-master architecture provides a solid foundation for automated task creation and management. By leveraging the patterns and components from avanti-agent-base, the implementation can focus on the specific needs of scrum task management while maintaining extensibility and reliability.

The modular design allows for incremental development and easy maintenance, while the comprehensive error handling ensures robust operation in production environments. The integration of LLM capabilities provides intelligent task creation and enhancement, making the system a valuable tool for development teams.

With the outlined architecture and implementation roadmap, the ai-scrum-master repository can be developed efficiently, providing immediate value while maintaining the flexibility to evolve with user needs.