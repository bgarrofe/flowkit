# Functional API Guide

The Functional API provides a Keras-style interface for building complex workflows with multiple inputs and outputs. This API is ideal when you need fine-grained control over the computational graph structure.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Basic Usage](#basic-usage)
- [Multiple Inputs and Outputs](#multiple-inputs-and-outputs)
- [Complex DAGs](#complex-dags)
- [API Reference](#api-reference)
- [Examples](#examples)

## Overview

The Functional API allows you to:
- Define workflows with multiple input nodes
- Create workflows with multiple output nodes
- Build complex DAG structures with branching and merging
- Execute tasks in parallel where dependencies allow
- Maintain explicit control over data flow

### When to Use Functional API

Use the Functional API when:
- You need multiple inputs or outputs
- You want explicit control over the graph structure
- You're building complex, non-linear workflows
- You prefer a declarative style similar to Keras

Use the Sequential Flow API when:
- You have a simple linear pipeline
- You prefer method chaining (`.add()`, `.branch()`, `.merge()`)
- You don't need multiple inputs/outputs

## Core Concepts

### Layer

A `Layer` wraps a task and makes it callable. When you call a layer, it creates an `AppliedTask` node in the computational graph.

```python
from flowkit import task, Layer

@task()
def my_task():
    return 42

# Wrap task as a layer
layer = Layer(my_task)

# Call layer to create a node
node = layer()
```

### AppliedTask

An `AppliedTask` represents a task application in the graph. It tracks:
- The task to execute
- Its input nodes (dependencies)
- Its output value (after execution)

You typically don't create `AppliedTask` instances directly—they're created when you call layers.

### FunctionalFlow

A `FunctionalFlow` defines a computational graph with specified inputs and outputs. It:
- Discovers all nodes by traversing from outputs to inputs
- Executes tasks in topological order
- Runs independent tasks in parallel
- Returns output values in the specified order

## Basic Usage

### Single Input, Single Output

```python
from flowkit import task, Layer, FunctionalFlow

@task()
def input_task():
    return 42

@task()
def output_task(input_task):
    return input_task * 2

# Build graph
inp = Layer(input_task)()
out = Layer(output_task)(inp)

# Create flow
flow = FunctionalFlow(inputs=inp, outputs=out, name="simple_flow")

# Run
result = flow.run()
print(result)  # 84
```

### Multiple Inputs, Single Output

```python
@task()
def input1():
    return 10

@task()
def input2():
    return 20

@task()
def combine(input1, input2):
    return input1 + input2

# Build graph
in1 = Layer(input1)()
in2 = Layer(input2)()
out = Layer(combine)(in1, in2)

# Create flow
flow = FunctionalFlow(inputs=(in1, in2), outputs=out, name="multi_input_flow")

# Run
result = flow.run()
print(result)  # 30
```

## Multiple Inputs and Outputs

The real power of the Functional API comes from supporting multiple inputs and outputs:

```python
@task(retries=2)
def fetch_user():
    return {"id": 123, "name": "Alice"}

@task(retries=2)
def fetch_orders():
    return ["order1", "order2"]

@task(retries=2)
def fetch_recommendations():
    return ["bookA", "movieX"]

@task()
def build_profile(fetch_user, fetch_orders):
    return {"profile": fetch_user, "past_orders": fetch_orders}

@task()
def generate_recommendations(fetch_user, fetch_recommendations):
    return {"personalized": ["itemX", "itemY"], "base": fetch_recommendations}

@task()
def summarize(build_profile, generate_recommendations):
    return {
        "user": build_profile["profile"]["name"],
        "recs": generate_recommendations["personalized"]
    }

@task()
def log_activity(build_profile, generate_recommendations):
    return "Activity logged"

# Build graph
UserLayer = Layer(fetch_user)
OrdersLayer = Layer(fetch_orders)
RecsLayer = Layer(fetch_recommendations)
ProfileLayer = Layer(build_profile)
GenRecsLayer = Layer(generate_recommendations)
SummaryLayer = Layer(summarize)
LogLayer = Layer(log_activity)

# Create nodes
user = UserLayer()
orders = OrdersLayer()
recs = RecsLayer()

# Multi-input tasks
profile = ProfileLayer(user, orders)
personalized_recs = GenRecsLayer(user, recs)

# Multiple outputs
summary = SummaryLayer(profile, personalized_recs)
activity_log = LogLayer(profile, personalized_recs)

# Define flow with multiple inputs and outputs
flow = FunctionalFlow(
    inputs=(user, orders, recs),
    outputs=(summary, activity_log),
    name="multi_head_pipeline"
)

# Run - returns tuple of outputs
summary_result, log_result = flow.run(executor="thread")

print("Summary:", summary_result)
print("Log:", log_result)
```

### Output Behavior

- **Single output**: Returns the output value directly
- **Multiple outputs**: Returns a tuple of values in the order specified

```python
# Single output
result = flow.run()  # Returns the value

# Multiple outputs
out1, out2, out3 = flow.run()  # Returns tuple
```

## Complex DAGs

### Diamond Pattern

```python
@task()
def root():
    return 10

@task()
def left(root):
    return root * 2

@task()
def right(root):
    return root * 3

@task()
def merge(left, right):
    return left + right

# Build diamond
r = Layer(root)()
l = Layer(left)(r)
ri = Layer(right)(r)
m = Layer(merge)(l, ri)

flow = FunctionalFlow(inputs=r, outputs=m, name="diamond")
result = flow.run()  # 50
```

### Multi-Level Hierarchy

```python
@task()
def level1():
    return 1

@task()
def level2a(level1):
    return level1 + 1

@task()
def level2b(level1):
    return level1 + 2

@task()
def level3(level2a, level2b):
    return level2a + level2b

# Build hierarchy
l1 = Layer(level1)()
l2a = Layer(level2a)(l1)
l2b = Layer(level2b)(l1)
l3 = Layer(level3)(l2a, l2b)

flow = FunctionalFlow(inputs=l1, outputs=l3, name="hierarchy")
result = flow.run()  # 5
```

## API Reference

### Layer

```python
class Layer:
    def __init__(self, task: Task)
    def __call__(self, *inputs: Union[Layer, AppliedTask]) -> AppliedTask
```

**Parameters:**
- `task`: The Task to wrap

**Methods:**
- `__call__(*inputs)`: Apply this layer to input nodes, creating an AppliedTask

### AppliedTask

```python
class AppliedTask:
    def __init__(self, task: Task, inputs: Tuple[Union[AppliedTask, Layer], ...])
```

**Attributes:**
- `task`: The Task to execute
- `inputs`: Tuple of upstream nodes
- `name`: Name of the task
- `outputs`: Result after execution (None before execution)

### FunctionalFlow

```python
class FunctionalFlow:
    def __init__(
        self,
        inputs: Union[AppliedTask, Layer, Tuple[Union[AppliedTask, Layer], ...]],
        outputs: Union[AppliedTask, Tuple[AppliedTask, ...]],
        name: str = "functional_flow",
        max_workers: Optional[int] = None
    )
    
    def run(self, executor: str = "thread") -> Union[Any, Tuple[Any, ...]]
    def visualize(self) -> str
```

**Parameters:**
- `inputs`: Single input node or tuple of input nodes
- `outputs`: Single output node or tuple of output nodes
- `name`: Name of the flow
- `max_workers`: Maximum number of parallel workers

**Methods:**
- `run(executor="thread")`: Execute the flow
  - `executor`: "thread" or "process"
  - Returns: Single value or tuple of values
- `visualize()`: Generate text visualization of the graph

## Examples

### Example 1: ETL Pipeline with Validation

```python
@task()
def extract():
    return [1, 2, 3, 4, 5]

@task()
def validate(extract):
    return all(x > 0 for x in extract)

@task()
def transform(extract):
    return [x * 2 for x in extract]

@task()
def load(transform, validate):
    if validate:
        return f"Loaded {len(transform)} items"
    return "Validation failed"

# Build graph
e = Layer(extract)()
v = Layer(validate)(e)
t = Layer(transform)(e)
l = Layer(load)(t, v)

flow = FunctionalFlow(inputs=e, outputs=l, name="etl_with_validation")
result = flow.run()
```

### Example 2: Parallel Data Processing

```python
@task()
def fetch_data():
    return {"users": [...], "orders": [...], "products": [...]}

@task()
def process_users(fetch_data):
    return len(fetch_data["users"])

@task()
def process_orders(fetch_data):
    return len(fetch_data["orders"])

@task()
def process_products(fetch_data):
    return len(fetch_data["products"])

@task()
def aggregate(process_users, process_orders, process_products):
    return {
        "total_users": process_users,
        "total_orders": process_orders,
        "total_products": process_products
    }

# Build graph
data = Layer(fetch_data)()
users = Layer(process_users)(data)
orders = Layer(process_orders)(data)
products = Layer(process_products)(data)
agg = Layer(aggregate)(users, orders, products)

flow = FunctionalFlow(inputs=data, outputs=agg, name="parallel_processing")
result = flow.run()
```

### Example 3: Multi-Output Report Generation

```python
@task()
def fetch_data():
    return {"sales": 1000, "costs": 600}

@task()
def calculate_profit(fetch_data):
    return fetch_data["sales"] - fetch_data["costs"]

@task()
def calculate_margin(fetch_data, calculate_profit):
    return (calculate_profit / fetch_data["sales"]) * 100

@task()
def generate_summary(fetch_data, calculate_profit):
    return f"Sales: ${fetch_data['sales']}, Profit: ${calculate_profit}"

@task()
def generate_detailed_report(fetch_data, calculate_profit, calculate_margin):
    return {
        "sales": fetch_data["sales"],
        "costs": fetch_data["costs"],
        "profit": calculate_profit,
        "margin": f"{calculate_margin:.2f}%"
    }

# Build graph
data = Layer(fetch_data)()
profit = Layer(calculate_profit)(data)
margin = Layer(calculate_margin)(data, profit)
summary = Layer(generate_summary)(data, profit)
detailed = Layer(generate_detailed_report)(data, profit, margin)

# Multiple outputs
flow = FunctionalFlow(
    inputs=data,
    outputs=(summary, detailed),
    name="report_generation"
)

summary_result, detailed_result = flow.run()
```

## Best Practices

1. **Name your flows meaningfully**: Use descriptive names for debugging and logging
2. **Keep tasks focused**: Each task should do one thing well
3. **Use type hints**: Help with code clarity and IDE support
4. **Handle errors in tasks**: Use try-except blocks for robust error handling
5. **Leverage retries**: Use `@task(retries=N)` for flaky operations
6. **Visualize complex graphs**: Use `flow.visualize()` to understand structure
7. **Test incrementally**: Build and test small subgraphs before combining

## Comparison with Sequential Flow API

| Feature | Functional API | Sequential Flow API |
|---------|---------------|---------------------|
| Multiple inputs | ✅ Yes | ❌ No |
| Multiple outputs | ✅ Yes | ❌ No |
| Explicit graph control | ✅ Yes | ⚠️ Limited |
| Method chaining | ❌ No | ✅ Yes |
| Learning curve | Medium | Easy |
| Best for | Complex DAGs | Linear pipelines |

## Troubleshooting

### Common Issues

**Issue**: `DAGCycleError: Circular dependency detected`
- **Cause**: Your graph has a cycle (task A depends on task B, which depends on task A)
- **Solution**: Review your dependencies and remove the cycle

**Issue**: Task receives wrong parameters
- **Cause**: Parameter names in task function don't match upstream task names
- **Solution**: Ensure task function parameters match the names of upstream tasks

**Issue**: Flow returns empty tuple
- **Cause**: No outputs specified or outputs tuple is empty
- **Solution**: Verify you're passing valid output nodes to `FunctionalFlow`

### Debugging Tips

1. Use `flow.visualize()` to see the graph structure
2. Check task names match function parameter names
3. Run with `executor="thread"` for easier debugging (process executor can hide errors)
4. Add print statements in tasks to trace execution order
5. Use the logger to track task execution

## Performance Considerations

- **Parallelism**: Independent tasks run in parallel automatically
- **Thread vs Process**: Use thread executor for I/O-bound tasks, process for CPU-bound
- **Max Workers**: Set `max_workers` to control parallelism level
- **Memory**: Large intermediate results are kept in memory during execution

## Next Steps

- Explore [examples/functional_api_example.py](../examples/functional_api_example.py)
- Read about [task configuration](./FLOW_API.md#task-decorator)
- Learn about [error handling and retries](./FLOW_API.md#error-handling)

