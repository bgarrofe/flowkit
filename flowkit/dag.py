"""DAG runner for executing task workflows with parallel execution."""

from typing import Optional, Dict, Any, List
from collections import defaultdict, deque
import concurrent.futures

from .task import Task
from .exceptions import DAGCycleError
from .logging import get_logger, LogLevel


class DAG:
    """
    Directed Acyclic Graph runner for executing task workflows.
    
    The DAG automatically discovers tasks from the global registry and executes
    them in topological order, respecting dependencies. Tasks at the same level
    can be executed in parallel using ThreadPoolExecutor or ProcessPoolExecutor.
    
    Attributes:
        name: Name of the workflow
        max_workers: Maximum number of parallel workers (None = default)
    """
    
    def __init__(self, name: str = "workflow", max_workers: Optional[int] = None):
        """
        Initialize a DAG.
        
        Args:
            name: Name of the workflow (default: "workflow")
            max_workers: Maximum number of parallel workers. If None, uses
                        the default for the chosen executor (default: None)
        """
        self.name = name
        self.max_workers = max_workers
        self.logger = get_logger()
    
    def run(self, executor: str = "thread") -> Dict[str, Any]:
        """
        Execute the DAG workflow.
        
        Tasks are executed in topological order based on their dependencies.
        Tasks with no dependencies or whose dependencies are satisfied are
        executed in parallel using the specified executor.
        
        Args:
            executor: Type of executor to use - "thread" for ThreadPoolExecutor
                     or "process" for ProcessPoolExecutor (default: "thread")
        
        Returns:
            Dictionary mapping task names to their results
            
        Raises:
            DAGCycleError: If a circular dependency is detected
            Exception: If any task fails (fail-fast behavior)
        """
        tasks = Task._all_tasks
        
        if not tasks:
            self.logger._log(LogLevel.WARNING, "No tasks defined.")
            return {}
        
        # Detect cycles by checking if topological sort is possible
        if self._has_cycle(tasks):
            self.logger._log(LogLevel.ERROR, "Circular dependency detected in DAG")
            raise DAGCycleError("Circular dependency detected in DAG")
        
        # Log DAG start
        self.logger.log_dag_start(self.name, total_tasks=len(tasks))
        
        # Build adjacency list and calculate indegree for each task
        adj: Dict[Task, List[Task]] = defaultdict(list)
        indegree: Dict[Task, int] = {t: len(t.upstream) for t in tasks}
        
        for task in tasks:
            for down in task.downstream:
                adj[task].append(down)
        
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
            ready = deque([t for t in tasks if indegree[t] == 0])
            
            # Submit initial ready tasks
            for t in ready:
                # Gather upstream results as arguments
                args = [results[u.name] for u in t.upstream]
                futures[pool.submit(t, *args)] = t
            
            completed = 0
            total = len(tasks)
            
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
                    for down in adj[task]:
                        indegree[down] -= 1
                        if indegree[down] == 0:
                            # All dependencies satisfied, submit for execution
                            args = [results.get(u.name) for u in down.upstream]
                            futures[pool.submit(down, *args)] = down
        
        self.logger.log_dag_complete(self.name, total_tasks=total)
        self.logger.log_system("Worker released.")
        return results
    
    def _has_cycle(self, tasks: List[Task]) -> bool:
        """
        Detect if there's a cycle in the task graph using DFS.
        
        Args:
            tasks: List of tasks to check
            
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
            for downstream in task.downstream:
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
        Generate a simple text visualization of the DAG.
        
        Returns:
            A string representation of the DAG structure
        """
        tasks = Task._all_tasks
        
        if not tasks:
            return "Empty DAG (no tasks defined)"
        
        lines = [f"DAG: {self.name}", "=" * 40]
        
        for task in tasks:
            upstream_names = [t.name for t in task.upstream]
            downstream_names = [t.name for t in task.downstream]
            
            lines.append(f"\nTask: {task.name}")
            if upstream_names:
                lines.append(f"  Upstream: {', '.join(upstream_names)}")
            if downstream_names:
                lines.append(f"  Downstream: {', '.join(downstream_names)}")
            if not upstream_names and not downstream_names:
                lines.append("  (isolated task)")
        
        return "\n".join(lines)

