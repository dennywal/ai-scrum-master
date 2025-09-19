"""GitHub issue creator using extracted tasks."""

import logging
from typing import Any

from src.integrations.github_client import GitHubClient
from src.models.tasks import ExtractedTask, TaskBatch, Priority
from src.agents.issue_mapper import IssueMapper


logger = logging.getLogger(__name__)


class GitHubIssueCreator:
    """Creates GitHub issues from extracted tasks."""

    def __init__(self, github_client: GitHubClient):
        """Initialize GitHubIssueCreator.
        
        Args:
            github_client: Configured GitHub client
        """
        self.github_client = github_client
        self.issue_mapper = IssueMapper()
        self.created_issues: list[dict] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def create_issue_from_task(self, 
                              repo_name: str, 
                              task: ExtractedTask,
                              dry_run: bool = False) -> dict[str, Any]:
        """Create a GitHub issue from a single task.
        
        Args:
            repo_name: Repository name
            task: Task to create issue from
            dry_run: If True, don't actually create issue
            
        Returns:
            Created issue details or dry run info
        """
        # Map task to issue format
        issue_data = self.issue_mapper.map_task_to_issue(task)
        
        if dry_run:
            self.logger.info(f"[DRY RUN] Would create issue: {issue_data['title']}")
            return {
                "dry_run": True,
                "title": issue_data["title"],
                "body": issue_data["body"],
                "labels": issue_data["labels"]
            }
        
        # Create the actual issue
        issue = self.github_client.create_issue(
            repo_name=repo_name,
            title=issue_data["title"],
            body=issue_data["body"],
            labels=issue_data["labels"],
            assignees=issue_data.get("assignees"),
            milestone=issue_data.get("milestone")
        )
        
        # Track created issue
        issue["dependencies"] = task.dependencies
        issue["blocks"] = task.blocks
        self.created_issues.append(issue)
        
        return issue

    def create_issues_from_batch(self,
                                repo_name: str,
                                batch: TaskBatch,
                                link_dependencies: bool = True,
                                check_rate_limit: bool = True) -> dict[str, Any]:
        """Create multiple issues from a task batch.
        
        Args:
            repo_name: Repository name
            batch: Batch of tasks
            link_dependencies: Whether to link dependent issues
            check_rate_limit: Whether to check rate limits
            
        Returns:
            Creation results
        """
        if check_rate_limit:
            rate_info = self.github_client.check_rate_limit()
            if not rate_info["ok"]:
                self.logger.warning(f"Rate limit low: {rate_info['remaining']}/{rate_info['limit']}")
        
        # Map all tasks to issues
        issues_data = self.issue_mapper.map_tasks_to_issues(batch.tasks)
        
        # Create issues in batch
        result = self.github_client.batch_create_issues(repo_name, issues_data)
        
        # Store created issues with task info
        for idx, issue in enumerate(result["issues"]):
            if idx < len(batch.tasks):
                issue["dependencies"] = batch.tasks[idx].dependencies
                issue["blocks"] = batch.tasks[idx].blocks
                issue["title"] = batch.tasks[idx].title
                self.created_issues.append(issue)
        
        # Link dependencies if requested
        if link_dependencies and result["created"] > 0:
            self.update_issue_references(repo_name)
        
        return result

    def update_issue_references(self, repo_name: str) -> None:
        """Update issues with cross-references based on dependencies.
        
        Args:
            repo_name: Repository name
        """
        # Create mapping of task titles to issue numbers
        title_to_number = {
            issue["title"]: issue["number"] 
            for issue in self.created_issues
        }
        
        for issue in self.created_issues:
            references = []
            
            # Add dependency references
            for dep_title in issue.get("dependencies", []):
                if dep_title in title_to_number:
                    dep_number = title_to_number[dep_title]
                    references.append(f"Depends on #{dep_number}")
            
            # Add blocking references
            for block_title in issue.get("blocks", []):
                if block_title in title_to_number:
                    block_number = title_to_number[block_title]
                    references.append(f"Blocks #{block_number}")
            
            # Add comment with references if any exist
            if references:
                comment = "## Issue References\n"
                comment += "\n".join(f"- {ref}" for ref in references)
                
                try:
                    self.github_client.add_comment_to_issue(
                        repo_name,
                        issue["number"],
                        comment
                    )
                    self.logger.info(f"Added references to issue #{issue['number']}")
                except Exception as e:
                    self.logger.error(f"Failed to add references: {str(e)}")

    def create_epic_issue(self,
                        repo_name: str,
                        tasks: list[ExtractedTask],
                        epic_title: str,
                        epic_description: str = "") -> dict[str, Any]:
        """Create an epic issue that references multiple tasks.
        
        Args:
            repo_name: Repository name
            tasks: Tasks to include in epic
            epic_title: Epic title
            epic_description: Epic description
            
        Returns:
            Created epic issue
        """
        epic_data = self.issue_mapper.create_epic_from_tasks(
            tasks, 
            epic_title,
            epic_description
        )
        
        epic = self.github_client.create_issue(
            repo_name=repo_name,
            title=epic_data["title"],
            body=epic_data["body"],
            labels=epic_data["labels"]
        )
        
        self.created_issues.append(epic)
        return epic

    def validate_and_create_labels(self, 
                                  repo_name: str,
                                  tasks: list[ExtractedTask]) -> list[str]:
        """Validate and create required labels for tasks.
        
        Args:
            repo_name: Repository name
            tasks: Tasks to get labels from
            
        Returns:
            List of validated/created labels
        """
        # Collect all unique labels
        all_labels = set()
        
        for task in tasks:
            # Get labels from task
            issue_data = self.issue_mapper.map_task_to_issue(task)
            all_labels.update(issue_data["labels"])
        
        # Ensure labels exist
        return self.github_client.get_or_create_labels(repo_name, list(all_labels))

    def create_milestone_if_needed(self, 
                                  repo_name: str, 
                                  milestone_title: str) -> Any:
        """Create a milestone if it doesn't exist.
        
        Args:
            repo_name: Repository name
            milestone_title: Milestone title
            
        Returns:
            Milestone object or None
        """
        try:
            repo = self.github_client.get_repository(repo_name)
            
            # Check if milestone exists
            for milestone in repo.get_milestones():
                if milestone.title == milestone_title:
                    return milestone
            
            # Create new milestone
            milestone = repo.create_milestone(title=milestone_title)
            self.logger.info(f"Created milestone: {milestone_title}")
            return milestone
            
        except Exception as e:
            self.logger.error(f"Failed to create milestone: {str(e)}")
            return None

    def group_tasks_by_priority(self, tasks: list[ExtractedTask]) -> dict[Priority, list[ExtractedTask]]:
        """Group tasks by priority for organized creation.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Tasks grouped by priority
        """
        grouped = {priority: [] for priority in Priority}
        
        for task in tasks:
            grouped[task.priority].append(task)
        
        return grouped

    def get_creation_summary(self) -> dict[str, Any]:
        """Get summary of all created issues.
        
        Returns:
            Summary dictionary
        """
        return {
            "total_created": len(self.created_issues),
            "issue_numbers": [issue["number"] for issue in self.created_issues],
            "issue_urls": [issue.get("url", "") for issue in self.created_issues],
            "issues": self.created_issues
        }

    def rollback_created_issues(self, repo_name: str) -> None:
        """Rollback (close) all created issues in case of failure.
        
        Args:
            repo_name: Repository name
        """
        self.logger.warning(f"Rolling back {len(self.created_issues)} created issues")
        
        for issue in self.created_issues:
            try:
                self.github_client.close_issue(repo_name, issue["number"])
                self.logger.info(f"Closed issue #{issue['number']} during rollback")
            except Exception as e:
                self.logger.error(f"Failed to close issue #{issue['number']}: {str(e)}")
        
        self.created_issues.clear()