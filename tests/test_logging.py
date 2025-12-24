"""Tests for logging module."""

import pytest
import json
from flowkit.logging import (
    FlowkitLogger,
    LogLevel,
    configure_logging,
    get_logger,
)


class TestFlowkitLogger:
    """Test FlowkitLogger class."""
    
    def test_logger_creation(self):
        """Test logger creation with defaults."""
        logger = FlowkitLogger()
        assert logger.name == "flowkit"
        assert logger.level == LogLevel.INFO
        assert logger.json_output is False
    
    def test_logger_with_params(self):
        """Test logger creation with custom parameters."""
        logger = FlowkitLogger(
            name="test_logger",
            level=LogLevel.DEBUG,
            json_output=True
        )
        assert logger.name == "test_logger"
        assert logger.level == LogLevel.DEBUG
        assert logger.json_output is True
    
    def test_log_task_start(self, capsys):
        """Test logging task start."""
        logger = FlowkitLogger()
        logger.log_task_start("my_task")
        
        captured = capsys.readouterr()
        assert "Task started: my_task" in captured.out
    
    def test_log_task_success(self, capsys):
        """Test logging task success."""
        logger = FlowkitLogger()
        logger.log_task_success("my_task", duration=1.5)
        
        captured = capsys.readouterr()
        assert "Task succeeded: my_task" in captured.out
        assert "1.5" in captured.out
    
    def test_log_task_failure(self, capsys):
        """Test logging task failure."""
        logger = FlowkitLogger()
        error = ValueError("Test error")
        logger.log_task_failure("my_task", error)
        
        captured = capsys.readouterr()
        assert "Task failed: my_task" in captured.out
        assert "ValueError" in captured.out
        assert "Test error" in captured.out
    
    def test_log_task_retry(self, capsys):
        """Test logging task retry."""
        logger = FlowkitLogger()
        logger.log_task_retry("my_task", attempt=2, max_retries=3, delay=2.0)
        
        captured = capsys.readouterr()
        assert "Task retry: my_task" in captured.out
        assert "2/3" in captured.out
        assert "2.0" in captured.out
    
    def test_log_task_skip(self, capsys):
        """Test logging task skip."""
        logger = FlowkitLogger()
        logger.log_task_skip("my_task", reason="condition not met")
        
        captured = capsys.readouterr()
        assert "Task skipped: my_task" in captured.out
        assert "condition not met" in captured.out
    
    def test_log_dag_start(self, capsys):
        """Test logging DAG start."""
        logger = FlowkitLogger()
        logger.log_dag_start("my_dag", total_tasks=5)
        
        captured = capsys.readouterr()
        assert "DAG started: my_dag" in captured.out
        assert "5 tasks" in captured.out
    
    def test_log_dag_progress(self, capsys):
        """Test logging DAG progress."""
        logger = FlowkitLogger()
        logger.log_dag_progress("my_dag", completed=3, total=5)
        
        captured = capsys.readouterr()
        assert "DAG progress: my_dag" in captured.out
        assert "3/5" in captured.out
        assert "60.0%" in captured.out
    
    def test_log_dag_complete(self, capsys):
        """Test logging DAG completion."""
        logger = FlowkitLogger()
        logger.log_dag_complete("my_dag", total_tasks=5, duration=10.5)
        
        captured = capsys.readouterr()
        assert "DAG completed: my_dag" in captured.out
        assert "5 tasks" in captured.out
        assert "10.5" in captured.out


class TestLogLevels:
    """Test different log levels."""
    
    def test_debug_level(self, capsys):
        """Test DEBUG log level."""
        logger = FlowkitLogger(level=LogLevel.DEBUG)
        logger._log(LogLevel.DEBUG, "Debug message")
        
        captured = capsys.readouterr()
        assert "Debug message" in captured.out
    
    def test_info_level(self, capsys):
        """Test INFO log level."""
        logger = FlowkitLogger(level=LogLevel.INFO)
        logger._log(LogLevel.INFO, "Info message")
        
        captured = capsys.readouterr()
        assert "Info message" in captured.out
    
    def test_warning_level(self, capsys):
        """Test WARNING log level."""
        logger = FlowkitLogger(level=LogLevel.WARNING)
        logger._log(LogLevel.WARNING, "Warning message")
        
        captured = capsys.readouterr()
        assert "Warning message" in captured.out
    
    def test_error_level(self, capsys):
        """Test ERROR log level."""
        logger = FlowkitLogger(level=LogLevel.ERROR)
        logger._log(LogLevel.ERROR, "Error message")
        
        captured = capsys.readouterr()
        assert "Error message" in captured.out
    
    def test_level_filtering(self, capsys):
        """Test that lower level messages are filtered out."""
        logger = FlowkitLogger(level=LogLevel.ERROR)
        logger._log(LogLevel.INFO, "Info message")
        logger._log(LogLevel.ERROR, "Error message")
        
        captured = capsys.readouterr()
        assert "Info message" not in captured.out
        assert "Error message" in captured.out


