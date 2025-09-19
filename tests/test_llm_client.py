"""Tests for LLMClient class."""

from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
import json

from src.integrations.llm_client import LLMClient, LLMProvider, ModelVariant
from src.core.exceptions import LLMConnectionError, LLMResponseError, LLMRateLimitError


class TestLLMClient:
    """Test suite for LLMClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.openai_key = "test_openai_key"
        self.anthropic_key = "test_anthropic_key"
        
    @patch('src.integrations.llm_client.OpenAI')
    def test_initialization_with_openai(self, mock_openai):
        """Test initialization with OpenAI provider."""
        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        assert client.provider == LLMProvider.OPENAI
        assert client.api_key == self.openai_key
        assert client.model == "gpt-5"  # Check default GPT-5 model
        mock_openai.assert_called_once_with(api_key=self.openai_key)

    @patch('src.integrations.llm_client.Anthropic')
    def test_initialization_with_anthropic(self, mock_anthropic):
        """Test initialization with Anthropic provider."""
        client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key=self.anthropic_key)
        
        assert client.provider == LLMProvider.ANTHROPIC
        assert client.api_key == self.anthropic_key
        assert client.model == "claude-opus-4.1"  # Check default Claude 4 model
        mock_anthropic.assert_called_once_with(api_key=self.anthropic_key)

    def test_initialization_without_api_key_raises_error(self):
        """Test initialization without API key raises error."""
        with pytest.raises(ValueError):
            LLMClient(provider=LLMProvider.OPENAI, api_key="")

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_completion_openai(self, mock_openai):
        """Test generating completion with OpenAI."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Generated response"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        response = await client.generate_completion(
            prompt="Test prompt",
            temperature=0.7,
            max_tokens=100
        )

        assert response == "Generated response"
        mock_client.chat.completions.create.assert_called_once()

    @patch('src.integrations.llm_client.Anthropic')
    @pytest.mark.asyncio
    async def test_generate_completion_anthropic(self, mock_anthropic):
        """Test generating completion with Anthropic."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Generated response")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key=self.anthropic_key)
        response = await client.generate_completion(
            prompt="Test prompt",
            temperature=0.7,
            max_tokens=100
        )

        assert response == "Generated response"
        mock_client.messages.create.assert_called_once()

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_structured_output(self, mock_openai):
        """Test generating structured JSON output with response_format."""
        mock_client = Mock()
        mock_response = Mock()
        structured_data = {"tasks": ["task1", "task2"], "priority": "high"}
        mock_response.choices = [Mock(message=Mock(content=json.dumps(structured_data)))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        response = await client.generate_structured_output(
            prompt="Extract tasks",
            schema={"type": "object", "properties": {"tasks": {"type": "array"}}}
        )

        assert response == structured_data
        assert "tasks" in response
        # Verify response_format is used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs.get('response_format') == {"type": "json_object"}
        assert len(response["tasks"]) == 2

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, mock_openai):
        """Test handling of rate limit errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        with pytest.raises(LLMRateLimitError):
            await client.generate_completion("Test prompt")

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_openai):
        """Test handling of connection errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        with pytest.raises(LLMConnectionError):
            await client.generate_completion("Test prompt")

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mock_openai):
        """Test handling of invalid JSON in structured output."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Not valid JSON {"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        with pytest.raises(LLMResponseError):
            await client.generate_structured_output(
                prompt="Extract tasks",
                schema={}
            )

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, mock_openai):
        """Test retry mechanism on transient failures."""
        mock_client = Mock()
        # Fail twice, then succeed
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Success"))]
        mock_client.chat.completions.create.side_effect = [
            Exception("Temporary failure"),
            Exception("Temporary failure"),
            mock_response
        ]
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key, max_retries=3)
        response = await client.generate_completion("Test prompt")

        assert response == "Success"
        assert mock_client.chat.completions.create.call_count == 3

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_batch_processing(self, mock_openai):
        """Test batch processing of multiple prompts."""
        mock_client = Mock()
        responses = []
        for i in range(3):
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content=f"Response {i}"))]
            responses.append(mock_response)
        mock_client.chat.completions.create.side_effect = responses
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        results = await client.batch_generate(prompts)

        assert len(results) == 3
        assert results[0] == "Response 0"
        assert results[2] == "Response 2"

    @patch('src.integrations.llm_client.OpenAI')
    def test_estimate_tokens(self, mock_openai):
        """Test token estimation for prompts."""
        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        # Rough estimation: ~4 characters per token
        text = "This is a test prompt with several words."
        estimated = client.estimate_tokens(text)
        
        assert estimated > 0
        assert estimated < len(text)  # Should be less than character count

    @patch('src.integrations.llm_client.OpenAI')
    def test_get_model_info(self, mock_openai):
        """Test getting model information."""
        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        info = client.get_model_info()
        
        assert "provider" in info
        assert "model" in info
        assert "max_tokens" in info
        assert info["provider"] == "openai"

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_streaming_response(self, mock_openai):
        """Test streaming response generation."""
        mock_client = Mock()
        mock_stream = [
            Mock(choices=[Mock(delta=Mock(content="Hello"))]),
            Mock(choices=[Mock(delta=Mock(content=" world"))]),
            Mock(choices=[Mock(delta=Mock(content="!"))])
        ]
        mock_client.chat.completions.create.return_value = iter(mock_stream)
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        chunks = []
        async for chunk in client.generate_stream("Test prompt"):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert "".join(chunks) == "Hello world!"

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_with_functions_tools_api(self, mock_openai):
        """Test function calling with new tools API."""
        mock_client = Mock()
        mock_response = Mock()
        tool_call = Mock()
        tool_call.function.name = "extract_tasks"
        tool_call.function.arguments = json.dumps({"tasks": ["task1", "task2"]})
        mock_response.choices = [Mock(message=Mock(tool_calls=[tool_call], content=None))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        functions = [{
            "name": "extract_tasks",
            "description": "Extract tasks from text",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {"type": "array", "items": {"type": "string"}}
                }
            }
        }]
        
        result = await client.generate_with_functions("Extract tasks from this text", functions)
        
        assert result["function_name"] == "extract_tasks"
        assert result["arguments"]["tasks"] == ["task1", "task2"]
        
        # Verify tools API is used instead of deprecated functions API
        call_args = mock_client.chat.completions.create.call_args
        assert "tools" in call_args.kwargs
        assert call_args.kwargs["tool_choice"] == "auto"

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_responses_api_for_gpt5(self, mock_openai):
        """Test that GPT-5 uses Responses API when available."""
        mock_client = Mock()
        mock_responses = Mock()
        mock_client.responses = mock_responses
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response from Responses API"))]
        mock_responses.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key, model="gpt-5")
        
        response = await client.generate_completion("Test prompt")
        
        assert response == "Response from Responses API"
        # Verify Responses API was called, not Chat Completions
        mock_responses.create.assert_called_once()
        mock_client.chat.completions.create.assert_not_called()

    @patch('src.integrations.llm_client.OpenAI')
    @pytest.mark.asyncio
    async def test_model_variants(self, mock_openai):
        """Test different model variants."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Test GPT-5 variants
        for variant in [ModelVariant.GPT5, ModelVariant.GPT5_MINI, ModelVariant.GPT5_NANO]:
            client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key, model=variant.value)
            assert client.model == variant.value
        
        # Test Claude variants
        for variant in [ModelVariant.CLAUDE_OPUS_4_1, ModelVariant.CLAUDE_SONNET_4]:
            with patch('src.integrations.llm_client.Anthropic'):
                client = LLMClient(provider=LLMProvider.ANTHROPIC, api_key=self.anthropic_key, model=variant.value)
                assert client.model == variant.value

    @patch('src.integrations.llm_client.OpenAI')
    def test_validate_api_key(self, mock_openai):
        """Test API key validation."""
        mock_client = Mock()
        mock_client.models.list.return_value = [Mock(id="gpt-5")]
        mock_openai.return_value = mock_client

        client = LLMClient(provider=LLMProvider.OPENAI, api_key=self.openai_key)
        
        is_valid = client.validate_api_key()
        
        assert is_valid is True
        mock_client.models.list.assert_called_once()

