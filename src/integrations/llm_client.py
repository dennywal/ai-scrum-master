"""LLM client for AI-powered task extraction and analysis."""

import json
import logging
from enum import Enum
from typing import Any, AsyncIterator, Type, TypeVar
import asyncio

from openai import OpenAI
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel

from src.core.exceptions import LLMConnectionError, LLMResponseError, LLMRateLimitError


logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelVariant(str, Enum):
    """Model size variants available in 2025."""
    # OpenAI GPT-5 variants
    GPT5 = "gpt-5"
    GPT5_MINI = "gpt-5-mini"
    GPT5_NANO = "gpt-5-nano"
    # Anthropic Claude 4 variants  
    CLAUDE_OPUS_4_1 = "claude-opus-4.1"
    CLAUDE_SONNET_4 = "claude-sonnet-4"


class LLMClient:
    """Client for interacting with LLM APIs."""

    def __init__(self, 
                 provider: LLMProvider,
                 api_key: str,
                 model: str | None = None,
                 max_retries: int = 3):
        """Initialize LLM client.
        
        Args:
            provider: LLM provider to use
            api_key: API key for the provider
            model: Model to use (defaults to provider default)
            max_retries: Maximum retry attempts
            
        Raises:
            ValueError: If API key is empty
        """
        if not api_key:
            raise ValueError("API key is required")
        
        self.provider = provider
        self.api_key = api_key
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize provider client
        if provider == LLMProvider.OPENAI:
            self.client = OpenAI(api_key=api_key)
            self.model = model or "gpt-5"
        elif provider == LLMProvider.ANTHROPIC:
            self.client = Anthropic(api_key=api_key)
            self.model = model or "claude-opus-4.1"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_completion(self,
                                 prompt: str,
                                 system_prompt: str | None = None,
                                 temperature: float = 0.7,
                                 max_tokens: int = 2000) -> str:
        """Generate a text completion.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
            
        Raises:
            LLMConnectionError: If connection fails
            LLMRateLimitError: If rate limited
            LLMResponseError: If response is invalid
        """
        try:
            if self.provider == LLMProvider.OPENAI:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Always use Chat Completions API
                # Use max_completion_tokens for newer models, max_tokens for older ones
                # GPT-5-nano only supports temperature=1.0
                api_temperature = 1.0 if "gpt-5-nano" in self.model else temperature
                
                try:
                    # Try with max_completion_tokens first (for newer models)
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=api_temperature,
                        max_completion_tokens=max_tokens,
                        response_format={"type": "text"}  # Ensure text response
                    )
                except Exception as e:
                    if "max_completion_tokens" in str(e) or "unsupported_parameter" in str(e):
                        # Fallback to max_tokens for older models
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=api_temperature,  # Use the same adjusted temperature
                            max_tokens=max_tokens
                        )
                    else:
                        raise
                
                # Extract content from response
                if not response.choices:
                    logger.warning(f"No choices in LLM response for prompt: {prompt[:100]}...")
                    raise LLMResponseError("LLM returned no choices in response")
                    
                content = response.choices[0].message.content
                # Only warn if content is None (not just empty string)
                if content is None:
                    logger.warning(f"None content from LLM for prompt: {prompt[:100]}...")
                    # Return empty string instead of raising error for backward compatibility
                    return ""
                    
                return content
                
            elif self.provider == LLMProvider.ANTHROPIC:
                kwargs = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                if system_prompt:
                    kwargs["system"] = system_prompt
                
                response = self.client.messages.create(**kwargs)
                return response.content[0].text
                
        except Exception as e:
            if "rate" in str(e).lower():
                raise LLMRateLimitError() from e
            elif "connection" in str(e).lower():
                raise LLMConnectionError(self.provider.value, e) from e
            else:
                raise LLMResponseError(f"Failed to generate completion: {str(e)}") from e

    async def generate_structured_output(self,
                                        prompt: str,
                                        schema: dict[str, Any],
                                        system_prompt: str | None = None) -> dict[str, Any]:
        """Generate structured JSON output using latest API features.
        
        Args:
            prompt: User prompt
            schema: JSON schema for output
            system_prompt: System prompt
            
        Returns:
            Parsed JSON response
            
        Raises:
            LLMResponseError: If response is not valid JSON
        """
        try:
            if self.provider == LLMProvider.OPENAI:
                # Use OpenAI's structured output with response_format
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Use Responses API for GPT-5 with structured output
                if "gpt-5" in self.model and hasattr(self.client, 'responses'):
                    response = self.client.responses.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.3,  # Lower temperature for structured output
                        response_format={"type": "json_schema", "json_schema": schema}  # Direct schema validation
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.3,
                        response_format={"type": "json_object"}
                    )
                
                return json.loads(response.choices[0].message.content)
            else:
                # Fallback for other providers
                json_prompt = f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
                
                response = await self.generate_completion(
                    prompt=json_prompt,
                    system_prompt=system_prompt or "You are a helpful assistant that always responds with valid JSON.",
                    temperature=0.3
                )
                
                return json.loads(response)
                
        except json.JSONDecodeError as e:
            raise LLMResponseError(f"Invalid JSON response: {str(e)}") from e
        except Exception as e:
            raise LLMResponseError(f"Failed to generate structured output: {str(e)}") from e

    async def generate_pydantic_output(self,
                                      prompt: str,
                                      response_model: Type[T],
                                      system_prompt: str | None = None,
                                      temperature: float = 0.7,
                                      max_tokens: int = 2000) -> T:
        """Generate structured output using Pydantic models with OpenAI Responses API.
        
        Uses the new Responses API for GPT-5 models when available, with fallback
        to structured output for GPT-4 models.
        
        Args:
            prompt: User prompt
            response_model: Pydantic model class for response structure
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Instance of the Pydantic model with generated data
            
        Raises:
            LLMResponseError: If response parsing fails
            
        Example:
            >>> client = LLMClient(provider=LLMProvider.OPENAI, api_key="...")
            >>> result = await client.generate_pydantic_output(
            ...     prompt="Create an issue for adding dark mode",
            ...     response_model=IssueGenerationOutput
            ... )
            >>> print(result.title)  # "Add dark mode support"
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            if self.provider == LLMProvider.OPENAI:
                # Check if we can use the Responses API with parse method for GPT-5
                if "gpt-5" in self.model and hasattr(self.client, 'responses'):
                    try:
                        # Use the new Responses API parse method
                        self.logger.debug(
                            f"Using Responses API with model {self.model}",
                            extra={
                                "model": self.model,
                                "response_model": response_model.__name__,
                                "prompt_length": len(prompt)
                            }
                        )
                        
                        # GPT-5-nano only supports temperature=1.0
                        api_temperature = 1.0 if "gpt-5-nano" in self.model else temperature
                        
                        # Responses API doesn't accept max_tokens or max_completion_tokens
                        response = self.client.responses.parse(
                            model=self.model,
                            input=messages,  # Note: using 'input' instead of 'messages'
                            text_format=response_model,  # Pass the Pydantic model directly
                            temperature=api_temperature
                            # Note: No max_tokens parameter - Responses API handles this automatically
                        )
                        
                        # The response should have an output_parsed attribute
                        if hasattr(response, 'output_parsed'):
                            self.logger.debug("Successfully used Responses API")
                            return response.output_parsed
                        else:
                            # Fallback to manual parsing if needed
                            self.logger.debug("Responses API lacks output_parsed, using direct output")
                            return response_model.model_validate(response.output)
                    except Exception as e:
                        self.logger.warning(
                            f"Responses API parse failed: {e}, falling back to standard method",
                            extra={"error": str(e), "model": self.model}
                        )
                        # Fall through to standard method
                
                # Fallback to standard structured output with JSON schema
                # Generate JSON schema from Pydantic model
                schema = response_model.model_json_schema()
                
                # Check if model supports structured output with JSON schema
                supports_json_schema = any(
                    model_prefix in self.model 
                    for model_prefix in ["gpt-4o", "gpt-4-turbo", "gpt-4-0125", "gpt-3.5-turbo-0125"]
                )
                
                if supports_json_schema:
                    # Models that support structured output with JSON schema
                    self.logger.debug(f"Using JSON schema structured output for {self.model}")
                    
                    # Use appropriate parameter based on model
                    completion_params = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": response_model.__name__,
                                "schema": schema,
                                "strict": True
                            }
                        }
                    }
                    
                    # GPT-5 models use max_completion_tokens
                    if "gpt-5" in self.model:
                        completion_params["max_completion_tokens"] = max_tokens
                        # GPT-5-nano only supports temperature=1.0
                        if "gpt-5-nano" in self.model:
                            completion_params["temperature"] = 1.0
                    else:
                        completion_params["max_tokens"] = max_tokens
                    
                    response = self.client.chat.completions.create(**completion_params)
                else:
                    # Older models - use JSON mode with schema in prompt
                    self.logger.debug(f"Using JSON mode with schema in prompt for {self.model}")
                    
                    # Add schema to the prompt for better compliance
                    schema_prompt = (
                        f"You must respond with valid JSON that matches this Pydantic model schema:\n"
                        f"{json.dumps(schema, indent=2)}\n\n"
                        f"Ensure all required fields are present and properly typed."
                    )
                    messages.append({"role": "system", "content": schema_prompt})
                    
                    # Build parameters based on model type
                    completion_params = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "response_format": {"type": "json_object"}
                    }
                    
                    # GPT-5 models use max_completion_tokens
                    if "gpt-5" in self.model:
                        completion_params["max_completion_tokens"] = max_tokens
                        # GPT-5-nano only supports temperature=1.0
                        if "gpt-5-nano" in self.model:
                            completion_params["temperature"] = 1.0
                    else:
                        completion_params["max_tokens"] = max_tokens
                    
                    response = self.client.chat.completions.create(**completion_params)
                
                # Parse the JSON response into Pydantic model
                json_str = response.choices[0].message.content
                return response_model.model_validate_json(json_str)
                
            elif self.provider == LLMProvider.ANTHROPIC:
                # For Anthropic, generate schema and request JSON
                schema = response_model.model_json_schema()
                json_prompt = f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
                
                response_text = await self.generate_completion(
                    prompt=json_prompt,
                    system_prompt=system_prompt or "You are a helpful assistant that always responds with valid JSON.",
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Parse into Pydantic model
                return response_model.model_validate_json(response_text)
            else:
                raise NotImplementedError(f"Pydantic output not implemented for {self.provider}")
                
        except Exception as e:
            self.logger.error(
                f"Failed to generate Pydantic output for model {self.model}: {str(e)}",
                extra={
                    "model": self.model,
                    "provider": self.provider.value,
                    "response_model": response_model.__name__,
                    "prompt_length": len(prompt),
                    "error_type": type(e).__name__
                }
            )
            raise LLMResponseError(
                f"Failed to generate structured output with {response_model.__name__}: {str(e)}"
            ) from e

    async def batch_generate(self, prompts: list[str]) -> list[str]:
        """Generate completions for multiple prompts.
        
        Args:
            prompts: List of prompts
            
        Returns:
            List of generated responses
        """
        tasks = [self.generate_completion(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        responses = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Batch generation error: {str(result)}")
                responses.append("")
            else:
                responses.append(result)
        
        return responses

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Generate streaming response.
        
        Args:
            prompt: User prompt
            
        Yields:
            Response chunks
        """
        try:
            if self.provider == LLMProvider.OPENAI:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            elif self.provider == LLMProvider.ANTHROPIC:
                # Anthropic streaming is more complex, simplified here
                response = await self.generate_completion(prompt)
                # Simulate streaming by yielding chunks
                chunk_size = 10
                for i in range(0, len(response), chunk_size):
                    yield response[i:i+chunk_size]
                    await asyncio.sleep(0.01)  # Small delay to simulate streaming
                    
        except Exception as e:
            self.logger.error(f"Streaming error: {str(e)}")
            raise LLMResponseError(f"Streaming failed: {str(e)}") from e

    async def generate_with_functions(self,
                                     prompt: str,
                                     functions: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate completion with function calling.
        
        Args:
            prompt: User prompt
            functions: List of function definitions
            
        Returns:
            Function call result
        """
        if self.provider != LLMProvider.OPENAI:
            raise NotImplementedError("Function calling only supported for OpenAI")
        
        try:
            # Using the new tools API instead of deprecated functions API
            tools = [{"type": "function", "function": func} for func in functions]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            if message.tool_calls:
                # Handle new tool calls format
                tool_call = message.tool_calls[0]
                return {
                    "function_name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments)
                }
            else:
                return {
                    "content": message.content
                }
                
        except Exception as e:
            raise LLMResponseError(f"Function calling failed: {str(e)}") from e

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token for English
        # More accurate would use tiktoken library
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Get information about current model.
        
        Returns:
            Model information
        """
        info = {
            "provider": self.provider.value,
            "model": self.model,
            "max_retries": self.max_retries
        }
        
        # Add provider-specific info
        if self.provider == LLMProvider.OPENAI:
            # Updated token limits for newer models
            if "gpt-4o" in self.model:
                info["max_tokens"] = 128000
            elif "gpt-4" in self.model:
                info["max_tokens"] = 128000
            elif "gpt-3.5" in self.model:
                info["max_tokens"] = 16384
            else:
                info["max_tokens"] = 128000  # Default for newer models
        elif self.provider == LLMProvider.ANTHROPIC:
            # Updated token limits for Claude models
            if "claude-3-5" in self.model or "claude-3-opus" in self.model:
                info["max_tokens"] = 200000
            elif "claude-3" in self.model:
                info["max_tokens"] = 200000
            else:
                info["max_tokens"] = 200000  # Default for newer Claude models
        
        return info

    def validate_api_key(self) -> bool:
        """Validate the API key.
        
        Returns:
            True if valid
        """
        try:
            if self.provider == LLMProvider.OPENAI:
                # Try to list models
                self.client.models.list()
            elif self.provider == LLMProvider.ANTHROPIC:
                # Try a minimal completion
                self.client.messages.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
            return True
        except Exception as e:
            self.logger.error(f"API key validation failed: {str(e)}")
            return False