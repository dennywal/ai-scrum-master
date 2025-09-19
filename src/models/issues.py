"""GitHub issue-related data models for AI Scrum Master."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator


class GeneratedIssueContent(BaseModel):
    """Content generated for a GitHub issue."""
    
    generated_title: str = Field(..., min_length=1, max_length=256, description="Generated issue title")
    generated_body: str = Field(..., min_length=1, description="Generated issue body in Markdown")
    labels_to_apply: List[str] = Field(default_factory=list, description="Labels to apply to the issue")
    suggested_assignees: List[str] = Field(default_factory=list, description="Suggested assignees")
    suggested_milestone: Optional[str] = Field(None, description="Suggested milestone")
    
    @validator('generated_title')
    def validate_title(cls, v):
        """Ensure title is properly formatted."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        if len(v) > 256:
            raise ValueError("Title too long (max 256 characters)")
        return v.strip()
    
    @validator('generated_body')
    def validate_body(cls, v):
        """Ensure body has content."""
        if not v.strip():
            raise ValueError("Body cannot be empty")
        return v.strip()


class GitHubIssueTemplate(BaseModel):
    """Template for creating a GitHub issue."""
    
    title: str = Field(..., min_length=1, max_length=256, description="Issue title")
    body: str = Field(..., min_length=1, description="Issue body in Markdown format")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    assignees: List[str] = Field(default_factory=list, description="Users to assign")
    milestone: Optional[str] = Field(None, description="Milestone name or number")
    project: Optional[str] = Field(None, description="Project board name")
    
    def to_github_params(self) -> Dict[str, Any]:
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
    issue_number: Optional[int] = Field(None, description="Issue number")
    title: str = Field(..., description="Issue title")
    body: str = Field(..., description="Issue body")
    labels: List[str] = Field(default_factory=list, description="Applied labels")
    assignees: List[str] = Field(default_factory=list, description="Assigned users")
    milestone: Optional[str] = Field(None, description="Associated milestone")
    state: str = Field("open", description="Issue state")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    def get_summary(self) -> Dict[str, Any]:
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
    
    created_issues: List[GitHubIssueOutput] = Field(default_factory=list, description="Successfully created issues")
    failed_issues: List[Dict[str, Any]] = Field(default_factory=list, description="Failed issue creations")
    total_extracted_tasks: int = Field(..., ge=0, description="Total number of tasks extracted")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    
    @validator('success_rate')
    def calculate_success_rate(cls, v, values):
        """Calculate success rate if not provided."""
        if 'created_issues' in values and 'total_extracted_tasks' in values:
            total = values['total_extracted_tasks']
            if total > 0:
                return len(values['created_issues']) / total
        return v
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the batch creation."""
        return {
            "total_tasks": self.total_extracted_tasks,
            "created": len(self.created_issues),
            "failed": len(self.failed_issues),
            "success_rate_percent": round(self.success_rate * 100, 2),
            "processing_time": self.processing_time_seconds
        }
    
    def get_failed_summary(self) -> List[Dict[str, str]]:
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
    title: Optional[str] = Field(None, max_length=256, description="New title")
    body: Optional[str] = Field(None, description="New body")
    state: Optional[str] = Field(None, description="New state (open/closed)")
    labels: Optional[List[str]] = Field(None, description="New labels (replaces existing)")
    add_labels: Optional[List[str]] = Field(None, description="Labels to add")
    remove_labels: Optional[List[str]] = Field(None, description="Labels to remove")
    assignees: Optional[List[str]] = Field(None, description="New assignees (replaces existing)")
    add_assignees: Optional[List[str]] = Field(None, description="Assignees to add")
    remove_assignees: Optional[List[str]] = Field(None, description="Assignees to remove")
    milestone: Optional[str] = Field(None, description="New milestone")
    
    def has_updates(self) -> bool:
        """Check if request contains any updates."""
        update_fields = [
            self.title, self.body, self.state, self.labels,
            self.add_labels, self.remove_labels, self.assignees,
            self.add_assignees, self.remove_assignees, self.milestone
        ]
        return any(field is not None for field in update_fields)