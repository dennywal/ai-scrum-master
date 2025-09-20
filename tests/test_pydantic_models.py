"""Tests for Pydantic model validation and conversion methods."""

import pytest
from pydantic import ValidationError

from src.models.issues import IssueGenerationOutput, GeneratedIssueContent
from src.models.tasks import (
    TaskExtractionItem, 
    TaskExtractionOutput, 
    ExtractedTask,
    TaskBatch,
    TaskType,
    Priority,
    EffortSize
)


class TestIssueGenerationOutput:
    """Test the IssueGenerationOutput Pydantic model."""
    
    def test_valid_issue_creation(self):
        """Test creating a valid issue with all fields."""
        issue = IssueGenerationOutput(
            title="Implement user authentication",
            body="## Description\nAdd OAuth2 authentication to the application",
            acceptance_criteria=["Users can login", "Sessions are secure"],
            priority="high",
            issue_type="feature",
            labels=["authentication", "security"],
            estimated_hours=16.0,
            components=["auth-module", "api"],
            dependencies=["database-setup"],
            technical_approach="Use JWT tokens with refresh mechanism"
        )
        
        assert issue.title == "Implement user authentication"
        assert issue.priority == "high"
        assert len(issue.acceptance_criteria) == 2
        assert "authentication" in issue.labels
        assert issue.estimated_hours == 16.0
    
    def test_minimal_issue_creation(self):
        """Test creating an issue with only required fields."""
        issue = IssueGenerationOutput(
            title="Fix bug",
            body="Fix the login bug"
        )
        
        assert issue.title == "Fix bug"
        assert issue.body == "Fix the login bug"
        assert issue.priority == "medium"  # Default
        assert issue.issue_type == "feature"  # Default
        assert issue.labels == []
        assert issue.estimated_hours is None
    
    def test_title_validation(self):
        """Test title validation rules."""
        # Title too short
        with pytest.raises(ValidationError) as exc_info:
            IssueGenerationOutput(
                title="",
                body="Some body content"
            )
        assert "at least 1 character" in str(exc_info.value).lower()
        
        # Title with only one word should fail custom validation
        with pytest.raises(ValidationError) as exc_info:
            IssueGenerationOutput(
                title="Bug",
                body="Some body content"
            )
        assert "at least 2 words" in str(exc_info.value)
        
        # Title too long
        with pytest.raises(ValidationError) as exc_info:
            IssueGenerationOutput(
                title="x" * 101,  # Max is 100
                body="Some body content"
            )
        assert "at most 100 character" in str(exc_info.value).lower()
    
    def test_priority_validation(self):
        """Test priority field validation."""
        # Valid priorities
        for priority in ["critical", "high", "medium", "low"]:
            issue = IssueGenerationOutput(
                title="Test issue",
                body="Test body content that is long enough",
                priority=priority
            )
            assert issue.priority == priority
        
        # Invalid priority
        with pytest.raises(ValidationError) as exc_info:
            IssueGenerationOutput(
                title="Test issue",
                body="Test body content that is long enough",
                priority="urgent"  # Not in pattern
            )
        assert "string should match pattern" in str(exc_info.value).lower()
    
    def test_issue_type_validation(self):
        """Test issue type field validation."""
        # Valid types
        for issue_type in ["bug", "feature", "enhancement", "task", "documentation"]:
            issue = IssueGenerationOutput(
                title="Test issue",
                body="Test body content that is long enough",
                issue_type=issue_type
            )
            assert issue.issue_type == issue_type
        
        # Invalid type
        with pytest.raises(ValidationError) as exc_info:
            IssueGenerationOutput(
                title="Test issue",
                body="Test body content that is long enough",
                issue_type="story"  # Not in pattern
            )
        assert "string should match pattern" in str(exc_info.value).lower()
    
    def test_label_cleaning(self):
        """Test that labels are cleaned and normalized."""
        issue = IssueGenerationOutput(
            title="Test issue",
            body="Test body content that is long enough for validation",
            labels=["  Bug Fix  ", "NEW FEATURE", "bug fix", "new-feature"]
        )
        
        # Labels should be lowercased, trimmed, spaces replaced with hyphens, and deduplicated
        assert "bug-fix" in issue.labels
        assert "new-feature" in issue.labels
        assert len(issue.labels) == 2  # Duplicates removed
    
    def test_estimated_hours_validation(self):
        """Test estimated hours validation."""
        # Valid range
        issue = IssueGenerationOutput(
            title="Test issue",
            body="Test body content that is long enough",
            estimated_hours=8.5
        )
        assert issue.estimated_hours == 8.5
        
        # Too low
        with pytest.raises(ValidationError) as exc_info:
            IssueGenerationOutput(
                title="Test issue",
                body="Test body content that is long enough",
                estimated_hours=0.25  # Min is 0.5
            )
        assert "greater than or equal to 0.5" in str(exc_info.value).lower()
        
        # Too high
        with pytest.raises(ValidationError) as exc_info:
            IssueGenerationOutput(
                title="Test issue",
                body="Test body content that is long enough",
                estimated_hours=200  # Max is 160
            )
        assert "less than or equal to 160" in str(exc_info.value).lower()
    
    def test_to_generated_content_conversion(self):
        """Test conversion to GeneratedIssueContent."""
        issue = IssueGenerationOutput(
            title="Implement caching",
            body="Add Redis caching layer",
            acceptance_criteria=["Cache hit rate > 80%", "TTL configuration"],
            priority="high",
            issue_type="enhancement",
            labels=["performance", "backend"],
            estimated_hours=24.0,
            components=["cache", "api"],
            dependencies=["redis-setup"],
            technical_approach="Use Redis with cache-aside pattern"
        )
        
        content = issue.to_generated_content()
        
        assert isinstance(content, GeneratedIssueContent)
        assert content.generated_title == "Implement caching"
        assert "Add Redis caching layer" in content.generated_body
        assert "## Acceptance Criteria" in content.generated_body
        assert "- [ ] Cache hit rate > 80%" in content.generated_body
        assert "- [ ] TTL configuration" in content.generated_body
        assert "## Technical Details" in content.generated_body
        assert "**Affected Components:** cache, api" in content.generated_body
        assert "**Dependencies:** redis-setup" in content.generated_body
        assert "**Suggested Approach:**" in content.generated_body
        assert "Redis with cache-aside pattern" in content.generated_body
        assert "## Metadata" in content.generated_body
        assert "**Priority:** high" in content.generated_body
        assert "**Type:** enhancement" in content.generated_body
        assert "**Estimated Effort:** 24.0 hours" in content.generated_body
        assert set(content.labels_to_apply) == {"performance", "backend"}
        assert content.priority == "high"
        assert content.issue_type == "enhancement"
        assert content.estimated_hours == 24.0
        assert content.acceptance_criteria == ["Cache hit rate > 80%", "TTL configuration"]


