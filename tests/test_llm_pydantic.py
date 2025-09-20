"""Tests for LLM Pydantic output generation functionality."""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pydantic import BaseModel, Field
from typing import List

from src.integrations.llm_client import LLMClient, LLMProvider, LLMResponseError
from src.models.issues import IssueGenerationOutput
from src.models.tasks import TaskExtractionOutput, TaskExtractionItem


# Test Pydantic model
class TestOutputModel(BaseModel):
    """Simple test model for output generation."""
    title: str = Field(..., min_length=1, max_length=100)
    items: List[str] = Field(default_factory=list)
    count: int = Field(default=0, ge=0)


class TestLLMPydanticGeneration:
    """Test Pydantic-based output generation in LLMClient."""
    
    @pytest.fixture
    def openai_key(self):
        """Test OpenAI API key."""
        return "test_openai_key_123"
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = Mock()
        mock_responses = Mock()
        mock_client.responses = mock_responses
        return mock_client
    
    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_pydantic_output_gpt5_success(self, mock_openai_class, openai_key):
        """Test successful Pydantic output generation with GPT-5 Responses API."""
        # Setup mock
        mock_client = Mock()
        mock_responses = Mock()
        mock_client.responses = mock_responses
        mock_openai_class.return_value = mock_client
        
        # Create expected output
        expected_output = IssueGenerationOutput(
            title="Implement caching system",
            body="Add Redis caching for API responses",
            priority="high",
            issue_type="feature",
            labels=["performance", "backend"],
            estimated_hours=16.0
        )
        
        # Mock the responses.parse method
        mock_response = Mock()
        mock_response.output_parsed = expected_output
        mock_responses.parse = AsyncMock(return_value=mock_response)
        
        # Create client and generate output
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=openai_key,
            model="gpt-5"
        )
        
        result = await client.generate_pydantic_output(
            prompt="Create an issue for implementing a caching system",
            response_model=IssueGenerationOutput,
            system_prompt="You are a software architect",
            temperature=0.7,
            max_tokens=2000
        )
        
        # Verify
        assert result == expected_output
        assert result.title == "Implement caching system"
        assert result.priority == "high"
        
        # Check the API was called correctly
        mock_responses.parse.assert_called_once()
        call_args = mock_responses.parse.call_args
        assert call_args.kwargs['model'] == "gpt-5"
        assert call_args.kwargs['text_format'] == IssueGenerationOutput
        assert call_args.kwargs['temperature'] == 0.7
        assert call_args.kwargs['max_tokens'] == 2000
    
    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_pydantic_output_gpt4_fallback(self, mock_openai_class, openai_key):
        """Test Pydantic output generation falls back to JSON schema for GPT-4."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # No responses attribute for GPT-4
        assert not hasattr(mock_client, 'responses')
        
        # Mock chat completions response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "title": "Fix login bug",
            "body": "Users cannot login with email",
            "priority": "critical",
            "issue_type": "bug",
            "labels": ["bug", "auth"],
            "estimated_hours": 4.0,
            "acceptance_criteria": ["Login works with email"],
            "components": ["auth"],
            "dependencies": []
        })
        mock_response.choices = [Mock(message=mock_message)]
        
        mock_completions = Mock()
        mock_completions.create = AsyncMock(return_value=mock_response)
        mock_chat = Mock()
        mock_chat.completions = mock_completions
        mock_client.chat = mock_chat
        
        # Create client and generate output
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=openai_key,
            model="gpt-4o"
        )
        
        result = await client.generate_pydantic_output(
            prompt="Create an issue for fixing login bug",
            response_model=IssueGenerationOutput
        )
        
        # Verify
        assert isinstance(result, IssueGenerationOutput)
        assert result.title == "Fix login bug"
        assert result.priority == "critical"
        assert result.issue_type == "bug"
        
        # Check JSON schema was used
        call_args = mock_completions.create.call_args
        assert "gpt-4o" in call_args.kwargs['model']
        response_format = call_args.kwargs['response_format']
        assert response_format['type'] == 'json_schema'
        assert 'json_schema' in response_format
    
    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_pydantic_output_validation_error(self, mock_openai_class, openai_key):
        """Test handling of validation errors in Pydantic output."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock response with invalid data
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "title": "X",  # Too short (needs 2 words)
            "body": "",  # Empty body
            "priority": "urgent",  # Invalid priority
            "issue_type": "story"  # Invalid type
        })
        mock_response.choices = [Mock(message=mock_message)]
        
        mock_completions = Mock()
        mock_completions.create = AsyncMock(return_value=mock_response)
        mock_chat = Mock()
        mock_chat.completions = mock_completions
        mock_client.chat = mock_chat
        
        # Create client
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=openai_key,
            model="gpt-4o"
        )
        
        # Should raise validation error
        with pytest.raises(LLMResponseError) as exc_info:
            await client.generate_pydantic_output(
                prompt="Create issue",
                response_model=IssueGenerationOutput
            )
        
        assert "Failed to generate structured output" in str(exc_info.value)
    
    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_pydantic_task_extraction(self, mock_openai_class, openai_key):
        """Test task extraction using Pydantic models."""
        # Setup mock
        mock_client = Mock()
        mock_responses = Mock()
        mock_client.responses = mock_responses
        mock_openai_class.return_value = mock_client
        
        # Create expected output
        expected_output = TaskExtractionOutput(
            tasks=[
                TaskExtractionItem(
                    title="Setup database",
                    description="Initialize PostgreSQL database",
                    task_type="infrastructure",
                    priority="high"
                ),
                TaskExtractionItem(
                    title="Create API endpoints",
                    description="Build REST API",
                    task_type="feature",
                    priority="high",
                    dependencies=["Setup database"]
                )
            ],
            total_estimated_effort=24.0
        )
        
        # Mock the responses.parse method
        mock_response = Mock()
        mock_response.output_parsed = expected_output
        mock_responses.parse = AsyncMock(return_value=mock_response)
        
        # Create client and generate output
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=openai_key,
            model="gpt-5"
        )
        
        result = await client.generate_pydantic_output(
            prompt="Extract tasks from technical document",
            response_model=TaskExtractionOutput
        )
        
        # Verify
        assert isinstance(result, TaskExtractionOutput)
        assert len(result.tasks) == 2
        assert result.tasks[0].title == "Setup database"
        assert result.tasks[1].dependencies == ["Setup database"]
        assert result.total_estimated_effort == 24.0
    
    @patch('src.integrations.llm_client.Anthropic')
    @pytest.mark.asyncio
    async def test_generate_pydantic_anthropic_fallback(self, mock_anthropic_class):
        """Test Pydantic output with Anthropic provider uses JSON fallback."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock message creation
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "title": "Test Task",
                "items": ["item1", "item2"],
                "count": 2
            }))
        ]
        mock_client.messages.create = Mock(return_value=mock_response)
        
        # Create client
        client = LLMClient(
            provider=LLMProvider.ANTHROPIC,
            api_key="test_anthropic_key",
            model="claude-opus-4.1"
        )
        
        # Generate output
        result = await client.generate_pydantic_output(
            prompt="Generate test output",
            response_model=TestOutputModel
        )
        
        # Verify
        assert isinstance(result, TestOutputModel)
        assert result.title == "Test Task"
        assert result.items == ["item1", "item2"]
        assert result.count == 2
    
    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_pydantic_with_system_prompt(self, mock_openai_class, openai_key):
        """Test that system prompt is properly included."""
        # Setup mock
        mock_client = Mock()
        mock_responses = Mock()
        mock_client.responses = mock_responses
        mock_openai_class.return_value = mock_client
        
        # Mock response
        expected_output = TestOutputModel(
            title="System prompt test",
            items=["test"],
            count=1
        )
        mock_response = Mock()
        mock_response.output_parsed = expected_output
        mock_responses.parse = AsyncMock(return_value=mock_response)
        
        # Create client
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=openai_key,
            model="gpt-5-mini"
        )
        
        # Generate with system prompt
        result = await client.generate_pydantic_output(
            prompt="User prompt",
            response_model=TestOutputModel,
            system_prompt="You are a helpful assistant"
        )
        
        # Verify system prompt was included
        call_args = mock_responses.parse.call_args
        messages = call_args.kwargs['input']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == 'You are a helpful assistant'
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == 'User prompt'
    
    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_pydantic_retry_on_failure(self, mock_openai_class, openai_key):
        """Test that generation retries on transient failures."""
        # Setup mock
        mock_client = Mock()
        mock_responses = Mock()
        mock_client.responses = mock_responses
        mock_openai_class.return_value = mock_client
        
        # First call fails, second succeeds
        expected_output = TestOutputModel(title="Retry test", count=1)
        mock_responses.parse = AsyncMock(
            side_effect=[
                Exception("Network error"),
                Mock(output_parsed=expected_output)
            ]
        )
        
        # Create client
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=openai_key,
            model="gpt-5-nano"
        )
        
        # Should succeed on retry (handled by fallback to JSON)
        # Since the Responses API fails, it should fall back to regular JSON
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "title": "Retry test",
            "items": [],
            "count": 1
        })
        mock_response.choices = [Mock(message=mock_message)]
        
        mock_completions = Mock()
        mock_completions.create = AsyncMock(return_value=mock_response)
        mock_chat = Mock()
        mock_chat.completions = mock_completions
        mock_client.chat = mock_chat
        
        result = await client.generate_pydantic_output(
            prompt="Test",
            response_model=TestOutputModel
        )
        
        # Verify fallback worked
        assert isinstance(result, TestOutputModel)
        assert result.title == "Retry test"
        assert result.count == 1


class TestIssueGenerationWithPydantic:
    """Test issue generation agent with Pydantic models."""
    
    @patch('src.agents.issue_generation_agent.LLMClient')
    def test_agent_uses_pydantic_when_available(self, mock_llm_class):
        """Test that issue generation agent uses Pydantic when available."""
        from src.agents.issue_generation_agent import IssueGenerationAgent
        
        # Mock LLM client
        mock_client = Mock()
        mock_llm_class.return_value = mock_client
        
        # Mock generate_pydantic_output method
        expected_output = IssueGenerationOutput(
            title="Test Issue",
            body="Test body",
            priority="high",
            issue_type="feature"
        )
        
        async def mock_generate_pydantic(*args, **kwargs):
            return expected_output
        
        mock_client.generate_pydantic_output = mock_generate_pydantic
        
        # Create agent
        agent = IssueGenerationAgent()
        agent.llm_client = mock_client
        
        # Generate content
        content = agent.generate_issue_content(
            brief_description="Test issue",
            platform="github"
        )
        
        # Should successfully convert Pydantic output
        assert content.generated_title == "Test Issue"
        assert "Test body" in content.generated_body