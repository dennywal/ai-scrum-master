# Task Creation Architecture Documentation

## Overview
This document captures the architecture and implementation details for the task creation and TDD/PRD to task conversion components found in the avanti-agent-base repository.

## Core Components

### 1. TDD/PRD Issue Generation Agent
**Location**: Referenced in `/tests/agents/test_tdd_prd_issue_generation_agent.py`

The TDD/PRD Issue Generation Agent is designed to parse Test-Driven Development (TDD) and Product Requirements Document (PRD) files and automatically generate GitHub issues from them.

#### Key Classes and Components:

##### DocumentParser
- **Purpose**: Parses TDD and PRD documents to extract structured sections
- **Key Methods**:
  - `parse_tdd_document(content)`: Extracts TDD sections (overview, test_cases, implementation_requirements)
  - `parse_prd_document(content)`: Extracts PRD sections (executive_summary, features, technical_requirements, dependencies)
- **Error Handling**: Throws `DocumentParsingError` for invalid or empty documents

##### TaskExtractor  
- **Purpose**: Extracts actionable tasks from parsed document sections
- **Key Methods**:
  - `extract_tasks_from_tdd(sections)`: Converts TDD sections into ExtractedTask objects
  - `extract_tasks_from_prd(sections)`: Converts PRD sections into ExtractedTask objects
  - `extract_acceptance_criteria(task_description)`: Parses task descriptions for acceptance criteria
- **Output**: Returns list of `ExtractedTask` objects

##### PriorityAnalyzer
- **Purpose**: Analyzes and assigns priorities to tasks based on keywords and dependencies
- **Key Methods**:
  - `analyze_priority(task)`: Analyzes single task priority based on keywords
  - `analyze_priorities_batch(tasks)`: Batch priority analysis considering dependencies
- **Logic**: Tasks with many dependencies get higher priority, security/critical keywords trigger high priority

##### DependencyResolver
- **Purpose**: Resolves task dependencies and creates a valid Directed Acyclic Graph (DAG)
- **Key Methods**:
  - `resolve_dependencies(tasks)`: Orders tasks based on dependencies
  - Detects circular dependencies and raises `ValidationError`
- **Output**: Returns topologically sorted task list

##### IssueMapper
- **Purpose**: Maps ExtractedTask objects to GitHub issue templates
- **Key Methods**:
  - `map_task_to_issue(task)`: Converts task to GitHubIssueTemplate
- **Features**:
  - Formats issue body in Markdown
  - Adds type prefix to title (e.g., "[Feature]", "[Bug]")
  - Creates checkbox lists for acceptance criteria
  - Maps priority to labels

##### BatchIssueCreator
- **Purpose**: Creates multiple GitHub issues in batch with error handling
- **Key Methods**:
  - `create_issues_batch(repo_owner, repo_name, templates)`: Creates multiple issues
- **Features**:
  - Partial failure handling
  - Success rate tracking
  - Rate limiting support (planned)

## Data Models

### ExtractedTask
```python
{
    title: str
    description: str
    task_type: str  # "feature", "test", "bug", "documentation"
    priority: str  # "high", "medium", "low"
    dependencies: List[str]
    acceptance_criteria: List[str]
    labels: List[str]
    milestone: Optional[str]
    estimated_effort: Optional[str]  # "small", "medium", "large"
}
```

### GitHubIssueTemplate
```python
{
    title: str
    body: str  # Markdown formatted
    labels: List[str]
    milestone: Optional[str]
}
```

### BatchIssueCreationOutput
```python
{
    created_issues: List[GitHubIssueOutput]
    failed_issues: List[Dict]
    total_extracted_tasks: int
    success_rate: float
}
```

## Workflow

1. **Document Input**: TDD/PRD content provided via DocumentInput
2. **Parsing**: DocumentParser extracts structured sections
3. **Task Extraction**: TaskExtractor creates ExtractedTask objects
4. **Priority Analysis**: PriorityAnalyzer assigns/adjusts priorities
5. **Dependency Resolution**: DependencyResolver orders tasks
6. **Issue Mapping**: IssueMapper creates GitHub templates
7. **Batch Creation**: BatchIssueCreator creates issues via GitHub API

## Integration Points

### Configuration
- Uses ConfigManager for API keys (OpenAI, GitHub)
- Default labels and settings stored in config
- Model configuration (GPT-4 for enhanced parsing)

### External APIs
- **GitHub API**: Via PyGithub library for issue creation
- **OpenAI API**: For NLP-enhanced task extraction (optional)

### Error Handling
- Custom exceptions: ValidationError, DocumentParsingError, TaskExtractionError, GitHubBatchCreationError
- Graceful partial failure handling in batch operations
- Rate limiting and retry logic

## Testing Strategy

### Unit Tests
- Mock-based testing for each component
- Test document parsing edge cases
- Validate dependency resolution
- Test priority analysis logic

### Integration Tests
- End-to-end flow testing
- Real API interaction tests (test repository)
- Performance testing for large documents (50+ tasks)

### Test Coverage Areas
- Document parsing accuracy
- Task extraction completeness
- Dependency cycle detection
- GitHub API error handling
- Markdown formatting validation