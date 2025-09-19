"""GitHub API client for issue management."""

import logging
from typing import Any
from datetime import datetime, UTC

from github import Github, GithubException, Auth

from src.core.exceptions import (
    GitHubAuthenticationError,
    GitHubRepositoryError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubBatchCreationError
)

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: str):
        """Initialize GitHub client.
        
        Args:
            token: GitHub personal access token
            
        Raises:
            GitHubAuthenticationError: If token is invalid
        """
        if not token:
            raise GitHubAuthenticationError()
        
        self.token = token
        self.github = Github(auth=Auth.Token(token))
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_repository(self, repo_name: str):
        """Get a repository object.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            
        Returns:
            Repository object
            
        Raises:
            GitHubRepositoryError: If repository not found
        """
        try:
            repo = self.github.get_repo(repo_name)
            self.logger.info(f"Successfully accessed repository: {repo_name}")
            return repo
        except Exception as e:
            self.logger.error(f"Failed to get repository {repo_name}: {str(e)}")
            raise GitHubRepositoryError(repo_name, str(e)) from e

    def create_issue(self, 
                    repo_name: str,
                    title: str,
                    body: str,
                    labels: list[str] | None = None,
                    assignees: list[str] | None = None,
                    milestone: str | None = None) -> dict[str, Any]:
        """Create a single issue.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            title: Issue title
            body: Issue body in markdown
            labels: List of label names
            assignees: List of usernames to assign
            milestone: Milestone title
            
        Returns:
            Dictionary with issue details
            
        Raises:
            GitHubPermissionError: If lacking permissions
            GitHubRepositoryError: If repository operation fails
        """
        try:
            repo = self.get_repository(repo_name)
            
            # Prepare arguments
            kwargs = {
                "title": title,
                "body": body
            }
            
            # Add labels if provided
            if labels:
                kwargs["labels"] = labels
            
            # Add assignees if provided
            if assignees:
                kwargs["assignees"] = assignees
            
            # Find and add milestone if provided
            if milestone:
                milestones = repo.get_milestones()
                for ms in milestones:
                    if ms.title == milestone:
                        kwargs["milestone"] = ms
                        break
            
            # Create the issue
            issue = repo.create_issue(**kwargs)
            
            self.logger.info(f"Created issue #{issue.number}: {title}")
            
            return {
                "number": issue.number,
                "url": issue.html_url,
                "title": title,
                "state": "open"
            }
            
        except PermissionError:
            raise GitHubPermissionError(repo_name, "create_issue")
        except Exception as e:
            if "permission" in str(e).lower():
                raise GitHubPermissionError(repo_name, "create_issue") from e
            raise GitHubRepositoryError(repo_name, f"Failed to create issue: {str(e)}") from e

    def batch_create_issues(self, 
                           repo_name: str, 
                           issues_data: list[dict]) -> dict[str, Any]:
        """Create multiple issues in batch.
        
        Args:
            repo_name: Repository name
            issues_data: List of issue dictionaries
            
        Returns:
            Dictionary with creation results
        """
        created_issues = []
        failed_issues = []
        errors = []
        
        for idx, issue_data in enumerate(issues_data):
            try:
                issue = self.create_issue(
                    repo_name=repo_name,
                    title=issue_data.get("title", f"Issue {idx + 1}"),
                    body=issue_data.get("body", ""),
                    labels=issue_data.get("labels"),
                    assignees=issue_data.get("assignees"),
                    milestone=issue_data.get("milestone")
                )
                created_issues.append(issue)
                
            except Exception as e:
                self.logger.error(f"Failed to create issue {idx + 1}: {str(e)}")
                failed_issues.append(idx)
                errors.append({
                    "index": idx,
                    "title": issue_data.get("title", f"Issue {idx + 1}"),
                    "error": str(e)
                })
        
        result = {
            "created": len(created_issues),
            "failed": len(failed_issues),
            "issues": created_issues,
            "errors": errors
        }
        
        if failed_issues and not created_issues:
            # All failed
            raise GitHubBatchCreationError(0, len(failed_issues), errors)
        
        return result

    def check_rate_limit(self, raise_if_exceeded: bool = False) -> dict[str, Any]:
        """Check GitHub API rate limit.
        
        Args:
            raise_if_exceeded: Whether to raise exception if limit exceeded
            
        Returns:
            Dictionary with rate limit info
            
        Raises:
            GitHubRateLimitError: If rate limit exceeded and raise_if_exceeded=True
        """
        rate_limit = self.github.get_rate_limit()
        
        remaining = rate_limit.core.remaining
        limit = rate_limit.core.limit
        reset_time = int(rate_limit.core.reset)
        
        result = {
            "remaining": remaining,
            "limit": limit,
            "reset_time": reset_time,
            "ok": remaining > 0
        }
        
        if remaining == 0 and raise_if_exceeded:
            raise GitHubRateLimitError(reset_time)
        
        return result

    def get_or_create_labels(self, repo_name: str, label_names: list[str]) -> list[str]:
        """Get existing labels or create new ones.
        
        Args:
            repo_name: Repository name
            label_names: List of label names
            
        Returns:
            List of label names that exist or were created
        """
        repo = self.get_repository(repo_name)
        existing_labels = {label.name for label in repo.get_labels()}
        
        created_labels = []
        for label_name in label_names:
            if label_name not in existing_labels:
                try:
                    # Create with default color
                    repo.create_label(
                        name=label_name,
                        color="0366d6",  # GitHub blue
                        description=f"Auto-created by AI Scrum Master"
                    )
                    created_labels.append(label_name)
                    self.logger.info(f"Created label: {label_name}")
                except Exception as e:
                    self.logger.warning(f"Could not create label {label_name}: {str(e)}")
        
        return list(set(label_names))

    def validate_repository_access(self, repo_name: str) -> bool:
        """Validate write access to repository.
        
        Args:
            repo_name: Repository name
            
        Returns:
            True if have write access
            
        Raises:
            GitHubPermissionError: If no write access
        """
        try:
            repo = self.get_repository(repo_name)
            
            # Check if we have push (write) permission
            if not repo.permissions.push:
                raise GitHubPermissionError(repo_name, "write")
            
            return True
            
        except GitHubPermissionError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to validate access: {str(e)}")
            return False

    def close_issue(self, repo_name: str, issue_number: int) -> None:
        """Close an issue.
        
        Args:
            repo_name: Repository name
            issue_number: Issue number
        """
        try:
            repo = self.get_repository(repo_name)
            issue = repo.get_issue(issue_number)
            issue.edit(state="closed")
            self.logger.info(f"Closed issue #{issue_number}")
        except Exception as e:
            self.logger.error(f"Failed to close issue #{issue_number}: {str(e)}")
            raise GitHubRepositoryError(repo_name, f"Failed to close issue: {str(e)}") from e

    def add_comment_to_issue(self, 
                           repo_name: str, 
                           issue_number: int, 
                           comment: str) -> dict[str, Any]:
        """Add a comment to an issue.
        
        Args:
            repo_name: Repository name
            issue_number: Issue number
            comment: Comment text
            
        Returns:
            Comment details
        """
        try:
            repo = self.get_repository(repo_name)
            issue = repo.get_issue(issue_number)
            comment_obj = issue.create_comment(comment)
            
            return {
                "id": comment_obj.id,
                "body": comment,
                "created_at": comment_obj.created_at
            }
        except Exception as e:
            self.logger.error(f"Failed to add comment: {str(e)}")
            raise GitHubRepositoryError(repo_name, f"Failed to add comment: {str(e)}") from e

    def update_issue(self,
                    repo_name: str,
                    issue_number: int,
                    title: str | None = None,
                    body: str | None = None,
                    labels: list[str] | None = None,
                    state: str | None = None) -> None:
        """Update an existing issue.
        
        Args:
            repo_name: Repository name
            issue_number: Issue number
            title: New title (optional)
            body: New body (optional)
            labels: New labels (optional)
            state: New state (optional)
        """
        try:
            repo = self.get_repository(repo_name)
            issue = repo.get_issue(issue_number)
            
            kwargs = {}
            if title is not None:
                kwargs["title"] = title
            if body is not None:
                kwargs["body"] = body
            if labels is not None:
                kwargs["labels"] = labels
            if state is not None:
                kwargs["state"] = state
            
            if kwargs:
                issue.edit(**kwargs)
                self.logger.info(f"Updated issue #{issue_number}")
        except Exception as e:
            self.logger.error(f"Failed to update issue: {str(e)}")
            raise GitHubRepositoryError(repo_name, f"Failed to update issue: {str(e)}") from e