"""LLM client for AI-powered task extraction and analysis."""

import json
import logging
from enum import Enum
from typing import Any, AsyncIterator
import asyncio

from openai import OpenAI
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.exceptions import LLMConnectionError, LLMResponseError, LLMRateLimitError


logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


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
            self.model = model or "gpt-4-turbo-preview"
        elif provider == LLMProvider.ANTHROPIC:
            self.client = Anthropic(api_key=api_key)
            self.model = model or "claude-3-opus-20240229"
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
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
                
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
        """Generate structured JSON output.
        
        Args:
            prompt: User prompt
            schema: JSON schema for output
            system_prompt: System prompt
            
        Returns:
            Parsed JSON response
            
        Raises:
            LLMResponseError: If response is not valid JSON
        """
        json_prompt = f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        
        response = await self.generate_completion(
            prompt=json_prompt,
            system_prompt=system_prompt or "You are a helpful assistant that always responds with valid JSON.",
            temperature=0.3  # Lower temperature for structured output
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise LLMResponseError(f"Invalid JSON response: {str(e)}", response) from e

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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                functions=functions,
                function_call="auto"
            )
            
            message = response.choices[0].message
            if message.function_call:
                return {
                    "function_name": message.function_call.name,
                    "arguments": json.loads(message.function_call.arguments)
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
            info["max_tokens"] = 128000 if "gpt-4" in self.model else 16384
        elif self.provider == LLMProvider.ANTHROPIC:
            info["max_tokens"] = 200000 if "claude-3" in self.model else 100000
        
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