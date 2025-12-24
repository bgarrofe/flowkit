"""Tests for conditional task execution."""

import pytest
from flowkit.task import task
from flowkit.dag import DAG


class TestConditionalBasic:
    """Test basic conditional execution."""
    
    def test_condition_true(self):
        """Test task executes when condition is true."""
        @task()
        def source():
            return 100
        
        @task(when=lambda x: x > 50)
        def conditional_task(value):
            return value * 2
        
        source >> conditional_task
        
        dag = DAG("condition_true")
        results = dag.run()
        
        assert results["source"] == 100
        assert results["conditional_task"] == 200
    
    def test_condition_false(self):
        """Test task skips when condition is false."""
        @task()
        def source():
            return 30
        
        @task(when=lambda x: x > 50)
        def conditional_task(value):
            return value * 2
        
        source >> conditional_task
        
        dag = DAG("condition_false")
        results = dag.run()
        
        assert results["source"] == 30
        assert "conditional_task" not in results
    
    def test_multiple_conditions(self):
        """Test multiple conditional tasks with different conditions."""
        @task()
        def source():
            return 75
        
        @task(when=lambda x: x > 100)
        def high_value_task(value):
            return f"High: {value}"
        
        @task(when=lambda x: 50 < x <= 100)
        def medium_value_task(value):
            return f"Medium: {value}"
        
        @task(when=lambda x: x <= 50)
        def low_value_task(value):
            return f"Low: {value}"
        
        source >> [high_value_task, medium_value_task, low_value_task]
        
        dag = DAG("multiple_conditions")
        results = dag.run()
        
        assert results["source"] == 75
        assert "high_value_task" not in results
        assert results["medium_value_task"] == "Medium: 75"
        assert "low_value_task" not in results


class TestConditionalBranching:
    """Test conditional execution with branching."""
    
    def test_conditional_fan_out(self):
        """Test conditional execution with fan-out pattern."""
        @task()
        def extract():
            return 1500
        
        @task(when=lambda x: x > 1000)
        def large_handler(value):
            return f"Large: {value}"
        
        @task(when=lambda x: x <= 1000)
        def small_handler(value):
            return f"Small: {value}"
        
        @task()
        def always_run(value):
            return f"Always: {value}"
        
        extract >> [large_handler, small_handler, always_run]
        
        dag = DAG("conditional_fan_out")
        results = dag.run()
        
        assert results["extract"] == 1500
        assert results["large_handler"] == "Large: 1500"
        assert "small_handler" not in results
        assert results["always_run"] == "Always: 1500"
    
    def test_conditional_fan_in(self):
        """Test conditional execution with fan-in pattern."""
        @task()
        def source1():
            return 100
        
        @task()
        def source2():
            return 200
        
        @task(when=lambda x: x > 150)
        def conditional_merge(x, y):
            return x + y
        
        [source1, source2] >> conditional_merge
        
        dag = DAG("conditional_fan_in")
        results = dag.run()
        
        assert results["source1"] == 100
        assert results["source2"] == 200
        assert results["conditional_merge"] == 300


class TestConditionalChaining:
    """Test conditional execution in chains."""
    
    def test_conditional_chain(self):
        """Test conditional tasks in a chain."""
        @task()
        def start():
            return 10
        
        @task()
        def multiply(x):
            return x * 10
        
        @task(when=lambda x: x > 50)
        def conditional_step(x):
            return x + 100
        
        @task()
        def final(x):
            return f"Final: {x}"
        
        start >> multiply >> conditional_step >> final
        
        dag = DAG("conditional_chain")
        results = dag.run()
        
        assert results["start"] == 10
        assert results["multiply"] == 100
        assert results["conditional_step"] == 200
        assert results["final"] == "Final: 200"
    
    def test_conditional_chain_skip(self):
        """Test chain with skipped conditional task."""
        @task()
        def start():
            return 3
        
        @task()
        def multiply(x):
            return x * 10
        
        @task(when=lambda x: x > 50)
        def conditional_step(x):
            return x + 100
        
        @task()
        def final(x):
            # This should receive None since conditional_step was skipped
            return f"Final: {x}"
        
        start >> multiply >> conditional_step >> final
        
        dag = DAG("conditional_chain_skip")
        results = dag.run()
        
        assert results["start"] == 3
        assert results["multiply"] == 30
        assert "conditional_step" not in results
        assert results["final"] == "Final: None"


