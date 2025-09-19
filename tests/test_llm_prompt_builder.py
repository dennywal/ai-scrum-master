"""Tests for LLMPromptBuilder class."""

import pytest

from src.integrations.llm_prompt_builder import LLMPromptBuilder, PromptTemplate
from src.models.documents import TDDSections, PRDSections


class TestLLMPromptBuilder:
    """Test suite for LLMPromptBuilder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = LLMPromptBuilder()

    def test_initialization(self):
        """Test LLMPromptBuilder initialization."""
        assert self.builder.templates is not None
        assert len(self.builder.templates) > 0

    def test_build_task_extraction_prompt_tdd(self):
        """Test building task extraction prompt for TDD."""
        tdd_sections = TDDSections(
            overview="Build a user authentication system",
            test_cases=["User can login", "User can logout"],
            implementation_requirements=["Use JWT", "Implement rate limiting"],
            acceptance_criteria=["All tests pass", "Security audit complete"]
        )

        prompt = self.builder.build_task_extraction_prompt(
            document_type="TDD",
            sections=tdd_sections
        )

        assert "TDD" in prompt
        assert "user authentication system" in prompt
        assert "User can login" in prompt
        assert "JWT" in prompt
        assert "extract" in prompt.lower() or "identify" in prompt.lower()

    def test_build_task_extraction_prompt_prd(self):
        """Test building task extraction prompt for PRD."""
        prd_sections = PRDSections(
            executive_summary="E-commerce platform for SMBs",
            features=[
                {"name": "Shopping Cart", "requirements": ["Add items", "Remove items"]},
                {"name": "Payment", "requirements": ["Credit card", "PayPal"]}
            ],
            user_stories=["As a customer, I want to browse products"]
        )

        prompt = self.builder.build_task_extraction_prompt(
            document_type="PRD",
            sections=prd_sections
        )

        assert "PRD" in prompt
        assert "E-commerce platform" in prompt
        assert "Shopping Cart" in prompt
        assert "Payment" in prompt

    def test_build_priority_analysis_prompt(self):
        """Test building priority analysis prompt."""
        task_descriptions = [
            "Fix critical security vulnerability",
            "Add new feature for user preferences",
            "Update documentation"
        ]

        prompt = self.builder.build_priority_analysis_prompt(task_descriptions)

        assert "priorities" in prompt.lower()
        assert "security vulnerability" in prompt
        assert all(desc in prompt for desc in task_descriptions)

    def test_build_dependency_detection_prompt(self):
        """Test building dependency detection prompt."""
        tasks = [
            {"title": "Setup database", "description": "Initialize PostgreSQL"},
            {"title": "Create models", "description": "Define data models"},
            {"title": "Write tests", "description": "Unit tests for models"}
        ]

        prompt = self.builder.build_dependency_detection_prompt(tasks)

        assert "dependency" in prompt.lower() or "dependencies" in prompt.lower()
        assert "Setup database" in prompt
        assert "Create models" in prompt
        assert "relationship" in prompt.lower() or "depend" in prompt.lower()

    def test_build_issue_refinement_prompt(self):
        """Test building issue refinement prompt."""
        issue_data = {
            "title": "Implement user authentication",
            "body": "Add login functionality",
            "labels": ["feature", "backend"]
        }

        prompt = self.builder.build_issue_refinement_prompt(issue_data)

        assert "user authentication" in prompt
        assert "login functionality" in prompt
        assert "improve" in prompt.lower() or "refine" in prompt.lower() or "enhance" in prompt.lower()

    def test_build_acceptance_criteria_prompt(self):
        """Test building acceptance criteria generation prompt."""
        task_description = "Implement password reset functionality with email verification"

        prompt = self.builder.build_acceptance_criteria_prompt(task_description)

        assert "acceptance criteria" in prompt.lower()
        assert "password reset" in prompt
        assert "email verification" in prompt
        assert "testable" in prompt.lower() or "measurable" in prompt.lower()

    def test_build_technical_analysis_prompt(self):
        """Test building technical analysis prompt."""
        requirements = [
            "Must support 10,000 concurrent users",
            "Response time under 100ms",
            "99.9% uptime"
        ]

        prompt = self.builder.build_technical_analysis_prompt(requirements)

        assert "technical" in prompt.lower()
        assert "10,000 concurrent users" in prompt
        assert "100ms" in prompt
        assert "analysis" in prompt.lower() or "analyze" in prompt.lower()

    def test_get_system_prompt(self):
        """Test getting system prompt for different contexts."""
        contexts = ["task_extraction", "priority_analysis", "technical_review"]

        for context in contexts:
            system_prompt = self.builder.get_system_prompt(context)
            assert system_prompt is not None
            assert len(system_prompt) > 0
            # Check for relevant keywords
            assert any(word in system_prompt.lower() for word in ["expert", "assistant", "senior", "principal", "specialized"])

    def test_format_prompt_with_context(self):
        """Test formatting prompt with additional context."""
        base_prompt = "Extract tasks from this document"
        context = {
            "project": "E-commerce Platform",
            "team_size": 5,
            "timeline": "3 months"
        }

        formatted = self.builder.format_prompt_with_context(base_prompt, context)

        assert "Extract tasks" in formatted
        assert "E-commerce Platform" in formatted
        assert "5" in formatted
        assert "3 months" in formatted

    def test_build_prompt_with_examples(self):
        """Test building prompt with few-shot examples."""
        task = "Identify the main features"
        examples = [
            {"input": "Build a chat app", "output": "1. User authentication\n2. Real-time messaging"},
            {"input": "Create a blog", "output": "1. Post creation\n2. Comment system"}
        ]

        prompt = self.builder.build_prompt_with_examples(task, examples)

        assert "Identify the main features" in prompt
        assert "chat app" in prompt
        assert "User authentication" in prompt
        assert "blog" in prompt
        assert "Comment system" in prompt

    def test_build_json_schema_prompt(self):
        """Test building prompt for JSON schema output."""
        schema = {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "priority": {"type": "string"}
            }
        }

        prompt = self.builder.build_json_schema_prompt(
            instruction="Extract tasks",
            schema=schema
        )

        assert "JSON" in prompt
        assert "Extract tasks" in prompt
        assert '"type": "object"' in prompt or "properties" in prompt

    def test_custom_template_registration(self):
        """Test registering and using custom templates."""
        custom_template = PromptTemplate(
            name="custom_test",
            template="Custom prompt: {content}",
            variables=["content"]
        )

        self.builder.register_template(custom_template)
        
        prompt = self.builder.use_template(
            "custom_test",
            content="Test content"
        )

        assert prompt == "Custom prompt: Test content"

    def test_template_validation(self):
        """Test template variable validation."""
        template = PromptTemplate(
            name="test",
            template="Hello {name}, your task is {task}",
            variables=["name", "task"]
        )

        self.builder.register_template(template)

        # Should raise error if required variables missing
        with pytest.raises(ValueError):
            self.builder.use_template("test", name="Alice")  # Missing 'task' variable

    def test_build_batch_prompt(self):
        """Test building prompts for batch processing."""
        items = [
            "Task 1: Login system",
            "Task 2: Payment integration",
            "Task 3: Email notifications"
        ]

        prompt = self.builder.build_batch_prompt(
            instruction="Analyze these tasks",
            items=items
        )

        assert "Analyze these tasks" in prompt
        assert all(item in prompt for item in items)
        assert prompt.count("Task") >= 3

    def test_prompt_length_optimization(self):
        """Test prompt length optimization."""
        long_content = "A" * 10000  # Very long content

        optimized = self.builder.optimize_prompt_length(
            long_content,
            max_tokens=1000
        )

        # Should be shorter than original
        assert len(optimized) < len(long_content)
        # Should mention truncation or summarization
        assert "truncated" in optimized.lower() or "..." in optimized