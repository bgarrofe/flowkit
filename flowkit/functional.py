"""Keras-style Functional API for building workflows with multiple inputs and outputs."""

from typing import Union, Tuple, Dict, Any, Optional, List
from collections import defaultdict, deque
import concurrent.futures
import inspect

from .task import Task
from .exceptions import DAGCycleError
from .logging import get_logger, LogLevel


class AppliedTask:
    """
    Represents a task that has been applied to input layers/tasks.
    
    This is an internal node in the functional API graph that tracks
    which inputs feed into which task.
    
    Attributes:
        task: The Task object to execute
        inputs: Tuple of upstream AppliedTask or Layer nodes
        name: Name of the task
        outputs: Result of task execution (populated during run)
    """
    
    def __init__(self, task: Task, inputs: Tuple[Union['AppliedTask', 'Layer'], ...]):
        """
        Initialize an AppliedTask.
        
        Args:
            task: The Task to execute
            inputs: Tuple of upstream nodes (AppliedTask or Layer instances)
        """
        self.task = task
        self.inputs = inputs
        self.name = task.name
        self.outputs = None
    
    def __repr__(self) -> str:
        """String representation showing task and its inputs."""
        input_names = ", ".join(i.name for i in self.inputs)
        return f"{self.name}({input_names})"


class Layer:
    """
    Wrapper that makes tasks callable like Keras layers.
    
    A Layer wraps a Task and allows it to be called with other layers
    as inputs, creating a functional API graph structure.
    
    Example:
        >>> @task()
        ... def my_task(input1, input2):
        ...     return input1 + input2
        >>> 
        >>> layer = Layer(my_task)
        >>> input1 = Layer(task1)()
        >>> input2 = Layer(task2)()
        >>> output = layer(input1, input2)
    
    Attributes:
        task: The wrapped Task object
        name: Name of the task
    """
    
    def __init__(self, task: Task):
        """
        Initialize a Layer.
        
        Args:
            task: The Task to wrap
        """
        self.task = task
        self.name = task.name
    
    def __call__(self, *inputs: Union['Layer', AppliedTask]) -> AppliedTask:
        """
        Apply this layer to input layers, creating an AppliedTask node.
        
        Args:
            *inputs: Variable number of upstream Layer or AppliedTask nodes
            
        Returns:
            An AppliedTask representing this task applied to the inputs
        """
        # If no inputs provided, this is a root node
        if not inputs:
            # Create a dummy AppliedTask with no inputs
            return AppliedTask(self.task, ())
        
        # Create an AppliedTask node
        return AppliedTask(self.task, inputs)
    
    def __repr__(self) -> str:
        """String representation of the layer."""
        return f"Layer({self.name})"


