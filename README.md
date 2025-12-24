# Flowkit

A lightweight Python orchestrator - minimalist, decorator-based workflow system inspired by Prefect.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Pure Python** - Zero external runtime dependencies
- **Decorator-based API** - Clean `@task` decorator syntax
- **Two Pipeline Styles** - Choose between operator-based (`>>`) or Keras-style Flow API
- **Automatic DAG** - Tasks auto-register for discovery
- **Parallel Execution** - Built-in ThreadPool/ProcessPool support
- **Retry Logic** - Exponential backoff with jitter
- **Conditional Tasks** - Skip tasks based on upstream results
- **Structured Logging** - Optional detailed execution tracking
- **State Persistence** - Optional result caching and resume

## Installation

```bash
# Using Poetry (recommended)
poetry add flowkit

# Using pip
pip install flowkit
```

## Quick Start

### Option 1: DAG API (Operator-based)

```python
from flowkit import task, DAG

@task(retries=3)
def extract():
    """Fetch data from source."""
    return fetch_data()

@task()
def transform(data):
    """Process the data."""
    return process(data)

@task()
def load(data):
    """Save to database."""
    save_to_db(data)
    return "Success"

# Define pipeline using >> operator
extract >> transform >> load

# Execute
dag = DAG("my_pipeline")
results = dag.run()
print(results)  # {'extract': ..., 'transform': ..., 'load': 'Success'}
```

### Option 2: Flow API (Keras-style)

```python
from flowkit import task, Flow

@task(retries=3)
def extract():
    """Fetch data from source."""
    return fetch_data()

@task()
def transform(extract):  # Parameter name matches task name
    """Process the data."""
    return process(extract)

@task()
def load(transform):
    """Save to database."""
    save_to_db(transform)
    return "Success"

# Build pipeline with chainable API
pipeline = (
    Flow("my_pipeline", max_workers=4)
    .add(extract)
    .add(transform)
    .add(load)
)

# Execute
results = pipeline.run()
print(results)  # {'extract': ..., 'transform': ..., 'load': 'Success'}
```

## Core Concepts

### Tasks

Tasks are the basic units of work in Flowkit. Use the `@task` decorator to convert any function into a task:

```python
from flowkit import task

@task()
def my_task(input_data):
    # Your code here
    return result
```

#### Task Parameters

- **retries** (int): Number of retry attempts on failure (default: 0)
- **delay** (float): Initial delay between retries in seconds (default: 1.0)
- **backoff** (float): Multiplier for exponential backoff (default: 2.0)
- **when** (callable): Condition function for conditional execution (default: None)

```python
@task(retries=3, delay=2.0, backoff=2.0)
def robust_task():
    # Will retry up to 3 times with exponential backoff
    return risky_operation()
```

### Pipeline Operators

Use the `>>` operator to define task dependencies:

```python
# Linear chain
task1 >> task2 >> task3

# Branching (fan-out)
task1 >> [task2, task3, task4]

# Merging (fan-in)
[task1, task2] >> task3

# Complex pipeline
extract >> transform >> [validate, enrich] >> load >> notify
```

### DAG Execution

The DAG runner executes tasks in topological order with parallel execution:

```python
from flowkit import DAG

dag = DAG("my_workflow", max_workers=4)
results = dag.run(executor="thread")  # or "process"
```

### Keras-Style Flow API

For a more intuitive pipeline building experience, use the Flow API:

```python
from flowkit import task, Flow

@task()
def fetch_user():
    return {"id": 1, "name": "Alice"}

@task()
def fetch_orders():
    return ["order1", "order2"]

@task()
def fetch_recommendations():
    return ["item1", "item2"]

@task()
def combine(fetch_user, fetch_orders, fetch_recommendations):
    return {
        "user": fetch_user,
        "orders": fetch_orders,
        "recommendations": fetch_recommendations
    }

# Build pipeline with method chaining
pipeline = (
    Flow("user_pipeline", max_workers=5)
    .add(fetch_user)                                    # Start
    .branch(fetch_orders, fetch_recommendations)        # Parallel branches
    .merge(combine)                                     # Merge results
)

results = pipeline.run()
```

**Key Features:**
- `.add(task)` - Add sequential task
- `.branch(task1, task2, ...)` - Create parallel branches
- `.merge(task)` - Merge all branches into one task
- Automatic parameter injection based on task names

See [Flow API Documentation](docs/FLOW_API.md) for detailed usage.

