"""Tests for TaskExtractor class."""

import pytest

from src.agents.task_extractor import TaskExtractor
from src.core.exceptions import TaskExtractionError
from src.models.documents import PRDSections, TDDSections
from src.models.tasks import ExtractedTask, Priority, TaskType


class TestTaskExtractor:
    """Test suite for TaskExtractor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = TaskExtractor()

    def test_extract_tasks_from_tdd_with_test_cases(self):
        """Test extracting tasks from TDD with test cases."""
        tdd_sections = TDDSections(
            overview="User authentication system",
            test_cases=[
                "User can register with email and password",
                "User can login with valid credentials",
                "User cannot login with invalid credentials"
            ],
            implementation_requirements=[
                "Use JWT for authentication",
                "Store passwords securely with bcrypt"
            ],
            acceptance_criteria=[
                "All endpoints must be secured",
                "Response time under 200ms"
            ]
        )

        tasks = self.extractor.extract_tasks_from_tdd(tdd_sections)

        assert len(tasks) >= 3
        assert all(isinstance(task, ExtractedTask) for task in tasks)

        # Check first test case task
        test_task = next((t for t in tasks if "register" in t.title.lower()), None)
        assert test_task is not None
        assert test_task.task_type == TaskType.TEST
        assert len(test_task.acceptance_criteria) > 0

    def test_extract_tasks_from_tdd_with_implementation_requirements(self):
        """Test extracting implementation tasks from TDD."""
        tdd_sections = TDDSections(
            implementation_requirements=[
                "Implement user registration endpoint",
                "Create database schema for users",
                "Set up email verification service"
            ]
        )

        tasks = self.extractor.extract_tasks_from_tdd(tdd_sections)

        assert len(tasks) == 3
        assert all(t.task_type == TaskType.FEATURE for t in tasks)
        assert "registration" in tasks[0].title.lower()
        assert "database" in tasks[1].title.lower()
        assert "email" in tasks[2].title.lower()

    def test_extract_tasks_from_prd_with_features(self):
        """Test extracting tasks from PRD with features."""
        prd_sections = PRDSections(
            features=[
                {
                    "name": "User Dashboard",
                    "requirements": [
                        "Display user profile information",
                        "Show recent activity",
                        "Allow profile editing"
                    ]
                },
                {
                    "name": "Notification System",
                    "requirements": [
                        "Email notifications",
                        "In-app notifications"
                    ]
                }
            ]
        )

        tasks = self.extractor.extract_tasks_from_prd(prd_sections)

        assert len(tasks) >= 2

        dashboard_task = next((t for t in tasks if "Dashboard" in t.title), None)
        assert dashboard_task is not None
        assert dashboard_task.task_type == TaskType.FEATURE
        assert len(dashboard_task.technical_requirements) >= 3

        notification_task = next((t for t in tasks if "Notification" in t.title), None)
        assert notification_task is not None
        assert len(notification_task.technical_requirements) >= 2

    def test_extract_tasks_from_prd_with_user_stories(self):
        """Test extracting tasks from PRD user stories."""
        prd_sections = PRDSections(
            user_stories=[
                "As a user, I want to reset my password so that I can regain access",
                "As an admin, I want to view user activity logs"
            ]
        )

        tasks = self.extractor.extract_tasks_from_prd(prd_sections)

        assert len(tasks) == 2
        assert all(t.task_type == TaskType.FEATURE for t in tasks)
        assert any("password" in t.title.lower() for t in tasks)
        assert any("activity" in t.title.lower() for t in tasks)

    def test_extract_acceptance_criteria_from_description(self):
        """Test extracting acceptance criteria from task description."""
        description = """
        Implement user login functionality.
        
        Acceptance Criteria:
        - User can login with email and password
        - Invalid credentials show error message
        - Successful login redirects to dashboard
        
        The system should validate input and provide feedback.
        """

        criteria = self.extractor.extract_acceptance_criteria(description)

        assert len(criteria) == 3
        assert "email and password" in criteria[0]
        assert "error message" in criteria[1]
        assert "dashboard" in criteria[2]

    def test_extract_tasks_with_dependencies(self):
        """Test that dependencies are properly extracted."""
        prd_sections = PRDSections(
            features=[
                {"name": "Database Setup", "requirements": ["Create schema"]},
                {"name": "User API", "requirements": ["Depends on Database Setup"]}
            ],
            dependencies={
                "User API": ["Database Setup"],
                "Admin Panel": ["User API", "Authentication"]
            }
        )

        tasks = self.extractor.extract_tasks_from_prd(prd_sections)

        user_api_task = next((t for t in tasks if "User API" in t.title), None)
        assert user_api_task is not None
        assert "Database Setup" in user_api_task.dependencies

    def test_empty_tdd_sections_raises_error(self):
        """Test that empty TDD sections raise an error."""
        tdd_sections = TDDSections()

        with pytest.raises(TaskExtractionError) as exc_info:
            self.extractor.extract_tasks_from_tdd(tdd_sections)

        assert "No tasks found" in str(exc_info.value)

    def test_empty_prd_sections_raises_error(self):
        """Test that empty PRD sections raise an error."""
        prd_sections = PRDSections()

        with pytest.raises(TaskExtractionError) as exc_info:
            self.extractor.extract_tasks_from_prd(prd_sections)

        assert "No tasks found" in str(exc_info.value)

    def test_task_priority_detection(self):
        """Test that critical keywords trigger high priority."""
        tdd_sections = TDDSections(
            test_cases=["Fix critical security vulnerability in authentication"]
        )

        tasks = self.extractor.extract_tasks_from_tdd(tdd_sections)

        assert len(tasks) == 1
        assert tasks[0].priority == Priority.CRITICAL

    def test_task_type_classification(self):
        """Test correct classification of task types."""
        tdd_sections = TDDSections(
            test_cases=["Test user login"],
            implementation_requirements=[
                "Fix bug in password validation",
                "Refactor authentication module",
                "Document API endpoints"
            ]
        )

        tasks = self.extractor.extract_tasks_from_tdd(tdd_sections)

        test_task = next((t for t in tasks if "Test" in t.title), None)
        assert test_task.task_type == TaskType.TEST

        bug_task = next((t for t in tasks if "Fix bug" in t.title), None)
        assert bug_task.task_type == TaskType.BUG

        refactor_task = next((t for t in tasks if "Refactor" in t.title), None)
        assert refactor_task.task_type == TaskType.REFACTOR

        doc_task = next((t for t in tasks if "Document" in t.title), None)
        assert doc_task.task_type == TaskType.DOCUMENTATION
