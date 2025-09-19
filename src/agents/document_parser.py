"""Document parsing functionality for AI Scrum Master."""

import re
from typing import Dict, List, Optional, Any
import logging
from src.models.documents import (
    ParsedDocument, ParsedSection, DocumentType,
    TDDSections, PRDSections
)
from src.core.exceptions import DocumentParsingError

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parses TDD and PRD documents into structured sections."""
    
    def __init__(self):
        """Initialize the document parser."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def parse_tdd_document(self, content: str) -> TDDSections:
        """
        Parse a TDD document into structured sections.
        
        Args:
            content: TDD document content
            
        Returns:
            TDDSections object with extracted sections
            
        Raises:
            DocumentParsingError: If parsing fails
        """
        if not content or not content.strip():
            raise DocumentParsingError("TDD", "Document is empty")
        
        self.logger.info("Parsing TDD document")
        
        try:
            parsed_doc = self._parse_markdown(content, DocumentType.TDD)
            sections = TDDSections()
            
            # Extract overview
            overview_section = self._find_section(parsed_doc, ["overview", "summary", "introduction"])
            if overview_section:
                sections.overview = overview_section.get_flat_content()
            
            # Extract test cases
            test_section = self._find_section(parsed_doc, ["test", "test cases", "tests", "testing"])
            if test_section:
                sections.test_cases = self._extract_list_items(test_section.get_flat_content())
            
            # Extract implementation requirements
            impl_section = self._find_section(parsed_doc, ["implementation", "requirements", "technical requirements"])
            if impl_section:
                sections.implementation_requirements = self._extract_list_items(impl_section.get_flat_content())
            
            # Extract acceptance criteria
            accept_section = self._find_section(parsed_doc, ["acceptance criteria", "acceptance", "criteria"])
            if accept_section:
                sections.acceptance_criteria = self._extract_list_items(accept_section.get_flat_content())
            
            # Extract dependencies
            dep_section = self._find_section(parsed_doc, ["dependencies", "depends on", "prerequisites"])
            if dep_section:
                sections.dependencies = self._extract_list_items(dep_section.get_flat_content())
            
            if not sections.is_valid():
                raise DocumentParsingError("TDD", "No valid test cases or requirements found")
            
            self.logger.info(f"Successfully parsed TDD with {len(sections.test_cases)} test cases")
            return sections
            
        except DocumentParsingError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing TDD: {str(e)}", exc_info=True)
            raise DocumentParsingError("TDD", f"Unexpected parsing error: {str(e)}")
    
    def parse_prd_document(self, content: str) -> PRDSections:
        """
        Parse a PRD document into structured sections.
        
        Args:
            content: PRD document content
            
        Returns:
            PRDSections object with extracted sections
            
        Raises:
            DocumentParsingError: If parsing fails
        """
        if not content or not content.strip():
            raise DocumentParsingError("PRD", "Document is empty")
        
        self.logger.info("Parsing PRD document")
        
        try:
            parsed_doc = self._parse_markdown(content, DocumentType.PRD)
            sections = PRDSections()
            
            # Extract executive summary
            summary_section = self._find_section(parsed_doc, ["executive summary", "summary", "overview"])
            if summary_section:
                sections.executive_summary = summary_section.get_flat_content()
            
            # Extract features
            features_section = self._find_section(parsed_doc, ["features", "feature list", "functionality"])
            if features_section:
                sections.features = self._extract_features(features_section)
            
            # Extract technical requirements
            tech_section = self._find_section(parsed_doc, ["technical requirements", "technical", "architecture"])
            if tech_section:
                sections.technical_requirements = self._extract_list_items(tech_section.get_flat_content())
            
            # Extract user stories
            stories_section = self._find_section(parsed_doc, ["user stories", "user story", "use cases"])
            if stories_section:
                sections.user_stories = self._extract_list_items(stories_section.get_flat_content())
            
            # Extract dependencies
            dep_section = self._find_section(parsed_doc, ["dependencies", "depends on", "relationships"])
            if dep_section:
                sections.dependencies = self._extract_dependencies(dep_section.get_flat_content())
            
            # Extract success metrics
            metrics_section = self._find_section(parsed_doc, ["success metrics", "metrics", "kpis", "goals"])
            if metrics_section:
                sections.success_metrics = self._extract_list_items(metrics_section.get_flat_content())
            
            if not sections.is_valid():
                raise DocumentParsingError("PRD", "No valid features or user stories found")
            
            self.logger.info(f"Successfully parsed PRD with {len(sections.features)} features")
            return sections
            
        except DocumentParsingError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing PRD: {str(e)}", exc_info=True)
            raise DocumentParsingError("PRD", f"Unexpected parsing error: {str(e)}")
    
    def _parse_markdown(self, content: str, doc_type: DocumentType) -> ParsedDocument:
        """
        Parse markdown content into a structured document.
        
        Args:
            content: Markdown content
            doc_type: Type of document
            
        Returns:
            ParsedDocument with sections
        """
        lines = content.split('\n')
        sections = []
        current_section = None
        current_content = []
        
        for line in lines:
            # Check if line is a heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if heading_match:
                # Save previous section
                if current_section:
                    current_section.content = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                # Start new section
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_section = ParsedSection(title=title, level=level, content="")
                current_content = []
            else:
                # Add to current content
                current_content.append(line)
        
        # Save last section
        if current_section:
            current_section.content = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        # Organize sections hierarchically
        organized_sections = self._organize_sections_hierarchically(sections)
        
        # Extract document title
        doc_title = None
        if organized_sections and organized_sections[0].level == 1:
            doc_title = organized_sections[0].title
            organized_sections = organized_sections[0].subsections or organized_sections[1:]
        
        return ParsedDocument(
            document_type=doc_type,
            title=doc_title,
            sections=organized_sections
        )
    
    def _organize_sections_hierarchically(self, sections: List[ParsedSection]) -> List[ParsedSection]:
        """Organize flat sections into a hierarchy based on levels."""
        if not sections:
            return []
        
        root_sections = []
        stack = []
        
        for section in sections:
            # Find parent for this section
            while stack and stack[-1].level >= section.level:
                stack.pop()
            
            if stack:
                # Add as subsection to parent
                stack[-1].subsections.append(section)
            else:
                # Add as root section
                root_sections.append(section)
            
            stack.append(section)
        
        return root_sections
    
    def _find_section(self, doc: ParsedDocument, keywords: List[str]) -> Optional[ParsedSection]:
        """Find a section by matching keywords in title."""
        keywords_lower = [k.lower() for k in keywords]
        
        for section in doc.get_all_sections_flat():
            section_title_lower = section.title.lower()
            if any(keyword in section_title_lower for keyword in keywords_lower):
                return section
        
        return None
    
    def _extract_list_items(self, content: str) -> List[str]:
        """Extract list items from content."""
        items = []
        lines = content.split('\n')
        
        for line in lines:
            # Match various list formats
            list_match = re.match(r'^[\s]*[-*+•]\s+(.+)$', line)
            numbered_match = re.match(r'^[\s]*\d+[\.)]\s+(.+)$', line)
            
            if list_match:
                items.append(list_match.group(1).strip())
            elif numbered_match:
                items.append(numbered_match.group(1).strip())
            elif line.strip() and not line.strip().startswith('#'):
                # Include non-empty lines that aren't headings
                # This helps capture items that might not be in list format
                items.append(line.strip())
        
        return items
    
    def _extract_features(self, section: ParsedSection) -> List[Dict[str, Any]]:
        """Extract features from a section."""
        features = []
        
        # Process main content
        if section.content:
            main_items = self._extract_list_items(section.content)
            for item in main_items:
                features.append({
                    "name": item,
                    "requirements": []
                })
        
        # Process subsections as features
        for subsection in section.subsections:
            feature = {
                "name": subsection.title,
                "requirements": self._extract_list_items(subsection.get_flat_content())
            }
            features.append(feature)
        
        return features
    
    def _extract_dependencies(self, content: str) -> Dict[str, List[str]]:
        """Extract dependencies from content."""
        dependencies = {}
        lines = content.split('\n')
        current_item = None
        
        for line in lines:
            # Check if line describes a dependency relationship
            dep_match = re.match(r'^(.+?)\s+(?:depends on|requires|needs)\s+(.+)$', line, re.IGNORECASE)
            if dep_match:
                item = dep_match.group(1).strip()
                deps = [d.strip() for d in dep_match.group(2).split(',')]
                dependencies[item] = deps
            else:
                # Try to parse as a list item
                list_match = re.match(r'^[\s]*[-*+]\s+(.+)$', line)
                if list_match:
                    text = list_match.group(1)
                    if ':' in text:
                        parts = text.split(':', 1)
                        current_item = parts[0].strip()
                        if len(parts) > 1:
                            deps = [d.strip() for d in parts[1].split(',')]
                            dependencies[current_item] = deps
        
        return dependencies