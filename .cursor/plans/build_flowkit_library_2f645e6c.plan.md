---
name: Build Flowkit Library
overview: Create a production-ready Python orchestration library based on the concept.py file, with Poetry setup, comprehensive unit tests, and proper package structure.
todos:
  - id: init-poetry
    content: Initialize Poetry project with pyproject.toml
    status: completed
  - id: create-exceptions
    content: Create exceptions.py with custom error types
    status: completed
  - id: create-task
    content: Implement task.py with Task class and decorator
    status: completed
  - id: create-dag
    content: Implement dag.py with DAG runner
    status: completed
    dependencies:
      - create-task
  - id: create-logging
    content: Implement logging.py with structured logging
    status: completed
  - id: create-state
    content: Implement state.py with persistence and caching
    status: completed
  - id: create-init
    content: Create __init__.py with public API exports
    status: completed
    dependencies:
      - create-task
      - create-dag
      - create-logging
      - create-state
      - create-exceptions
  - id: test-task
    content: Write comprehensive tests for task.py
    status: completed
    dependencies:
      - create-task
  - id: test-dag
    content: Write comprehensive tests for dag.py
    status: completed
    dependencies:
      - create-dag
  - id: test-conditional
    content: Write tests for conditional execution and branching
    status: completed
    dependencies:
      - create-dag
  - id: test-logging
    content: Write tests for logging functionality
    status: completed
    dependencies:
      - create-logging
  - id: test-state
    content: Write tests for state persistence
    status: completed
    dependencies:
      - create-state
  - id: create-readme
    content: Create comprehensive README.md with examples
    status: completed
    dependencies:
      - create-init
---

# Build Flowkit Library

## Overview

Transform the [`concept.py`](/home/garrofe/Code/garrofe/flowkit/concept.py) prototype into a production-ready Python library called **flowkit** - a lightweight, decorator-based workflow orchestrator inspired by Prefect. The library will feature DAG execution, retry logic, conditional tasks, parallel execution, structured logging, and state persistence.

## Architecture

```mermaid
graph TB
    UserCode[User Code] -->|@task decorator| TaskClass[Task Class]
    TaskClass -->|registers to| TaskRegistry[Task Registry]
    TaskRegistry -->|consumed by| DAGRunner[DAG Runner]
    TaskClass -->|implements| RetryLogic[Retry Logic with Backoff]
    TaskClass -->|supports| ConditionalExec[Conditional Execution]
    DAGRunner -->|uses| TopoSort[Topological Sort]
    DAGRunner -->|executes via| Executor[ThreadPool/ProcessPool]
    DAGRunner -->|tracks with| Logger[Structured Logger]
    DAGRunner -->|persists to| StateManager[State Manager]
    StateManager -->|caches| TaskResults[Task Results]
```



## Project Structure

```javascript
flowkit/
├── flowkit/
│   ├── __init__.py          # Public API exports
│   ├── exceptions.py        # Custom exception classes
│   ├── task.py              # Task class and @task decorator
│   ├── dag.py               # DAG runner with parallel execution
│   ├── logging.py           # Structured logging module
│   └── state.py             # State persistence and caching
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_task.py         # Task tests
│   ├── test_dag.py          # DAG execution tests
│   ├── test_conditional.py  # Conditional execution tests
│   ├── test_logging.py      # Logging tests
│   └── test_state.py        # State persistence tests
├── pyproject.toml           # Poetry configuration
├── README.md                # Documentation
└── .gitignore
```



## Implementation Steps

### 1. Project Initialization

- Initialize Poetry project with `pyproject.toml`
- Configure Python 3.11+ requirement
- Set up development dependencies: pytest, pytest-cov, pytest-mock
- No external runtime dependencies (pure Python core)
- Create `.gitignore` for Python projects

### 2. Core Modules

**Exceptions Module** ([flowkit/exceptions.py](/home/garrofe/Code/garrofe/flowkit/flowkit/exceptions.py))Create custom exception hierarchy:

- `FlowkitError` - base exception
- `TaskExecutionError` - task execution failures
- `DAGCycleError` - circular dependency detection
- `TaskNotFoundError` - missing task references

**Task Module** ([flowkit/task.py](/home/garrofe/Code/garrofe/flowkit/flowkit/task.py))Extract and enhance from [`concept.py`](/home/garrofe/Code/garrofe/flowkit/concept.py) lines 11-105:

- `Task` class with auto-registration to global registry
- Retry logic with exponential backoff and jitter (lines 49-64)
- Conditional execution via `when` parameter (lines 36-45)
- Operator overloading (`>>`) for pipeline syntax (lines 69-90)
- `@task` decorator with configuration options
- Add comprehensive type hints and docstrings

**DAG Module** ([flowkit/dag.py](/home/garrofe/Code/garrofe/flowkit/flowkit/dag.py))Extract and enhance from [`concept.py`](/home/garrofe/Code/garrofe/flowkit/concept.py) lines 111-166:

- `DAG` class with topological sort execution
- Parallel execution via ThreadPoolExecutor/ProcessPoolExecutor
- Task dependency resolution and indegree tracking
- Result collection and propagation
- Error handling with fail-fast behavior
- Integration points for logging and state modules

**Logging Module** ([flowkit/logging.py](/home/garrofe/Code/garrofe/flowkit/flowkit/logging.py))New structured logging system:

- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Task lifecycle events: start, success, failure, retry, skip
- DAG progress tracking with completion percentage
- Optional JSON output for log aggregation systems
- Thread-safe logging for parallel execution

**State Module** ([flowkit/state.py](/home/garrofe/Code/garrofe/flowkit/flowkit/state.py))New state persistence system:

- `StateManager` class with in-memory storage (default)
- Optional file-based persistence (JSON format)
- Task result caching with configurable TTL
- Cache invalidation strategies
- Resume capability for failed DAG runs

**Package Init** ([flowkit/__init__.py](/home/garrofe/Code/garrofe/flowkit/flowkit/__init__.py))Export public API:

```python
from flowkit.task import Task, task
from flowkit.dag import DAG
from flowkit.state import StateManager
from flowkit.logging import configure_logging
from flowkit.exceptions import *
```



### 3. Comprehensive Test Suite

**Test Task Module** ([tests/test_task.py](/home/garrofe/Code/garrofe/flowkit/tests/test_task.py))

- Task creation and decorator usage
- Operator overloading (`>>`) for single and list targets
- Retry logic with mocked time.sleep
- Conditional execution with `when` parameter
- Task registration and cleanup

**Test DAG Module** ([tests/test_dag.py](/home/garrofe/Code/garrofe/flowkit/tests/test_dag.py))

- Linear pipeline execution
- Parallel task execution
- Dependency resolution
- Error propagation
- ThreadPool vs ProcessPool executors
- Empty DAG handling

**Test Conditional Execution** ([tests/test_conditional.py](/home/garrofe/Code/garrofe/flowkit/tests/test_conditional.py))

- Branching (fan-out) patterns
- Merging (fan-in) patterns
- Conditional task skipping
- Complex conditional workflows

**Test Logging** ([tests/test_logging.py](/home/garrofe/Code/garrofe/flowkit/tests/test_logging.py))

- Log level configuration
- Task event logging
- DAG progress tracking
- JSON output format
- Thread-safe logging

**Test State Persistence** ([tests/test_state.py](/home/garrofe/Code/garrofe/flowkit/tests/test_state.py))

- In-memory state management
- File-based persistence
- Result caching and retrieval
- TTL expiration
- Resume functionality

**Test Configuration** ([tests/conftest.py](/home/garrofe/Code/garrofe/flowkit/tests/conftest.py))

- Fixtures for task cleanup
- Mock time utilities
- Temporary file handling
- Common test patterns

### 4. Documentation

**README** ([README.md](/home/garrofe/Code/garrofe/flowkit/README.md))

- Quick start example
- Installation instructions
- Core concepts explanation
- Advanced features guide
- API reference
- Comparison with Prefect/Airflow

## Key Features

1. **Pure Python**: Zero external runtime dependencies
2. **Decorator-based API**: Clean `@task` decorator syntax
3. **Pipeline Operators**: Intuitive `>>` for left-to-right flows
4. **Automatic DAG**: Tasks auto-register for discovery
5. **Parallel Execution**: Built-in ThreadPool/ProcessPool support
6. **Retry Logic**: Exponential backoff with jitter
7. **Conditional Tasks**: Skip tasks based on upstream results
8. **Structured Logging**: Optional detailed execution tracking
9. **State Persistence**: Optional result caching and resume

## Testing Strategy

- Target: >90% code coverage
- Unit tests for each module in isolation
- Integration tests for complete workflows
- Mock time.sleep for fast retry tests