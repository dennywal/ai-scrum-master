"""Prompt builder for LLM interactions."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Type, TypeVar

from pydantic import BaseModel
from src.models.documents import TDDSections, PRDSections

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)


logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Template for prompts."""
    name: str
    template: str
    variables: list[str]


class LLMPromptBuilder:
    """Builds optimized prompts for LLM interactions."""

    def __init__(self):
        """Initialize prompt builder."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.templates: dict[str, PromptTemplate] = self._initialize_templates()

    def _initialize_templates(self) -> dict[str, PromptTemplate]:
        """Initialize default prompt templates."""
        return {
            "task_extraction": PromptTemplate(
                name="task_extraction",
                template="""Analyze the following {document_type} document and extract actionable tasks.

Document Content:
{content}

Please identify and list all tasks that need to be completed. For each task, include:
- Title: Brief, descriptive title
- Description: Detailed description
- Type: (feature/bug/test/documentation/refactor/research/infrastructure)
- Priority suggestion: (critical/high/medium/low)
- Dependencies: Other tasks this depends on
- Acceptance criteria: Testable criteria for completion

Format your response as a structured list.""",
                variables=["document_type", "content"]
            ),
            
            "priority_analysis": PromptTemplate(
                name="priority_analysis",
                template="""Analyze the following tasks and assign appropriate priorities.

Tasks:
{tasks}

Consider these factors:
- Business impact
- Technical complexity
- Dependencies
- Security implications
- User experience impact

Assign priorities (critical/high/medium/low) and explain your reasoning.""",
                variables=["tasks"]
            ),
            
            "dependency_detection": PromptTemplate(
                name="dependency_detection",
                template="""Analyze the following tasks and identify dependencies between them.

Tasks:
{tasks}

Identify which tasks depend on others and create a dependency graph.
Consider:
- Technical dependencies (what must be built first)
- Logical dependencies (what makes sense to do in order)
- Resource dependencies (shared components or data)

List all dependencies in the format: "Task A depends on Task B" """,
                variables=["tasks"]
            )
        }

    def build_task_extraction_prompt(self, 
                                    document_type: str,
                                    sections: TDDSections | PRDSections) -> str:
        """Build prompt for task extraction.
        
        Args:
            document_type: Type of document (TDD/PRD)
            sections: Document sections
            
        Returns:
            Formatted prompt
        """
        content_parts = []
        
        if isinstance(sections, TDDSections):
            if sections.overview:
                content_parts.append(f"Overview:\n{sections.overview}\n")
            if sections.test_cases:
                content_parts.append(f"Test Cases:\n" + "\n".join(f"- {tc}" for tc in sections.test_cases) + "\n")
            if sections.implementation_requirements:
                content_parts.append(f"Implementation Requirements:\n" + "\n".join(f"- {req}" for req in sections.implementation_requirements) + "\n")
            if sections.acceptance_criteria:
                content_parts.append(f"Acceptance Criteria:\n" + "\n".join(f"- {ac}" for ac in sections.acceptance_criteria) + "\n")
                
        elif isinstance(sections, PRDSections):
            if sections.executive_summary:
                content_parts.append(f"Executive Summary:\n{sections.executive_summary}\n")
            if sections.features:
                content_parts.append("Features:\n")
                for feature in sections.features:
                    content_parts.append(f"- {feature['name']}")
                    if feature.get('requirements'):
                        for req in feature['requirements']:
                            content_parts.append(f"  - {req}")
                content_parts.append("")
            if sections.user_stories:
                content_parts.append(f"User Stories:\n" + "\n".join(f"- {story}" for story in sections.user_stories) + "\n")
        
        content = "\n".join(content_parts)
        
        return self.use_template(
            "task_extraction",
            document_type=document_type,
            content=content
        )

    def build_priority_analysis_prompt(self, task_descriptions: list[str]) -> str:
        """Build prompt for priority analysis.
        
        Args:
            task_descriptions: List of task descriptions
            
        Returns:
            Formatted prompt
        """
        tasks_text = "\n".join(f"{i+1}. {desc}" for i, desc in enumerate(task_descriptions))
        
        return self.use_template(
            "priority_analysis",
            tasks=tasks_text
        )

    def build_dependency_detection_prompt(self, tasks: list[dict[str, str]]) -> str:
        """Build prompt for dependency detection.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Formatted prompt
        """
        tasks_text = "\n".join(
            f"- {task['title']}: {task['description']}" 
            for task in tasks
        )
        
        return self.use_template(
            "dependency_detection",
            tasks=tasks_text
        )

    def build_issue_refinement_prompt(self, issue_data: dict[str, Any]) -> str:
        """Build prompt for refining GitHub issue content.
        
        Args:
            issue_data: Issue data dictionary
            
        Returns:
            Formatted prompt
        """
        return f"""Please improve and refine the following GitHub issue:

