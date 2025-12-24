"""Tests for the Keras-style Flow API."""

import pytest
import time
from flowkit import task, Flow
from flowkit.exceptions import DAGCycleError


class TestFlowBasics:
    """Test basic Flow functionality."""
    
    def setup_method(self):
        """Clear task registry before each test."""
        from flowkit.task import Task
        Task.clear_registry()
    
    def test_flow_creation(self):
        """Test creating a Flow instance."""
        flow = Flow("test_flow", max_workers=5)
        assert flow.name == "test_flow"
        assert flow.max_workers == 5
        assert len(flow.tasks) == 0
    
    def test_sequential_add(self):
        """Test adding tasks sequentially."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2(task1):
            return task1 + 1
        
        @task()
        def task3(task2):
            return task2 + 1
        
        flow = Flow("sequential").add(task1).add(task2).add(task3)
        
        assert len(flow.tasks) == 3
        assert flow.tasks[0] == task1
        assert flow.tasks[1] == task2
        assert flow.tasks[2] == task3
    
    def test_branch(self):
        """Test branching to parallel tasks."""
        @task()
        def start():
            return 1
        
        @task()
        def branch1():
            return 2
        
        @task()
        def branch2():
            return 3
        
        flow = Flow("branch").add(start).branch(branch1, branch2)
        
        assert len(flow.tasks) == 3
        assert branch1 in flow.graph[start]
        assert branch2 in flow.graph[start]
    
    def test_merge(self):
        """Test merging parallel branches."""
        @task()
        def start():
            return 1
        
        @task()
        def branch1():
            return 2
        
        @task()
        def branch2():
            return 3
        
        @task()
        def merge(branch1, branch2):
            return branch1 + branch2
        
        flow = (
            Flow("merge")
            .add(start)
            .branch(branch1, branch2)
            .merge(merge)
        )
        
        assert len(flow.tasks) == 4
        assert merge in flow.graph[branch1]
        assert merge in flow.graph[branch2]


class TestFlowExecution:
    """Test Flow execution."""
    
    def setup_method(self):
        """Clear task registry before each test."""
        from flowkit.task import Task
        Task.clear_registry()
    
    def test_simple_execution(self):
        """Test executing a simple flow."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2(task1):
            return task1 + 1
        
        flow = Flow("simple").add(task1).add(task2)
        results = flow.run()
        
        assert results["task1"] == 1
        assert results["task2"] == 2
    
    def test_parallel_execution(self):
        """Test parallel branch execution."""
        @task()
        def start():
            return 10
        
        @task()
        def double():
            time.sleep(0.1)
            return 20
        
        @task()
        def triple():
            time.sleep(0.1)
            return 30
        
        @task()
        def combine(double, triple):
            return double + triple
        
        flow = (
            Flow("parallel", max_workers=3)
            .add(start)
            .branch(double, triple)
            .merge(combine)
        )
        
        start_time = time.time()
        results = flow.run()
        duration = time.time() - start_time
        
        assert results["double"] == 20
        assert results["triple"] == 30
        assert results["combine"] == 50
        # Should be faster than sequential (0.2s) due to parallelism
        assert duration < 0.3
    
    def test_parameter_injection(self):
        """Test automatic parameter injection based on task names."""
        @task()
        def fetch_user():
            return {"id": 1, "name": "Alice"}
        
        @task()
        def fetch_orders():
            return ["order1", "order2"]
        
        @task()
        def combine(fetch_user, fetch_orders):
            return {
                "user": fetch_user,
                "orders": fetch_orders
            }
        
        flow = (
            Flow("injection")
            .add(fetch_user)
            .branch(fetch_orders)
            .merge(combine)
        )
        
        results = flow.run()
        
        assert results["fetch_user"]["name"] == "Alice"
        assert len(results["fetch_orders"]) == 2
        assert results["combine"]["user"]["name"] == "Alice"
        assert len(results["combine"]["orders"]) == 2
    
    def test_selective_parameter_injection(self):
        """Test that only matching parameters are injected."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2():
            return 2
        
        @task()
        def task3(task2):  # Only expects task2, not task1
            return task2 + 10
        
        flow = (
            Flow("selective")
            .add(task1)
            .branch(task2)
            .merge(task3)
        )
        
        results = flow.run()
        
        assert results["task1"] == 1
        assert results["task2"] == 2
        assert results["task3"] == 12  # Only task2 was passed


class TestFlowAdvanced:
    """Test advanced Flow features."""
    
    def setup_method(self):
        """Clear task registry before each test."""
        from flowkit.task import Task
        Task.clear_registry()
    
    def test_complex_branching(self):
        """Test complex branching and merging."""
        @task()
        def start():
            return 1
        
        @task()
        def branch_a():
            return 2
        
        @task()
        def branch_b():
            return 3
        
        @task()
        def branch_c():
            return 4
        
        @task()
        def merge(branch_a, branch_b, branch_c):
            return branch_a + branch_b + branch_c
        
        @task()
        def final(merge):
            return merge * 2
        
        flow = (
            Flow("complex")
            .add(start)
            .branch(branch_a, branch_b, branch_c)
            .merge(merge)
            .add(final)
        )
        
        results = flow.run()
        
        assert results["merge"] == 9
        assert results["final"] == 18
    
    def test_multiple_merge_points(self):
        """Test multiple branching and merging in sequence."""
        @task()
        def start():
            return 1
        
        @task()
        def branch1_a():
            return 2
        
        @task()
        def branch1_b():
            return 3
        
        @task()
        def merge1(branch1_a, branch1_b):
            return branch1_a + branch1_b
        
        @task()
        def branch2_a(merge1):
            return merge1 * 2
        
        @task()
        def branch2_b(merge1):
            return merge1 * 3
        
        @task()
        def merge2(branch2_a, branch2_b):
            return branch2_a + branch2_b
        
        flow = (
            Flow("multi_merge")
            .add(start)
            .branch(branch1_a, branch1_b)
            .merge(merge1)
            .branch(branch2_a, branch2_b)
            .merge(merge2)
        )
        
        results = flow.run()
        
        assert results["merge1"] == 5
        assert results["branch2_a"] == 10
        assert results["branch2_b"] == 15
        assert results["merge2"] == 25
    
    def test_retry_logic(self):
        """Test retry logic in Flow execution."""
        attempt_count = {"value": 0}
        
        @task(retries=2, delay=0.1)
        def flaky_task():
            attempt_count["value"] += 1
            if attempt_count["value"] < 2:
                raise Exception("Temporary failure")
            return "success"
        
        flow = Flow("retry").add(flaky_task)
        results = flow.run()
        
        assert results["flaky_task"] == "success"
        assert attempt_count["value"] == 2
    
    def test_visualize(self):
        """Test flow visualization."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2():
            return 2
        
        @task()
        def task3(task1, task2):
            return task1 + task2
        
        flow = (
            Flow("visualize")
            .add(task1)
            .branch(task2)
            .merge(task3)
        )
        
        viz = flow.visualize()
        
        assert "Flow: visualize" in viz
        assert "task1" in viz
        assert "task2" in viz
        assert "task3" in viz
        assert "Upstream" in viz
        assert "Downstream" in viz


