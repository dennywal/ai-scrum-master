"""Tests for GitHubClient class."""

from unittest.mock import Mock, patch, MagicMock
import pytest
from datetime import datetime, UTC

from src.integrations.github_client import GitHubClient
from src.core.exceptions import (
    GitHubAuthenticationError,
    GitHubRepositoryError,
    GitHubPermissionError,
    GitHubRateLimitError
)


class TestGitHubClient:
    """Test suite for GitHubClient."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token = "test_token_123"
        self.client = GitHubClient(token=self.token)

    @patch('src.integrations.github_client.Github')
    def test_initialization_with_token(self, mock_github):
        """Test client initialization with token."""
        client = GitHubClient(token="test_token")
        mock_github.assert_called_once_with("test_token")
        assert client.github is not None

    def test_initialization_without_token_raises_error(self):
        """Test initialization without token raises error."""
        with pytest.raises(GitHubAuthenticationError):
            GitHubClient(token="")

    @patch('src.integrations.github_client.Github')
    def test_get_repository_success(self, mock_github):
        """Test successful repository retrieval."""
        mock_repo = Mock()
        mock_repo.full_name = "owner/repo"
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        repo = client.get_repository("owner/repo")

        assert repo == mock_repo
        mock_github.return_value.get_repo.assert_called_once_with("owner/repo")

    @patch('src.integrations.github_client.Github')
    def test_get_repository_not_found(self, mock_github):
        """Test repository not found error."""
        mock_github.return_value.get_repo.side_effect = Exception("Repository not found")

        client = GitHubClient(token=self.token)
        
        with pytest.raises(GitHubRepositoryError) as exc_info:
            client.get_repository("owner/nonexistent")
        
        assert "owner/nonexistent" in str(exc_info.value)

    @patch('src.integrations.github_client.Github')
    def test_create_issue_success(self, mock_github):
        """Test successful issue creation."""
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.html_url = "https://github.com/owner/repo/issues/123"
        mock_repo.create_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        issue = client.create_issue(
            repo_name="owner/repo",
            title="Test Issue",
            body="Test body",
            labels=["bug", "urgent"],
            assignees=["user1"],
            milestone=None
        )

        assert issue["number"] == 123
        assert issue["url"] == "https://github.com/owner/repo/issues/123"
        mock_repo.create_issue.assert_called_once()

    @patch('src.integrations.github_client.Github')
    def test_create_issue_with_milestone(self, mock_github):
        """Test issue creation with milestone."""
        mock_repo = Mock()
        mock_milestone = Mock()
        mock_milestone.number = 1
        mock_repo.get_milestones.return_value = [mock_milestone]
        mock_milestone.title = "v1.0.0"
        
        mock_issue = Mock()
        mock_issue.number = 124
        mock_issue.html_url = "https://github.com/owner/repo/issues/124"
        mock_repo.create_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        issue = client.create_issue(
            repo_name="owner/repo",
            title="Test Issue",
            body="Test body",
            milestone="v1.0.0"
        )

        assert issue["number"] == 124
        call_args = mock_repo.create_issue.call_args
        assert call_args[1]["milestone"] == mock_milestone

    @patch('src.integrations.github_client.Github')
    def test_create_issue_permission_denied(self, mock_github):
        """Test issue creation with permission denied."""
        mock_repo = Mock()
        mock_repo.create_issue.side_effect = Exception("Permission denied")
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        
        with pytest.raises(GitHubPermissionError) as exc_info:
            client.create_issue(
                repo_name="owner/repo",
                title="Test Issue",
                body="Test body"
            )
        
        assert "owner/repo" in str(exc_info.value)

    @patch('src.integrations.github_client.Github')
    def test_batch_create_issues_success(self, mock_github):
        """Test successful batch issue creation."""
        mock_repo = Mock()
        mock_issues = []
        
        for i in range(3):
            mock_issue = Mock()
            mock_issue.number = 100 + i
            mock_issue.html_url = f"https://github.com/owner/repo/issues/{100 + i}"
            mock_issues.append(mock_issue)
        
        mock_repo.create_issue.side_effect = mock_issues
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        
        issues_data = [
            {"title": f"Issue {i}", "body": f"Body {i}", "labels": []}
            for i in range(3)
        ]
        
        results = client.batch_create_issues("owner/repo", issues_data)

        assert results["created"] == 3
        assert results["failed"] == 0
        assert len(results["issues"]) == 3
        assert results["issues"][0]["number"] == 100

    @patch('src.integrations.github_client.Github')
    def test_batch_create_issues_partial_failure(self, mock_github):
        """Test batch issue creation with partial failure."""
        mock_repo = Mock()
        
        # First issue succeeds
        mock_issue1 = Mock()
        mock_issue1.number = 101
        mock_issue1.html_url = "https://github.com/owner/repo/issues/101"
        
        # Second issue fails
        def create_issue_side_effect(*args, **kwargs):
            if mock_repo.create_issue.call_count == 1:
                return mock_issue1
            else:
                raise Exception("API Error")
        
        mock_repo.create_issue.side_effect = create_issue_side_effect
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        
        issues_data = [
            {"title": "Issue 1", "body": "Body 1", "labels": []},
            {"title": "Issue 2", "body": "Body 2", "labels": []}
        ]
        
        results = client.batch_create_issues("owner/repo", issues_data)

        assert results["created"] == 1
        assert results["failed"] == 1
        assert len(results["issues"]) == 1
        assert len(results["errors"]) == 1

    @patch('src.integrations.github_client.Github')
    def test_check_rate_limit_ok(self, mock_github):
        """Test rate limit check when within limits."""
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 4000
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.reset = datetime.now(UTC).timestamp() + 3600
        mock_github.return_value.get_rate_limit.return_value = mock_rate_limit

        client = GitHubClient(token=self.token)
        result = client.check_rate_limit()

        assert result["remaining"] == 4000
        assert result["limit"] == 5000
        assert result["ok"] is True

    @patch('src.integrations.github_client.Github')
    def test_check_rate_limit_exceeded(self, mock_github):
        """Test rate limit check when exceeded."""
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 0
        mock_rate_limit.core.limit = 5000
        reset_time = datetime.now(UTC).timestamp() + 1800
        mock_rate_limit.core.reset = reset_time
        mock_github.return_value.get_rate_limit.return_value = mock_rate_limit

        client = GitHubClient(token=self.token)
        
        with pytest.raises(GitHubRateLimitError) as exc_info:
            client.check_rate_limit(raise_if_exceeded=True)
        
        assert str(int(reset_time)) in str(exc_info.value.details["reset_time"])

    @patch('src.integrations.github_client.Github')
    def test_get_or_create_labels(self, mock_github):
        """Test getting or creating labels."""
        mock_repo = Mock()
        
        # Existing label
        existing_label = Mock()
        existing_label.name = "bug"
        
        # New label to create
        new_label = Mock()
        new_label.name = "enhancement"
        
        mock_repo.get_labels.return_value = [existing_label]
        mock_repo.create_label.return_value = new_label
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        labels = client.get_or_create_labels(
            "owner/repo", 
            ["bug", "enhancement"]
        )

        assert len(labels) == 2
        assert "bug" in labels
        assert "enhancement" in labels
        mock_repo.create_label.assert_called_once()

    @patch('src.integrations.github_client.Github')
    def test_validate_repository_access_success(self, mock_github):
        """Test successful repository access validation."""
        mock_repo = Mock()
        mock_repo.permissions.push = True
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        result = client.validate_repository_access("owner/repo")

        assert result is True

    @patch('src.integrations.github_client.Github')
    def test_validate_repository_access_no_permission(self, mock_github):
        """Test repository access validation with no write permission."""
        mock_repo = Mock()
        mock_repo.permissions.push = False
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        
        with pytest.raises(GitHubPermissionError):
            client.validate_repository_access("owner/repo")

    @patch('src.integrations.github_client.Github')
    def test_close_issue(self, mock_github):
        """Test closing an issue."""
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.state = "open"
        mock_repo.get_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        client.close_issue("owner/repo", 123)

        mock_issue.edit.assert_called_once_with(state="closed")

    @patch('src.integrations.github_client.Github')
    def test_add_comment_to_issue(self, mock_github):
        """Test adding a comment to an issue."""
        mock_repo = Mock()
        mock_issue = Mock()
        mock_comment = Mock()
        mock_comment.id = 456
        mock_issue.create_comment.return_value = mock_comment
        mock_repo.get_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        comment = client.add_comment_to_issue(
            "owner/repo", 
            123, 
            "This is a comment"
        )

        assert comment["id"] == 456
        mock_issue.create_comment.assert_called_once_with("This is a comment")

    @patch('src.integrations.github_client.Github')
    def test_update_issue(self, mock_github):
        """Test updating an issue."""
        mock_repo = Mock()
        mock_issue = Mock()
        mock_repo.get_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo

        client = GitHubClient(token=self.token)
        client.update_issue(
            "owner/repo",
            123,
            title="Updated Title",
            body="Updated Body",
            labels=["updated", "bug"]
        )

        mock_issue.edit.assert_called_once()
        call_kwargs = mock_issue.edit.call_args[1]
        assert call_kwargs["title"] == "Updated Title"
        assert call_kwargs["body"] == "Updated Body"