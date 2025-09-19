"""Task-related data models for AI Scrum Master."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TaskType(str, Enum):
    """Types of tasks that can be created."""
    FEATURE = "feature"
    BUG = "bug"
    TEST = "test"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    RESEARCH = "research"
    INFRASTRUCTURE = "infrastructure"


class Priority(str, Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EffortSize(str, Enum):
    """Estimated effort size for tasks."""
    SMALL = "small"  # < 1 day
    MEDIUM = "medium"  # 1-3 days
    LARGE = "large"  # 3-5 days
    EXTRA_LARGE = "extra_large"  # > 5 days


class TaskStatus(str, Enum):
    """Status of a task in the workflow."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExtractedTask(BaseModel):
    """Represents a task extracted from TDD/PRD documents."""

    # Core fields
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(..., description="Detailed task description")
    task_type: TaskType = Field(TaskType.FEATURE, description="Type of task")
    priority: Priority = Field(Priority.MEDIUM, description="Task priority")

    # Relationships
    dependencies: list[str] = Field(default_factory=list, description="List of task titles this depends on")
    blocks: list[str] = Field(default_factory=list, description="List of tasks this blocks")

    # Requirements
    acceptance_criteria: list[str] = Field(default_factory=list, description="Testable acceptance criteria")
    technical_requirements: list[str] = Field(default_factory=list, description="Technical requirements")

    # Metadata
    labels: list[str] = Field(default_factory=list, description="Task labels")
    estimated_effort: EffortSize | None = Field(None, description="Estimated effort size")
    milestone: str | None = Field(None, description="Associated milestone")
    assignees: list[str] = Field(default_factory=list, description="Assigned users")

    # Tracking
    status: TaskStatus = Field(TaskStatus.PENDING, description="Current task status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Task creation time")
    updated_at: datetime | None = Field(None, description="Last update time")

    # Source tracking
    source_document: str | None = Field(None, description="Source document type (TDD/PRD)")
    source_section: str | None = Field(None, description="Section in source document")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Ensure title is properly formatted."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator('dependencies')
    @classmethod
    def validate_dependencies(cls, v, info):
        """Ensure no self-dependencies."""
        if info.data.get('title') and info.data['title'] in v:
            raise ValueError("Task cannot depend on itself")
        return v

    @field_validator('priority')
    @classmethod
    def adjust_critical_priority(cls, v, info):
        """Auto-adjust priority based on keywords."""
        if info.data.get('title') and info.data.get('description'):
            critical_keywords = ['security', 'vulnerability', 'critical', 'urgent', 'blocker']
            content = f"{info.data['title']} {info.data['description']}".lower()
            if any(keyword in content for keyword in critical_keywords):
                return Priority.CRITICAL
        return v

    def to_github_format(self) -> dict[str, Any]:
        """Convert to format suitable for GitHub issue creation."""
        return {
            "title": self.get_formatted_title(),
            "body": self.get_formatted_body(),
            "labels": self.get_github_labels(),
            "assignees": self.assignees,
            "milestone": self.milestone
        }

    def get_formatted_title(self) -> str:
        """Get formatted title with type prefix."""
        type_prefix = {
            TaskType.FEATURE: "[Feature]",
            TaskType.BUG: "[Bug]",
            TaskType.TEST: "[Test]",
            TaskType.DOCUMENTATION: "[Docs]",
            TaskType.REFACTOR: "[Refactor]",
            TaskType.RESEARCH: "[Research]",
            TaskType.INFRASTRUCTURE: "[Infra]"
        }
        prefix = type_prefix.get(self.task_type, "")
        return f"{prefix} {self.title}".strip()

    def get_formatted_body(self) -> str:
        """Get formatted body in Markdown."""
        sections = []

        # Description
        sections.append("## Description")
        sections.append(self.description)

        # Acceptance Criteria
        if self.acceptance_criteria:
            sections.append("\n## Acceptance Criteria")
            for criterion in self.acceptance_criteria:
                sections.append(f"- [ ] {criterion}")

        # Technical Requirements
        if self.technical_requirements:
            sections.append("\n## Technical Requirements")
            for req in self.technical_requirements:
                sections.append(f"- {req}")

        # Dependencies
        if self.dependencies:
            sections.append("\n## Dependencies")
            sections.append("This task depends on:")
            for dep in self.dependencies:
                sections.append(f"- {dep}")

        # Blocks
        if self.blocks:
            sections.append("\n## Blocks")
            sections.append("This task blocks:")
            for blocked in self.blocks:
                sections.append(f"- {blocked}")

        # Metadata
        sections.append("\n## Metadata")
        sections.append(f"- **Priority:** {self.priority.value}")
        sections.append(f"- **Type:** {self.task_type.value}")
        if self.estimated_effort:
            sections.append(f"- **Estimated Effort:** {self.estimated_effort.value}")
        if self.source_document:
            sections.append(f"- **Source:** {self.source_document}")

        return "\n".join(sections)

    def get_github_labels(self) -> list[str]:
        """Get labels for GitHub issue."""
        labels = list(self.labels)  # Copy existing labels

        # Add type label
        labels.append(self.task_type.value)

        # Add priority label
        priority_labels = {
            Priority.CRITICAL: "priority:critical",
            Priority.HIGH: "priority:high",
            Priority.MEDIUM: "priority:medium",
            Priority.LOW: "priority:low"
        }
        labels.append(priority_labels[self.priority])

        # Add effort label if specified
        if self.estimated_effort:
            labels.append(f"effort:{self.estimated_effort.value}")

        # Add status label if not pending
        if self.status != TaskStatus.PENDING:
            labels.append(f"status:{self.status.value}")

        return list(set(labels))  # Remove duplicates


class TaskBatch(BaseModel):
    """Collection of tasks for batch processing."""

    tasks: list[ExtractedTask] = Field(..., min_length=1, description="List of tasks")
    source: str = Field(..., description="Source identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator('tasks')
    @classmethod
    def validate_unique_titles(cls, v):
        """Ensure all task titles are unique."""
        titles = [task.title for task in v]
        if len(titles) != len(set(titles)):
            raise ValueError("All task titles must be unique within a batch")
        return v

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Get dependency graph for all tasks."""
        graph = {}
        for task in self.tasks:
            graph[task.title] = task.dependencies
        return graph

    def get_tasks_by_priority(self) -> dict[Priority, list[ExtractedTask]]:
        """Group tasks by priority."""
        grouped = {priority: [] for priority in Priority}
        for task in self.tasks:
            grouped[task.priority].append(task)
        return grouped

    def get_tasks_by_type(self) -> dict[TaskType, list[ExtractedTask]]:
        """Group tasks by type."""
        grouped = {task_type: [] for task_type in TaskType}
        for task in self.tasks:
            grouped[task.task_type].append(task)
        return grouped
