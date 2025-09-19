"""Document-related data models for AI Scrum Master."""

from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator, HttpUrl


class DocumentType(str, Enum):
    """Types of documents that can be processed."""
    TDD = "tdd"  # Test-Driven Development
    PRD = "prd"  # Product Requirements Document
    USER_STORY = "user_story"
    TECHNICAL_SPEC = "technical_spec"
    BUG_REPORT = "bug_report"


class DocumentInput(BaseModel):
    """Input model for document parsing and task extraction."""
    
    # Document content
    tdd_content: Optional[str] = Field(None, description="TDD document content")
    prd_content: Optional[str] = Field(None, description="PRD document content")
    user_story_content: Optional[str] = Field(None, description="User story content")
    
    # Target repository
    repo_owner: str = Field(..., min_length=1, description="GitHub repository owner")
    repo_name: str = Field(..., min_length=1, description="GitHub repository name")
    
    # Options
    auto_create_issues: bool = Field(True, description="Automatically create GitHub issues")
    validate_dependencies: bool = Field(True, description="Validate task dependencies")
    assign_priorities: bool = Field(True, description="Automatically assign priorities")
    
    # Metadata
    document_source: Optional[str] = Field(None, description="Source of the document")
    project_context: Optional[str] = Field(None, description="Additional project context")
    
    @validator('repo_owner', 'repo_name')
    def validate_repo_fields(cls, v):
        """Validate repository fields."""
        if not v or not v.strip():
            raise ValueError("Repository fields cannot be empty")
        # Basic validation for GitHub naming
        if not v.replace('-', '').replace('_', '').replace('.', '').isalnum():
            raise ValueError(f"Invalid repository name format: {v}")
        return v.strip()
    
    def has_content(self) -> bool:
        """Check if at least one document is provided."""
        return bool(
            self.tdd_content or 
            self.prd_content or 
            self.user_story_content
        )
    
    @validator('tdd_content', 'prd_content', 'user_story_content')
    def validate_content_not_empty(cls, v):
        """Ensure content is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Document content cannot be empty")
        return v
    
    def get_document_types(self) -> List[DocumentType]:
        """Get list of document types provided."""
        types = []
        if self.tdd_content:
            types.append(DocumentType.TDD)
        if self.prd_content:
            types.append(DocumentType.PRD)
        if self.user_story_content:
            types.append(DocumentType.USER_STORY)
        return types


class ParsedSection(BaseModel):
    """Represents a parsed section of a document."""
    
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    level: int = Field(1, ge=1, le=6, description="Section level (1-6)")
    subsections: List['ParsedSection'] = Field(default_factory=list, description="Nested subsections")
    
    def get_flat_content(self) -> str:
        """Get flattened content including subsections."""
        content_parts = [self.content]
        for subsection in self.subsections:
            content_parts.append(subsection.get_flat_content())
        return "\n".join(content_parts)


# Allow self-reference in ParsedSection
ParsedSection.model_rebuild()


class ParsedDocument(BaseModel):
    """Represents a fully parsed document."""
    
    document_type: DocumentType = Field(..., description="Type of document")
    title: Optional[str] = Field(None, description="Document title")
    sections: List[ParsedSection] = Field(default_factory=list, description="Parsed sections")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    parsed_at: datetime = Field(default_factory=datetime.utcnow, description="Parsing timestamp")
    
    def get_section_by_title(self, title: str) -> Optional[ParsedSection]:
        """Find a section by its title."""
        title_lower = title.lower()
        for section in self.sections:
            if section.title.lower() == title_lower:
                return section
        return None
    
    def get_all_sections_flat(self) -> List[ParsedSection]:
        """Get all sections including subsections in a flat list."""
        result = []
        
        def add_section(section: ParsedSection):
            result.append(section)
            for subsection in section.subsections:
                add_section(subsection)
        
        for section in self.sections:
            add_section(section)
        
        return result


class TDDSections(BaseModel):
    """Structured representation of TDD document sections."""
    
    overview: Optional[str] = Field(None, description="Document overview")
    test_cases: List[str] = Field(default_factory=list, description="List of test cases")
    implementation_requirements: List[str] = Field(default_factory=list, description="Implementation requirements")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies")
    
    def is_valid(self) -> bool:
        """Check if TDD has minimum required content."""
        return len(self.test_cases) > 0 or len(self.implementation_requirements) > 0


class PRDSections(BaseModel):
    """Structured representation of PRD document sections."""
    
    executive_summary: Optional[str] = Field(None, description="Executive summary")
    features: List[Dict[str, Any]] = Field(default_factory=list, description="Feature specifications")
    technical_requirements: List[str] = Field(default_factory=list, description="Technical requirements")
    user_stories: List[str] = Field(default_factory=list, description="User stories")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Feature dependencies")
    success_metrics: List[str] = Field(default_factory=list, description="Success metrics")
    
    def is_valid(self) -> bool:
        """Check if PRD has minimum required content."""
        return len(self.features) > 0 or len(self.user_stories) > 0


class BriefIssueInput(BaseModel):
    """Input model for creating a single issue from a brief description."""
    
    repo_owner: str = Field(..., min_length=1, description="Repository owner")
    repo_name: str = Field(..., min_length=1, description="Repository name")
    brief_description: str = Field(..., min_length=10, description="Brief issue description")
    initial_labels: Optional[List[str]] = Field(None, description="Initial labels to apply")
    assignees: Optional[List[str]] = Field(None, description="Users to assign")
    milestone: Optional[str] = Field(None, description="Milestone to associate")
    
    @validator('brief_description')
    def validate_description_length(cls, v):
        """Ensure description is meaningful."""
        if len(v.split()) < 3:
            raise ValueError("Description must contain at least 3 words")
        return v