class TestTaskExtractionModels:
    """Test the TaskExtractionItem and TaskExtractionOutput models."""
    
    def test_valid_task_item_creation(self):
        """Test creating a valid task item."""
        task = TaskExtractionItem(
            title="Setup database migrations",
            description="Create migration scripts for user tables",
            task_type="infrastructure",
            priority="high",
            dependencies=["database-setup"],
            acceptance_criteria=["Migrations run without errors", "Rollback works"],
            technical_requirements=["PostgreSQL 14+", "Alembic"],
            estimated_effort="medium",
            labels=["database", "setup"]
        )
        
        assert task.title == "Setup database migrations"
        assert task.task_type == "infrastructure"
        assert task.priority == "high"
        assert len(task.dependencies) == 1
        assert len(task.acceptance_criteria) == 2
    
    def test_task_item_validation(self):
        """Test task item field validation."""
        # Title too short
        with pytest.raises(ValidationError) as exc_info:
            TaskExtractionItem(
                title="DB",  # Min is 3 chars
                description="Setup database"
            )
        assert "at least 3 character" in str(exc_info.value).lower()
        
        # Invalid task type
        with pytest.raises(ValidationError) as exc_info:
            TaskExtractionItem(
                title="Setup database",
                description="Setup database",
                task_type="story"  # Not in pattern
            )
        assert "string should match pattern" in str(exc_info.value).lower()
        
        # Invalid effort size
        with pytest.raises(ValidationError) as exc_info:
            TaskExtractionItem(
                title="Setup database",
                description="Setup database",
                estimated_effort="huge"  # Not in pattern
            )
        assert "string should match pattern" in str(exc_info.value).lower()
    
    def test_task_item_to_extracted_task(self):
        """Test conversion from TaskExtractionItem to ExtractedTask."""
        item = TaskExtractionItem(
            title="Implement API endpoint",
            description="Create REST endpoint for user management",
            task_type="feature",
            priority="high",
            dependencies=["auth-setup"],
            acceptance_criteria=["Returns 200 on success", "Validates input"],
            technical_requirements=["FastAPI", "Pydantic"],
            estimated_effort="large",
            labels=["api", "backend"]
        )
        
        task = item.to_extracted_task(source_document="PRD-001")
        
        assert isinstance(task, ExtractedTask)
        assert task.title == "Implement API endpoint"
        assert task.description == "Create REST endpoint for user management"
        assert task.task_type == TaskType.FEATURE
        assert task.priority == Priority.HIGH
        assert task.dependencies == ["auth-setup"]
        assert task.acceptance_criteria == ["Returns 200 on success", "Validates input"]
        assert task.technical_requirements == ["FastAPI", "Pydantic"]
        assert task.estimated_effort == EffortSize.LARGE
        assert task.labels == ["api", "backend"]
        assert task.source_document == "PRD-001"
    
    def test_task_extraction_output(self):
        """Test TaskExtractionOutput model."""
        tasks = [
            TaskExtractionItem(
                title="Task one",
                description="First task description",
                task_type="feature",
                priority="high"
            ),
            TaskExtractionItem(
                title="Task two",
                description="Second task description",
                task_type="test",
                priority="medium"
            )
        ]
        
        output = TaskExtractionOutput(
            tasks=tasks,
            summary="Extracted 2 tasks from document",
            total_estimated_effort=16.0
        )
        
        assert len(output.tasks) == 2
        assert output.summary == "Extracted 2 tasks from document"
        assert output.total_estimated_effort == 16.0
    
    def test_task_extraction_unique_titles(self):
        """Test that duplicate task titles are made unique."""
        tasks = [
            TaskExtractionItem(
                title="Setup database",
                description="First database task",
                task_type="infrastructure"
            ),
            TaskExtractionItem(
                title="Setup database",  # Duplicate title
                description="Second database task",
                task_type="infrastructure"
            ),
            TaskExtractionItem(
                title="Setup database",  # Another duplicate
                description="Third database task",
                task_type="infrastructure"
            )
        ]
        
        output = TaskExtractionOutput(tasks=tasks)
        
        # Validator should make titles unique
        titles = [task.title for task in output.tasks]
        assert titles[0] == "Setup database"
        assert titles[1] == "Setup database (2)"
        assert titles[2] == "Setup database (3)"
    
    def test_task_extraction_to_batch(self):
        """Test conversion from TaskExtractionOutput to TaskBatch."""
        tasks = [
            TaskExtractionItem(
                title="API implementation",
                description="Implement user API",
                task_type="feature"
            ),
            TaskExtractionItem(
                title="API tests",
                description="Write API tests",
                task_type="test",
                dependencies=["API implementation"]
            )
        ]
        
        output = TaskExtractionOutput(
            tasks=tasks,
            total_estimated_effort=24.0
        )
        
        batch = output.to_task_batch("TDD-002")
        
        assert isinstance(batch, TaskBatch)
        assert len(batch.tasks) == 2
        assert batch.source == "TDD-002"
        assert batch.tasks[0].title == "API implementation"
        assert batch.tasks[1].dependencies == ["API implementation"]
    
    def test_task_extraction_empty_tasks(self):
        """Test that TaskExtractionOutput requires at least one task."""
        with pytest.raises(ValidationError) as exc_info:
            TaskExtractionOutput(tasks=[])
        assert "at least 1 item" in str(exc_info.value).lower()


