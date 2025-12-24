"""Example demonstrating conditional task execution."""

from flowkit import task, DAG, Task, configure_logging, LogLevel, get_logger
import random

# Clear any previous tasks
Task.clear_registry()

# Configure colored logging
configure_logging(level=LogLevel.INFO, use_colors=True)


@task()
def generate_value():
    """Generate a random value."""
    logger = get_logger()
    value = random.randint(500, 2000)
    logger.log_progress(f"Generated random value: {value}")
    return value


@task()
def transform(value):
    """Transform the value."""
    logger = get_logger()
    result = value * 2
    logger.log_progress(f"Transformed: {value} -> {result}")
    return result


@task(when=lambda x: x > 1200)
def require_approval(value):
    """Handle large values (requires approval)."""
    logger = get_logger()
    logger._log(LogLevel.WARNING, f"⚠️  Large value detected: {value} - Manual approval required")
    return "MANUAL_APPROVAL"


@task(when=lambda x: x <= 1200)
def auto_approve(value):
    """Handle small values (auto-approved)."""
    logger = get_logger()
    logger._log(LogLevel.SUCCESS, f"✓ Small value: {value} - Auto-approved")
    return "AUTO_APPROVED"


@task()
def finalize(transformed, manual=None, auto=None):
    """Finalize the process."""
    logger = get_logger()
    approval = manual or auto or "NO_APPROVAL"
    logger.log_progress(f"Finalizing with approval: {approval}")
    return f"Completed: {transformed} ({approval})"


# Build conditional pipeline
generate_value >> transform
transform >> [require_approval, auto_approve]
[transform, require_approval, auto_approve] >> finalize

# Execute
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Flowkit - Conditional Workflow Example")
    print("=" * 70 + "\n")
    
    dag = DAG("conditional_workflow")
    results = dag.run()
    
    print("\n" + "=" * 70)
    print("Final Results:")
    print("=" * 70)
    for task_name, result in results.items():
        print(f"  {task_name}: {result}")
    print()

