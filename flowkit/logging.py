"""Structured logging module for flowkit workflows."""

import logging
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARN"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    SYSTEM = "SYSTEM"


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal formatting."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class FlowkitLogger:
    """
    Structured logger for flowkit workflows.
    
    Provides task lifecycle logging with optional JSON output for
    log aggregation systems. Thread-safe for parallel execution.
    
    Attributes:
        name: Logger name
        level: Logging level
        json_output: Whether to output logs in JSON format
    """
    
    def __init__(
        self,
        name: str = "flowkit",
        level: LogLevel = LogLevel.INFO,
        json_output: bool = False,
        use_colors: bool = True,
    ):
        """
        Initialize a FlowkitLogger.
        
        Args:
            name: Logger name (default: "flowkit")
            level: Logging level (default: LogLevel.INFO)
            json_output: Output logs in JSON format (default: False)
            use_colors: Use ANSI colors in output (default: True)
        """
        self.name = name
        self.level = level
        self.json_output = json_output
        self.use_colors = use_colors and sys.stdout.isatty()
        self._logger = logging.getLogger(name)
        self._configure_logger()
        
        # Level color mapping
        self._level_colors = {
            LogLevel.DEBUG: Colors.BRIGHT_BLACK,
            LogLevel.INFO: Colors.BLUE,
            LogLevel.WARNING: Colors.YELLOW,
            LogLevel.ERROR: Colors.RED,
            LogLevel.SUCCESS: Colors.GREEN,
            LogLevel.SYSTEM: Colors.MAGENTA,
        }
    
    def _configure_logger(self) -> None:
        """Configure the underlying Python logger."""
        self._logger.setLevel(logging.DEBUG)  # Set to DEBUG, filter in handler
        
        # Remove existing handlers
        self._logger.handlers.clear()
        
        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        # Set formatter based on output format
        if self.json_output:
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(ColoredFormatter(self.use_colors))
        
        self._logger.addHandler(handler)
    
    def _format_level(self, level: LogLevel) -> str:
        """Format log level with color."""
        if not self.use_colors:
            return f"[{level.value}]"
        
        color = self._level_colors.get(level, Colors.WHITE)
        return f"{color}[{level.value}]{Colors.RESET}"
    
    def _log_formatted(self, level: LogLevel, message: str) -> None:
        """Log a formatted message with timestamp and level."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_str = self._format_level(level)
        print(f"{timestamp}  {level_str} {message}", flush=True)
    
    def log_task_start(self, task_name: str, **context: Any) -> None:
        """
        Log task execution start.
        
        Args:
            task_name: Name of the task
            **context: Additional context to log
        """
        self._log(
            LogLevel.INFO,
            f'Starting task "{task_name}"...',
            event="task_start",
            task_name=task_name,
            **context
        )
    
    def log_task_success(
        self,
        task_name: str,
        duration: Optional[float] = None,
        output_size: Optional[str] = None,
        **context: Any
    ) -> None:
        """
        Log task execution success.
        
        Args:
            task_name: Name of the task
            duration: Execution duration in seconds
            output_size: Size of output data
            **context: Additional context to log
        """
        msg = f'Task completed successfully: "{task_name}"'
        details = []
        if duration is not None:
            details.append(f"duration: {duration:.2f}s")
        if output_size is not None:
            details.append(f"output: {output_size}")
        
        if details:
            msg += f". {', '.join(details).capitalize()}."
        
        self._log(
            LogLevel.SUCCESS,
            msg,
            event="task_success",
            task_name=task_name,
            duration=duration,
            **context
        )
    
    def log_task_failure(
        self,
        task_name: str,
        error: Exception,
        **context: Any
    ) -> None:
        """
        Log task execution failure.
        
        Args:
            task_name: Name of the task
            error: The exception that caused the failure
            **context: Additional context to log
        """
        self._log(
            LogLevel.ERROR,
            f"Task failed: {task_name} - {type(error).__name__}: {str(error)}",
            event="task_failure",
            task_name=task_name,
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )
    
    def log_task_retry(
        self,
        task_name: str,
        attempt: int,
        max_retries: int,
        delay: float,
        **context: Any
    ) -> None:
        """
        Log task retry attempt.
        
        Args:
            task_name: Name of the task
            attempt: Current retry attempt number
            max_retries: Maximum number of retries
            delay: Delay before retry in seconds
            **context: Additional context to log
        """
        self._log(
            LogLevel.WARNING,
            f"Task retry: {task_name} (attempt {attempt}/{max_retries}, delay: {delay:.2f}s)",
            event="task_retry",
            task_name=task_name,
            attempt=attempt,
            max_retries=max_retries,
            delay=delay,
            **context
        )
    
    def log_task_skip(self, task_name: str, reason: str = "condition not met", **context: Any) -> None:
        """
        Log task skip due to condition.
        
        Args:
            task_name: Name of the task
            reason: Reason for skipping
            **context: Additional context to log
        """
        self._log(
            LogLevel.SYSTEM,
            f'Task skipped: "{task_name}" ({reason})',
            event="task_skip",
            task_name=task_name,
            reason=reason,
            **context
        )
    
    def log_progress(self, message: str, percentage: Optional[int] = None, **context: Any) -> None:
        """
        Log progress information.
        
        Args:
            message: Progress message
            percentage: Percentage complete (0-100)
            **context: Additional context to log
        """
        if percentage is not None:
            # Create progress bar
            bar_length = 20
            filled = int(bar_length * percentage / 100)
            bar = "=" * filled + " " * (bar_length - filled)
            msg = f"{message}: [{bar}] {percentage}%"
        else:
            msg = message
        
        self._log(
            LogLevel.INFO,
            msg,
            event="progress",
            **context
        )
    
    def log_system(self, message: str, **context: Any) -> None:
        """
        Log system-level information.
        
        Args:
            message: System message
            **context: Additional context to log
        """
        self._log(
            LogLevel.SYSTEM,
            message,
            event="system",
            **context
        )
    
    def log_dag_start(self, dag_name: str, total_tasks: int, **context: Any) -> None:
        """
        Log DAG execution start.
        
        Args:
            dag_name: Name of the DAG
            total_tasks: Total number of tasks in the DAG
            **context: Additional context to log
        """
        self._log(
            LogLevel.INFO,
            f"DAG started: {dag_name} ({total_tasks} tasks)",
            event="dag_start",
            dag_name=dag_name,
            total_tasks=total_tasks,
            **context
        )
    
    def log_dag_progress(
        self,
        dag_name: str,
        completed: int,
        total: int,
        **context: Any
    ) -> None:
        """
        Log DAG execution progress.
        
        Args:
            dag_name: Name of the DAG
            completed: Number of completed tasks
            total: Total number of tasks
            **context: Additional context to log
        """
        percentage = (completed / total * 100) if total > 0 else 0
        self._log(
            LogLevel.INFO,
            f"DAG progress: {dag_name} ({completed}/{total} - {percentage:.1f}%)",
            event="dag_progress",
            dag_name=dag_name,
            completed=completed,
            total=total,
            percentage=percentage,
            **context
        )
    
    def log_dag_complete(
        self,
        dag_name: str,
        total_tasks: int,
        duration: Optional[float] = None,
        **context: Any
    ) -> None:
        """
        Log DAG execution completion.
        
        Args:
            dag_name: Name of the DAG
            total_tasks: Total number of tasks completed
            duration: Total execution duration in seconds
            **context: Additional context to log
        """
        msg = f"DAG completed: {dag_name} ({total_tasks} tasks)"
        if duration is not None:
            msg += f" (duration: {duration:.2f}s)"
        
        self._log(
            LogLevel.INFO,
            msg,
            event="dag_complete",
            dag_name=dag_name,
            total_tasks=total_tasks,
            duration=duration,
            **context
        )
    
    def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """
        Internal logging method.
        
        Args:
            level: Log level
            message: Log message
            **context: Additional context to include
        """
        if self.json_output:
            # JSON output
            level_map = {
                LogLevel.DEBUG: self._logger.debug,
                LogLevel.INFO: self._logger.info,
                LogLevel.WARNING: self._logger.warning,
                LogLevel.ERROR: self._logger.error,
                LogLevel.SUCCESS: self._logger.info,
                LogLevel.SYSTEM: self._logger.info,
            }
            log_func = level_map[level]
            log_func(message, extra={"context": context, "level_name": level.value})
        else:
            # Formatted output
            self._log_formatted(level, message)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for terminal output."""
    
    def __init__(self, use_colors: bool = True):
        """Initialize formatter."""
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """Format is handled by FlowkitLogger._log_formatted."""
        return record.getMessage()


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": getattr(record, "level_name", record.levelname),
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context if available
        if hasattr(record, "context"):
            log_data.update(record.context)  # type: ignore
        
        return json.dumps(log_data)


# Global logger instance
_global_logger: Optional[FlowkitLogger] = None


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    json_output: bool = False,
    use_colors: bool = True,
) -> FlowkitLogger:
    """
    Configure global flowkit logging.
    
    Args:
        level: Logging level (default: LogLevel.INFO)
        json_output: Output logs in JSON format (default: False)
        use_colors: Use ANSI colors in output (default: True)
    
    Returns:
        Configured FlowkitLogger instance
    """
    global _global_logger
    _global_logger = FlowkitLogger(level=level, json_output=json_output, use_colors=use_colors)
    return _global_logger


def get_logger() -> FlowkitLogger:
    """
    Get the global logger instance.
    
    Returns:
        Global FlowkitLogger instance (creates default if not configured)
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = FlowkitLogger()
    return _global_logger

