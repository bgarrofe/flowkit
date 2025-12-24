"""Tests for DAG module."""

import pytest
from flowkit.task import Task, task
from flowkit.dag import DAG
from flowkit.exceptions import DAGCycleError


class TestDAGBasic:
    """Test basic DAG functionality."""
    
    def test_dag_creation(self):
        """Test DAG creation."""
        dag = DAG("test_dag")
        assert dag.name == "test_dag"
        assert dag.max_workers is None
    
    def test_dag_with_max_workers(self):
        """Test DAG creation with max_workers."""
        dag = DAG("test_dag", max_workers=4)
        assert dag.max_workers == 4
    
    def test_empty_dag(self):
        """Test running empty DAG."""
        dag = DAG("empty")
        results = dag.run()
        assert results == {}


class TestDAGExecution:
    """Test DAG execution."""
    
    def test_single_task(self):
        """Test DAG with single task."""
        @task()
        def single_task():
            return 42
        
        dag = DAG("single")
        results = dag.run()
        
        assert "single_task" in results
        assert results["single_task"] == 42
    
    def test_linear_pipeline(self):
        """Test linear pipeline execution."""
        @task()
        def task1():
            return 10
        
        @task()
        def task2(x):
            return x * 2
        
        @task()
        def task3(x):
            return x + 5
        
        task1 >> task2 >> task3
        
        dag = DAG("linear")
        results = dag.run()
        
        assert results["task1"] == 10
        assert results["task2"] == 20
        assert results["task3"] == 25
    
    def test_parallel_tasks(self):
        """Test parallel task execution."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2():
            return 2
        
        @task()
        def task3():
            return 3
        
        # No dependencies - all should run in parallel
        
        dag = DAG("parallel", max_workers=3)
        results = dag.run()
        
        assert results["task1"] == 1
        assert results["task2"] == 2
        assert results["task3"] == 3
    
    def test_branching_pipeline(self):
        """Test pipeline with branching (fan-out)."""
        @task()
        def extract():
            return 100
        
        @task()
        def transform1(x):
            return x * 2
        
        @task()
        def transform2(x):
            return x + 50
        
        extract >> [transform1, transform2]
        
        dag = DAG("branching")
        results = dag.run()
        
        assert results["extract"] == 100
        assert results["transform1"] == 200
        assert results["transform2"] == 150
    
    def test_merging_pipeline(self):
        """Test pipeline with merging (fan-in)."""
        @task()
        def source1():
            return 10
        
        @task()
        def source2():
            return 20
        
        @task()
        def combine(x, y):
            return x + y
        
        [source1, source2] >> combine
        
        dag = DAG("merging")
        results = dag.run()
        
        assert results["source1"] == 10
        assert results["source2"] == 20
        assert results["combine"] == 30
    
    def test_complex_dag(self):
        """Test complex DAG with branching and merging."""
        @task()
        def extract():
            return 10
        
        @task()
        def transform1(x):
            return x * 2
        
        @task()
        def transform2(x):
            return x + 5
        
        @task()
        def load(x, y):
            return x + y
        
        @task()
        def notify(result):
            return f"Done: {result}"
        
        # Build complex pipeline
        extract >> [transform1, transform2]
        [transform1, transform2] >> load
        load >> notify
        
        dag = DAG("complex")
        results = dag.run()
        
        assert results["extract"] == 10
        assert results["transform1"] == 20
        assert results["transform2"] == 15
        assert results["load"] == 35
        assert results["notify"] == "Done: 35"


class TestDAGExecutors:
    """Test different executor types."""
    
    def test_thread_executor(self):
        """Test DAG with ThreadPoolExecutor."""
        @task()
        def task1():
            return "thread"
        
        dag = DAG("thread_test")
        results = dag.run(executor="thread")
        
        assert results["task1"] == "thread"
    
    def test_process_executor(self):
        """Test DAG with ProcessPoolExecutor."""
        @task()
        def task1():
            return "process"
        
        dag = DAG("process_test")
        results = dag.run(executor="process")
        
        assert results["task1"] == "process"


class TestDAGErrorHandling:
    """Test DAG error handling."""
    
    def test_task_failure_propagates(self):
        """Test that task failure causes DAG to fail."""
        @task()
        def failing_task():
            raise ValueError("Task failed")
        
        dag = DAG("failing")
        
        with pytest.raises(ValueError, match="Task failed"):
            dag.run()
    
    def test_failure_stops_downstream(self):
        """Test that failure prevents downstream tasks from running."""
        executed = []
        
        @task()
        def task1():
            executed.append("task1")
            raise ValueError("Failure")
        
        @task()
        def task2(x):
            executed.append("task2")
            return x
        
        task1 >> task2
        
        dag = DAG("stop_on_failure")
        
        with pytest.raises(ValueError):
            dag.run()
        
        assert "task1" in executed
        assert "task2" not in executed


class TestDAGCycleDetection:
    """Test cycle detection in DAG."""
    
    def test_no_cycle(self):
        """Test that valid DAG has no cycle."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2(x):
            return x + 1
        
        task1 >> task2
        
        dag = DAG("no_cycle")
        # Should not raise
        results = dag.run()
        assert results["task1"] == 1
    
    def test_self_cycle(self):
        """Test detection of self-referencing cycle."""
        @task()
        def task1():
            return 1
        
        # Create self-cycle
        task1.downstream.append(task1)
        task1.upstream.append(task1)
        
        dag = DAG("self_cycle")
        
        with pytest.raises(DAGCycleError):
            dag.run()
    
    def test_two_task_cycle(self):
        """Test detection of cycle between two tasks."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2():
            return 2
        
        # Create cycle: task1 >> task2 >> task1
        task1 >> task2
        task2.downstream.append(task1)
        task1.upstream.append(task2)
        
        dag = DAG("two_task_cycle")
        
        with pytest.raises(DAGCycleError):
            dag.run()
    
    def test_complex_cycle(self):
        """Test detection of cycle in complex graph."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2():
            return 2
        
        @task()
        def task3():
            return 3
        
        # Create cycle: task1 >> task2 >> task3 >> task1
        task1 >> task2 >> task3
        task3.downstream.append(task1)
        task1.upstream.append(task3)
        
        dag = DAG("complex_cycle")
        
        with pytest.raises(DAGCycleError):
            dag.run()


