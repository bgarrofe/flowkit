# Keras-Style Flow API

The Flow API provides a Keras-inspired interface for building data pipelines in Flowkit. It offers an intuitive, chainable API that makes pipeline construction feel like building a neural network model.

## Overview

The Flow class allows you to:
- **Chain tasks sequentially** with `.add()`
- **Branch tasks in parallel** with `.branch()`
- **Merge parallel branches** with `.merge()`
- **Execute with automatic parallelization**
- **Visualize pipeline structure**

## Quick Start

```python
from flowkit import task, Flow

@task(retries=2)
def fetch_data():
    return {"data": [1, 2, 3]}

@task()
def process_a(fetch_data):
    return {"result_a": sum(fetch_data["data"])}

@task()
def process_b(fetch_data):
    return {"result_b": len(fetch_data["data"])}

@task()
def combine(process_a, process_b):
    return {**process_a, **process_b}

# Build pipeline
pipeline = (
    Flow("my_pipeline", max_workers=5)
    .add(fetch_data)
    .branch(process_a, process_b)  # Run in parallel
    .merge(combine)                # Wait for both
)

# Execute
results = pipeline.run()
```

## Core Concepts

### 1. Sequential Chaining with `.add()`

Use `.add()` to create a linear chain where each task depends on the previous one:

```python
pipeline = (
    Flow("sequential")
    .add(task1)
    .add(task2)
    .add(task3)
)
# Execution order: task1 → task2 → task3
```

### 2. Parallel Branching with `.branch()`

Use `.branch()` to execute multiple tasks in parallel after the previous task:

```python
pipeline = (
    Flow("parallel")
    .add(task1)
    .branch(task2, task3, task4)  # All run in parallel after task1
)
# Execution: task1 → [task2, task3, task4] (parallel)
```

### 3. Merging Branches with `.merge()`

Use `.merge()` to combine results from parallel branches:

```python
pipeline = (
    Flow("merge")
    .add(task1)
    .branch(task2, task3)
    .merge(task4)  # Waits for both task2 and task3
)
# Execution: task1 → [task2, task3] (parallel) → task4
```

### 4. Complex Pipelines

Combine these operations to build complex workflows:

```python
pipeline = (
    Flow("complex", max_workers=10)
    .add(start)
    .branch(fetch_a, fetch_b, fetch_c)  # 3-way parallel fetch
    .merge(combine_all)                  # Wait for all 3
    .add(transform)
    .branch(save_db, send_email)        # Parallel output
    .merge(finalize)
)
```

## Task Parameter Injection

The Flow API automatically passes upstream task results as keyword arguments to downstream tasks. The parameter names must match the upstream task function names:

```python
@task()
def fetch_user():
    return {"id": 1, "name": "Alice"}

@task()
def fetch_orders():
    return ["order1", "order2"]

@task()
def combine(fetch_user, fetch_orders):  # Parameter names match task names!
    return {
        "user": fetch_user,
        "orders": fetch_orders
    }

pipeline = (
    Flow("example")
    .add(fetch_user)
    .branch(fetch_orders)  # Runs after fetch_user
    .merge(combine)        # Receives both results
)
```

**Important**: The Flow API uses function introspection to determine which upstream results to pass to each task. Only results matching the function's parameter names will be passed.

## Execution

### Thread-based Execution (Default)

```python
results = pipeline.run(executor="thread")
```

Best for:
- I/O-bound tasks (API calls, database queries, file I/O)
- Tasks that release the GIL
- Most common use case

### Process-based Execution

```python
results = pipeline.run(executor="process")
```

Best for:
- CPU-bound tasks (data processing, calculations)
- Tasks that need true parallelism
- When you need to bypass Python's GIL

### Controlling Parallelism

```python
# Limit concurrent workers
pipeline = Flow("my_flow", max_workers=5)

# Unlimited workers (uses executor default)
pipeline = Flow("my_flow", max_workers=None)
```

## Visualization

Visualize your pipeline structure before execution:

```python
pipeline = (
    Flow("example")
    .add(task1)
    .branch(task2, task3)
    .merge(task4)
)

print(pipeline.visualize())
```

Output:
```
Flow: example
========================================

Task: task1
  Downstream: task2, task3

Task: task2
  Upstream: task1
  Downstream: task4

Task: task3
  Upstream: task1
  Downstream: task4

Task: task4
  Upstream: task2, task3
```

## Error Handling

The Flow API supports fail-fast behavior and retry logic:

```python
@task(retries=3, delay=1.0, backoff=2.0)
def unreliable_task():
    # Will retry up to 3 times with exponential backoff
    return fetch_from_api()

pipeline = Flow("robust").add(unreliable_task)

try:
    results = pipeline.run()
except Exception as e:
    print(f"Pipeline failed: {e}")
```

## Complete Example

```python
from flowkit import task, Flow
import time

# Define tasks
@task(retries=2)
def fetch_user_data():
    time.sleep(2)
    return {"user_id": 42, "name": "Alice"}

@task(retries=2)
def fetch_orders():
    time.sleep(3)
    return ["order_1", "order_2", "order_3"]

@task(retries=2)
def fetch_recommendations():
    time.sleep(1.5)
    return ["book_A", "movie_X"]

@task()
def enrich_profile(fetch_user_data, fetch_orders, fetch_recommendations):
    return {
        "profile": fetch_user_data,
        "orders": fetch_orders,
        "recommendations": fetch_recommendations
    }

@task()
def send_summary(enrich_profile):
    print(f"Sending email to {enrich_profile['profile']['name']}")
    return "Email sent"

# Build pipeline
pipeline = (
    Flow("user_enrichment", max_workers=5)
    .add(fetch_user_data)
    .branch(fetch_orders, fetch_recommendations)  # Parallel fetch
    .merge(enrich_profile)                        # Combine results
    .add(send_summary)                            # Final step
)

# Visualize
print(pipeline.visualize())

# Execute
results = pipeline.run()
print(f"Result: {results['send_summary']}")
```