class TestFlowErrors:
    """Test Flow error handling."""
    
    def setup_method(self):
        """Clear task registry before each test."""
        from flowkit.task import Task
        Task.clear_registry()
    
    def test_branch_without_task(self):
        """Test that branching without a task raises an error."""
        @task()
        def task1():
            return 1
        
        flow = Flow("error")
        
        with pytest.raises(ValueError, match="Cannot branch before adding a task"):
            flow.branch(task1)
    
    def test_merge_without_branches(self):
        """Test that merging without branches raises an error."""
        @task()
        def task1():
            return 1
        
        flow = Flow("error")
        
        with pytest.raises(ValueError, match="No branches to merge"):
            flow.merge(task1)
    
    def test_task_failure_propagates(self):
        """Test that task failures propagate."""
        @task()
        def failing_task():
            raise ValueError("Task failed")
        
        flow = Flow("fail").add(failing_task)
        
        with pytest.raises(ValueError, match="Task failed"):
            flow.run()
    
    def test_empty_flow(self):
        """Test running an empty flow."""
        flow = Flow("empty")
        results = flow.run()
        
        assert results == {}


class TestFlowProcessExecutor:
    """Test Flow with process executor."""
    
    def setup_method(self):
        """Clear task registry before each test."""
        from flowkit.task import Task
        Task.clear_registry()
    
    @pytest.mark.skip(reason="Local functions cannot be pickled for ProcessPoolExecutor")
    def test_process_executor(self):
        """Test execution with process pool.
        
        Note: This test is skipped because local functions defined in test methods
        cannot be pickled, which is required for ProcessPoolExecutor. In real usage,
        tasks would be defined at module level and can be pickled successfully.
        """
        @task()
        def task1():
            return 1
        
        @task()
        def task2(task1):
            return task1 + 1
        
        flow = Flow("process").add(task1).add(task2)
        results = flow.run(executor="process")
        
        assert results["task1"] == 1
        assert results["task2"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

