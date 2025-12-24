"""Task class and decorator for defining workflow tasks."""

from functools import wraps
from typing import Callable, Optional, List, Any, Union
import time
import random

from .logging import get_logger


class Task:
    """
    A task represents a unit of work in a workflow.
    
    Tasks can be chained together using the >> operator to define dependencies.
    They support retry logic, conditional execution, and automatic registration
    for DAG execution.
    
    Attributes:
        func: The function to execute
        name: The task name (derived from function name)
        upstream: List of tasks that must complete before this task
        downstream: List of tasks that depend on this task
        retries: Number of retry attempts on failure
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for exponential backoff
        when: Optional condition function to determine if task should run
    """
    
    _all_tasks: List['Task'] = []  # Global task registry for DAG discovery
    
    def __init__(
        self,
        func: Callable,
        *,
        retries: int = 0,
        delay: float = 1.0,
        backoff: float = 2.0,
        when: Optional[Callable[..., bool]] = None,
    ):
        """
        Initialize a Task.
        
        Args:
            func: The function to execute
            retries: Number of retry attempts on failure (default: 0)
            delay: Initial delay between retries in seconds (default: 1.0)
            backoff: Multiplier for exponential backoff (default: 2.0)
            when: Optional condition function that receives upstream results
                  and returns True if task should execute (default: None)
        """
        self.func = func
        self.name = func.__name__
        self.upstream: List['Task'] = []
        self.downstream: List['Task'] = []
        self.retries = retries
        self.delay = delay
        self.backoff = backoff
        self.when = when
        self.logger = get_logger()
        wraps(func)(self)
        Task._all_tasks.append(self)
    
    def __call__(self, *args, **kwargs) -> Any:
        """
        Execute the task with retry logic and conditional execution.
        
        Args:
            *args: Positional arguments (typically upstream task results)
            **kwargs: Keyword arguments
            
        Returns:
            The result of the task function, or None if skipped
            
        Raises:
            Exception: If task fails after all retry attempts
        """
        # Conditional execution check
        if self.when is not None:
            # Pass the first upstream result to the condition function
            if args:
                if not self.when(args[0]):
                    self.logger.log_task_skip(self.name, reason="condition not met")
                    return None
            else:
                self.logger.log_task_skip(self.name, reason="no upstream data")
                return None
        
        self.logger.log_task_start(self.name)
        
        # Retry logic with exponential backoff and jitter
        attempt = 0
        current_delay = self.delay
        start_time = time.time()
        
        while True:
            try:
                result = self.func(*args, **kwargs)
                duration = time.time() - start_time
                self.logger.log_task_success(self.name, duration=duration)
                return result
            except Exception as e:
                attempt += 1
                if attempt > self.retries:
                    self.logger.log_task_failure(self.name, e)
                    raise
                if self.retries > 0:
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, current_delay * 0.1)
                    total_delay = current_delay + jitter
                    self.logger.log_task_retry(self.name, attempt=attempt, max_retries=self.retries, delay=total_delay)
                    time.sleep(total_delay)
                    current_delay *= self.backoff
    
    def __rshift__(self, other: Union['Task', List['Task']]) -> Union['Task', List['Task']]:
        """
        Define downstream dependencies using >> operator.
        
        Supports both single task and list of tasks (fan-out/branching).
        
        Examples:
            task1 >> task2              # Linear chain
            task1 >> [task2, task3]     # Branching (fan-out)
        
        Args:
            other: A single Task or list of Tasks to depend on this task
            
        Returns:
            The downstream task(s) for further chaining
        """
        if isinstance(other, list):
            for t in other:
                t.upstream.append(self)
                self.downstream.append(t)
            return other
        else:
            other.upstream.append(self)
            self.downstream.append(other)
            return other
    
    def __rrshift__(self, other: Union['Task', List['Task']]) -> 'Task':
        """
        Define upstream dependencies using >> operator (reverse).
        
        Supports merging multiple tasks into one (fan-in).
        
        Examples:
            [task1, task2] >> task3     # Merging (fan-in)
        
        Args:
            other: A single Task or list of Tasks that this task depends on
            
        Returns:
            This task for further chaining
        """
        if isinstance(other, list):
            for t in other:
                self.upstream.append(t)
                t.downstream.append(self)
        else:
            self.upstream.append(other)
            other.downstream.append(self)
        return self
    
    def __repr__(self) -> str:
        """String representation of the task."""
        return f"Task(name='{self.name}', upstream={len(self.upstream)}, downstream={len(self.downstream)})"
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear the global task registry. Useful for testing and REPL usage."""
        cls._all_tasks.clear()


def task(
    *,
    retries: int = 0,
    delay: float = 1.0,
    backoff: float = 2.0,
    when: Optional[Callable[..., bool]] = None,
) -> Callable[[Callable], Task]:
    """
    Decorator to convert a function into a Task.
    
    Args:
        retries: Number of retry attempts on failure (default: 0)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Multiplier for exponential backoff (default: 2.0)
        when: Optional condition function that receives upstream results
              and returns True if task should execute (default: None)
    
    Returns:
        A decorator that converts a function into a Task
        
    Example:
        @task(retries=3, delay=1.0, backoff=2.0)
        def my_task(data):
            return process(data)
        
        @task(when=lambda x: x > 100)
        def conditional_task(value):
            return handle_large_value(value)
    """
    def decorator(func: Callable) -> Task:
        return Task(func, retries=retries, delay=delay, backoff=backoff, when=when)
    return decorator

