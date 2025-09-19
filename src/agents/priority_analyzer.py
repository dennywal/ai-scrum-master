"""Priority analysis functionality for AI Scrum Master."""

import logging

from src.models.tasks import ExtractedTask, Priority, TaskType

logger = logging.getLogger(__name__)


class PriorityAnalyzer:
    """Analyzes and assigns priorities to tasks based on keywords and dependencies."""

    def __init__(self):
        """Initialize the priority analyzer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Define priority keywords
        self.critical_keywords = [
            'critical', 'urgent', 'blocker', 'security', 'vulnerability',
            'exploit', 'breach', 'attack', 'injection', 'xss', 'csrf'
        ]

        self.high_keywords = [
            'important', 'high priority', 'must have', 'required',
            'essential', 'core', 'key', 'major'
        ]

        self.low_keywords = [
            'nice to have', 'optional', 'future', 'low priority',
            'minor', 'cosmetic', 'enhancement'
        ]

        # Task types that typically get priority boost
        self.priority_boost_types = [TaskType.BUG, TaskType.INFRASTRUCTURE]

    def analyze_priority(self, task: ExtractedTask) -> ExtractedTask:
        """
        Analyze and assign priority to a single task.
        
        Args:
            task: Task to analyze
            
        Returns:
            Task with updated priority
        """
        self.logger.debug(f"Analyzing priority for task: {task.title}")

        # If task already has critical priority, preserve it
        if task.priority == Priority.CRITICAL:
            return task

        # Check for priority keywords in title and description
        content = f"{task.title} {task.description}".lower()

        # Check for critical keywords
        if any(keyword in content for keyword in self.critical_keywords):
            task.priority = Priority.CRITICAL
            self.logger.info(f"Assigned CRITICAL priority to: {task.title}")
            return task

        # Check for high keywords
        if any(keyword in content for keyword in self.high_keywords):
            task.priority = Priority.HIGH
            self.logger.info(f"Assigned HIGH priority to: {task.title}")
            return task

        # Check for low keywords
        if any(keyword in content for keyword in self.low_keywords):
            task.priority = Priority.LOW
            self.logger.info(f"Assigned LOW priority to: {task.title}")
            return task

        # Apply task type priority boost
        if task.task_type in self.priority_boost_types:
            if task.task_type == TaskType.BUG:
                # Bugs typically get high priority
                task.priority = Priority.HIGH
                self.logger.info(f"Boosted bug task to HIGH priority: {task.title}")
            elif task.task_type == TaskType.INFRASTRUCTURE:
                # Infrastructure tasks often block others
                if task.priority == Priority.LOW:
                    task.priority = Priority.MEDIUM
                elif task.priority == Priority.MEDIUM:
                    task.priority = Priority.HIGH
                self.logger.info(f"Boosted infrastructure task priority: {task.title}")

        return task

    def analyze_priorities_batch(self, tasks: list[ExtractedTask]) -> list[ExtractedTask]:
        """
        Analyze priorities for a batch of tasks considering dependencies.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            List of tasks with updated priorities
        """
        if not tasks:
            return []

        self.logger.info(f"Analyzing priorities for {len(tasks)} tasks")

        # First pass: analyze individual task priorities
        for task in tasks:
            self.analyze_priority(task)

        # Build dependency graph
        task_map = {task.title: task for task in tasks}
        dependency_graph = self._build_dependency_graph(tasks)

        # Find tasks that block others (have dependents)
        blocking_tasks = self._find_blocking_tasks(dependency_graph)

        # Second pass: boost priority of blocking tasks
        for task_title, dependent_count in blocking_tasks.items():
            if task_title in task_map:
                task = task_map[task_title]

                # Boost priority based on how many tasks depend on it
                if dependent_count >= 2:
                    # Multiple tasks depend on this
                    if task.priority == Priority.LOW:
                        task.priority = Priority.MEDIUM
                    elif task.priority == Priority.MEDIUM:
                        task.priority = Priority.HIGH
                    elif task.priority == Priority.HIGH and dependent_count >= 3:
                        task.priority = Priority.CRITICAL

                    self.logger.info(f"Boosted priority of blocking task '{task.title}' " +
                                   f"(blocks {dependent_count} tasks)")
                elif dependent_count == 1:
                    # Single task depends on this
                    if task.priority == Priority.LOW:
                        task.priority = Priority.MEDIUM

                    self.logger.info(f"Slightly boosted priority of blocking task '{task.title}'")

        # Third pass: propagate critical priority through dependency chains
        self._propagate_critical_priority(tasks, dependency_graph)

        return tasks

    def _build_dependency_graph(self, tasks: list[ExtractedTask]) -> dict[str, set[str]]:
        """
        Build a dependency graph from tasks.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Dictionary mapping task titles to their dependents
        """
        graph = {}

        for task in tasks:
            # Initialize entry for this task
            if task.title not in graph:
                graph[task.title] = set()

            # Add this task as dependent to its dependencies
            for dep in task.dependencies:
                if dep not in graph:
                    graph[dep] = set()
                graph[dep].add(task.title)

        return graph

    def _find_blocking_tasks(self, dependency_graph: dict[str, set[str]]) -> dict[str, int]:
        """
        Find tasks that block others and count how many.
        
        Args:
            dependency_graph: Dependency graph
            
        Returns:
            Dictionary mapping task titles to count of dependent tasks
        """
        blocking_tasks = {}

        for task_title, dependents in dependency_graph.items():
            if dependents:
                blocking_tasks[task_title] = len(dependents)

        return blocking_tasks

    def _propagate_critical_priority(self, tasks: list[ExtractedTask],
                                    dependency_graph: dict[str, set[str]]):
        """
        Propagate critical priority backward through dependency chains.
        
        Args:
            tasks: List of tasks
            dependency_graph: Dependency graph
        """
        task_map = {task.title: task for task in tasks}

        # Find all critical tasks
        critical_tasks = [task for task in tasks if task.priority == Priority.CRITICAL]

        for critical_task in critical_tasks:
            # Find all tasks that this critical task depends on
            self._propagate_priority_to_dependencies(
                critical_task.title,
                task_map,
                min_priority=Priority.HIGH
            )

    def _propagate_priority_to_dependencies(self, task_title: str,
                                           task_map: dict[str, ExtractedTask],
                                           min_priority: Priority):
        """
        Recursively propagate minimum priority to dependencies.
        
        Args:
            task_title: Title of the task
            task_map: Map of task titles to tasks
            min_priority: Minimum priority to set
        """
        if task_title not in task_map:
            return

        task = task_map[task_title]

        for dep_title in task.dependencies:
            if dep_title in task_map:
                dep_task = task_map[dep_title]

                # Upgrade priority if needed
                if self._should_upgrade_priority(dep_task.priority, min_priority):
                    old_priority = dep_task.priority
                    dep_task.priority = min_priority

                    self.logger.info(f"Propagated priority from {old_priority} to {min_priority} " +
                                   f"for dependency '{dep_title}'")

                    # Recursively propagate to this task's dependencies
                    self._propagate_priority_to_dependencies(dep_title, task_map, min_priority)

    def _should_upgrade_priority(self, current: Priority, target: Priority) -> bool:
        """
        Check if priority should be upgraded.
        
        Args:
            current: Current priority
            target: Target priority
            
        Returns:
            True if priority should be upgraded
        """
        priority_order = {
            Priority.LOW: 0,
            Priority.MEDIUM: 1,
            Priority.HIGH: 2,
            Priority.CRITICAL: 3
        }

        return priority_order[current] < priority_order[target]