Title: {issue_data.get('title', 'No title')}
Body: {issue_data.get('body', 'No description')}
Labels: {', '.join(issue_data.get('labels', []))}

Enhance the issue by:
1. Making the title more descriptive and actionable
2. Adding clear acceptance criteria
3. Including implementation hints if applicable
4. Ensuring the description is comprehensive
5. Adding relevant technical details

Provide the improved version."""

    def build_acceptance_criteria_prompt(self, task_description: str) -> str:
        """Build prompt for generating acceptance criteria.
        
        Args:
            task_description: Task description
            
        Returns:
            Formatted prompt
        """
        return f"""Generate clear, testable acceptance criteria for the following task:

Task: {task_description}

Create acceptance criteria that:
- Are specific and measurable
- Can be tested/verified
- Cover both functional and non-functional requirements
- Include edge cases
- Are written from the user's perspective

Format as a bulleted list of criteria."""

    def build_technical_analysis_prompt(self, requirements: list[str]) -> str:
        """Build prompt for technical analysis.
        
        Args:
            requirements: List of technical requirements
            
        Returns:
            Formatted prompt
        """
        req_text = "\n".join(f"- {req}" for req in requirements)
        
        return f"""Perform a technical analysis of the following requirements:

Requirements:
{req_text}

Provide analysis including:
1. Technical feasibility
2. Potential challenges
3. Recommended technologies/approaches
4. Performance considerations
5. Security implications
6. Estimated complexity

Structure your analysis clearly."""

    def get_system_prompt(self, context: str) -> str:
        """Get system prompt for specific context.
        
        Args:
            context: Context identifier
            
        Returns:
            System prompt
        """
        prompts = {
            "task_extraction": "You are an expert software project manager skilled at breaking down requirements into actionable tasks.",
            "priority_analysis": "You are a senior technical lead experienced in prioritizing software development tasks based on business value and technical dependencies.",
            "technical_review": "You are a principal software architect with deep expertise in system design and technical requirements analysis.",
            "default": "You are a helpful AI assistant specialized in software development and project management."
        }
        
        return prompts.get(context, prompts["default"])

    def format_prompt_with_context(self, 
                                  base_prompt: str,
                                  context: dict[str, Any]) -> str:
        """Format prompt with additional context.
        
        Args:
            base_prompt: Base prompt text
            context: Context dictionary
            
        Returns:
            Formatted prompt
        """
        context_parts = [base_prompt, "\nContext:"]
        for key, value in context.items():
            context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts)

    def build_prompt_with_examples(self,
                                  task: str,
                                  examples: list[dict[str, str]]) -> str:
        """Build prompt with few-shot examples.
        
        Args:
            task: Task description
            examples: List of input/output examples
            
        Returns:
            Formatted prompt
        """
        prompt_parts = [task, "\nExamples:"]
        
        for i, example in enumerate(examples, 1):
            prompt_parts.append(f"\nExample {i}:")
            prompt_parts.append(f"Input: {example['input']}")
            prompt_parts.append(f"Output: {example['output']}")
        
        prompt_parts.append("\nNow, complete the task:")
        
        return "\n".join(prompt_parts)

    def build_json_schema_prompt(self,
                                instruction: str,
                                schema: dict[str, Any]) -> str:
        """Build prompt for JSON schema output.
        
        Args:
            instruction: Task instruction
            schema: JSON schema
            
        Returns:
            Formatted prompt
        """
        return f"""{instruction}

Respond with valid JSON that matches this schema:
{json.dumps(schema, indent=2)}