class TestModelIntegration:
    """Test integration between different models."""
    
    def test_full_issue_generation_flow(self):
        """Test complete flow from IssueGenerationOutput to GitHubIssueTemplate."""
        # Create issue using Pydantic model
        issue_output = IssueGenerationOutput(
            title="Add monitoring dashboard",
            body="Implement Grafana dashboard for system metrics",
            acceptance_criteria=[
                "Shows CPU and memory usage",
                "Displays request latency",
                "Has alerting configured"
            ],
            priority="high",
            issue_type="feature",
            labels=["monitoring", "observability"],
            estimated_hours=40.0,
            components=["monitoring", "infrastructure"],
            dependencies=["prometheus-setup"],
            technical_approach="Use Grafana with Prometheus data source"
        )
        
        # Convert to GeneratedIssueContent
        content = issue_output.to_generated_content()
        
        # Verify the conversion maintains all data
        assert content.generated_title == issue_output.title
        assert all(ac in content.generated_body for ac in issue_output.acceptance_criteria)
        assert content.priority == issue_output.priority
        assert content.issue_type == issue_output.issue_type
        assert content.labels_to_apply == issue_output.labels
        assert content.estimated_hours == issue_output.estimated_hours
    
    def test_full_task_extraction_flow(self):
        """Test complete flow from TaskExtractionOutput to ExtractedTask."""
        # Create tasks using Pydantic models
        extraction_output = TaskExtractionOutput(
            tasks=[
                TaskExtractionItem(
                    title="Design authentication flow",
                    description="Create detailed auth flow diagrams",
                    task_type="research",
                    priority="high",
                    estimated_effort="small",
                    labels=["design", "auth"]
                ),
                TaskExtractionItem(
                    title="Implement auth backend",
                    description="Build authentication service",
                    task_type="feature",
                    priority="critical",
                    dependencies=["Design authentication flow"],
                    estimated_effort="large",
                    labels=["backend", "auth"]
                )
            ],
            total_estimated_effort=48.0
        )
        
        # Convert to TaskBatch
        batch = extraction_output.to_task_batch("PRD-003")
        
        # Verify the conversion
        assert len(batch.tasks) == 2
        assert batch.source == "PRD-003"
        
        # Check first task
        task1 = batch.tasks[0]
        assert task1.title == "Design authentication flow"
        assert task1.task_type == TaskType.RESEARCH
        assert task1.priority == Priority.HIGH
        assert task1.estimated_effort == EffortSize.SMALL
        
        # Check second task with dependencies
        task2 = batch.tasks[1]
        assert task2.title == "Implement auth backend"
        assert task2.task_type == TaskType.FEATURE
        assert task2.priority == Priority.CRITICAL
        assert task2.dependencies == ["Design authentication flow"]
        assert task2.estimated_effort == EffortSize.LARGE