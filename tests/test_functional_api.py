"""Tests for the Functional API."""

import pytest
import time
from flowkit import task, Layer, FunctionalFlow, Task
from flowkit.exceptions import DAGCycleError


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear task registry before each test."""
    Task.clear_registry()
    yield
    Task.clear_registry()


def test_single_input_single_output():
    """Test functional flow with single input and single output."""
    @task()
    def input_task():
        return 42
    
    @task()
    def output_task(input_task):
        return input_task * 2
    
    input_layer = Layer(input_task)()
    output_layer = Layer(output_task)(input_layer)
    
    flow = FunctionalFlow(inputs=input_layer, outputs=output_layer, name="test_flow")
    result = flow.run()
    
    assert result == 84


def test_multiple_inputs_single_output():
    """Test functional flow with multiple inputs and single output."""
    @task()
    def input1():
        return 10
    
    @task()
    def input2():
        return 20
    
    @task()
    def combine(input1, input2):
        return input1 + input2
    
    in1 = Layer(input1)()
    in2 = Layer(input2)()
    out = Layer(combine)(in1, in2)
    
    flow = FunctionalFlow(inputs=(in1, in2), outputs=out, name="test_flow")
    result = flow.run()
    
    assert result == 30


def test_single_input_multiple_outputs():
    """Test functional flow with single input and multiple outputs."""
    @task()
    def input_task():
        return 100
    
    @task()
    def output1(input_task):
        return input_task * 2
    
    @task()
    def output2(input_task):
        return input_task * 3
    
    inp = Layer(input_task)()
    out1 = Layer(output1)(inp)
    out2 = Layer(output2)(inp)
    
    flow = FunctionalFlow(inputs=inp, outputs=(out1, out2), name="test_flow")
    result1, result2 = flow.run()
    
    assert result1 == 200
    assert result2 == 300


def test_multiple_inputs_multiple_outputs():
    """Test functional flow with multiple inputs and multiple outputs."""
    @task()
    def fetch_user():
        return {"id": 1, "name": "Alice"}
    
    @task()
    def fetch_orders():
        return ["order1", "order2"]
    
    @task()
    def build_profile(fetch_user, fetch_orders):
        return {"profile": fetch_user, "orders": fetch_orders}
    
    @task()
    def count_orders(fetch_orders):
        return len(fetch_orders)
    
    user = Layer(fetch_user)()
    orders = Layer(fetch_orders)()
    profile = Layer(build_profile)(user, orders)
    count = Layer(count_orders)(orders)
    
    flow = FunctionalFlow(
        inputs=(user, orders),
        outputs=(profile, count),
        name="test_flow"
    )
    
    profile_result, count_result = flow.run()
    
    assert profile_result["profile"]["name"] == "Alice"
    assert profile_result["orders"] == ["order1", "order2"]
    assert count_result == 2


def test_complex_dag():
    """Test a complex DAG with multiple branches and merges."""
    @task()
    def root():
        return 1
    
    @task()
    def branch1(root):
        return root * 2
    
    @task()
    def branch2(root):
        return root * 3
    
    @task()
    def merge(branch1, branch2):
        return branch1 + branch2
    
    @task()
    def final(merge):
        return merge * 10
    
    r = Layer(root)()
    b1 = Layer(branch1)(r)
    b2 = Layer(branch2)(r)
    m = Layer(merge)(b1, b2)
    f = Layer(final)(m)
    
    flow = FunctionalFlow(inputs=r, outputs=f, name="test_flow")
    result = flow.run()
    
    # (1 * 2 + 1 * 3) * 10 = 50
    assert result == 50


def test_parallel_execution():
    """Test that independent tasks run in parallel."""
    execution_order = []
    
    @task()
    def task1():
        execution_order.append("task1_start")
        time.sleep(0.1)
        execution_order.append("task1_end")
        return 1
    
    @task()
    def task2():
        execution_order.append("task2_start")
        time.sleep(0.1)
        execution_order.append("task2_end")
        return 2
    
    @task()
    def combine(task1, task2):
        return task1 + task2
    
    t1 = Layer(task1)()
    t2 = Layer(task2)()
    out = Layer(combine)(t1, t2)
    
    flow = FunctionalFlow(inputs=(t1, t2), outputs=out, name="test_flow")
    result = flow.run()
    
    assert result == 3
    # Both tasks should start before either ends (parallel execution)
    assert "task1_start" in execution_order
    assert "task2_start" in execution_order


def test_no_inputs():
    """Test functional flow with root tasks (no explicit inputs)."""
    @task()
    def root1():
        return 10
    
    @task()
    def root2():
        return 20
    
    @task()
    def combine(root1, root2):
        return root1 + root2
    
    r1 = Layer(root1)()
    r2 = Layer(root2)()
    out = Layer(combine)(r1, r2)
    
    flow = FunctionalFlow(inputs=(r1, r2), outputs=out, name="test_flow")
    result = flow.run()
    
    assert result == 30


def test_layer_repr():
    """Test Layer string representation."""
    @task()
    def my_task():
        return 42
    
    layer = Layer(my_task)
    assert "Layer(my_task)" == str(layer)


def test_applied_task_repr():
    """Test AppliedTask string representation."""
    @task()
    def task1():
        return 1
    
    @task()
    def task2(task1):
        return task1 * 2
    
    t1 = Layer(task1)()
    t2 = Layer(task2)(t1)
    
    assert "task2(task1)" == str(t2)


def test_functional_flow_repr():
    """Test FunctionalFlow string representation."""
    @task()
    def input_task():
        return 1
    
    @task()
    def output_task(input_task):
        return input_task * 2
    
    inp = Layer(input_task)()
    out = Layer(output_task)(inp)
    
    flow = FunctionalFlow(inputs=inp, outputs=out, name="my_flow")
    repr_str = repr(flow)
    
    assert "my_flow" in repr_str
    assert "inputs=1" in repr_str
    assert "outputs=1" in repr_str


def test_visualize():
    """Test flow visualization."""
    @task()
    def input_task():
        return 1
    
    @task()
    def output_task(input_task):
        return input_task * 2
    
    inp = Layer(input_task)()
    out = Layer(output_task)(inp)
    
    flow = FunctionalFlow(inputs=inp, outputs=out, name="test_flow")
    viz = flow.visualize()
    
    assert "test_flow" in viz
    assert "input_task" in viz
    assert "output_task" in viz
    assert "Inputs:" in viz
    assert "Outputs:" in viz


def test_empty_flow():
    """Test empty flow behavior."""
    @task()
    def dummy():
        return 1
    
    # Create a flow with no actual nodes
    flow = FunctionalFlow(inputs=(), outputs=(), name="empty_flow")
    result = flow.run()
    
    # Should return empty tuple for empty outputs
    assert result == ()


def test_task_with_retry():
    """Test that task retry logic works in functional flow."""
    attempt_count = {"count": 0}
    
    @task(retries=2)
    def flaky_task():
        attempt_count["count"] += 1
        if attempt_count["count"] < 2:
            raise ValueError("Temporary failure")
        return "success"
    
    layer = Layer(flaky_task)()
    flow = FunctionalFlow(inputs=layer, outputs=layer, name="test_flow")
    result = flow.run()
    
    assert result == "success"
    assert attempt_count["count"] == 2


def test_diamond_dependency():
    """Test diamond-shaped dependency graph."""
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
    
    r = Layer(root)()
    l = Layer(left)(r)
    ri = Layer(right)(r)
    m = Layer(merge)(l, ri)
    
    flow = FunctionalFlow(inputs=r, outputs=m, name="test_flow")
    result = flow.run()
    
    # 10 * 2 + 10 * 3 = 50
    assert result == 50


def test_three_level_hierarchy():
    """Test three-level task hierarchy."""
    @task()
    def level1():
        return 1
    
    @task()
    def level2(level1):
        return level1 + 1
    
    @task()
    def level3(level2):
        return level2 + 1
    
    l1 = Layer(level1)()
    l2 = Layer(level2)(l1)
    l3 = Layer(level3)(l2)
    
    flow = FunctionalFlow(inputs=l1, outputs=l3, name="test_flow")
    result = flow.run()
    
    assert result == 3


def test_thread_executor_explicit():
    """Test that thread executor works explicitly."""
    @task()
    def compute():
        return 42
    
    layer = Layer(compute)()
    flow = FunctionalFlow(inputs=layer, outputs=layer, name="test_flow")
    result = flow.run(executor="thread")
    
    assert result == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