## Advanced Features

### Retry Logic

Tasks automatically retry on failure with exponential backoff and jitter:

```python
@task(retries=5, delay=1.0, backoff=2.0)
def flaky_api_call():
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()
```

Retry delays: 1s → 2s → 4s → 8s → 16s (with random jitter)

### Conditional Execution

Skip tasks based on upstream results:

```python
@task()
def check_data():
    return 1500  # Some metric

@task(when=lambda x: x > 1000)
def handle_large_data(value):
    return f"Processing large dataset: {value}"

@task(when=lambda x: x <= 1000)
def handle_small_data(value):
    return f"Processing small dataset: {value}"

check_data >> [handle_large_data, handle_small_data]
```

### Branching and Merging

Build complex workflows with fan-out and fan-in patterns:

```python
@task()
def fetch_data():
    return get_raw_data()

@task()
def process_a(data):
    return process_method_a(data)

@task()
def process_b(data):
    return process_method_b(data)

@task()
def process_c(data):
    return process_method_c(data)

@task()
def aggregate(data, result_a, result_b, result_c):
    return combine_results(result_a, result_b, result_c)

# Fan-out to parallel processing, then fan-in
fetch_data >> [process_a, process_b, process_c]
[fetch_data, process_a, process_b, process_c] >> aggregate
```

### Structured Logging

Enable beautiful, colored terminal logging:

```python
from flowkit import configure_logging, LogLevel

# Configure colored logging (default)
configure_logging(level=LogLevel.INFO, use_colors=True)

# Or JSON output for log aggregation
configure_logging(level=LogLevel.DEBUG, json_output=True)
```

**Log Output Example:**
```
14:30:05  [INFO] Starting task "Fetch Data (API)"...
14:30:06  [INFO] Resolving endpoint api.data-provider.com
14:30:07  [INFO] Connection established. Handshake successful.
14:30:08  [WARN] Response latency higher than expected (450ms).
14:30:15  [INFO] Streaming data chunks: [====================] 100%
14:30:45  [INFO] Received 14,502 records.
14:30:50  [INFO] Validating schema integrity...
14:31:10  [SUCCESS] Task completed successfully. Output size: 45MB.
14:31:10  [SYSTEM] Worker released.
```

**Available Log Levels:**
- `LogLevel.DEBUG` - Detailed debugging information
- `LogLevel.INFO` - General informational messages (blue)
- `LogLevel.WARNING` - Warning messages (yellow)
- `LogLevel.ERROR` - Error messages (red)
- `LogLevel.SUCCESS` - Success messages (green)
- `LogLevel.SYSTEM` - System-level messages (magenta)

### State Persistence

Cache task results and resume failed workflows:

```python
from flowkit import StateManager

# In-memory caching
state = StateManager()

# File-based persistence
state = StateManager(storage_path=".flowkit/state.json", default_ttl=3600)

# Store and retrieve results
state.set("task_result", data, ttl=3600)
cached = state.get("task_result")
```

## Complete Examples

### ETL Pipeline

```python
from flowkit import task, DAG

@task(retries=3)
def extract_from_api():
    """Extract data from API."""
    response = requests.get("https://api.example.com/data")
    return response.json()

@task()
def transform_data(raw_data):
    """Clean and transform data."""
    return [
        {
            'id': item['id'],
            'value': item['value'] * 2,
            'timestamp': datetime.now()
        }
        for item in raw_data
    ]

@task()
def load_to_database(transformed_data):
    """Load data into database."""
    db.bulk_insert(transformed_data)
    return f"Loaded {len(transformed_data)} records"

@task()
def send_notification(result):
    """Notify completion."""
    send_email(f"ETL completed: {result}")
    return "Notification sent"

# Build pipeline
extract_from_api >> transform_data >> load_to_database >> send_notification

# Execute
dag = DAG("etl_pipeline", max_workers=2)
results = dag.run()
```

### Approval Workflow

```python
from flowkit import task, DAG

@task()
def extract():
    return fetch_data_size()

@task()
def transform(data_size):
    return data_size * 2

@task(when=lambda x: x > 2000)
def require_manual_approval(size):
    """Large datasets need approval."""
    print(f"Large dataset ({size}) - manual approval required")
    return "MANUAL_APPROVAL"

@task(when=lambda x: x <= 2000)
def auto_approve(size):
    """Small datasets auto-approved."""
    print(f"Small dataset ({size}) - auto-approved")
    return "AUTO_APPROVED"

@task()
def load(transform_result, manual=None, auto=None):
    approval = manual or auto
    print(f"Loading {transform_result} with {approval}")
    return f"LOADED_{approval}"

# Build conditional pipeline
extract >> transform
transform >> [require_manual_approval, auto_approve]
[transform, require_manual_approval, auto_approve] >> load

# Execute
dag = DAG("approval_workflow")
results = dag.run()
```

