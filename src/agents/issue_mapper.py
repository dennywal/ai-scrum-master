"""Maps extracted tasks to GitHub issue format."""

from typing import Any

from src.core.base_agent import BaseAgent
from src.models.tasks import ExtractedTask


class IssueMapper(BaseAgent):
    """Maps extracted tasks to GitHub issue format."""

    def __init__(self):
        """Initialize IssueMapper."""
        super().__init__(name="IssueMapper")

    def _initialize(self):
        """Initialize agent-specific components."""
        pass

    def map_task_to_issue(self, task: ExtractedTask) -> dict[str, Any]:
        """Map a single task to GitHub issue format.
        
        Args:
            task: ExtractedTask to convert
            
        Returns:
            Dictionary with GitHub issue format
        """
        return {
            "title": task.get_formatted_title(),
            "body": task.get_formatted_body(),
            "labels": task.get_github_labels(),
            "assignees": task.assignees,
            "milestone": task.milestone
        }

    def map_tasks_to_issues(self, tasks: list[ExtractedTask]) -> list[dict[str, Any]]:
        """Map multiple tasks to GitHub issues.
        
        Args:
            tasks: List of ExtractedTask objects
            
        Returns:
            List of GitHub issue dictionaries
        """
        return [self.map_task_to_issue(task) for task in tasks]

    def add_cross_references(self, issues: list[dict], tasks: list[ExtractedTask]) -> list[dict]:
        """Add cross-references between related issues.
        
        Args:
            issues: List of GitHub issue dictionaries
            tasks: Original tasks with dependency information
            
        Returns:
            Updated issues with cross-references
        """
        # Create mapping of task title to issue index
        title_to_index = {task.title: idx for idx, task in enumerate(tasks)}
        
        for _idx, (issue, task) in enumerate(zip(issues, tasks, strict=False)):
            references = []
            
            # Add references to dependencies
            for dep_title in task.dependencies:
                if dep_title in title_to_index:
                    dep_idx = title_to_index[dep_title]
                    references.append(f"Depends on #{dep_idx + 1}")
            
            # Add references to blocked tasks
            for blocked_title in task.blocks:
                if blocked_title in title_to_index:
                    blocked_idx = title_to_index[blocked_title]
                    references.append(f"Blocks #{blocked_idx + 1}")
            
            # Add references to issue body if any exist
            if references:
                issue["body"] += "\n\n## Issue References\n"
                for ref in references:
                    issue["body"] += f"- {ref}\n"
        
        return issues

    def validate_issue_format(self, issue: dict) -> bool:
        """Validate that issue has required GitHub fields.
        
        Args:
            issue: Issue dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["title", "body"]
        return all(field in issue and issue[field] for field in required_fields)

    def batch_validate_issues(self, issues: list[dict]) -> tuple[list[dict], list[str]]:
        """Validate a batch of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Tuple of (valid_issues, error_messages)
        """
        valid_issues = []
        errors = []
        
        for idx, issue in enumerate(issues):
            if self.validate_issue_format(issue):
                valid_issues.append(issue)
            else:
                errors.append(f"Issue {idx + 1} missing required fields")
        
        return valid_issues, errors

    def enrich_with_templates(self, issue: dict, template_type: str = "default") -> dict:
        """Enrich issue with template content.
        
        Args:
            issue: Issue dictionary
            template_type: Type of template to use
            
        Returns:
            Enriched issue
        """
        templates = {
            "bug": "\n\n## Steps to Reproduce\n1. \n2. \n3. \n\n## Expected Behavior\n\n## Actual Behavior\n\n## Environment\n- OS: \n- Version: ",
            "feature": "\n\n## User Story\n\n## Implementation Details\n\n## Testing Plan\n",
            "default": ""
        }
        
        # Determine template based on labels
        if "bug" in issue.get("labels", []):
            template = templates["bug"]
        elif "feature" in issue.get("labels", []):
            template = templates["feature"]
        else:
            template = templates[template_type]
        
        if template:
            issue["body"] += template
        
        return issue

    def group_by_priority(self, tasks: list[ExtractedTask]) -> dict[str, list[dict]]:
        """Group tasks by priority for batch creation.
        
        Args:
            tasks: List of tasks to group
            
        Returns:
            Dictionary grouped by priority
        """
        grouped = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for task in tasks:
            issue = self.map_task_to_issue(task)
            grouped[task.priority.value].append(issue)
        
        return grouped

    def create_epic_from_tasks(self, tasks: list[ExtractedTask], epic_title: str, epic_description: str = "") -> dict:
        """Create an epic issue that references multiple tasks.
        
        Args:
            tasks: List of tasks to include in epic
            epic_title: Title for the epic
            epic_description: Description for the epic
            
        Returns:
            Epic issue dictionary
        """
        epic_body = epic_description or "This epic tracks the following tasks:"
        epic_body += "\n\n## Tasks\n"
        
        # Group tasks by type
        tasks_by_type = {}
        for task in tasks:
            task_type = task.task_type.value
            if task_type not in tasks_by_type:
                tasks_by_type[task_type] = []
            tasks_by_type[task_type].append(task)
        
        # Add tasks to epic body
        for task_type, type_tasks in tasks_by_type.items():
            epic_body += f"\n### {task_type.title()}\n"
            for task in type_tasks:
                status_emoji = "⬜" if task.status.value == "pending" else "✅"
                epic_body += f"- {status_emoji} {task.title}\n"
        
        # Add summary statistics
        epic_body += "\n\n## Summary\n"
        epic_body += f"- Total tasks: {len(tasks)}\n"
        epic_body += f"- Task types: {', '.join(tasks_by_type.keys())}\n"
        
        priority_counts = {}
        for task in tasks:
            priority = task.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        epic_body += "- Priorities: "
        epic_body += ", ".join([f"{p}: {c}" for p, c in priority_counts.items()])
        
        return {
            "title": f"[Epic] {epic_title}",
            "body": epic_body,
            "labels": ["epic"],
            "assignees": [],
            "milestone": None
        }