Ensure your response is properly formatted JSON."""

    def register_template(self, template: PromptTemplate) -> None:
        """Register a custom template.
        
        Args:
            template: Template to register
        """
        self.templates[template.name] = template
        self.logger.info(f"Registered template: {template.name}")

    def use_template(self, template_name: str, **kwargs) -> str:
        """Use a registered template.
        
        Args:
            template_name: Template name
            **kwargs: Template variables
            
        Returns:
            Formatted prompt
            
        Raises:
            ValueError: If template not found or missing variables
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        
        # Check all required variables are provided
        missing = set(template.variables) - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        return template.template.format(**kwargs)

    def build_batch_prompt(self,
                         instruction: str,
                         items: list[str]) -> str:
        """Build prompt for batch processing.
        
        Args:
            instruction: Processing instruction
            items: List of items to process
            
        Returns:
            Formatted prompt
        """
        items_text = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
        
        return f"""{instruction}

Items to process:
{items_text}

Process each item and provide results."""

    def optimize_prompt_length(self,
                              content: str,
                              max_tokens: int = 2000) -> str:
        """Optimize prompt length to fit token limits.
        
        Args:
            content: Original content
            max_tokens: Maximum token count
            
        Returns:
            Optimized content
        """
        # Rough estimation: 4 chars per token
        max_chars = max_tokens * 4
        
        if len(content) <= max_chars:
            return content
        
        # Truncate with indicator
        truncated = content[:max_chars - 100]
        return f"{truncated}... [Content truncated to fit token limit]"

    def build_pydantic_prompt(self,
                            instruction: str,
                            model_class: Type[T],
                            context: dict[str, Any] | None = None) -> str:
        """Build prompt optimized for Pydantic model output.
        
        Args:
            instruction: Main instruction/task
            model_class: Pydantic model class for output
            context: Optional context dictionary
            
        Returns:
            Formatted prompt
        """
        prompt_parts = [instruction]
        
        if context:
            prompt_parts.append("\nContext:")
            for key, value in context.items():
                prompt_parts.append(f"- {key}: {value}")
        
        # Add field descriptions from the model
        if hasattr(model_class, 'model_fields'):
            prompt_parts.append("\nPlease provide the following information:")
            for field_name, field_info in model_class.model_fields.items():
                if field_info.description:
                    prompt_parts.append(f"- {field_name}: {field_info.description}")
        
        return "\n".join(prompt_parts)

    def build_task_extraction_pydantic_prompt(self,
                                             document_type: str,
                                             sections: TDDSections | PRDSections) -> str:
        """Build prompt for task extraction using Pydantic models.
        
        Args:
            document_type: Type of document (TDD/PRD)
            sections: Document sections
            
        Returns:
            Formatted prompt
        """
        content_parts = []
        
        if isinstance(sections, TDDSections):
            if sections.overview:
                content_parts.append(f"Overview:\n{sections.overview}\n")
            if sections.test_cases:
                content_parts.append(f"Design Elements:\n" + "\n".join(f"- {tc}" for tc in sections.test_cases) + "\n")
            if sections.implementation_requirements:
                content_parts.append(f"Implementation Requirements:\n" + "\n".join(f"- {req}" for req in sections.implementation_requirements) + "\n")
            if sections.acceptance_criteria:
                content_parts.append(f"Acceptance Criteria:\n" + "\n".join(f"- {ac}" for ac in sections.acceptance_criteria) + "\n")
                
        elif isinstance(sections, PRDSections):
            if sections.executive_summary:
                content_parts.append(f"Executive Summary:\n{sections.executive_summary}\n")
            if sections.features:
                content_parts.append("Features:\n")
                for feature in sections.features:
                    content_parts.append(f"- {feature['name']}")
                    if feature.get('requirements'):
                        for req in feature['requirements']:
                            content_parts.append(f"  - {req}")
                content_parts.append("")
            if sections.user_stories:
                content_parts.append(f"User Stories:\n" + "\n".join(f"- {story}" for story in sections.user_stories) + "\n")
        
        content = "\n".join(content_parts)
        
        return f"""Analyze the following {document_type} document and extract all actionable tasks.

{content}

Extract comprehensive tasks with:
- Clear, actionable titles
- Detailed descriptions
- Appropriate task types and priorities
- Dependencies between tasks
- Testable acceptance criteria
- Technical requirements where applicable

Ensure each task is complete and actionable."""

    def get_pydantic_system_prompt(self, context: str, model_class: Type[T] | None = None) -> str:
        """Get system prompt optimized for Pydantic model generation.
        
        Args:
            context: Context identifier
            model_class: Optional Pydantic model class
            
        Returns:
            System prompt
        """
        base_prompts = {
            "task_extraction": "You are an expert software project manager skilled at breaking down requirements into actionable, well-structured tasks.",
            "issue_generation": "You are an expert software project manager creating detailed, actionable issues with comprehensive information.",
            "priority_analysis": "You are a senior technical lead experienced in prioritizing tasks based on business value and technical dependencies.",
            "technical_review": "You are a principal software architect with expertise in system design and technical analysis.",
            "default": "You are a helpful AI assistant specialized in software development and project management."
        }
        
        prompt = base_prompts.get(context, base_prompts["default"])
        
        if model_class:
            prompt += f" Always structure your responses according to the provided format specifications."
        
        return prompt