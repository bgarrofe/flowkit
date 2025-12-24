"""Keras-style Flow builder for intuitive pipeline construction."""

from typing import Optional, List, Dict, Any
from collections import defaultdict, deque
import concurrent.futures
import inspect

from .task import Task
from .exceptions import DAGCycleError
from .logging import get_logger, LogLevel


class Flow:
    """
    Keras-style flow builder for creating pipelines with an intuitive API.
    
    The Flow class provides a chainable interface for building workflows that
    feels similar to building neural network models in Keras. It supports:
    - Sequential task chaining with .add()
    - Parallel branching with .branch()
    - Merging branches with .merge()
    - Automatic dependency resolution
    - Parallel execution with thread or process pools
    
    Example:
        >>> flow = (Flow("my_pipeline", max_workers=5)
        ...     .add(task1)
        ...     .branch(task2, task3)  # Run in parallel
        ...     .merge(task4)          # Wait for both
        ...     .add(task5))
        >>> results = flow.run()
    
    Attributes:
        name: Name of the flow/pipeline
        max_workers: Maximum number of parallel workers
    """
    
    def __init__(self, name: str = "flow", max_workers: Optional[int] = None):
        """
        Initialize a Flow.
        
        Args:
            name: Name of the flow/pipeline (default: "flow")
            max_workers: Maximum number of parallel workers. If None, uses
                        the default for the chosen executor (default: None)
        """
        self.name = name
        self.max_workers = max_workers
        self.tasks: List[Task] = []
        self.graph: Dict[Task, List[Task]] = defaultdict(list)  # upstream -> downstream
        self.reverse_graph: Dict[Task, List[Task]] = defaultdict(list)  # downstream -> upstream
        self.logger = get_logger()
        self._branch_points: List[Task] = []  # Track tasks that can be merged
    
    def add(self, task: Task) -> 'Flow':
        """
        Add a task that depends on the previously added task (sequential).
        
        This creates a linear chain where each task depends on the previous one.
        
        Args:
            task: The task to add to the flow
            
        Returns:
            Self for method chaining
            
        Example:
            >>> flow.add(task1).add(task2).add(task3)
            # task1 -> task2 -> task3
        """
        self.tasks.append(task)
        
        if len(self.tasks) > 1:
            # Connect to the previous task
            prev = self.tasks[-2]
            self.graph[prev].append(task)
            self.reverse_graph[task].append(prev)
        
        # Clear branch points since we've added a sequential task
        self._branch_points = [task]
        
        return self
    
    def branch(self, *branch_tasks: Task) -> 'Flow':
        """
        Add multiple parallel branches from the last task.
        
        All branch tasks will execute in parallel after the previous task completes.
        
        Args:
            *branch_tasks: Variable number of tasks to run in parallel
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If no task has been added yet
            
        Example:
            >>> flow.add(task1).branch(task2, task3, task4)
            # task1 -> [task2, task3, task4] (all run in parallel)
        """
        if not self._branch_points:
            raise ValueError("Cannot branch before adding a task")
        
        # Get the last task(s) to branch from
        prev_tasks = self._branch_points
        
        # Connect each branch to all previous branch points
        for prev in prev_tasks:
            for branch_task in branch_tasks:
                self.graph[prev].append(branch_task)
                self.reverse_graph[branch_task].append(prev)
        
        # Add branch tasks to the task list
        for branch_task in branch_tasks:
            if branch_task not in self.tasks:
                self.tasks.append(branch_task)
        
        # Update branch points to the new branches
        self._branch_points = list(branch_tasks)
        
        return self
    
    def merge(self, merge_task: Task) -> 'Flow':
        """
        Merge all recent branches into one task.
        
        The merge task will wait for all branch tasks to complete before executing.
        
        Args:
            merge_task: The task that merges all branches
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If no branches exist to merge
            
        Example:
            >>> flow.add(task1).branch(task2, task3).merge(task4)
            # task4 waits for both task2 and task3 to complete
        """
        if not self._branch_points:
            raise ValueError("No branches to merge")
        
        # Connect all branch points to the merge task
        for branch in self._branch_points:
            self.graph[branch].append(merge_task)
            self.reverse_graph[merge_task].append(branch)
        
        # Add merge task to the task list
        if merge_task not in self.tasks:
            self.tasks.append(merge_task)
        
        # Update branch points to just the merge task
        self._branch_points = [merge_task]
        
        return self
    
    def run(self, executor: str = "thread") -> Dict[str, Any]:
        """
        Execute the flow with parallel execution where possible.
        
        Tasks are executed based on their dependencies. Tasks with satisfied
        dependencies run in parallel using the specified executor type.
        
        Args:
            executor: Type of executor to use - "thread" for ThreadPoolExecutor
                     or "process" for ProcessPoolExecutor (default: "thread")
        
        Returns:
            Dictionary mapping task names to their results
            
        Raises:
            DAGCycleError: If a circular dependency is detected
            Exception: If any task fails (fail-fast behavior)
        """
        # Collect all tasks (including transitive dependencies)
        all_tasks = set(self.tasks)
        for task in self.tasks:
            self._collect_transitive_tasks(task, all_tasks)
        
        if not all_tasks:
            self.logger._log(LogLevel.WARNING, f"Flow '{self.name}': No tasks to run.")
            return {}
        
        # Detect cycles
        if self._has_cycle(all_tasks):
            self.logger._log(LogLevel.ERROR, f"Flow '{self.name}': Circular dependency detected")
            raise DAGCycleError(f"Circular dependency detected in flow '{self.name}'")
        
        # Log flow start
        self.logger.log_dag_start(self.name, total_tasks=len(all_tasks))
        
        # Build indegree map
        indegree: Dict[Task, int] = {t: len(self.reverse_graph[t]) for t in all_tasks}
        
        # Dictionary to store task results
        results: Dict[str, Any] = {}
        
        # Choose executor type
        ExecutorClass = (
            concurrent.futures.ThreadPoolExecutor 
            if executor == "thread" 
            else concurrent.futures.ProcessPoolExecutor
        )
        
        with ExecutorClass(max_workers=self.max_workers) as pool:
            # Map futures to tasks
            futures: Dict[concurrent.futures.Future, Task] = {}
            
            # Find initial ready tasks (no dependencies)
            ready = deque([t for t in all_tasks if indegree[t] == 0])
            
            # Submit initial ready tasks
            for t in ready:
                futures[pool.submit(self._execute_task, t, {})] = t
            
            completed = 0
            total = len(all_tasks)
            
            # Process completed tasks and submit newly ready ones
            while futures:
                for fut in concurrent.futures.as_completed(futures):
                    task = futures.pop(fut)
                    
                    try:
                        result = fut.result()
                        # Store result (None means task was skipped due to condition)
                        if result is not None:
                            results[task.name] = result
                        completed += 1
                        self.logger.log_dag_progress(self.name, completed=completed, total=total)
                    except Exception as e:
                        self.logger._log(LogLevel.ERROR, f"Task '{task.name}' failed: {type(e).__name__}: {str(e)}")
                        # Fail-fast: propagate the exception
                        raise
                    
                    # Unlock downstream tasks whose dependencies are now satisfied
                    for down in self.graph[task]:
                        indegree[down] -= 1
                        if indegree[down] == 0:
                            # All dependencies satisfied, prepare kwargs from ALL available results
                            # This allows tasks to access any upstream result, not just immediate parents
                            down_kwargs = dict(results)  # Pass all results accumulated so far
                            
                            # Submit task with all upstream results
                            futures[pool.submit(self._execute_task, down, down_kwargs)] = down
        
        self.logger.log_dag_complete(self.name, total_tasks=total)
        self.logger.log_system("Worker released.")
        return results
    
    def _execute_task(self, task: Task, upstream_results: Dict[str, Any]) -> Any:
        """
        Execute a task with upstream results passed as kwargs.
        
        This method inspects the task function signature and only passes
        the upstream results that match the function's parameter names.
        
        Args:
            task: The task to execute
            upstream_results: Dictionary of upstream task results
            
        Returns:
            The result of the task execution
        """
        if not upstream_results:
            # No upstream results, just call the task
            return task()
        
        # Inspect the function signature to see what parameters it expects
        sig = inspect.signature(task.func)
        params = sig.parameters
        
        # Filter upstream_results to only include parameters the function expects
        filtered_kwargs = {}
        for param_name in params:
            if param_name in upstream_results:
                filtered_kwargs[param_name] = upstream_results[param_name]
        
        # Call the task function with filtered kwargs
        if filtered_kwargs:
            return task.func(**filtered_kwargs)
        else:
            # Function doesn't expect any of the upstream results
            return task()
    
    def _collect_transitive_tasks(self, task: Task, collected: set) -> None:
        """
        Recursively collect all downstream tasks.
        
        Args:
            task: The task to start from
            collected: Set to store collected tasks
        """
        for downstream in self.graph[task]:
            if downstream not in collected:
                collected.add(downstream)
                self._collect_transitive_tasks(downstream, collected)
    
    def _has_cycle(self, tasks: set) -> bool:
        """
        Detect if there's a cycle in the task graph using DFS.
        
        Args:
            tasks: Set of tasks to check
            
        Returns:
            True if a cycle is detected, False otherwise
        """
        # Track visited states: 0=unvisited, 1=visiting, 2=visited
        state: Dict[Task, int] = {t: 0 for t in tasks}
        
        def dfs(task: Task) -> bool:
            """DFS helper to detect cycles."""
            if state[task] == 1:  # Currently visiting - cycle detected
                return True
            if state[task] == 2:  # Already visited
                return False
            
            state[task] = 1  # Mark as visiting
            
            # Check all downstream tasks
            for downstream in self.graph[task]:
                if dfs(downstream):
                    return True
            
            state[task] = 2  # Mark as visited
            return False
        
        # Check each task
        for task in tasks:
            if state[task] == 0:
                if dfs(task):
                    return True
        
        return False
    
    def visualize(self) -> str:
        """
        Generate a simple text visualization of the flow.
        
        Returns:
            A string representation of the flow structure
        """
        if not self.tasks:
            return f"Flow: {self.name}\n(empty)"
        
        lines = [f"Flow: {self.name}", "=" * 40]
        
        # Collect all tasks including transitive
        all_tasks = set(self.tasks)
        for task in self.tasks:
            self._collect_transitive_tasks(task, all_tasks)
        
        for task in all_tasks:
            upstream_names = [t.name for t in self.reverse_graph[task]]
            downstream_names = [t.name for t in self.graph[task]]
            
            lines.append(f"\nTask: {task.name}")
            if upstream_names:
                lines.append(f"  Upstream: {', '.join(upstream_names)}")
            if downstream_names:
                lines.append(f"  Downstream: {', '.join(downstream_names)}")
            if not upstream_names and not downstream_names:
                lines.append("  (isolated task)")
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        """String representation of the flow."""
        return f"Flow(name='{self.name}', tasks={len(self.tasks)}, max_workers={self.max_workers})"