class TestDAGVisualization:
    """Test DAG visualization."""
    
    def test_visualize_empty(self):
        """Test visualization of empty DAG."""
        dag = DAG("empty")
        viz = dag.visualize()
        
        assert "Empty DAG" in viz
    
    def test_visualize_simple(self):
        """Test visualization of simple DAG."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2(x):
            return x + 1
        
        task1 >> task2
        
        dag = DAG("simple")
        viz = dag.visualize()
        
        assert "simple" in viz
        assert "task1" in viz
        assert "task2" in viz
        assert "Upstream" in viz
        assert "Downstream" in viz
    
    def test_visualize_complex(self):
        """Test visualization of complex DAG."""
        @task()
        def extract():
            return 1
        
        @task()
        def transform1(x):
            return x
        
        @task()
        def transform2(x):
            return x
        
        @task()
        def load(x, y):
            return x + y
        
        extract >> [transform1, transform2]
        [transform1, transform2] >> load
        
        dag = DAG("complex")
        viz = dag.visualize()
        
        assert "extract" in viz
        assert "transform1" in viz
        assert "transform2" in viz
        assert "load" in viz


class TestDAGIntegration:
    """Integration tests for complete workflows."""
    
    def test_etl_pipeline(self):
        """Test a complete ETL pipeline."""
        @task()
        def extract():
            return [1, 2, 3, 4, 5]
        
        @task()
        def transform(data):
            return [x * 2 for x in data]
        
        @task()
        def load(data):
            return sum(data)
        
        extract >> transform >> load
        
        dag = DAG("etl")
        results = dag.run()
        
        assert results["extract"] == [1, 2, 3, 4, 5]
        assert results["transform"] == [2, 4, 6, 8, 10]
        assert results["load"] == 30
    
    def test_parallel_processing(self):
        """Test parallel processing workflow."""
        @task()
        def fetch_data():
            return 100
        
        @task()
        def process_a(data):
            return data * 2
        
        @task()
        def process_b(data):
            return data + 50
        
        @task()
        def process_c(data):
            return data - 10
        
        @task()
        def aggregate(a, b, c):
            return a + b + c
        
        fetch_data >> [process_a, process_b, process_c]
        [process_a, process_b, process_c] >> aggregate
        
        dag = DAG("parallel_processing", max_workers=3)
        results = dag.run()
        
        assert results["fetch_data"] == 100
        assert results["process_a"] == 200
        assert results["process_b"] == 150
        assert results["process_c"] == 90
        assert results["aggregate"] == 440

