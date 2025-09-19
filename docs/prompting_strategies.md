# Prompting Strategies Documentation

## Overview
This document captures the prompting strategies used throughout the avanti-agent-base repository for task creation and issue generation.

## Issue Generation Prompting

### Title Generation Strategy
**Location**: `IssueContentGenerator` in `issue_generation_agent.py`

```python
prompt_for_title = f"Given the repository '{repo_name}' and the following brief issue description, generate a concise and descriptive GitHub issue title (max 10 words). Description: {brief_description}"
```

**Key Elements**:
- Context: Repository name provided
- Constraint: Maximum 10 words
- Focus: Concise and descriptive
- Input: Brief description

### Body Generation Strategy
**Location**: `IssueContentGenerator` in `issue_generation_agent.py`

```python
prompt_for_body = (
    f"Given the repository '{repo_name}' and the following brief issue description, generate a comprehensive GitHub issue body. "
    f"The body must be in Markdown format and include the following sections:\n"
    f"- **Problem Statement / Goal:** (Elaborate on the brief description)\n"
    f"- **Acceptance Criteria / Requirements for Implementation:** (List specific, testable criteria)\n"
    f"- **Suggested Approach (Optional):** (High-level steps or considerations)\n"
    f"- **Context / Background:** (Expand on any context from the brief description)\n\n"
    f"Brief Description: {brief_description}"
)
```

**Key Elements**:
- Structured output: Predefined sections
- Format requirement: Markdown
- Section purposes clearly defined
- Mix of required and optional sections

## Plan Development Prompting

### Development Plan Generation
**Location**: `PlanGenerator` in `plan_development_agent.py`

```python
system_prompt = """You are an AI assistant that generates development plans for GitHub issues.
Given an issue title and body, create a basic Markdown-formatted plan outlining potential implementation steps.
Focus on clarity and actionable points.
"""

user_prompt = f"Issue Title: {issue_title}\n\nIssue Body:\n{issue_body}\n\nBased on the above, please generate a concise development plan in Markdown format, including key implementation steps."
```

**Key Elements**:
- Role definition: Development plan specialist
- Output format: Markdown
- Focus: Clarity and actionability
- Structure: Implementation steps

## Prompting Best Practices Observed

### 1. Context Provision
- Always include relevant context (repo name, project type)
- Provide clear role definitions in system prompts
- Reference specific domains or technologies when relevant

### 2. Output Structure
- Request specific format (Markdown)
- Define required sections explicitly
- Use bullet points or numbered lists for clarity
- Include optional sections for flexibility

### 3. Constraints and Guidelines
- Set length limits (e.g., "max 10 words")
- Temperature settings (0.5 for balanced creativity/consistency)
- Max tokens to control response length
- Clear acceptance criteria format

### 4. Error Handling in Prompts
- Validation of generated content
- Detection of failure indicators ("sorry", "cannot")
- Fallback content generation
- Partial success handling

## Configuration for LLM Usage

### Model Selection
**Default Models**:
- `gpt-4.1-nano`: Primary model for issue generation
- `gpt-4.1-mini`: Used for plan development
- `gpt-4`: Available for enhanced parsing (TDD/PRD)

### API Configuration
```python
LLMSettings:
  - model_name: Configurable per agent
  - temperature: 0.5 (balanced)
  - max_tokens: 1000-2000 (task-dependent)
```

### Response Processing
- Strip whitespace from responses
- Validate response structure
- Check for minimum content length
- Parse structured output when expected

## TDD/PRD Task Extraction Prompting (Inferred)

Based on the test structure, the TDD/PRD parsing likely uses prompts that:

### For TDD Documents
- Extract test cases as individual tasks
- Identify implementation requirements
- Map test descriptions to acceptance criteria
- Categorize tasks (feature, test, bug)

### For PRD Documents
- Parse features into implementable tasks
- Extract dependencies between features
- Identify technical requirements
- Map business requirements to development tasks

## Prompt Engineering Patterns

### 1. Chain-of-Thought
- Not explicitly used but could enhance task extraction
- Would help in dependency analysis

### 2. Few-Shot Examples
- Not currently implemented
- Could improve consistency in task extraction

### 3. Role-Based Prompting
- Used in plan development ("You are an AI assistant")
- Could be enhanced with more specific roles

### 4. Structured Output Prompting
- Heavy use of structured formats
- Markdown sections predefined
- Clear delineation of required fields

## Recommendations for ai-scrum-master

### Enhanced Prompting Strategies
1. **Task Decomposition**: Add prompts for breaking down large tasks
2. **Priority Analysis**: Prompts to analyze and assign task priorities
3. **Effort Estimation**: Prompts to estimate task complexity
4. **Dependency Mapping**: Prompts to identify task relationships

### Prompt Templates
```python
# Task Extraction Template
task_extraction_prompt = """
Given a {document_type} document, extract actionable tasks.
For each task, identify:
1. Title (concise, action-oriented)
2. Description (detailed requirements)
3. Acceptance Criteria (testable conditions)
4. Priority (high/medium/low based on keywords)
5. Dependencies (other tasks that must complete first)
6. Estimated Effort (small/medium/large)
"""

# Priority Analysis Template
priority_prompt = """
Analyze the following task and assign priority:
- HIGH: Security, critical bugs, blocking issues
- MEDIUM: Core features, performance improvements
- LOW: Documentation, minor enhancements
Consider dependencies and business impact.
"""
```

### Validation Prompts
```python
validation_prompt = """
Review the extracted tasks and ensure:
1. No duplicate tasks
2. Clear acceptance criteria
3. Realistic scope
4. Proper dependency chain
5. Consistent naming conventions
"""
```

## Error Recovery Strategies

### Fallback Prompting
When primary prompts fail:
1. Use simpler, more direct prompts
2. Request basic structure only
3. Fill in defaults for missing sections
4. Add error indicators to output

### Retry with Context
1. Include error message in retry prompt
2. Request specific missing information
3. Use alternative phrasing
4. Reduce complexity requirements