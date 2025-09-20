# Pydantic Structured Output Updates for OpenAI Responses API

## Overview
Updated the codebase to support OpenAI's new Responses API with Pydantic-based structured outputs, making it more straightforward to handle outputs using Pydantic models instead of JSON schemas.

## Changes Made

### 1. Enhanced LLM Client (`src/integrations/llm_client.py`)
- Added `generate_pydantic_output()` method that works with Pydantic models directly
- Support for OpenAI Responses API's `parse()` method with GPT-5 models
- Automatic fallback to JSON schema-based structured output for GPT-4 models
- Backward compatibility maintained with existing `generate_structured_output()` method

### 2. New Pydantic Models for Structured Outputs

#### Issue Generation (`src/models/issues.py`)
- Added `IssueGenerationOutput` model with fields:
  - `title`: Concise issue title
  - `body`: Detailed description in Markdown
  - `acceptance_criteria`: List of testable criteria
  - `priority`: Issue priority level
  - `issue_type`: Type of issue
  - `labels`: Relevant labels
  - `estimated_hours`: Effort estimation
  - `components`: Affected components
  - `dependencies`: Blocking issues
  - `technical_approach`: Implementation suggestions
- Includes `to_generated_content()` method for backward compatibility

#### Task Extraction (`src/models/tasks.py`)
- Added `TaskExtractionItem` model for individual tasks
- Added `TaskExtractionOutput` model for batch extraction:
  - `tasks`: List of extracted tasks
  - `summary`: Optional extraction summary
  - `total_estimated_effort`: Total hours estimate
- Includes conversion methods to existing `ExtractedTask` and `TaskBatch` models

### 3. Updated Issue Generation Agent (`src/agents/issue_generation_agent.py`)
- Enhanced to try Pydantic-based generation first with automatic fallback
- Added `_build_pydantic_generation_prompt()` for optimized prompting
- Maintains backward compatibility with text-based generation

### 4. Enhanced Prompt Builder (`src/integrations/llm_prompt_builder.py`)
- Added `build_pydantic_prompt()` for Pydantic model prompting
- Added `build_task_extraction_pydantic_prompt()` for structured task extraction
- Added `get_pydantic_system_prompt()` for model-aware system prompts

## Usage Example

### Using the Responses API with Pydantic (GPT-5)
```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class IssueGenerationOutput(BaseModel):
    title: str
    body: str
    acceptance_criteria: list[str]
    priority: str
    issue_type: str
    labels: list[str]
    estimated_hours: float
    components: list[str]
    dependencies: list[str]

response = client.responses.parse(
    model="gpt-5",
    input=[
        {
            "role": "system",
            "content": "You are an expert project manager.",
        },
        {"role": "user", "content": "Create an issue for implementing user authentication"},
    ],
    text_format=IssueGenerationOutput,
)

issue = response.output_parsed  # Returns IssueGenerationOutput instance
```

### Using the Updated LLM Client
```python
from src.integrations.llm_client import LLMClient, LLMProvider
from src.models.issues import IssueGenerationOutput

client = LLMClient(
    provider=LLMProvider.OPENAI,
    api_key="your_api_key",
    model="gpt-5"  # or "gpt-4o-mini" for fallback
)

# Generate with Pydantic model
result = await client.generate_pydantic_output(
    prompt="Create a comprehensive GitHub issue for implementing a caching system",
    response_model=IssueGenerationOutput,
    system_prompt="You are an expert software architect.",
    temperature=0.7,
    max_tokens=2000
)

# Result is a fully typed Pydantic model instance
print(f"Title: {result.title}")
print(f"Priority: {result.priority}")
print(f"Acceptance Criteria: {result.acceptance_criteria}")
```

## Benefits

1. **Type Safety**: Pydantic models provide full type hints and validation
2. **Cleaner Code**: No more manual JSON parsing and validation
3. **Better IDE Support**: Auto-completion and type checking for all fields
4. **Automatic Validation**: Pydantic validates the response structure automatically
5. **Easier Testing**: Pydantic models are easier to mock and test
6. **Backward Compatibility**: All existing code continues to work

## Migration Path

Existing code using JSON schema continues to work. To migrate:

1. Define a Pydantic model for your output structure
2. Use `generate_pydantic_output()` instead of `generate_structured_output()`
3. Access fields directly on the returned model instance

## Testing

Created `examples/test_pydantic_api.py` to demonstrate:
- Issue generation with Pydantic models
- Task extraction with Pydantic models
- Conversion to backward-compatible formats

## Notes

- The OpenAI Responses API with `parse()` method is available for GPT-5 models
- GPT-4 models fall back to JSON schema-based structured output
- All models maintain full backward compatibility with existing code
- The implementation handles both sync and async contexts appropriately