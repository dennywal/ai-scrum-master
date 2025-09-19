"""Tests for IssueMapper class."""

import pytest

from src.agents.issue_mapper import IssueMapper
from src.models.tasks import ExtractedTask, Priority, TaskType, EffortSize


class TestIssueMapper:
    """Test suite for IssueMapper."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = IssueMapper()

    def test_map_single_task_to_issue(self):
        """Test mapping a single task to GitHub issue format."""
        task = ExtractedTask(
            title="Implement user authentication",
            description="Add JWT-based authentication system",
            task_type=TaskType.FEATURE,
            priority=Priority.HIGH,
            acceptance_criteria=[
                "Users can register with email",
                "Users can login with credentials",
                "JWT tokens are generated and validated"
            ],
            labels=["backend", "security"],
            estimated_effort=EffortSize.MEDIUM
        )

        issue = self.mapper.map_task_to_issue(task)

        assert issue["title"] == "[Feature] Implement user authentication"
        assert "JWT-based authentication system" in issue["body"]
        assert "backend" in issue["labels"]
        assert "security" in issue["labels"]
        assert "feature" in issue["labels"]
        assert "priority:high" in issue["labels"]
        assert "effort:medium" in issue["labels"]

    def test_map_tasks_batch(self):
        """Test mapping multiple tasks to issues."""
        tasks = [
            ExtractedTask(
                title="Setup database",
                description="Initialize PostgreSQL database",
                task_type=TaskType.INFRASTRUCTURE,
                priority=Priority.CRITICAL
            ),
            ExtractedTask(
                title="Create user model",
                description="Define user data model",
                task_type=TaskType.FEATURE,
                priority=Priority.HIGH,
                dependencies=["Setup database"]
            ),
            ExtractedTask(
                title="Write user tests",
                description="Unit tests for user model",
                task_type=TaskType.TEST,
                priority=Priority.MEDIUM,
                dependencies=["Create user model"]
            )
        ]

        issues = self.mapper.map_tasks_to_issues(tasks)

        assert len(issues) == 3
        
        # Check first issue
        assert issues[0]["title"] == "[Infra] Setup database"
        assert "priority:critical" in issues[0]["labels"]
        
        # Check dependencies are mentioned
        assert "Setup database" in issues[1]["body"]
        assert "Create user model" in issues[2]["body"]

    def test_add_milestone_and_assignees(self):
        """Test adding milestone and assignees to issues."""
        task = ExtractedTask(
            title="Fix login bug",
            description="Login fails with special characters",
            task_type=TaskType.BUG,
            priority=Priority.HIGH,
            milestone="v1.0.0",
            assignees=["alice", "bob"]
        )

        issue = self.mapper.map_task_to_issue(task)

        assert issue["milestone"] == "v1.0.0"
        assert issue["assignees"] == ["alice", "bob"]

    def test_format_acceptance_criteria_as_checklist(self):
        """Test acceptance criteria are formatted as checklist."""
        task = ExtractedTask(
            title="Add search feature",
            description="Implement full-text search",
            acceptance_criteria=[
                "Search by title",
                "Search by content",
                "Filter by date"
            ]
        )

        issue = self.mapper.map_task_to_issue(task)

        assert "- [ ] Search by title" in issue["body"]
        assert "- [ ] Search by content" in issue["body"]
        assert "- [ ] Filter by date" in issue["body"]

    def test_preserve_technical_requirements(self):
        """Test technical requirements are preserved in issue body."""
        task = ExtractedTask(
            title="API endpoint",
            description="REST API for user management",
            technical_requirements=[
                "Use FastAPI framework",
                "Implement rate limiting",
                "Add OpenAPI documentation"
            ]
        )

        issue = self.mapper.map_task_to_issue(task)

        assert "Technical Requirements" in issue["body"]
        assert "FastAPI framework" in issue["body"]
        assert "rate limiting" in issue["body"]
        assert "OpenAPI documentation" in issue["body"]

    def test_dependency_linking(self):
        """Test dependencies are properly linked in issue body."""
        task = ExtractedTask(
            title="Deploy application",
            description="Deploy to production",
            dependencies=["Complete testing", "Security audit", "Performance optimization"],
            blocks=["Release v1.0", "Marketing launch"]
        )

        issue = self.mapper.map_task_to_issue(task)

        assert "Dependencies" in issue["body"]
        assert "Complete testing" in issue["body"]
        assert "Security audit" in issue["body"]
        assert "Performance optimization" in issue["body"]
        
        assert "Blocks" in issue["body"]
        assert "Release v1.0" in issue["body"]
        assert "Marketing launch" in issue["body"]

    def test_empty_task_list(self):
        """Test handling empty task list."""
        issues = self.mapper.map_tasks_to_issues([])
        assert issues == []

    def test_task_type_prefix_mapping(self):
        """Test correct prefix for each task type."""
        test_cases = [
            (TaskType.FEATURE, "[Feature]"),
            (TaskType.BUG, "[Bug]"),
            (TaskType.TEST, "[Test]"),
            (TaskType.DOCUMENTATION, "[Docs]"),
            (TaskType.REFACTOR, "[Refactor]"),
            (TaskType.RESEARCH, "[Research]"),
            (TaskType.INFRASTRUCTURE, "[Infra]")
        ]

        for task_type, expected_prefix in test_cases:
            task = ExtractedTask(
                title="Test task",
                description="Test description",
                task_type=task_type
            )
            issue = self.mapper.map_task_to_issue(task)
            assert issue["title"].startswith(expected_prefix)

    def test_priority_label_mapping(self):
        """Test correct priority labels."""
        test_cases = [
            (Priority.CRITICAL, "priority:critical"),
            (Priority.HIGH, "priority:high"),
            (Priority.MEDIUM, "priority:medium"),
            (Priority.LOW, "priority:low")
        ]

        for priority, expected_label in test_cases:
            task = ExtractedTask(
                title="Test task",
                description="Test description",
                priority=priority
            )
            issue = self.mapper.map_task_to_issue(task)
            assert expected_label in issue["labels"]

    def test_effort_size_label_mapping(self):
        """Test effort size labels."""
        test_cases = [
            (EffortSize.SMALL, "effort:small"),
            (EffortSize.MEDIUM, "effort:medium"),
            (EffortSize.LARGE, "effort:large"),
            (EffortSize.EXTRA_LARGE, "effort:extra_large")
        ]

        for effort, expected_label in test_cases:
            task = ExtractedTask(
                title="Test task",
                description="Test description",
                estimated_effort=effort
            )
            issue = self.mapper.map_task_to_issue(task)
            assert expected_label in issue["labels"]

    def test_source_document_metadata(self):
        """Test source document metadata is included."""
        task = ExtractedTask(
            title="Implement feature",
            description="Feature from TDD",
            source_document="TDD",
            source_section="Implementation Requirements"
        )

        issue = self.mapper.map_task_to_issue(task)

        assert "Source:" in issue["body"]
        assert "TDD" in issue["body"]

    def test_batch_processing_preserves_order(self):
        """Test batch processing maintains task order."""
        tasks = [
            ExtractedTask(title=f"Task {i}", description=f"Description {i}")
            for i in range(10)
        ]

        issues = self.mapper.map_tasks_to_issues(tasks)

        assert len(issues) == 10
        for i, issue in enumerate(issues):
            assert f"Task {i}" in issue["title"]

    def test_custom_labels_preserved(self):
        """Test custom labels are preserved along with generated ones."""
        task = ExtractedTask(
            title="Custom task",
            description="Task with custom labels",
            labels=["urgent", "needs-review", "api"],
            task_type=TaskType.FEATURE,
            priority=Priority.HIGH
        )

        issue = self.mapper.map_task_to_issue(task)

        # Custom labels
        assert "urgent" in issue["labels"]
        assert "needs-review" in issue["labels"]
        assert "api" in issue["labels"]
        
        # Generated labels
        assert "feature" in issue["labels"]
        assert "priority:high" in issue["labels"]

    def test_no_duplicate_labels(self):
        """Test that duplicate labels are removed."""
        task = ExtractedTask(
            title="Task with duplicate labels",
            description="Test deduplication",
            labels=["feature", "backend", "feature", "backend"],
            task_type=TaskType.FEATURE
        )

        issue = self.mapper.map_task_to_issue(task)

        # Count occurrences of 'feature' label
        feature_count = issue["labels"].count("feature")
        backend_count = issue["labels"].count("backend")
        
        assert feature_count == 1
        assert backend_count == 1