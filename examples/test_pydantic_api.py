#!/usr/bin/env python
"""Example demonstrating the new Pydantic-based OpenAI Responses API integration."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.llm_client import LLMClient, LLMProvider
from src.models.issues import IssueGenerationOutput
from src.models.tasks import TaskExtractionOutput, TaskExtractionItem

async def test_pydantic_issue_generation():
    """Test issue generation with Pydantic models."""
    
    # Initialize LLM client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        print("Please set a valid OPENAI_API_KEY environment variable")
        return
    
    try:
        # Try with GPT-5 model (for Responses API)
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=api_key,
            model="gpt-5"  # Will use Responses API
        )
    except Exception as e:
        print(f"Falling back to GPT-4: {e}")
        # Fallback to GPT-4
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=api_key,
            model="gpt-4o-mini"  # Use a model that actually exists
        )
    
    print(f"Using model: {client.model}")
    print("-" * 50)
    
    # Test issue generation with Pydantic
    prompt = """Create a comprehensive GitHub issue for the following:

Brief Description: Implement a caching system for frequently accessed API responses to improve performance and reduce external API calls.

This should include proper cache invalidation, TTL configuration, and monitoring capabilities."""
    
    try:
        print("Generating issue with Pydantic structured output...")
        result = await client.generate_pydantic_output(
            prompt=prompt,
            response_model=IssueGenerationOutput,
            system_prompt="You are an expert software architect creating detailed, actionable issues.",
            temperature=0.7,
            max_tokens=2000
        )
        
        print("\n✅ Successfully generated issue using Pydantic model!")
        print("\n📋 Generated Issue:")
        print(f"Title: {result.title}")
        print(f"Priority: {result.priority}")
        print(f"Type: {result.issue_type}")
        print(f"Estimated Hours: {result.estimated_hours}")
        print(f"\nBody Preview: {result.body[:200]}...")
        print(f"\nAcceptance Criteria:")
        for i, criterion in enumerate(result.acceptance_criteria[:3], 1):
            print(f"  {i}. {criterion}")
        if len(result.acceptance_criteria) > 3:
            print(f"  ... and {len(result.acceptance_criteria) - 3} more")
        print(f"\nLabels: {', '.join(result.labels)}")
        print(f"Components: {', '.join(result.components)}")
        
        # Convert to backward-compatible format
        generated_content = result.to_generated_content()
        print(f"\n✅ Successfully converted to GeneratedIssueContent format")
        
    except Exception as e:
        print(f"❌ Error generating issue: {e}")
        import traceback
        traceback.print_exc()

async def test_pydantic_task_extraction():
    """Test task extraction with Pydantic models."""
    
    # Initialize LLM client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        print("Please set a valid OPENAI_API_KEY environment variable")
        return
    
    try:
        # Try with GPT-5 model (for Responses API)
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=api_key,
            model="gpt-5"  # Will use Responses API
        )
    except Exception as e:
        print(f"Falling back to GPT-4: {e}")
        # Fallback to GPT-4
        client = LLMClient(
            provider=LLMProvider.OPENAI,
            api_key=api_key,
            model="gpt-4o-mini"  # Use a model that actually exists
        )
    
    print(f"\nUsing model: {client.model} for task extraction")
    print("-" * 50)
    
    # Test task extraction with Pydantic
    prompt = """Extract actionable tasks from the following technical design document:

## Overview
We need to implement a real-time notification system for our web application that supports multiple channels (email, SMS, push notifications).

## Requirements
1. Design a scalable message queue architecture
2. Implement notification templates with variable substitution
3. Create APIs for sending notifications
4. Add user preference management for notification settings
5. Implement rate limiting to prevent spam
6. Add monitoring and alerting for notification delivery
7. Create documentation and integration guides

Each component should be thoroughly tested and include proper error handling."""
    
    try:
        print("Extracting tasks with Pydantic structured output...")
        result = await client.generate_pydantic_output(
            prompt=prompt,
            response_model=TaskExtractionOutput,
            system_prompt="You are an expert project manager extracting actionable tasks from requirements.",
            temperature=0.7,
            max_tokens=3000
        )
        
        print("\n✅ Successfully extracted tasks using Pydantic model!")
        print(f"\n📋 Extracted {len(result.tasks)} tasks:")
        
        for i, task in enumerate(result.tasks, 1):
            print(f"\n{i}. {task.title}")
            print(f"   Type: {task.task_type} | Priority: {task.priority}")
            print(f"   Description: {task.description[:100]}...")
            if task.acceptance_criteria:
                print(f"   Acceptance Criteria: {len(task.acceptance_criteria)} items")
            if task.dependencies:
                print(f"   Dependencies: {', '.join(task.dependencies)}")
        
        if result.total_estimated_effort:
            print(f"\n⏱️  Total Estimated Effort: {result.total_estimated_effort} hours")
        
        # Convert to TaskBatch for processing
        task_batch = result.to_task_batch("TDD-001")
        print(f"\n✅ Successfully converted to TaskBatch with {len(task_batch.tasks)} tasks")
        
    except Exception as e:
        print(f"❌ Error extracting tasks: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Pydantic-based OpenAI Responses API Integration")
    print("=" * 60)
    
    # Test issue generation
    await test_pydantic_issue_generation()
    
    print("\n" + "=" * 60)
    
    # Test task extraction
    await test_pydantic_task_extraction()
    
    print("\n" + "=" * 60)
    print("✅ Demo completed!")

if __name__ == "__main__":
    asyncio.run(main())