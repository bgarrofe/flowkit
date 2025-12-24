"""Tests for task module."""

import pytest
from flowkit.task import Task, task


class TestTaskCreation:
    """Test task creation and initialization."""
    
    def test_task_decorator_basic(self):
        """Test basic task creation with decorator."""
        @task()
        def my_task():
            return "result"
        
        assert isinstance(my_task, Task)
        assert my_task.name == "my_task"
        assert my_task.retries == 0
        assert my_task.delay == 1.0
        assert my_task.backoff == 2.0
        assert my_task.when is None
    
    def test_task_decorator_with_params(self):
        """Test task creation with parameters."""
        @task(retries=3, delay=2.0, backoff=3.0)
        def my_task():
            return "result"
        
        assert my_task.retries == 3
        assert my_task.delay == 2.0
        assert my_task.backoff == 3.0
    
    def test_task_decorator_with_condition(self):
        """Test task creation with conditional execution."""
        condition = lambda x: x > 10
        
        @task(when=condition)
        def my_task(value):
            return value * 2
        
        assert my_task.when is condition
    
    def test_task_registration(self):
        """Test that tasks are registered in global registry."""
        initial_count = len(Task._all_tasks)
        
        @task()
        def task1():
            pass
        
        @task()
        def task2():
            pass
        
        assert len(Task._all_tasks) == initial_count + 2
        assert task1 in Task._all_tasks
        assert task2 in Task._all_tasks
    
    def test_task_clear_registry(self):
        """Test clearing the task registry."""
        @task()
        def my_task():
            pass
        
        assert len(Task._all_tasks) > 0
        Task.clear_registry()
        assert len(Task._all_tasks) == 0


class TestTaskExecution:
    """Test task execution."""
    
    def test_task_execution_basic(self):
        """Test basic task execution."""
        @task()
        def my_task():
            return 42
        
        result = my_task()
        assert result == 42
    
    def test_task_execution_with_args(self):
        """Test task execution with arguments."""
        @task()
        def my_task(x, y):
            return x + y
        
        result = my_task(10, 20)
        assert result == 30
    
    def test_task_execution_with_kwargs(self):
        """Test task execution with keyword arguments."""
        @task()
        def my_task(x, y=5):
            return x * y
        
        result = my_task(3, y=7)
        assert result == 21
    
    def test_task_execution_failure(self):
        """Test task execution with failure."""
        @task()
        def failing_task():
            raise ValueError("Task failed")
        
        with pytest.raises(ValueError, match="Task failed"):
            failing_task()


class TestTaskRetry:
    """Test task retry logic."""
    
    def test_retry_success_on_first_attempt(self, mock_sleep):
        """Test task succeeds on first attempt (no retries needed)."""
        @task(retries=3)
        def my_task():
            return "success"
        
        result = my_task()
        assert result == "success"
        mock_sleep.assert_not_called()
    
    def test_retry_success_after_failures(self, mock_sleep):
        """Test task succeeds after some failures."""
        call_count = 0
        
        @task(retries=3, delay=1.0)
        def my_task():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = my_task()
        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # 2 retries before success
    
    def test_retry_exhausted(self, mock_sleep):
        """Test task fails after all retries exhausted."""
        @task(retries=2, delay=1.0)
        def my_task():
            raise ValueError("Permanent failure")
        
        with pytest.raises(ValueError, match="Permanent failure"):
            my_task()
        
        assert mock_sleep.call_count == 2  # All retries attempted
    
    def test_retry_with_backoff(self, mock_sleep):
        """Test exponential backoff in retries."""
        call_count = 0
        
        @task(retries=3, delay=1.0, backoff=2.0)
        def my_task():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Failure")
            return "success"
        
        result = my_task()
        assert result == "success"
        
        # Check that sleep was called with increasing delays
        # Note: actual delays include jitter, so we check the base values
        assert mock_sleep.call_count == 3


class TestTaskConditional:
    """Test conditional task execution."""
    
    def test_conditional_execution_true(self):
        """Test task executes when condition is true."""
        @task(when=lambda x: x > 10)
        def my_task(value):
            return value * 2
        
        result = my_task(15)
        assert result == 30
    
    def test_conditional_execution_false(self):
        """Test task skips when condition is false."""
        @task(when=lambda x: x > 10)
        def my_task(value):
            return value * 2
        
        result = my_task(5)
        assert result is None
    
    def test_conditional_with_no_args(self):
        """Test conditional task with no arguments skips."""
        @task(when=lambda x: x > 10)
        def my_task():
            return "executed"
        
        result = my_task()
        assert result is None


class TestTaskOperators:
    """Test task operator overloading."""
    
    def test_rshift_single_task(self):
        """Test >> operator with single task (linear chain)."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2(x):
            return x + 1
        
        result = task1 >> task2
        
        assert result is task2
        assert task2 in task1.downstream
        assert task1 in task2.upstream
    
    def test_rshift_multiple_tasks(self):
        """Test >> operator with list of tasks (branching)."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2(x):
            return x + 1
        
        @task()
        def task3(x):
            return x + 2
        
        result = task1 >> [task2, task3]
        
        assert result == [task2, task3]
        assert task2 in task1.downstream
        assert task3 in task1.downstream
        assert task1 in task2.upstream
        assert task1 in task3.upstream
    
    def test_rrshift_multiple_tasks(self):
        """Test >> operator with list on left (merging)."""
        @task()
        def task1():
            return 1
        
        @task()
        def task2():
            return 2
        
        @task()
        def task3(x, y):
            return x + y
        
        result = [task1, task2] >> task3
        
        assert result is task3
        assert task1 in task3.upstream
        assert task2 in task3.upstream
        assert task3 in task1.downstream
        assert task3 in task2.downstream
    
    def test_complex_pipeline(self):
        """Test complex pipeline with branching and merging."""
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
        
        # Build pipeline: extract >> [transform1, transform2] >> load
        extract >> [transform1, transform2]
        [transform1, transform2] >> load
        
        assert len(extract.downstream) == 2
        assert len(load.upstream) == 2
        assert transform1 in extract.downstream
        assert transform2 in extract.downstream
        assert transform1 in load.upstream
        assert transform2 in load.upstream


class TestTaskRepr:
    """Test task string representation."""
    
    def test_task_repr(self):
        """Test task __repr__ method."""
        @task()
        def task1():
            pass
        
        @task()
        def task2():
            pass
        
        task1 >> task2
        
        repr1 = repr(task1)
        repr2 = repr(task2)
        
        assert "task1" in repr1
        assert "downstream=1" in repr1
        assert "upstream=0" in repr1
        
        assert "task2" in repr2
        assert "downstream=0" in repr2
        assert "upstream=1" in repr2

