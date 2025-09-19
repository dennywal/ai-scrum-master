"""Tests for DependencyResolver class."""

import pytest

from src.agents.dependency_resolver import DependencyResolver
from src.core.exceptions import CircularDependencyError, DependencyError
from src.models.tasks import ExtractedTask, Priority, TaskType


class TestDependencyResolver:
    """Test suite for DependencyResolver."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = DependencyResolver()

    def test_resolve_simple_dependencies(self):
        """Test resolving simple linear dependencies."""
        tasks = [
            ExtractedTask(
                title="Task A",
                description="First task",
                dependencies=[]
            ),
            ExtractedTask(
                title="Task B",
                description="Second task",
                dependencies=["Task A"]
            ),
            ExtractedTask(
                title="Task C",
                description="Third task",
                dependencies=["Task B"]
            )
        ]

        ordered_tasks = self.resolver.resolve_dependencies(tasks)

        assert len(ordered_tasks) == 3
        assert ordered_tasks[0].title == "Task A"
        assert ordered_tasks[1].title == "Task B"
        assert ordered_tasks[2].title == "Task C"

    def test_resolve_parallel_dependencies(self):
        """Test resolving tasks that can be done in parallel."""
        tasks = [
            ExtractedTask(
                title="Task A",
                description="Independent task 1",
                dependencies=[]
            ),
            ExtractedTask(
                title="Task B",
                description="Independent task 2",
                dependencies=[]
            ),
            ExtractedTask(
                title="Task C",
                description="Depends on both",
                dependencies=["Task A", "Task B"]
            )
        ]

        ordered_tasks = self.resolver.resolve_dependencies(tasks)

        assert len(ordered_tasks) == 3
        assert ordered_tasks[2].title == "Task C"
        # Tasks A and B can be in any order
        assert {ordered_tasks[0].title, ordered_tasks[1].title} == {"Task A", "Task B"}

    def test_detect_circular_dependencies(self):
        """Test detection of circular dependencies."""
        tasks = [
            ExtractedTask(
                title="Task A",
                description="First task",
                dependencies=["Task C"]
            ),
            ExtractedTask(
                title="Task B",
                description="Second task",
                dependencies=["Task A"]
            ),
            ExtractedTask(
                title="Task C",
                description="Third task",
                dependencies=["Task B"]
            )
        ]

        with pytest.raises(CircularDependencyError) as exc_info:
            self.resolver.resolve_dependencies(tasks)

        assert "Circular dependency detected" in str(exc_info.value)

    def test_missing_dependency_error(self):
        """Test error when dependency doesn't exist."""
        tasks = [
            ExtractedTask(
                title="Task A",
                description="Task with missing dep",
                dependencies=["Non-existent Task"]
            )
        ]

        with pytest.raises(DependencyError) as exc_info:
            self.resolver.resolve_dependencies(tasks)

        assert "Non-existent Task" in str(exc_info.value)

    def test_complex_dependency_graph(self):
        """Test resolving complex dependency graph."""
        tasks = [
            ExtractedTask(
                title="Database Setup",
                description="Set up database",
                dependencies=[]
            ),
            ExtractedTask(
                title="API Framework",
                description="Set up API framework",
                dependencies=[]
            ),
            ExtractedTask(
                title="User Model",
                description="Create user model",
                dependencies=["Database Setup"]
            ),
            ExtractedTask(
                title="Auth Service",
                description="Create auth service",
                dependencies=["User Model", "API Framework"]
            ),
            ExtractedTask(
                title="User Controller",
                description="Create user controller",
                dependencies=["Auth Service", "User Model"]
            ),
            ExtractedTask(
                title="Frontend Setup",
                description="Set up frontend",
                dependencies=[]
            ),
            ExtractedTask(
                title="Login UI",
                description="Create login UI",
                dependencies=["Frontend Setup"]
            ),
            ExtractedTask(
                title="Integration",
                description="Integrate frontend with backend",
                dependencies=["Login UI", "User Controller"]
            )
        ]

        ordered_tasks = self.resolver.resolve_dependencies(tasks)

        assert len(ordered_tasks) == 8

        # Create a mapping for easier validation
        task_index = {task.title: idx for idx, task in enumerate(ordered_tasks)}

        # Validate dependencies are respected
        assert task_index["Database Setup"] < task_index["User Model"]
        assert task_index["User Model"] < task_index["Auth Service"]
        assert task_index["API Framework"] < task_index["Auth Service"]
        assert task_index["Auth Service"] < task_index["User Controller"]
        assert task_index["User Model"] < task_index["User Controller"]
        assert task_index["Frontend Setup"] < task_index["Login UI"]
        assert task_index["Login UI"] < task_index["Integration"]
        assert task_index["User Controller"] < task_index["Integration"]

    def test_update_blocks_relationships(self):
        """Test updating blocks relationships based on dependencies."""
        tasks = [
            ExtractedTask(
                title="Task A",
                description="First task",
                dependencies=[]
            ),
            ExtractedTask(
                title="Task B",
                description="Second task",
                dependencies=["Task A"]
            ),
            ExtractedTask(
                title="Task C",
                description="Third task",
                dependencies=["Task A", "Task B"]
            )
        ]

        updated_tasks = self.resolver.update_blocks_relationships(tasks)

        # Find tasks by title
        task_a = next(t for t in updated_tasks if t.title == "Task A")
        task_b = next(t for t in updated_tasks if t.title == "Task B")
        task_c = next(t for t in updated_tasks if t.title == "Task C")

        # Task A blocks both B and C
        assert "Task B" in task_a.blocks
        assert "Task C" in task_a.blocks

        # Task B blocks C
        assert "Task C" in task_b.blocks

        # Task C blocks nothing
        assert len(task_c.blocks) == 0

    def test_get_dependency_levels(self):
        """Test getting tasks organized by dependency levels."""
        tasks = [
            ExtractedTask(
                title="Level 0 - A",
                description="No dependencies",
                dependencies=[]
            ),
            ExtractedTask(
                title="Level 0 - B",
                description="No dependencies",
                dependencies=[]
            ),
            ExtractedTask(
                title="Level 1 - A",
                description="One level deep",
                dependencies=["Level 0 - A"]
            ),
            ExtractedTask(
                title="Level 2 - A",
                description="Two levels deep",
                dependencies=["Level 1 - A"]
            ),
            ExtractedTask(
                title="Level 2 - B",
                description="Two levels deep",
                dependencies=["Level 0 - A", "Level 0 - B", "Level 1 - A"]
            )
        ]

        levels = self.resolver.get_dependency_levels(tasks)

        assert len(levels) == 3

        # Level 0: tasks with no dependencies
        assert len(levels[0]) == 2
        level_0_titles = {t.title for t in levels[0]}
        assert level_0_titles == {"Level 0 - A", "Level 0 - B"}

        # Level 1: tasks depending on level 0
        assert len(levels[1]) == 1
        assert levels[1][0].title == "Level 1 - A"

        # Level 2: tasks depending on level 0 or 1
        assert len(levels[2]) == 2
        level_2_titles = {t.title for t in levels[2]}
        assert level_2_titles == {"Level 2 - A", "Level 2 - B"}

    def test_validate_dependencies_empty_list(self):
        """Test validating empty task list."""
        tasks = []
        result = self.resolver.validate_dependencies(tasks)
        assert result == {"valid": True, "errors": []}

    def test_validate_dependencies_with_errors(self):
        """Test validation with various dependency errors."""
        tasks = [
            ExtractedTask(
                title="Task A",
                description="Has missing dependency",
                dependencies=["Missing Task"]
            ),
            ExtractedTask(
                title="Task C",
                description="Part of cycle",
                dependencies=["Task D"]
            ),
            ExtractedTask(
                title="Task D",
                description="Part of cycle",
                dependencies=["Task C"]
            )
        ]

        result = self.resolver.validate_dependencies(tasks)

        assert result["valid"] is False
        assert len(result["errors"]) >= 2
        
        error_messages = " ".join(result["errors"])
        assert "Missing Task" in error_messages
        assert "circular" in error_messages.lower() or "cycle" in error_messages.lower()
        
    def test_self_dependency_prevented_by_model(self):
        """Test that self-dependencies are prevented at model validation level."""
        with pytest.raises(ValueError) as exc_info:
            ExtractedTask(
                title="Task B",
                description="Self dependency",
                dependencies=["Task B"]
            )
        
        assert "cannot depend on itself" in str(exc_info.value)

    def test_topological_sort_empty(self):
        """Test topological sort with empty list."""
        result = self.resolver.topological_sort([])
        assert result == []

    def test_topological_sort_single_task(self):
        """Test topological sort with single task."""
        tasks = [
            ExtractedTask(
                title="Single Task",
                description="Only task",
                dependencies=[]
            )
        ]
        
        result = self.resolver.topological_sort(tasks)
        assert len(result) == 1
        assert result[0].title == "Single Task"