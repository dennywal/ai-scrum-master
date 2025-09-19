"""Dependency resolver for task ordering and cycle detection."""

from collections import defaultdict, deque

from src.core.base_agent import BaseAgent, Workflow
from src.core.exceptions import CircularDependencyError, DependencyError
from src.models.tasks import ExtractedTask


class DependencyResolver(BaseAgent):
    """Resolves task dependencies and creates execution order."""

    def __init__(self):
        """Initialize DependencyResolver."""
        super().__init__(name="DependencyResolver")

    def _initialize(self):
        """Initialize agent-specific components."""
        pass

    def resolve_dependencies(self, tasks: list[ExtractedTask]) -> list[ExtractedTask]:
        """Resolve dependencies and return tasks in execution order.
        
        Args:
            tasks: List of tasks with dependencies
            
        Returns:
            List of tasks in valid execution order
            
        Raises:
            CircularDependencyError: If circular dependencies detected
            DependencyError: If invalid dependencies found
        """
        if not tasks:
            return []

        # Validate all dependencies exist
        task_names = {task.title for task in tasks}
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_names:
                    raise DependencyError(
                        f"Task '{task.title}' depends on non-existent task '{dep}'",
                        [task.title, dep]
                    )

        # Perform topological sort
        return self.topological_sort(tasks)

    def topological_sort(self, tasks: list[ExtractedTask]) -> list[ExtractedTask]:
        """Perform topological sort on tasks.
        
        Args:
            tasks: List of tasks to sort
            
        Returns:
            Sorted list of tasks
            
        Raises:
            CircularDependencyError: If cycle detected
        """
        if not tasks:
            return []

        # Build adjacency list and in-degree map
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        task_map = {task.title: task for task in tasks}

        # Initialize all tasks in in_degree map
        for task in tasks:
            if task.title not in in_degree:
                in_degree[task.title] = 0

        # Build graph
        for task in tasks:
            for dep in task.dependencies:
                graph[dep].append(task.title)
                in_degree[task.title] += 1

        # Find all nodes with no incoming edges
        queue = deque([title for title in in_degree if in_degree[title] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(task_map[current])

            # Reduce in-degree for neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycle
        if len(result) != len(tasks):
            # Find cycle for better error message
            cycle = self._find_cycle(tasks)
            raise CircularDependencyError(cycle)

        return result

    def _find_cycle(self, tasks: list[ExtractedTask]) -> list[str]:
        """Find a cycle in the dependency graph.
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of task titles forming a cycle
        """
        # Build adjacency list
        graph = defaultdict(list)
        for task in tasks:
            for dep in task.dependencies:
                graph[task.title].append(dep)

        visited = set()
        rec_stack = set()
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:]

            path.pop()
            rec_stack.remove(node)
            return False

        for task in tasks:
            if task.title not in visited:
                cycle = dfs(task.title)
                if cycle:
                    return cycle if isinstance(cycle, list) else [task.title]

        return []

    def update_blocks_relationships(self, tasks: list[ExtractedTask]) -> list[ExtractedTask]:
        """Update the 'blocks' field based on dependencies.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Updated list of tasks with blocks relationships
        """
        # Create a mapping for quick lookup
        task_map = {task.title: task for task in tasks}

        # Clear existing blocks relationships
        for task in tasks:
            task.blocks = []

        # Update blocks based on dependencies
        for task in tasks:
            for dep_title in task.dependencies:
                if dep_title in task_map:
                    dep_task = task_map[dep_title]
                    if task.title not in dep_task.blocks:
                        dep_task.blocks.append(task.title)

        return tasks

    def get_dependency_levels(self, tasks: list[ExtractedTask]) -> list[list[ExtractedTask]]:
        """Group tasks by dependency levels.
        
        Level 0: Tasks with no dependencies
        Level 1: Tasks depending only on level 0
        Level n: Tasks depending on levels 0 to n-1
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of task lists, grouped by dependency level
        """
        if not tasks:
            return []

        levels = []
        remaining_tasks = list(tasks)
        assigned_tasks = set()

        while remaining_tasks:
            current_level = []
            
            for task in remaining_tasks:
                # Check if all dependencies are already assigned
                if all(dep in assigned_tasks or dep == task.title 
                       for dep in task.dependencies):
                    # Skip self-dependencies for this check
                    if not task.dependencies or all(dep in assigned_tasks 
                                                     for dep in task.dependencies 
                                                     if dep != task.title):
                        current_level.append(task)

            if not current_level:
                # No progress made, might have cycles or missing deps
                break

            levels.append(current_level)
            for task in current_level:
                assigned_tasks.add(task.title)
            
            remaining_tasks = [t for t in remaining_tasks if t not in current_level]

        return levels

    def validate_dependencies(self, tasks: list[ExtractedTask]) -> dict:
        """Validate task dependencies for issues.
        
        Args:
            tasks: List of tasks to validate
            
        Returns:
            Dictionary with validation results:
            - valid: Boolean indicating if dependencies are valid
            - errors: List of error messages
        """
        errors = []
        
        if not tasks:
            return {"valid": True, "errors": errors}

        task_names = {task.title for task in tasks}

        # Check for missing dependencies
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_names:
                    errors.append(f"Task '{task.title}' depends on non-existent task '{dep}'")

        # Check for self-dependencies
        for task in tasks:
            if task.title in task.dependencies:
                errors.append(f"Task '{task.title}' has self-dependency")

        # Check for cycles
        try:
            self.topological_sort(tasks)
        except CircularDependencyError as e:
            errors.append(f"Circular dependency detected: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def create_workflow(self, **kwargs) -> Workflow:
        """Create workflow for dependency resolution.
        
        Args:
            **kwargs: Workflow parameters
            
        Returns:
            Configured workflow
        """
        workflow = Workflow(name="dependency_resolution")
        workflow.add_step(self.validate_dependencies, "validate")
        workflow.add_step(self.resolve_dependencies, "resolve")
        workflow.add_step(self.update_blocks_relationships, "update_blocks")
        workflow.add_step(self.get_dependency_levels, "group_levels")
        return workflow