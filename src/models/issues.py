"""GitHub issue-related data models for AI Scrum Master."""

from datetime import UTC, datetime
from typing import Any, Optional, List

from pydantic import BaseModel, Field, HttpUrl, field_validator


class GeneratedIssueContent(BaseModel):
    """Content generated for a GitHub issue."""

    generated_title: str = Field(..., min_length=1, max_length=256, description="Generated issue title")
    generated_body: str = Field(..., min_length=1, description="Generated issue body in Markdown")
    labels_to_apply: list[str] = Field(default_factory=list, description="Labels to apply to the issue")
    suggested_assignees: list[str] = Field(default_factory=list, description="Suggested assignees")
    suggested_milestone: str | None = Field(None, description="Suggested milestone")
    priority: Optional[str] = Field("medium", description="Issue priority")
    issue_type: Optional[str] = Field("feature", description="Type of issue")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours")
    acceptance_criteria: Optional[list[str]] = Field(default_factory=list, description="Acceptance criteria")

    @field_validator('generated_title')
    @classmethod
    def validate_title(cls, v):
        """Ensure title is properly formatted."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        if len(v) > 256:
            raise ValueError("Title too long (max 256 characters)")
        return v.strip()

    @field_validator('generated_body')
    @classmethod
    def validate_body(cls, v):
        """Ensure body has content."""
        if not v.strip():
            raise ValueError("Body cannot be empty")
        return v.strip()


class GitHubIssueTemplate(BaseModel):
    """Template for creating a GitHub issue."""

    title: str = Field(..., min_length=1, max_length=256, description="Issue title")
    body: str = Field(..., min_length=1, description="Issue body in Markdown format")
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    assignees: list[str] = Field(default_factory=list, description="Users to assign")
    milestone: str | None = Field(None, description="Milestone name or number")
    project: str | None = Field(None, description="Project board name")

    def to_github_params(self) -> dict[str, Any]:
        """Convert to parameters for GitHub API."""
        params = {
            "title": self.title,
            "body": self.body
        }

        if self.labels:
            params["labels"] = self.labels

        if self.assignees:
            params["assignees"] = self.assignees

        if self.milestone:
            params["milestone"] = self.milestone

        return params

    def validate_github_limits(self) -> bool:
        """Validate against GitHub's limits."""
        # GitHub limits: title max 256 chars, body max 65536 chars
        if len(self.title) > 256:
            return False
        if len(self.body) > 65536:
            return False
        # Max 100 labels per issue
        if len(self.labels) > 100:
            return False
        # Max 10 assignees per issue
        if len(self.assignees) > 10:
            return False
        return True


class GitHubIssueOutput(BaseModel):
    """Output model for a created GitHub issue."""

    issue_url: HttpUrl = Field(..., description="URL of the created issue")
    issue_number: int | None = Field(None, description="Issue number")
    title: str = Field(..., description="Issue title")
    body: str = Field(..., description="Issue body")
    labels: list[str] = Field(default_factory=list, description="Applied labels")
    assignees: list[str] = Field(default_factory=list, description="Assigned users")
    milestone: str | None = Field(None, description="Associated milestone")
    state: str = Field("open", description="Issue state")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the issue."""
        return {
            "url": str(self.issue_url),
            "number": self.issue_number,
            "title": self.title[:100] + "..." if len(self.title) > 100 else self.title,
            "labels": self.labels,
            "state": self.state
        }


class BatchIssueCreationOutput(BaseModel):
    """Output model for batch issue creation."""

    created_issues: list[GitHubIssueOutput] = Field(default_factory=list, description="Successfully created issues")
    failed_issues: list[dict[str, Any]] = Field(default_factory=list, description="Failed issue creations")
    total_extracted_tasks: int = Field(..., ge=0, description="Total number of tasks extracted")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)")
    processing_time_seconds: float | None = Field(None, description="Total processing time")

    @field_validator('success_rate')
    @classmethod
    def calculate_success_rate(cls, v, info):
        """Calculate success rate if not provided."""
        if info.data.get('created_issues') and info.data.get('total_extracted_tasks'):
            total = info.data['total_extracted_tasks']
            if total > 0:
                return len(info.data['created_issues']) / total
        return v

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the batch creation."""
        return {
            "total_tasks": self.total_extracted_tasks,
            "created": len(self.created_issues),
            "failed": len(self.failed_issues),
            "success_rate_percent": round(self.success_rate * 100, 2),
            "processing_time": self.processing_time_seconds
        }

    def get_failed_summary(self) -> list[dict[str, str]]:
        """Get summary of failed issues."""
        summary = []
        for failed in self.failed_issues:
            summary.append({
                "title": failed.get("title", "Unknown"),
                "error": failed.get("error", "Unknown error")
            })
        return summary


