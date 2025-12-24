"""
Flowkit - A lightweight Python orchestrator.

A minimalist, decorator-based workflow system inspired by Prefect.
Focuses on simplicity and pure-Python workflows with DAG execution,
retry logic, conditional tasks, and parallel execution.

Example:
    >>> from flowkit import task, DAG
    >>> 
    >>> @task(retries=3)
    >>> def extract():
    >>>     return fetch_data()
    >>> 
    >>> @task()
    >>> def transform(data):
    >>>     return process(data)
    >>> 
    >>> @task()
    >>> def load(data):
    >>>     save_to_db(data)
    >>> 
    >>> # Define pipeline
    >>> extract >> transform >> load
    >>> 
    >>> # Execute
    >>> dag = DAG("my_pipeline")
    >>> results = dag.run()
"""

__version__ = "0.1.0"

# Core imports
from flowkit.task import Task, task
from flowkit.dag import DAG
from flowkit.flow import Flow
from flowkit.state import StateManager, TaskCache
from flowkit.logging import (
    FlowkitLogger,
    LogLevel,
    configure_logging,
    get_logger,
)
from flowkit.exceptions import (
    FlowkitError,
    TaskExecutionError,
    DAGCycleError,
    TaskNotFoundError,
)

# Public API
__all__ = [
    # Version
    "__version__",
    # Core classes
    "Task",
    "task",
    "DAG",
    "Flow",
    # State management
    "StateManager",
    "TaskCache",
    # Logging
    "FlowkitLogger",
    "LogLevel",
    "configure_logging",
    "get_logger",
    # Exceptions
    "FlowkitError",
    "TaskExecutionError",
    "DAGCycleError",
    "TaskNotFoundError",
]