class FunctionalFlow:
    """
    Functional API Flow that supports multiple inputs and outputs.
    
    This class implements a Keras-style Functional API where you define
    a computational graph by connecting layers/tasks, then specify which
    nodes are inputs and which are outputs.
    
    Example:
        >>> # Define tasks
        >>> @task()
        ... def task1():
        ...     return 1
        >>> 
        >>> @task()
        ... def task2():
        ...     return 2
        >>> 
        >>> @task()
        ... def combine(task1, task2):
        ...     return task1 + task2
        >>> 
        >>> # Build functional graph
        >>> input1 = Layer(task1)()
        >>> input2 = Layer(task2)()
        >>> output = Layer(combine)(input1, input2)
        >>> 
        >>> # Create flow
        >>> flow = FunctionalFlow(
        ...     inputs=(input1, input2),
        ...     outputs=output,
        ...     name="my_flow"
        ... )
        >>> 
        >>> # Run
        >>> results = flow.run()
    
    Attributes:
        name: Name of the flow
        inputs: Tuple of input nodes
        outputs: Tuple of output nodes
        max_workers: Maximum number of parallel workers
    """
    
    def __init__(
        self,
        inputs: Union[AppliedTask, Layer, Tuple[Union[AppliedTask, Layer], ...]],
        outputs: Union[AppliedTask, Tuple[AppliedTask, ...]],
        name: str = "functional_flow",
        max_workers: Optional[int] = None
    ):
        """
        Initialize a FunctionalFlow.
        
        Args:
            inputs: Single input node or tuple of input nodes
            outputs: Single output node or tuple of output nodes
            name: Name of the flow (default: "functional_flow")
            max_workers: Maximum number of parallel workers (default: None)
        """
        self.name = name
        self.max_workers = max_workers
        
        # Normalize inputs and outputs to tuples
        self.inputs = inputs if isinstance(inputs, tuple) else (inputs,)
        self.outputs = outputs if isinstance(outputs, tuple) else (outputs,)
        
        self.logger = get_logger()
        
        # Build the graph
        self.all_nodes: set = set()
        self.graph: Dict[AppliedTask, List[AppliedTask]] = defaultdict(list)  # node -> downstream
        self.reverse_graph: Dict[AppliedTask, List[AppliedTask]] = defaultdict(list)  # node -> upstream
        
        self._build_graph()
    
    def _build_graph(self) -> None:
        """
        Build the computational graph by traversing from outputs back to inputs.
        
        This method discovers all nodes in the graph and builds forward and
        reverse adjacency lists for dependency tracking.
        """
        def traverse(node: Union[AppliedTask, Layer]) -> None:
            """Recursively traverse the graph."""
            # Convert Layer to AppliedTask if needed
            if isinstance(node, Layer):
                node = node()
            
            if node in self.all_nodes:
                return
            
            self.all_nodes.add(node)
            
            # Traverse inputs
            for inp in node.inputs:
                # Convert Layer to AppliedTask if needed
                if isinstance(inp, Layer):
                    inp = inp()
                
                traverse(inp)
                
                # Build edges
                self.graph[inp].append(node)
                self.reverse_graph[node].append(inp)
        
        # Start from all outputs
        for output in self.outputs:
            traverse(output)
    
    def run(self, executor: str = "thread") -> Union[Any, Tuple[Any, ...]]:
        """
        Execute the functional flow with parallel execution where possible.
        
        Tasks are executed in topological order based on their dependencies.
        Tasks with satisfied dependencies run in parallel using the specified
        executor type.
        
        Args:
            executor: Type of executor to use - "thread" for ThreadPoolExecutor
                     or "process" for ProcessPoolExecutor (default: "thread")
        
        Returns:
            If single output: the output value
            If multiple outputs: tuple of output values in the same order as
                               specified in the constructor
            
        Raises:
            DAGCycleError: If a circular dependency is detected
            Exception: If any task fails (fail-fast behavior)
        """
        if not self.all_nodes:
            self.logger._log(LogLevel.WARNING, f"FunctionalFlow '{self.name}': No nodes to execute.")
            return None if len(self.outputs) == 1 else tuple(None for _ in self.outputs)
        
        # Detect cycles
        if self._has_cycle():
            self.logger._log(LogLevel.ERROR, f"FunctionalFlow '{self.name}': Circular dependency detected")
            raise DAGCycleError(f"Circular dependency detected in flow '{self.name}'")
        
        # Log flow start
        self.logger.log_dag_start(self.name, total_tasks=len(self.all_nodes))
        
        # Build indegree map
        indegree: Dict[AppliedTask, int] = {
            node: len(self.reverse_graph[node]) for node in self.all_nodes
        }
        
        # Dictionary to store node results
        results: Dict[str, Any] = {}
        
        # Choose executor type
        ExecutorClass = (
            concurrent.futures.ThreadPoolExecutor 
            if executor == "thread" 
            else concurrent.futures.ProcessPoolExecutor
        )
        
        with ExecutorClass(max_workers=self.max_workers) as pool:
            # Map futures to nodes
            futures: Dict[concurrent.futures.Future, AppliedTask] = {}
            
            # Find initial ready nodes (no dependencies)
            ready = deque([node for node in self.all_nodes if indegree[node] == 0])
            
            # Submit initial ready nodes
            for node in ready:
                future = pool.submit(self._execute_node, node, results)
                futures[future] = node
            
            completed = 0
            total = len(self.all_nodes)
            
            # Process completed nodes and submit newly ready ones
            while futures:
                for fut in concurrent.futures.as_completed(futures):
                    node = futures.pop(fut)
                    
                    try:
                        result = fut.result()
                        # Store result
                        results[node.name] = result
                        node.outputs = result
                        completed += 1
                        self.logger.log_dag_progress(self.name, completed=completed, total=total)
                    except Exception as e:
                        self.logger._log(
                            LogLevel.ERROR,
                            f"Task '{node.name}' failed: {type(e).__name__}: {str(e)}"
                        )
                        # Fail-fast: propagate the exception
                        raise
                    
                    # Unlock downstream nodes whose dependencies are now satisfied
                    for down in self.graph[node]:
                        indegree[down] -= 1
                        if indegree[down] == 0:
                            # All dependencies satisfied, submit the node
                            futures[pool.submit(self._execute_node, down, results)] = down
        
        self.logger.log_dag_complete(self.name, total_tasks=total)
        self.logger.log_system("Worker released.")
        
        # Return output(s)
        output_values = tuple(results[out.name] for out in self.outputs)
        
        # If single output, return the value directly; otherwise return tuple
        if len(output_values) == 1:
            return output_values[0]
        return output_values
    
    def _execute_node(self, node: AppliedTask, results: Dict[str, Any]) -> Any:
        """
        Execute a node with upstream results passed as kwargs.
        
        This method inspects the task function signature and passes
        upstream results that match the function's parameter names.
        
        Args:
            node: The AppliedTask node to execute
            results: Dictionary of upstream node results
            
        Returns:
            The result of the task execution
        """
        if not node.inputs:
            # No inputs, just call the task
            return node.task()
        
        # Inspect the function signature
        sig = inspect.signature(node.task.func)
        params = sig.parameters
        
        # Build kwargs from upstream results
        kwargs = {}
        for param_name in params:
            if param_name in results:
                kwargs[param_name] = results[param_name]
        
        # Call the task function with kwargs
        if kwargs:
            return node.task.func(**kwargs)
        else:
            # Function doesn't expect any of the upstream results
            return node.task()
    
    def _has_cycle(self) -> bool:
        """
        Detect if there's a cycle in the graph using DFS.
        
        Returns:
            True if a cycle is detected, False otherwise
        """
        # Track visited states: 0=unvisited, 1=visiting, 2=visited
        state: Dict[AppliedTask, int] = {node: 0 for node in self.all_nodes}
        
        def dfs(node: AppliedTask) -> bool:
            """DFS helper to detect cycles."""
            if state[node] == 1:  # Currently visiting - cycle detected
                return True
            if state[node] == 2:  # Already visited
                return False
            
            state[node] = 1  # Mark as visiting
            
            # Check all downstream nodes
            for downstream in self.graph[node]:
                if dfs(downstream):
                    return True
            
            state[node] = 2  # Mark as visited
            return False
        
        # Check each node
        for node in self.all_nodes:
            if state[node] == 0:
                if dfs(node):
                    return True
        
        return False

    def summary(self) -> None:
        """
        Print a Keras-style summary of the functional flow.

        Displays a tabular overview of all tasks in the flow including:
        - Task names
        - Input sources
        - Conditions (when present)
        - Retry counts
        - Parallel execution hints

        The tasks are displayed in topological order for clarity.
        """
        if not self.all_nodes:
            print(f"{'='*60}")
            print(f"FunctionalFlow: {self.name}")
            print(f"{'='*60}")
            print("(empty flow)")
            print(f"{'='*60}")
            return

        # Build indegree map for topological sorting
        indegree = {node: len(self.reverse_graph[node]) for node in self.all_nodes}

        # Perform topological sort
        ordered_nodes = []
        queue = deque([node for node in self.all_nodes if indegree[node] == 0])
        while queue:
            node = queue.popleft()
            ordered_nodes.append(node)
            for downstream in self.graph[node]:
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    queue.append(downstream)

        print(f"{'='*60}")
        print(f"FunctionalFlow: {self.name}")
        print(f"{'='*60}")
        print(f"{'Layer (Task)':<30} {'Input From':<25} {'Condition':<12} {'Retries':<8} Parallel")
        print(f"{'-'*60}")

        for node in ordered_nodes:
            name = node.name
            inputs = ", ".join(inp.name for inp in node.inputs) if node.inputs else "(input)"
            condition = "Yes" if node.task.when is not None else ""
            retries = node.task.retries

            # Parallel hint: multiple inputs OR any input has multiple outputs (branching)
            parallel_hint = ""
            if len(node.inputs) > 1:
                parallel_hint = "↔"
            else:
                # Check if any upstream node has multiple downstream connections (branching)
                for inp in node.inputs:
                    if len(self.graph[inp]) > 1:
                        parallel_hint = "↔"
                        break

            print(f"{name:<30} {inputs:<25} {condition:<12} {retries:<8} {parallel_hint}")

        print(f"{'-'*60}")
        print(f"Total tasks: {len(ordered_nodes)}")
        print(f"Input tasks: {len(self.inputs)}")
        print(f"Output tasks: {len(self.outputs) if isinstance(self.outputs, tuple) else 1}")
        print(f"{'='*60}")

    def visualize(self) -> str:
        """
        Generate a simple text visualization of the functional flow.
        
        Returns:
            A string representation of the flow structure
        """
        if not self.all_nodes:
            return f"FunctionalFlow: {self.name}\n(empty)"
        
        lines = [f"FunctionalFlow: {self.name}", "=" * 50]
        
        # Show inputs
        input_names = [node.name for node in self.inputs]
        lines.append(f"\nInputs: {', '.join(input_names)}")
        
        # Show outputs
        output_names = [node.name for node in self.outputs]
        lines.append(f"Outputs: {', '.join(output_names)}")
        
        lines.append("\nGraph Structure:")
        lines.append("-" * 50)
        
        for node in self.all_nodes:
            upstream_names = [n.name for n in self.reverse_graph[node]]
            downstream_names = [n.name for n in self.graph[node]]
            
            lines.append(f"\nNode: {node.name}")
            if upstream_names:
                lines.append(f"  Upstream: {', '.join(upstream_names)}")
            else:
                lines.append("  Upstream: (input)")
            if downstream_names:
                lines.append(f"  Downstream: {', '.join(downstream_names)}")
            else:
                lines.append("  Downstream: (output)")
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        """String representation of the functional flow."""
        return (
            f"FunctionalFlow(name='{self.name}', "
            f"inputs={len(self.inputs)}, "
            f"outputs={len(self.outputs)}, "
            f"nodes={len(self.all_nodes)})"
        )