## Comparison with DAG API

Flowkit provides two APIs for building pipelines:

### DAG API (Operator-based)

```python
from flowkit import task, DAG

@task()
def task1():
    return 1

@task()
def task2():
    return 2

@task()
def task3(a, b):
    return a + b

# Define dependencies with >> operator
task1 >> task3
task2 >> task3

# Execute
dag = DAG("my_dag")
results = dag.run()
```

### Flow API (Keras-style)

```python
from flowkit import task, Flow

@task()
def task1():
    return 1

@task()
def task2():
    return 2

@task()
def task3(task1, task2):  # Note: params match task names
    return task1 + task2

# Build with chainable API
pipeline = (
    Flow("my_flow")
    .add(task1)
    .branch(task2)
    .merge(task3)
)

# Execute
results = pipeline.run()
```

**Choose Flow API when:**
- You want a more intuitive, readable pipeline definition
- You prefer method chaining over operators
- You're building complex branching/merging workflows
- You want explicit control over execution flow

**Choose DAG API when:**
- You prefer operator-based syntax (`>>`)
- You want automatic task discovery
- You're building simpler linear or fan-out workflows
- You want tasks to automatically register globally

## Best Practices

### 1. Use Descriptive Task Names

Task names become parameter names in downstream tasks:

```python
@task()
def fetch_user_profile():  # Clear, descriptive name
    return {"id": 1}

@task()
def process(fetch_user_profile):  # Easy to understand
    return fetch_user_profile["id"]
```

### 2. Keep Tasks Focused

Each task should do one thing well:

```python
# Good: Separate concerns
@task()
def fetch_data():
    return get_from_api()

@task()
def validate_data(fetch_data):
    return validate(fetch_data)

# Bad: Too much in one task
@task()
def fetch_and_validate_and_transform():
    data = get_from_api()
    validated = validate(data)
    return transform(validated)
```

### 3. Use Retries for Unreliable Operations

```python
@task(retries=3, delay=1.0, backoff=2.0)
def fetch_from_external_api():
    return requests.get("https://api.example.com/data").json()
```

### 4. Visualize Before Running

Always visualize complex pipelines to verify structure:

```python
pipeline = build_complex_pipeline()
print(pipeline.visualize())  # Check structure first
results = pipeline.run()      # Then execute
```

### 5. Handle Errors Gracefully

```python
try:
    results = pipeline.run()
except Exception as e:
    logger.error(f"Pipeline failed: {e}")
    # Handle cleanup, notifications, etc.
```

## Advanced Features

### Conditional Execution

Tasks can be conditionally executed based on upstream results:

```python
@task(when=lambda x: x > 100)
def process_large_dataset(fetch_data):
    return expensive_operation(fetch_data)
```

### Accessing All Upstream Results

Tasks receive ALL upstream results that have been computed, not just immediate parents:

```python
@task()
def task1():
    return 1

@task()
def task2():
    return 2

@task()
def task3(task1, task2):  # Can access both task1 and task2
    return task1 + task2
```

## Troubleshooting

### Issue: "Missing required positional argument"

**Problem**: Task parameter names don't match upstream task names.

```python
# Wrong
@task()
def process(data):  # Parameter name doesn't match any task
    return data

# Correct
@task()
def process(fetch_data):  # Matches upstream task name
    return fetch_data
```

### Issue: "Circular dependency detected"

**Problem**: Tasks have circular dependencies.

```python
# Wrong
flow.add(task1).branch(task2).merge(task1)  # task1 depends on itself!

# Correct
flow.add(task1).branch(task2).merge(task3)
```

### Issue: Tasks not running in parallel

**Problem**: Not using `.branch()` correctly.

```python
# Wrong - Sequential execution
flow.add(task1).add(task2).add(task3)

# Correct - Parallel execution
flow.add(task1).branch(task2, task3)
```

## API Reference

### Flow Class

#### `__init__(name: str = "flow", max_workers: Optional[int] = None)`

Create a new Flow.

**Parameters:**
- `name`: Name of the flow/pipeline
- `max_workers`: Maximum number of parallel workers (None = executor default)

#### `add(task: Task) -> Flow`

Add a task that depends on the previously added task (sequential).

**Returns:** Self for method chaining

#### `branch(*branch_tasks: Task) -> Flow`

Add multiple parallel branches from the last task.

**Parameters:**
- `*branch_tasks`: Variable number of tasks to run in parallel

**Returns:** Self for method chaining

#### `merge(merge_task: Task) -> Flow`

Merge all recent branches into one task.

**Parameters:**
- `merge_task`: The task that merges all branches

**Returns:** Self for method chaining

#### `run(executor: str = "thread") -> Dict[str, Any]`

Execute the flow with parallel execution.

**Parameters:**
- `executor`: Type of executor - "thread" or "process"

**Returns:** Dictionary mapping task names to their results

#### `visualize() -> str`

Generate a text visualization of the flow structure.

**Returns:** String representation of the flow

## See Also

- [Task Decorator Documentation](TASKS.md)
- [DAG API Documentation](DAG.md)
- [Examples](../examples/)