class TestConditionalComplex:
    """Test complex conditional workflows."""
    
    def test_approval_workflow(self):
        """Test approval workflow with conditional branches."""
        @task()
        def extract():
            return 1800
        
        @task()
        def transform(data):
            return data * 2
        
        @task(when=lambda data: data > 2000)
        def require_approval(data):
            return "MANUAL_APPROVAL"
        
        @task(when=lambda data: data <= 2000)
        def auto_approve(data):
            return "AUTO_APPROVED"
        
        @task()
        def load(transform_result, approval1=None, approval2=None):
            approval = approval1 or approval2 or "NO_APPROVAL"
            return f"Loaded {transform_result} with {approval}"
        
        extract >> transform
        transform >> [require_approval, auto_approve]
        [transform, require_approval, auto_approve] >> load
        
        dag = DAG("approval_workflow")
        results = dag.run()
        
        assert results["extract"] == 1800
        assert results["transform"] == 3600
        assert results["require_approval"] == "MANUAL_APPROVAL"
        assert "auto_approve" not in results
        assert "MANUAL_APPROVAL" in results["load"]
    
    def test_multi_stage_conditional(self):
        """Test multi-stage workflow with multiple conditional branches."""
        @task()
        def fetch_data():
            return 75
        
        @task(when=lambda x: x > 100)
        def high_priority(value):
            return value * 3
        
        @task(when=lambda x: 50 <= x <= 100)
        def medium_priority(value):
            return value * 2
        
        @task(when=lambda x: x < 50)
        def low_priority(value):
            return value * 1
        
        @task()
        def aggregate(data, high=None, medium=None, low=None):
            result = high or medium or low or 0
            return f"Processed: {result}"
        
        fetch_data >> [high_priority, medium_priority, low_priority]
        [fetch_data, high_priority, medium_priority, low_priority] >> aggregate
        
        dag = DAG("multi_stage")
        results = dag.run()
        
        assert results["fetch_data"] == 75
        assert "high_priority" not in results
        assert results["medium_priority"] == 150
        assert "low_priority" not in results
        assert results["aggregate"] == "Processed: 150"
    
    def test_conditional_with_error_handling(self):
        """Test conditional execution with error scenarios."""
        @task()
        def risky_operation():
            return 200
        
        @task(when=lambda x: x > 100)
        def safe_path(value):
            return value / 2
        
        @task(when=lambda x: x <= 100)
        def risky_path(value):
            # This would fail if executed
            raise ValueError("Risky operation failed")
        
        @task()
        def finalize(result):
            return f"Result: {result}"
        
        risky_operation >> [safe_path, risky_path]
        safe_path >> finalize
        
        dag = DAG("conditional_error")
        results = dag.run()
        
        # risky_path should be skipped, so no error
        assert results["risky_operation"] == 200
        assert results["safe_path"] == 100.0
        assert "risky_path" not in results
        assert results["finalize"] == "Result: 100.0"


class TestConditionalEdgeCases:
    """Test edge cases in conditional execution."""
    
    def test_condition_with_none_value(self):
        """Test conditional with None upstream value."""
        @task()
        def source():
            return None
        
        @task(when=lambda x: x is not None)
        def conditional_task(value):
            return "executed"
        
        source >> conditional_task
        
        dag = DAG("condition_none")
        results = dag.run()
        
        assert results["source"] is None
        assert "conditional_task" not in results
    
    def test_condition_with_zero_value(self):
        """Test conditional with zero value (falsy but valid)."""
        @task()
        def source():
            return 0
        
        @task(when=lambda x: x >= 0)
        def conditional_task(value):
            return value + 10
        
        source >> conditional_task
        
        dag = DAG("condition_zero")
        results = dag.run()
        
        assert results["source"] == 0
        assert results["conditional_task"] == 10
    
    def test_condition_with_boolean(self):
        """Test conditional with boolean values."""
        @task()
        def check():
            return True
        
        @task(when=lambda x: x is True)
        def on_true(value):
            return "true_branch"
        
        @task(when=lambda x: x is False)
        def on_false(value):
            return "false_branch"
        
        check >> [on_true, on_false]
        
        dag = DAG("condition_boolean")
        results = dag.run()
        
        assert results["check"] is True
        assert results["on_true"] == "true_branch"
        assert "on_false" not in results
    
    def test_complex_condition_function(self):
        """Test with complex condition function."""
        def complex_condition(data):
            """Complex condition with multiple checks."""
            if not isinstance(data, dict):
                return False
            return data.get("status") == "active" and data.get("value", 0) > 100
        
        @task()
        def source():
            return {"status": "active", "value": 150}
        
        @task(when=complex_condition)
        def conditional_task(data):
            return f"Processing: {data['value']}"
        
        source >> conditional_task
        
        dag = DAG("complex_condition")
        results = dag.run()
        
        assert results["source"]["value"] == 150
        assert results["conditional_task"] == "Processing: 150"