class IssueCreationRequest(BaseModel):
    """Request model for issue creation."""

    template: GitHubIssueTemplate = Field(..., description="Issue template")
    repo_owner: str = Field(..., description="Repository owner")
    repo_name: str = Field(..., description="Repository name")
    dry_run: bool = Field(False, description="If true, validate but don't create")

    def get_repo_full_name(self) -> str:
        """Get full repository name."""
        return f"{self.repo_owner}/{self.repo_name}"


class IssueUpdateRequest(BaseModel):
    """Request model for updating an existing issue."""

    issue_number: int = Field(..., gt=0, description="Issue number to update")
    repo_owner: str = Field(..., description="Repository owner")
    repo_name: str = Field(..., description="Repository name")

    # Update fields (all optional)
    title: str | None = Field(None, max_length=256, description="New title")
    body: str | None = Field(None, description="New body")
    state: str | None = Field(None, description="New state (open/closed)")
    labels: list[str] | None = Field(None, description="New labels (replaces existing)")
    add_labels: list[str] | None = Field(None, description="Labels to add")
    remove_labels: list[str] | None = Field(None, description="Labels to remove")
    assignees: list[str] | None = Field(None, description="New assignees (replaces existing)")
    add_assignees: list[str] | None = Field(None, description="Assignees to add")
    remove_assignees: list[str] | None = Field(None, description="Assignees to remove")
    milestone: str | None = Field(None, description="New milestone")

    def has_updates(self) -> bool:
        """Check if request contains any updates."""
        update_fields = [
            self.title, self.body, self.state, self.labels,
            self.add_labels, self.remove_labels, self.assignees,
            self.add_assignees, self.remove_assignees, self.milestone
        ]
        return any(field is not None for field in update_fields)


# Structured output models for LLM issue generation
class IssueGenerationOutput(BaseModel):
    """Structured output for LLM issue generation using OpenAI Responses API."""
    
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Concise, descriptive issue title"
    )
    
    body: str = Field(
        ...,
        min_length=10,
        description="Detailed issue description in Markdown format"
    )
    
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Specific, testable acceptance criteria"
    )
    
    priority: str = Field(
        default="medium",
        pattern="^(critical|high|medium|low)$",
        description="Issue priority level"
    )
    
    issue_type: str = Field(
        default="feature",
        pattern="^(bug|feature|enhancement|task|documentation)$",
        description="Type of issue"
    )
    
    labels: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="Relevant labels for the issue"
    )
    
    estimated_hours: Optional[float] = Field(
        None,
        ge=0.5,
        le=160,
        description="Estimated effort in hours"
    )
    
    components: List[str] = Field(
        default_factory=list,
        description="Affected components or modules"
    )
    
    dependencies: List[str] = Field(
        default_factory=list,
        description="Blocking issues or prerequisites"
    )
    
    technical_approach: Optional[str] = Field(
        None,
        description="Suggested technical approach or implementation ideas"
    )
    
    @field_validator('title')
    @classmethod
    def validate_title_content(cls, v):
        """Ensure title is meaningful."""
        if len(v.split()) < 2:
            raise ValueError("Title must contain at least 2 words")
        return v.strip()
    
    @field_validator('labels')
    @classmethod
    def clean_labels(cls, v):
        """Clean and validate labels."""
        # Remove empty strings and duplicates
        cleaned = [label.strip().lower().replace(' ', '-') for label in v if label.strip()]
        return list(set(cleaned))
    
    def to_generated_content(self) -> GeneratedIssueContent:
        """Convert to GeneratedIssueContent for backward compatibility."""
        # Build the full issue body with all sections
        body_sections = [self.body]
        
        # Add acceptance criteria section
        if self.acceptance_criteria:
            body_sections.append("\n## Acceptance Criteria\n")
            for criterion in self.acceptance_criteria:
                body_sections.append(f"- [ ] {criterion}")
        
        # Add technical details
        if self.components or self.dependencies or self.technical_approach:
            body_sections.append("\n## Technical Details\n")
            if self.components:
                body_sections.append(f"**Affected Components:** {', '.join(self.components)}")
            if self.dependencies:
                body_sections.append(f"**Dependencies:** {', '.join(self.dependencies)}")
            if self.technical_approach:
                body_sections.append(f"\n**Suggested Approach:**\n{self.technical_approach}")
        
        # Add metadata section
        body_sections.append("\n## Metadata\n")
        body_sections.append(f"- **Priority:** {self.priority}")
        body_sections.append(f"- **Type:** {self.issue_type}")
        if self.estimated_hours:
            body_sections.append(f"- **Estimated Effort:** {self.estimated_hours} hours")
        
        # Combine all sections
        full_body = '\n'.join(body_sections)
        
        return GeneratedIssueContent(
            generated_title=self.title,
            generated_body=full_body,
            labels_to_apply=self.labels,
            priority=self.priority,
            issue_type=self.issue_type,
            estimated_hours=self.estimated_hours,
            acceptance_criteria=self.acceptance_criteria
        )
