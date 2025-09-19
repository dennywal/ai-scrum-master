"""Task extraction functionality for AI Scrum Master."""

import logging
import re
from typing import Any

from src.core.exceptions import TaskExtractionError
from src.models.documents import PRDSections, TDDSections
from src.models.tasks import ExtractedTask, Priority, TaskType

logger = logging.getLogger(__name__)


class TaskExtractor:
    """Extracts actionable tasks from parsed document sections."""

    def __init__(self):
        """Initialize the task extractor."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_tasks_from_tdd(self, sections: TDDSections) -> list[ExtractedTask]:
        """
        Extract tasks from TDD sections.
        
        Args:
            sections: Parsed TDD sections
            
        Returns:
            List of extracted tasks
            
        Raises:
            TaskExtractionError: If no tasks can be extracted
        """
        self.logger.info("Extracting tasks from TDD sections")
        tasks = []

        # Extract tasks from test cases
        for test_case in sections.test_cases:
            task = self._create_task_from_test_case(test_case)
            tasks.append(task)

        # Extract tasks from implementation requirements
        for requirement in sections.implementation_requirements:
            task = self._create_task_from_requirement(requirement)
            tasks.append(task)

        # Add acceptance criteria to all tasks if available
        if sections.acceptance_criteria:
            for task in tasks:
                if not task.acceptance_criteria:
                    task.acceptance_criteria = sections.acceptance_criteria

        # Extract dependencies if specified
        if sections.dependencies:
            self._apply_dependencies_to_tasks(tasks, sections.dependencies)

        if not tasks:
            raise TaskExtractionError("TDD", "No tasks found in document")

        self.logger.info(f"Extracted {len(tasks)} tasks from TDD")
        return tasks

    def extract_tasks_from_prd(self, sections: PRDSections) -> list[ExtractedTask]:
        """
        Extract tasks from PRD sections.
        
        Args:
            sections: Parsed PRD sections
            
        Returns:
            List of extracted tasks
            
        Raises:
            TaskExtractionError: If no tasks can be extracted
        """
        self.logger.info("Extracting tasks from PRD sections")
        tasks = []

        # Extract tasks from features
        for feature in sections.features:
            task = self._create_task_from_feature(feature)
            tasks.append(task)

        # Extract tasks from user stories
        for story in sections.user_stories:
            task = self._create_task_from_user_story(story)
            tasks.append(task)

        # Apply dependencies if specified
        if sections.dependencies:
            self._apply_prd_dependencies(tasks, sections.dependencies)

        if not tasks:
            raise TaskExtractionError("PRD", "No tasks found in document")

        self.logger.info(f"Extracted {len(tasks)} tasks from PRD")
        return tasks

    def extract_acceptance_criteria(self, description: str) -> list[str]:
        """
        Extract acceptance criteria from a task description.
        
        Args:
            description: Task description text
            
        Returns:
            List of acceptance criteria
        """
        criteria = []

        # Look for explicit "Acceptance Criteria" section
        # Use more flexible pattern to match various formats
        ac_pattern = r"(?:Acceptance Criteria|AC|Criteria):?\s*\n((?:\s*[-*]\s*.+\n?)+)"
        ac_match = re.search(ac_pattern, description, re.IGNORECASE | re.MULTILINE)

        if ac_match:
            criteria_text = ac_match.group(1)
            # Extract individual criteria
            criteria_lines = re.findall(r"[-*]\s*(.+)", criteria_text)
            criteria.extend([line.strip() for line in criteria_lines])

        return criteria

    def _create_task_from_test_case(self, test_case: str) -> ExtractedTask:
        """Create a task from a test case."""
        task = ExtractedTask(
            title=self._clean_title(test_case),
            description=f"Test case: {test_case}",
            task_type=TaskType.TEST,
            priority=self._detect_priority(test_case),
            source_document="TDD",
            source_section="test_cases"
        )

        # Extract acceptance criteria from the test case description
        criteria = self.extract_acceptance_criteria(test_case)
        if criteria:
            task.acceptance_criteria = criteria
        else:
            # Use the test case itself as acceptance criterion
            task.acceptance_criteria = [test_case]

        return task

    def _create_task_from_requirement(self, requirement: str) -> ExtractedTask:
        """Create a task from an implementation requirement."""
        task_type = self._detect_task_type(requirement)

        task = ExtractedTask(
            title=self._clean_title(requirement),
            description=requirement,
            task_type=task_type,
            priority=self._detect_priority(requirement),
            source_document="TDD",
            source_section="implementation_requirements"
        )

        # Extract acceptance criteria if embedded in requirement
        criteria = self.extract_acceptance_criteria(requirement)
        if criteria:
            task.acceptance_criteria = criteria

        return task

    def _create_task_from_feature(self, feature: dict[str, Any]) -> ExtractedTask:
        """Create a task from a PRD feature."""
        name = feature.get("name", "Unnamed Feature")
        requirements = feature.get("requirements", [])

        task = ExtractedTask(
            title=self._clean_title(name),
            description=f"Implement feature: {name}",
            task_type=TaskType.FEATURE,
            priority=self._detect_priority(name),
            technical_requirements=requirements,
            source_document="PRD",
            source_section="features"
        )

        # Convert requirements to acceptance criteria if needed
        if requirements and not task.acceptance_criteria:
            task.acceptance_criteria = requirements[:3]  # Use first 3 as criteria

        return task

    def _create_task_from_user_story(self, story: str) -> ExtractedTask:
        """Create a task from a user story."""
        # Parse user story format: "As a ..., I want ... so that ..."
        story_pattern = r"As (?:a|an)\s+(.+?),\s*I want\s+(.+?)(?:\s+so that\s+(.+))?$"
        match = re.match(story_pattern, story, re.IGNORECASE)

        if match:
            want = match.group(2)

            title = f"Implement: {want}"
            description = story
        else:
            title = self._clean_title(story)
            description = story

        task = ExtractedTask(
            title=title,
            description=description,
            task_type=TaskType.FEATURE,
            priority=self._detect_priority(story),
            source_document="PRD",
            source_section="user_stories"
        )

        return task

    def _detect_task_type(self, text: str) -> TaskType:
        """Detect the type of task from text."""
        text_lower = text.lower()

        if any(word in text_lower for word in ["bug", "fix", "issue", "error"]):
            return TaskType.BUG
        elif any(word in text_lower for word in ["test", "verify", "validate"]):
            return TaskType.TEST
        elif any(word in text_lower for word in ["document", "docs", "readme"]):
            return TaskType.DOCUMENTATION
        elif any(word in text_lower for word in ["refactor", "restructure", "reorganize"]):
            return TaskType.REFACTOR
        elif any(word in text_lower for word in ["research", "investigate", "explore"]):
            return TaskType.RESEARCH
        elif any(word in text_lower for word in ["infrastructure", "deploy", "ci/cd", "pipeline"]):
            return TaskType.INFRASTRUCTURE
        else:
            return TaskType.FEATURE

    def _detect_priority(self, text: str) -> Priority:
        """Detect priority from text keywords."""
        text_lower = text.lower()

        critical_keywords = ["critical", "urgent", "blocker", "security", "vulnerability"]
        high_keywords = ["important", "high priority", "must have", "required"]
        low_keywords = ["nice to have", "optional", "future", "low priority"]

        if any(keyword in text_lower for keyword in critical_keywords):
            return Priority.CRITICAL
        elif any(keyword in text_lower for keyword in high_keywords):
            return Priority.HIGH
        elif any(keyword in text_lower for keyword in low_keywords):
            return Priority.LOW
        else:
            return Priority.MEDIUM

    def _clean_title(self, text: str) -> str:
        """Clean and format task title."""
        # Remove common prefixes
        text = re.sub(r"^(implement|create|add|build|develop)\s+", "", text, flags=re.IGNORECASE)

        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]

        # Limit length
        if len(text) > 200:
            text = text[:197] + "..."

        return text.strip()

    def _apply_dependencies_to_tasks(self, tasks: list[ExtractedTask], dependencies: list[str]):
        """Apply dependencies to tasks from TDD."""
        # For TDD, dependencies are usually sequential or listed
        for _i, task in enumerate(tasks):
            for dep_text in dependencies:
                if dep_text in task.description or dep_text in task.title:
                    # Find matching task
                    for other_task in tasks:
                        if other_task != task and (dep_text in other_task.title or dep_text in other_task.description):
                            task.dependencies.append(other_task.title)

    def _apply_prd_dependencies(self, tasks: list[ExtractedTask], dependencies: dict[str, list[str]]):
        """Apply dependencies to tasks from PRD."""
        for task in tasks:
            # Check if this task has dependencies defined
            for dep_key, dep_list in dependencies.items():
                if dep_key in task.title or task.title in dep_key:
                    for dep in dep_list:
                        # Find matching task
                        for other_task in tasks:
                            if dep in other_task.title or other_task.title in dep:
                                if other_task.title not in task.dependencies:
                                    task.dependencies.append(other_task.title)
                                break
                        else:
                            # Dependency not found in current tasks, add as external
                            if dep not in task.dependencies:
                                task.dependencies.append(dep)
