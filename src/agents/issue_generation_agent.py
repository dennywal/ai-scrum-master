"""
GitHub/Jira/Linear Issue Generation Agent for creating detailed issues from brief descriptions.

This agent takes a brief description and generates a comprehensive issue
with proper formatting, labels, priority, and detailed content using LLM.
"""

import logging
import time
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from src.core.base_agent import BaseAgent
from src.models.tasks import ExtractedTask, Priority
from src.models.issues import GeneratedIssueContent, IssueGenerationOutput
from src.integrations.llm_client import LLMClient, LLMProvider

logger = logging.getLogger(__name__)


class IssueGenerationAgent(BaseAgent):
    """Agent that generates detailed issues from brief descriptions using LLM."""
    
    def __init__(self, name: str = "IssueGenerationAgent"):
        """Initialize the Issue Generation Agent.
        
        Args:
            name: Agent name
        """
        super().__init__(name=name)
        
        # Initialize LLM client with settings
        try:
            # Try to get settings - might fail if env vars not set
            from src.config.settings import settings
            
            # Determine provider based on settings
            provider = LLMProvider.OPENAI  # Default to OpenAI
            api_key = settings.llm.openai_api_key.get_secret_value()
            # Use gpt-3.5-turbo as a reliable default
            model = "gpt-5-nano"  # Override model to use a stable one
            logger.info(f"Using model: {model}")
            
            # Check if we should use Anthropic instead
            if hasattr(settings.llm, 'anthropic_api_key') and settings.llm.anthropic_api_key:
                if 'claude' in model.lower():
                    provider = LLMProvider.ANTHROPIC
                    api_key = settings.llm.anthropic_api_key.get_secret_value()
            
            # Only create client if we have a real API key
            if api_key and api_key not in ['', 'test_', None] and not api_key.startswith('test_') and not api_key.startswith('your_'):
                self.llm_client = LLMClient(
                    provider=provider,
                    api_key=api_key,
                    model=model
                )
            else:
                logger.warning("No valid API key found. Using fallback content generation.")
                self.llm_client = None
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}. Will use fallback content generation.")
            self.llm_client = None
        
    def _initialize(self):
        """Initialize agent-specific components."""
        logger.info(f"Initialized {self.name}")
    
    def generate_issue_content(self, 
                              brief_description: str, 
                              platform: str = "github",
                              repo_name: str = "",
                              project_context: str = "") -> GeneratedIssueContent:
        """Generate detailed issue content from a brief description using LLM.
        
        Args:
            brief_description: Brief description of the issue
            platform: Target platform (github, jira, linear)
            repo_name: Repository or project name for context
            project_context: Additional project context
            
        Returns:
            GeneratedIssueContent with generated fields
        """
        # Construct prompt for comprehensive issue generation
        prompt = self._build_generation_prompt(
            brief_description, 
            platform, 
            repo_name,
            project_context
        )
        
        try:
            # Check if LLM client is available
            if not self.llm_client:
                logger.warning("LLM client not initialized, using fallback content")
                return self._create_fallback_content(brief_description, "LLM client not available")
            
            # Generate issue content using LLM
            # The LLMClient methods are async, so we need to handle that
            import asyncio
            import traceback
            
            async def get_response():
                try:
                    logger.debug(f"Attempting to use Pydantic structured output with model: {self.llm_client.model}")
                    
                    # Try to use the new Pydantic-based approach first
                    if hasattr(self.llm_client, 'generate_pydantic_output'):
                        try:
                            # Use the new Pydantic structured output method
                            result = await self.llm_client.generate_pydantic_output(
                                prompt=self._build_pydantic_generation_prompt(
                                    brief_description, platform, repo_name, project_context
                                ),
                                response_model=IssueGenerationOutput,
                                system_prompt="You are an expert software project manager creating detailed, actionable issues.",
                                temperature=0.7,
                                max_tokens=2000
                            )
                            logger.debug("Successfully used Pydantic structured output")
                            return result
                        except Exception as e:
                            logger.warning(f"Pydantic structured output failed: {e}, falling back to text generation")
                            # Fall through to text-based generation
                    
                    # Fallback to text-based generation
                    logger.debug(f"Using text-based generation with prompt length: {len(prompt)} chars")
                    response = await self.llm_client.generate_completion(
                        prompt=prompt,
                        temperature=1.0,  # Use default temperature for compatibility
                        max_tokens=2000
                    )
                    logger.debug(f"LLM response received, length: {len(response) if response else 0} chars")
                    return response
                except Exception as llm_error:
                    logger.error(f"LLM API call failed: {llm_error}")
                    logger.error(f"LLM error type: {type(llm_error).__name__}")
                    logger.error(f"LLM error traceback:\n{traceback.format_exc()}")
                    raise
            
            # Run the async function - simplify to always use asyncio.run
            # This avoids issues with event loops in different contexts
            try:
                import nest_asyncio
                nest_asyncio.apply()  # Allow nested event loops if needed
                response = asyncio.run(get_response())
            except ImportError:
                # If nest_asyncio is not installed, try alternative approach
                logger.debug("nest_asyncio not available, using alternative approach")
                try:
                    # Try to get existing loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're already in an async context, create a new task
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, get_response())
                            response = future.result(timeout=30)
                    else:
                        response = loop.run_until_complete(get_response())
                except RuntimeError:
                    # If no event loop exists, create one
                    response = asyncio.run(get_response())
            
            # Parse the response into structured format
            if isinstance(response, IssueGenerationOutput):
                # We got a Pydantic model back, convert to GeneratedIssueContent
                return response.to_generated_content()
            else:
                # We got text back, parse it the old way
                return self._parse_llm_response(response, brief_description)
            
        except asyncio.TimeoutError:
            error_msg = "LLM request timed out after 30 seconds"
            logger.error(error_msg)
            return self._create_fallback_content(brief_description, error_msg)
        except Exception as e:
            error_details = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Failed to generate issue content: {error_details}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            # Return fallback content with more details
            return self._create_fallback_content(brief_description, error_details)
    
    def _build_generation_prompt(self, 
                                brief_description: str, 
                                platform: str,
                                repo_name: str,
                                project_context: str) -> str:
        """Build the prompt for LLM issue generation.
        
        Args:
            brief_description: Brief issue description
            platform: Target platform
            repo_name: Repository/project name
            project_context: Additional context
            
        Returns:
            Formatted prompt string
        """
        platform_specific = {
            "github": "GitHub issue",
            "jira": "Jira ticket",
            "linear": "Linear issue"
        }.get(platform, "issue")
        
        prompt = f"""You are an expert software project manager creating a detailed {platform_specific}.
        
Repository/Project: {repo_name if repo_name else 'General Project'}
Context: {project_context if project_context else 'Software development project'}

Brief Description: {brief_description}

Generate a comprehensive {platform_specific} with the following structure:

1. TITLE: A concise, descriptive title (max 100 characters)

2. DESCRIPTION/BODY: A detailed description in Markdown format including:
   - Problem Statement: Clear explanation of the issue or feature
   - Current Behavior: What happens now (if applicable)
   - Expected Behavior: What should happen
   - Impact: Why this matters

3. ACCEPTANCE CRITERIA: Specific, testable criteria (bullet points)

4. TECHNICAL DETAILS:
   - Affected Components: List relevant components/modules
   - Dependencies: Any blocking issues or prerequisites
   - Suggested Approach: High-level implementation ideas

5. METADATA:
   - Priority: critical/high/medium/low
   - Type: bug/feature/enhancement/task/documentation
   - Estimated Effort: hours or story points
   - Labels: Relevant tags (comma-separated)

6. ADDITIONAL NOTES: Any other relevant information

The created {platform_specific} should be as detailed as possible and include all the information that is needed to implement the issue. \
    It should be written so that a developer can implement the issue without having to ask for more information.

IMPORTANT: Your response MUST be ONLY valid JSON, with no additional text before or after.
Format your response as a single JSON object with these exact keys:
{{
    "title": "...",
    "body": "...",
    "acceptance_criteria": ["criterion 1", "criterion 2", ...],
    "priority": "medium",
    "issue_type": "feature",
    "labels": ["label1", "label2"],
    "estimated_hours": 8,
    "components": ["component1"],
    "dependencies": []
}}

Return ONLY the JSON object, nothing else. Do not include explanations or markdown formatting."""
        
        return prompt
    
    def _build_pydantic_generation_prompt(self,
                                         brief_description: str,
                                         platform: str,
                                         repo_name: str,
                                         project_context: str) -> str:
        """Build optimized prompt for Pydantic-based generation.
        
        Args:
            brief_description: Brief issue description
            platform: Target platform
            repo_name: Repository/project name
            project_context: Additional context
            
        Returns:
            Formatted prompt string
        """
        platform_specific = {
            "github": "GitHub issue",
            "jira": "Jira ticket",
            "linear": "Linear issue"
        }.get(platform, "issue")
        
        prompt = f"""Create a detailed {platform_specific} for the following:

Repository/Project: {repo_name if repo_name else 'General Project'}
Context: {project_context if project_context else 'Software development project'}

Brief Description: {brief_description}

Provide comprehensive details including:
- A clear, actionable title
- Detailed description with problem statement, current vs expected behavior, and impact
- Specific, testable acceptance criteria
- Technical details including affected components, dependencies, and implementation approach
- Appropriate priority, type, and effort estimation
- Relevant labels for categorization

Ensure the issue is detailed enough that a developer can implement it without needing additional clarification."""
        
        return prompt
    
    def _parse_llm_response(self, response: str, brief_description: str) -> GeneratedIssueContent:
        """Parse LLM response into structured issue content.
        
        Args:
            response: Raw LLM response
            brief_description: Original description for fallback
            
        Returns:
            GeneratedIssueContent object
        """
        import json
        import re
        
        # Check for empty response
        if not response or not response.strip():
            logger.warning("Empty LLM response, using fallback content")
            return self._create_fallback_content(brief_description, "Empty response from LLM")
        
        try:
            # First, try to parse as clean JSON
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            try:
                # Try to extract JSON from response
                # Handle case where LLM might wrap JSON in markdown code blocks
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                else:
                    raise json.JSONDecodeError("No JSON found", response, 0)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}. Using text parsing fallback.")
                return self._parse_text_response(response, brief_description)
        
        # Build the full issue body with all sections
        body_sections = []
        
        # Add main description
        if data.get('body'):
            body_sections.append(data['body'])
        
        # Add acceptance criteria section
        if data.get('acceptance_criteria'):
            body_sections.append("\n## Acceptance Criteria\n")
            for criterion in data['acceptance_criteria']:
                body_sections.append(f"- [ ] {criterion}")
        
        # Add technical details
        if data.get('components') or data.get('dependencies'):
            body_sections.append("\n## Technical Details\n")
            if data.get('components'):
                body_sections.append(f"**Affected Components:** {', '.join(data['components'])}")
            if data.get('dependencies'):
                body_sections.append(f"**Dependencies:** {', '.join(data['dependencies'])}")
        
        # Add metadata section
        body_sections.append("\n## Metadata\n")
        body_sections.append(f"- **Priority:** {data.get('priority', 'medium')}")
        body_sections.append(f"- **Type:** {data.get('issue_type', 'feature')}")
        if data.get('estimated_hours'):
            body_sections.append(f"- **Estimated Effort:** {data['estimated_hours']} hours")
        
        # Combine all sections
        full_body = '\n'.join(body_sections)
        
        return GeneratedIssueContent(
            generated_title=data.get('title', f"Issue: {brief_description[:50]}"),
            generated_body=full_body,
            labels_to_apply=data.get('labels', []),
            priority=data.get('priority', 'medium'),
            issue_type=data.get('issue_type', 'feature'),
            estimated_hours=data.get('estimated_hours'),
            acceptance_criteria=data.get('acceptance_criteria', [])
        )
    
    def _parse_text_response(self, response: str, brief_description: str) -> GeneratedIssueContent:
        """Parse text response when JSON parsing fails.
        
        Args:
            response: Text response from LLM
            brief_description: Original description for fallback
            
        Returns:
            GeneratedIssueContent with extracted information
        """
        import re
        
        # Try to extract key information from text
        title_match = re.search(r'(?:TITLE|Title):\s*(.+?)(?:\n|$)', response)
        title = title_match.group(1).strip() if title_match else f"Issue: {brief_description[:50]}"
        
        # Extract priority if mentioned
        priority = "medium"
        if re.search(r'\b(critical|high priority|urgent)\b', response.lower()):
            priority = "high"
        elif re.search(r'\b(low priority|minor)\b', response.lower()):
            priority = "low"
            
        # Extract labels from common patterns
        labels = []
        label_match = re.search(r'(?:Labels?|Tags?):\s*(.+?)(?:\n|$)', response, re.IGNORECASE)
        if label_match:
            labels = [l.strip() for l in label_match.group(1).split(',')]
        
        # Use the response as the body if we can't parse it
        body = response if len(response) > 100 else f"""## Description
{brief_description}

## Generated Content
{response}

---
*Note: This issue was partially generated. Please review and edit as needed.*"""
        
        return GeneratedIssueContent(
            generated_title=title,
            generated_body=body,
            labels_to_apply=labels,
            priority=priority
        )
    
    def _create_fallback_content(self, brief_description: str, error: str) -> GeneratedIssueContent:
        """Create fallback content when generation fails.
        
        Args:
            brief_description: Original description
            error: Error message
            
        Returns:
            GeneratedIssueContent with fallback values
        """
        title = f"[Draft] {brief_description[:80]}{'...' if len(brief_description) > 80 else ''}"
        
        body = f"""## Description
{brief_description}

## Details
*This issue needs to be expanded with more details.*

### Suggested sections to add:
- Problem statement
- Current vs expected behavior  
- Acceptance criteria
- Technical approach
- Priority and effort estimation

---
*Note: Automatic generation failed ({error}). Please complete this issue manually.*"""
        
        return GeneratedIssueContent(
            generated_title=title,
            generated_body=body,
            labels_to_apply=["needs-details", "draft"],
            priority="medium"
        )
    
    def create_github_issue(self, 
                          content: GeneratedIssueContent,
                          repo_owner: str,
                          repo_name: str) -> Dict[str, Any]:
        """Create a GitHub issue from generated content.
        
        Args:
            content: Generated issue content
            repo_owner: Repository owner
            repo_name: Repository name
            
        Returns:
            Dict with issue details including URL
        """
        try:
            from src.config.settings import settings
            from src.integrations.github_client import GitHubClient
            
            github_token = settings.github.github_token.get_secret_value()
            
            # Check if we have a valid GitHub token
            if not github_token or github_token in ['', 'test_', None] or github_token.startswith('test_') or github_token.startswith('your_'):
                logger.warning("No valid GitHub token found.")
                return {
                    'success': False,
                    'error': 'GitHub token not configured. Please add GITHUB_TOKEN to your .env file'
                }
            
            # Create GitHub client and issue directly
            github_client = GitHubClient(token=github_token)
            
            # Format repo name as "owner/repo"
            full_repo_name = f"{repo_owner}/{repo_name}"
            
            # Create the issue using the client directly
            issue_result = github_client.create_issue(
                repo_name=full_repo_name,
                title=content.generated_title,
                body=content.generated_body,
                labels=content.labels_to_apply if content.labels_to_apply else None,
                assignees=None,
                milestone=None
            )
            
            # Return success result
            return {
                'success': True,
                'issue_url': issue_result.get('html_url', ''),
                'issue_number': issue_result.get('number', 0),
                'title': issue_result.get('title', content.generated_title)
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Failed to create GitHub issue: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"GitHub creation traceback:\n{traceback.format_exc()}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the issue generation workflow.
        
        Args:
            input_data: Dict containing:
                - brief_description: Brief issue description
                - platform: Target platform (github/jira/linear)
                - repo_owner: Repository owner (for GitHub)
                - repo_name: Repository name (for GitHub)
                - project_context: Optional project context
                
        Returns:
            Dict with generated content and creation result
        """
        brief_description = input_data.get('brief_description', '')
        platform = input_data.get('platform', 'github').lower()
        repo_owner = input_data.get('repo_owner', '')
        repo_name = input_data.get('repo_name', '')
        project_context = input_data.get('project_context', '')
        
        # Generate issue content
        content = self.generate_issue_content(
            brief_description=brief_description,
            platform=platform,
            repo_name=repo_name,
            project_context=project_context
        )
        
        # Create the actual issue if it's GitHub
        result = {
            'generated_content': {
                'title': content.generated_title,
                'body': content.generated_body,
                'labels': content.labels_to_apply,
                'priority': content.priority,
                'issue_type': getattr(content, 'issue_type', 'feature'),
                'estimated_hours': getattr(content, 'estimated_hours', None),
                'acceptance_criteria': getattr(content, 'acceptance_criteria', [])
            }
        }
        
        if platform == 'github' and repo_owner and repo_name:
            creation_result = self.create_github_issue(content, repo_owner, repo_name)
            result['creation_result'] = creation_result
        else:
            result['creation_result'] = {
                'success': False,
                'error': f'Issue creation for {platform} not yet implemented' if platform != 'github' else 'Missing repository information'
            }
        
        return result