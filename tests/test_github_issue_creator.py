"""Tests for GitHubIssueCreator class."""

from unittest.mock import Mock, patch, MagicMock
import pytest

from src.integrations.github_issue_creator import GitHubIssueCreator
from src.models.tasks import ExtractedTask, Priority, TaskType, TaskBatch


class TestGitHubIssueCreator:
    """Test suite for GitHubIssueCreator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.creator = GitHubIssueCreator(github_client=self.mock_client)

    def test_initialization(self):
        """Test GitHubIssueCreator initialization."""
        assert self.creator.github_client == self.mock_client
        assert self.creator.created_issues == []

    def test_create_issue_from_task(self):
        """Test creating a single issue from a task."""
        task = ExtractedTask(
            title="Implement login",
            description="Add user login functionality",
            task_type=TaskType.FEATURE,
            priority=Priority.HIGH,
            labels=["auth"],
            assignees=["developer1"],
            milestone="v1.0"
        )

        self.mock_client.create_issue.return_value = {
            "number": 1,
            "url": "https://github.com/owner/repo/issues/1",
            "title": "[Feature] Implement login",
            "state": "open"
        }

        issue = self.creator.create_issue_from_task(
            repo_name="owner/repo",
            task=task
        )

        assert issue["number"] == 1
        self.mock_client.create_issue.assert_called_once()
        call_args = self.mock_client.create_issue.call_args
        assert call_args[1]["title"] == "[Feature] Implement login"
        assert "auth" in call_args[1]["labels"]
        assert call_args[1]["assignees"] == ["developer1"]

    def test_create_issues_from_batch(self):
        """Test creating multiple issues from a task batch."""
        tasks = [
            ExtractedTask(
                title=f"Task {i}",
                description=f"Description {i}",
                priority=Priority.MEDIUM
            ) for i in range(3)
        ]

        batch = TaskBatch(
            tasks=tasks,
            source="test"
        )

        self.mock_client.check_rate_limit.return_value = {
            "remaining": 5000,
            "limit": 5000,
            "ok": True
        }

        self.mock_client.batch_create_issues.return_value = {
            "created": 3,
            "failed": 0,
            "issues": [
                {"number": i+1, "url": f"https://github.com/owner/repo/issues/{i+1}"}
                for i in range(3)
            ],
            "errors": []
        }

        result = self.creator.create_issues_from_batch(
            repo_name="owner/repo",
            batch=batch
        )

        assert result["created"] == 3
        assert result["failed"] == 0
        assert len(self.creator.created_issues) == 3
        self.mock_client.batch_create_issues.assert_called_once()

    def test_create_issues_with_dependencies(self):
        """Test creating issues with dependency references."""
        task1 = ExtractedTask(
            title="Setup database",
            description="Initialize database",
            priority=Priority.HIGH
        )
        
        task2 = ExtractedTask(
            title="Create models",
            description="Create data models",
            dependencies=["Setup database"],
            priority=Priority.MEDIUM
        )

        tasks = [task1, task2]
        batch = TaskBatch(tasks=tasks, source="test")

        self.mock_client.check_rate_limit.return_value = {
            "remaining": 5000,
            "limit": 5000,
            "ok": True
        }

        # Mock the batch creation to return issues
        self.mock_client.batch_create_issues.return_value = {
            "created": 2,
            "failed": 0,
            "issues": [
                {"number": 1, "url": "https://github.com/owner/repo/issues/1"},
                {"number": 2, "url": "https://github.com/owner/repo/issues/2"}
            ],
            "errors": []
        }

        result = self.creator.create_issues_from_batch(
            repo_name="owner/repo",
            batch=batch,
            link_dependencies=True
        )

        # Should add comments to link dependencies
        self.mock_client.add_comment_to_issue.assert_called()
        
    def test_create_epic_issue(self):
        """Test creating an epic issue that references multiple tasks."""
        tasks = [
            ExtractedTask(
                title="Frontend setup",
                description="Setup frontend framework",
                task_type=TaskType.FEATURE
            ),
            ExtractedTask(
                title="Backend API",
                description="Create REST API",
                task_type=TaskType.FEATURE
            ),
            ExtractedTask(
                title="Write tests",
                description="Unit tests",
                task_type=TaskType.TEST
            )
        ]

        self.mock_client.create_issue.return_value = {
            "number": 100,
            "url": "https://github.com/owner/repo/issues/100",
            "title": "[Epic] MVP Development",
            "state": "open"
        }

        epic = self.creator.create_epic_issue(
            repo_name="owner/repo",
            tasks=tasks,
            epic_title="MVP Development",
            epic_description="Complete MVP features"
        )

        assert epic["number"] == 100
        self.mock_client.create_issue.assert_called_once()
        call_args = self.mock_client.create_issue.call_args
        assert "[Epic]" in call_args[1]["title"]
        assert "epic" in call_args[1]["labels"]

    def test_validate_and_create_labels(self):
        """Test validating and creating required labels."""
        tasks = [
            ExtractedTask(
                title="Task 1",
                description="Description",
                task_type=TaskType.FEATURE,
                priority=Priority.HIGH,
                labels=["custom-label"]
            )
        ]

        self.mock_client.get_or_create_labels.return_value = [
            "feature", "priority:high", "custom-label"
        ]

        labels = self.creator.validate_and_create_labels(
            repo_name="owner/repo",
            tasks=tasks
        )

        assert "feature" in labels
        assert "priority:high" in labels
        assert "custom-label" in labels
        self.mock_client.get_or_create_labels.assert_called_once()

    def test_update_issue_references(self):
        """Test updating issues with cross-references."""
        self.creator.created_issues = [
            {"number": 1, "title": "Task A", "dependencies": []},
            {"number": 2, "title": "Task B", "dependencies": ["Task A"]},
            {"number": 3, "title": "Task C", "dependencies": ["Task B"]}
        ]

        self.creator.update_issue_references("owner/repo")

        # Should add comments to link related issues
        assert self.mock_client.add_comment_to_issue.call_count >= 2

    def test_create_milestone_if_needed(self):
        """Test creating a milestone if it doesn't exist."""
        tasks = [
            ExtractedTask(
                title="Task with milestone",
                description="Description",
                milestone="v2.0.0"
            )
        ]

        # Mock repository and milestone operations
        mock_repo = Mock()
        mock_repo.get_milestones.return_value = []
        mock_repo.create_milestone.return_value = Mock(title="v2.0.0", number=1)
        self.mock_client.get_repository.return_value = mock_repo

        milestone = self.creator.create_milestone_if_needed(
            repo_name="owner/repo",
            milestone_title="v2.0.0"
        )

        assert milestone is not None
        mock_repo.create_milestone.assert_called_once_with(title="v2.0.0")

    def test_group_tasks_by_priority(self):
        """Test grouping tasks by priority for batch processing."""
        tasks = [
            ExtractedTask(title="Critical", description="", priority=Priority.CRITICAL),
            ExtractedTask(title="High 1", description="", priority=Priority.HIGH),
            ExtractedTask(title="High 2", description="", priority=Priority.HIGH),
            ExtractedTask(title="Low", description="", priority=Priority.LOW),
        ]

        grouped = self.creator.group_tasks_by_priority(tasks)

        assert len(grouped[Priority.CRITICAL]) == 1
        assert len(grouped[Priority.HIGH]) == 2
        assert len(grouped[Priority.MEDIUM]) == 0
        assert len(grouped[Priority.LOW]) == 1

    def test_create_issues_respects_rate_limit(self):
        """Test that issue creation respects GitHub rate limits."""
        self.mock_client.check_rate_limit.return_value = {
            "remaining": 10,
            "limit": 5000,
            "ok": True
        }

        tasks = [ExtractedTask(title=f"Task {i}", description="") for i in range(20)]
        batch = TaskBatch(tasks=tasks, source="test")

        # Mock batch creation
        self.mock_client.batch_create_issues.return_value = {
            "created": 10,  # Only 10 created due to rate limit
            "failed": 0,
            "issues": [{"number": i+1} for i in range(10)],
            "errors": []
        }

        result = self.creator.create_issues_from_batch(
            repo_name="owner/repo",
            batch=batch,
            check_rate_limit=True
        )

        self.mock_client.check_rate_limit.assert_called()
        assert result["created"] == 10

    def test_dry_run_mode(self):
        """Test dry run mode doesn't create actual issues."""
        task = ExtractedTask(
            title="Test task",
            description="Test description"
        )

        result = self.creator.create_issue_from_task(
            repo_name="owner/repo",
            task=task,
            dry_run=True
        )

        # Should not call actual create method in dry run
        self.mock_client.create_issue.assert_not_called()
        assert result["dry_run"] is True
        assert "title" in result
        assert "body" in result

    def test_get_creation_summary(self):
        """Test getting a summary of created issues."""
        self.creator.created_issues = [
            {"number": 1, "title": "Task 1", "url": "url1"},
            {"number": 2, "title": "Task 2", "url": "url2"}
        ]

        summary = self.creator.get_creation_summary()

        assert summary["total_created"] == 2
        assert summary["issue_numbers"] == [1, 2]
        assert len(summary["issue_urls"]) == 2

    def test_rollback_on_failure(self):
        """Test rolling back created issues on failure."""
        self.creator.created_issues = [
            {"number": 1, "title": "Task 1"},
            {"number": 2, "title": "Task 2"}
        ]

        self.creator.rollback_created_issues("owner/repo")

        # Should close all created issues
        assert self.mock_client.close_issue.call_count == 2
        assert len(self.creator.created_issues) == 0