class TestJsonOutput:
    """Test JSON output format."""
    
    def test_json_output_format(self, capsys):
        """Test that JSON output is valid JSON."""
        logger = FlowkitLogger(json_output=True)
        logger.log_task_start("my_task")
        
        captured = capsys.readouterr()
        
        # Should be valid JSON
        log_entry = json.loads(captured.out.strip())
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
        assert log_entry["level"] == "INFO"
        assert "my_task" in log_entry["message"]
    
    def test_json_with_context(self, capsys):
        """Test JSON output includes context."""
        logger = FlowkitLogger(json_output=True)
        logger.log_task_success("my_task", duration=1.5, custom_field="value")
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["duration"] == 1.5
        assert log_entry["custom_field"] == "value"
    
    def test_json_task_failure(self, capsys):
        """Test JSON output for task failure."""
        logger = FlowkitLogger(json_output=True)
        error = ValueError("Test error")
        logger.log_task_failure("my_task", error)
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["event"] == "task_failure"
        assert log_entry["task_name"] == "my_task"
        assert log_entry["error_type"] == "ValueError"
        assert log_entry["error_message"] == "Test error"


class TestGlobalLogger:
    """Test global logger configuration."""
    
    def test_configure_logging(self):
        """Test global logger configuration."""
        logger = configure_logging(level=LogLevel.DEBUG, json_output=True)
        
        assert isinstance(logger, FlowkitLogger)
        assert logger.level == LogLevel.DEBUG
        assert logger.json_output is True
    
    def test_get_logger_default(self):
        """Test getting default logger."""
        # Reset global logger
        import flowkit.logging as logging_module
        logging_module._global_logger = None
        
        logger = get_logger()
        assert isinstance(logger, FlowkitLogger)
        assert logger.level == LogLevel.INFO
    
    def test_get_logger_configured(self):
        """Test getting configured logger."""
        configured = configure_logging(level=LogLevel.WARNING)
        retrieved = get_logger()
        
        assert retrieved is configured
        assert retrieved.level == LogLevel.WARNING


class TestLoggerContext:
    """Test logger with additional context."""
    
    def test_task_start_with_context(self, capsys):
        """Test task start logging with context."""
        logger = FlowkitLogger()
        logger.log_task_start("my_task", user="test_user", run_id="123")
        
        captured = capsys.readouterr()
        assert "Task started: my_task" in captured.out
    
    def test_json_context_preserved(self, capsys):
        """Test that context is preserved in JSON output."""
        logger = FlowkitLogger(json_output=True)
        logger.log_task_start(
            "my_task",
            user="test_user",
            run_id="123",
            environment="test"
        )
        
        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip())
        
        assert log_entry["user"] == "test_user"
        assert log_entry["run_id"] == "123"
        assert log_entry["environment"] == "test"


class TestLoggerIntegration:
    """Integration tests for logger with workflows."""
    
    def test_complete_workflow_logging(self, capsys):
        """Test logging for a complete workflow."""
        logger = FlowkitLogger()
        
        # Simulate workflow
        logger.log_dag_start("test_workflow", total_tasks=3)
        
        logger.log_task_start("task1")
        logger.log_task_success("task1", duration=0.5)
        
        logger.log_task_start("task2")
        logger.log_task_retry("task2", attempt=1, max_retries=2, delay=1.0)
        logger.log_task_success("task2", duration=1.5)
        
        logger.log_task_start("task3")
        logger.log_task_skip("task3", reason="condition not met")
        
        logger.log_dag_complete("test_workflow", total_tasks=3, duration=2.5)
        
        captured = capsys.readouterr()
        
        assert "DAG started: test_workflow" in captured.out
        assert "Task started: task1" in captured.out
        assert "Task succeeded: task1" in captured.out
        assert "Task retry: task2" in captured.out
        assert "Task skipped: task3" in captured.out
        assert "DAG completed: test_workflow" in captured.out
    
    def test_workflow_with_failure(self, capsys):
        """Test logging workflow with failure."""
        logger = FlowkitLogger()
        
        logger.log_dag_start("failing_workflow", total_tasks=2)
        logger.log_task_start("task1")
        logger.log_task_success("task1", duration=0.5)
        
        logger.log_task_start("task2")
        error = RuntimeError("Task execution failed")
        logger.log_task_failure("task2", error)
        
        captured = capsys.readouterr()
        
        assert "DAG started: failing_workflow" in captured.out
        assert "Task succeeded: task1" in captured.out
        assert "Task failed: task2" in captured.out
        assert "RuntimeError" in captured.out


class TestLoggerEdgeCases:
    """Test edge cases in logging."""
    
    def test_empty_task_name(self, capsys):
        """Test logging with empty task name."""
        logger = FlowkitLogger()
        logger.log_task_start("")
        
        captured = capsys.readouterr()
        assert "Task started:" in captured.out
    
    def test_none_duration(self, capsys):
        """Test logging success without duration."""
        logger = FlowkitLogger()
        logger.log_task_success("my_task", duration=None)
        
        captured = capsys.readouterr()
        assert "Task succeeded: my_task" in captured.out
    
    def test_zero_total_tasks(self, capsys):
        """Test DAG progress with zero total tasks."""
        logger = FlowkitLogger()
        logger.log_dag_progress("my_dag", completed=0, total=0)
        
        captured = capsys.readouterr()
        assert "0/0" in captured.out
    
    def test_special_characters_in_message(self, capsys):
        """Test logging with special characters."""
        logger = FlowkitLogger()
        logger.log_task_start("task_with_特殊字符_and_émojis_🚀")
        
        captured = capsys.readouterr()
        assert "Task started:" in captured.out