### Parallel Processing

```python
from flowkit import task, DAG

@task()
def fetch_data():
    """Fetch initial dataset."""
    return range(1000)

@task()
def process_batch_1(data):
    """Process first batch."""
    return sum(list(data)[:333])

@task()
def process_batch_2(data):
    """Process second batch."""
    return sum(list(data)[333:666])

@task()
def process_batch_3(data):
    """Process third batch."""
    return sum(list(data)[666:])

@task()
def aggregate_results(data, b1, b2, b3):
    """Combine all results."""
    total = b1 + b2 + b3
    return f"Total: {total}"

# Parallel processing pipeline
fetch_data >> [process_batch_1, process_batch_2, process_batch_3]
[fetch_data, process_batch_1, process_batch_2, process_batch_3] >> aggregate_results

# Execute with parallel workers
dag = DAG("parallel_processing", max_workers=3)
results = dag.run(executor="thread")
```

## API Reference

### Task

```python
class Task:
    """A task represents a unit of work in a workflow."""
    
    def __init__(
        self,
        func: Callable,
        *,
        retries: int = 0,
        delay: float = 1.0,
        backoff: float = 2.0,
        when: Optional[Callable[..., bool]] = None,
    )
```

### @task Decorator

```python
def task(
    *,
    retries: int = 0,
    delay: float = 1.0,
    backoff: float = 2.0,
    when: Optional[Callable[..., bool]] = None,
) -> Callable[[Callable], Task]
```

### DAG

```python
class DAG:
    """Directed Acyclic Graph runner for executing task workflows."""
    
    def __init__(self, name: str = "workflow", max_workers: Optional[int] = None)
    
    def run(self, executor: str = "thread") -> Dict[str, Any]
    
    def visualize(self) -> str
```

### Flow

```python
class Flow:
    """Keras-style flow builder for creating pipelines."""
    
    def __init__(self, name: str = "flow", max_workers: Optional[int] = None)
    
    def add(self, task: Task) -> 'Flow'
    
    def branch(self, *branch_tasks: Task) -> 'Flow'
    
    def merge(self, merge_task: Task) -> 'Flow'
    
    def run(self, executor: str = "thread") -> Dict[str, Any]
    
    def visualize(self) -> str
```

### StateManager

```python
class StateManager:
    """Manages task result caching and state persistence."""
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        default_ttl: Optional[float] = None,
    )
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, metadata: Optional[Dict] = None)
    def get(self, key: str, default: Any = None) -> Any
    def has(self, key: str) -> bool
    def delete(self, key: str) -> bool
    def clear(self) -> None
    def get_all(self) -> Dict[str, Any]
```

### Logging

```python
from flowkit import configure_logging, LogLevel

configure_logging(
    level: LogLevel = LogLevel.INFO,
    json_output: bool = False,
) -> FlowkitLogger
```

## Comparison with Other Tools

| Feature | Flowkit | Prefect | Airflow |
|---------|---------|---------|---------|
| Setup Complexity | Minimal | Medium | High |
| External Dependencies | None | Many | Many |
| Learning Curve | Low | Medium | High |
| Infrastructure Required | None | Optional | Required |
| Best For | Simple workflows | Cloud workflows | Enterprise ETL |

## Design Philosophy

1. **Simplicity First** - No complex setup, no external services required
2. **Pure Python** - Works anywhere Python works
3. **Explicit is Better** - Clear pipeline definitions with `>>`
4. **Fail Fast** - Errors propagate immediately for quick debugging
5. **Batteries Included** - Retry, conditional, logging, state - all built-in

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/flowkit.git
cd flowkit

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=flowkit --cov-report=html
```

## Testing

Flowkit includes comprehensive test coverage:

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_task.py

# Run with verbose output
poetry run pytest -v

# Generate coverage report
poetry run pytest --cov=flowkit --cov-report=term-missing
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Credits

Inspired by [Prefect](https://www.prefect.io/) and modern workflow orchestration tools, built with a focus on simplicity and pure-Python workflows.

