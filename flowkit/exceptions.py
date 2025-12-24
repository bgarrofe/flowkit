"""Custom exceptions for flowkit."""


class FlowkitError(Exception):
    """Base exception for all flowkit errors."""
    pass


class TaskExecutionError(FlowkitError):
    """Raised when a task fails to execute after all retries."""
    
    def __init__(self, task_name: str, original_error: Exception):
        self.task_name = task_name
        self.original_error = original_error
        super().__init__(
            f"Task '{task_name}' failed: {type(original_error).__name__}: {str(original_error)}"
        )


class DAGCycleError(FlowkitError):
    """Raised when a circular dependency is detected in the DAG."""
    
    def __init__(self, message: str = "Circular dependency detected in DAG"):
        super().__init__(message)


class TaskNotFoundError(FlowkitError):
    """Raised when a referenced task cannot be found."""
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        super().__init__(f"Task '{task_name}' not found in registry")

