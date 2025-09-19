"""Tests for PriorityAnalyzer class."""

from src.agents.priority_analyzer import PriorityAnalyzer
from src.models.tasks import ExtractedTask, Priority, TaskType


class TestPriorityAnalyzer:
    """Test suite for PriorityAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PriorityAnalyzer()

    def test_analyze_single_task_with_critical_keywords(self):
        """Test that critical keywords trigger critical priority."""
        task = ExtractedTask(
            title="Fix security vulnerability",
            description="Critical security issue found in authentication",
            task_type=TaskType.BUG
        )

        analyzed = self.analyzer.analyze_priority(task)

        assert analyzed.priority == Priority.CRITICAL

    def test_analyze_single_task_with_high_keywords(self):
        """Test that high priority keywords trigger high priority."""
        task = ExtractedTask(
            title="Important feature",
            description="This is a high priority must-have feature",
            task_type=TaskType.FEATURE
        )

        analyzed = self.analyzer.analyze_priority(task)

        assert analyzed.priority == Priority.HIGH

    def test_analyze_single_task_with_low_keywords(self):
        """Test that low priority keywords trigger low priority."""
        task = ExtractedTask(
            title="Nice to have feature",
            description="Optional enhancement for future release",
            task_type=TaskType.FEATURE
        )

        analyzed = self.analyzer.analyze_priority(task)

        assert analyzed.priority == Priority.LOW

    def test_analyze_single_task_default_priority(self):
        """Test that tasks without priority keywords get medium priority."""
        task = ExtractedTask(
            title="Regular feature",
            description="Standard feature implementation",
            task_type=TaskType.FEATURE
        )

        analyzed = self.analyzer.analyze_priority(task)

        assert analyzed.priority == Priority.MEDIUM

    def test_analyze_batch_with_dependencies(self):
        """Test batch analysis considers dependencies for priority."""
        tasks = [
            ExtractedTask(
                title="Database Setup",
                description="Set up database schema",
                task_type=TaskType.INFRASTRUCTURE,
                priority=Priority.MEDIUM
            ),
            ExtractedTask(
                title="User API",
                description="Implement user API endpoints",
                task_type=TaskType.FEATURE,
                priority=Priority.MEDIUM,
                dependencies=["Database Setup"]
            ),
            ExtractedTask(
                title="Admin Panel",
                description="Create admin panel",
                task_type=TaskType.FEATURE,
                priority=Priority.MEDIUM,
                dependencies=["User API", "Database Setup"]
            )
        ]

        analyzed = self.analyzer.analyze_priorities_batch(tasks)

        # Database Setup should have higher priority as it blocks others
        db_task = next(t for t in analyzed if t.title == "Database Setup")
        assert db_task.priority in [Priority.HIGH, Priority.CRITICAL]

        # User API should have elevated priority as it blocks Admin Panel
        api_task = next(t for t in analyzed if t.title == "User API")
        assert api_task.priority in [Priority.HIGH, Priority.MEDIUM]

    def test_task_type_priority_boost(self):
        """Test that certain task types get priority boost."""
        bug_task = ExtractedTask(
            title="Fix login bug",
            description="Users cannot login",
            task_type=TaskType.BUG
        )

        infra_task = ExtractedTask(
            title="Setup CI/CD",
            description="Configure continuous integration",
            task_type=TaskType.INFRASTRUCTURE
        )

        bug_analyzed = self.analyzer.analyze_priority(bug_task)
        infra_analyzed = self.analyzer.analyze_priority(infra_task)

        # Bugs should get priority boost
        assert bug_analyzed.priority in [Priority.HIGH, Priority.CRITICAL]
        # Infrastructure tasks should get priority consideration
        assert infra_analyzed.priority in [Priority.HIGH, Priority.MEDIUM]

    def test_preserve_existing_critical_priority(self):
        """Test that existing critical priority is not downgraded."""
        task = ExtractedTask(
            title="Regular task",
            description="Normal description without keywords",
            task_type=TaskType.FEATURE,
            priority=Priority.CRITICAL
        )

        analyzed = self.analyzer.analyze_priority(task)

        assert analyzed.priority == Priority.CRITICAL

    def test_analyze_empty_batch(self):
        """Test analyzing empty batch returns empty list."""
        tasks = []
        analyzed = self.analyzer.analyze_priorities_batch(tasks)
        assert analyzed == []

    def test_analyze_batch_maintains_task_count(self):
        """Test that batch analysis returns same number of tasks."""
        tasks = [
            ExtractedTask(title=f"Task {i}", description=f"Description {i}")
            for i in range(5)
        ]

        analyzed = self.analyzer.analyze_priorities_batch(tasks)

        assert len(analyzed) == len(tasks)
        assert all(isinstance(t, ExtractedTask) for t in analyzed)

    def test_security_tasks_get_critical_priority(self):
        """Test that security-related tasks automatically get critical priority."""
        tasks = [
            ExtractedTask(
                title="Fix XSS vulnerability",
                description="Cross-site scripting issue",
                task_type=TaskType.BUG
            ),
            ExtractedTask(
                title="Update security headers",
                description="Add CSP headers",
                task_type=TaskType.INFRASTRUCTURE
            ),
            ExtractedTask(
                title="Patch SQL injection",
                description="SQL injection vulnerability found",
                task_type=TaskType.BUG
            )
        ]

        analyzed = self.analyzer.analyze_priorities_batch(tasks)

        for task in analyzed:
            assert task.priority == Priority.CRITICAL

    def test_dependency_chain_priority_propagation(self):
        """Test priority propagation through dependency chain."""
        tasks = [
            ExtractedTask(
                title="Task A",
                description="First task",
                priority=Priority.LOW
            ),
            ExtractedTask(
                title="Task B",
                description="Depends on A",
                dependencies=["Task A"],
                priority=Priority.LOW
            ),
            ExtractedTask(
                title="Task C",
                description="Critical task depending on B",
                dependencies=["Task B"],
                priority=Priority.CRITICAL
            )
        ]

        analyzed = self.analyzer.analyze_priorities_batch(tasks)

        # Tasks in critical path should have elevated priority
        task_a = next(t for t in analyzed if t.title == "Task A")
        task_b = next(t for t in analyzed if t.title == "Task B")

        assert task_a.priority in [Priority.HIGH, Priority.CRITICAL]
        assert task_b.priority in [Priority.HIGH, Priority.CRITICAL]
