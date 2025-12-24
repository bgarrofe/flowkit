"""Example demonstrating parallel task execution."""

from flowkit import task, DAG, Task, configure_logging, LogLevel, get_logger
import time

# Clear any previous tasks
Task.clear_registry()

# Configure colored logging
configure_logging(level=LogLevel.INFO, use_colors=True)


@task()
def fetch_data():
    """Fetch initial data."""
    logger = get_logger()
    logger.log_progress("Fetching data from source...")
    return list(range(100))


@task()
def process_batch_1(data):
    """Process first batch."""
    logger = get_logger()
    logger.log_progress("Processing batch 1 (parallel)...")
    time.sleep(0.1)  # Simulate work
    batch = data[:33]
    return sum(batch)


@task()
def process_batch_2(data):
    """Process second batch."""
    logger = get_logger()
    logger.log_progress("Processing batch 2 (parallel)...")
    time.sleep(0.1)  # Simulate work
    batch = data[33:66]
    return sum(batch)


@task()
def process_batch_3(data):
    """Process third batch."""
    logger = get_logger()
    logger.log_progress("Processing batch 3 (parallel)...")
    time.sleep(0.1)  # Simulate work
    batch = data[66:]
    return sum(batch)


@task()
def aggregate(data, b1, b2, b3):
    """Aggregate all results."""
    logger = get_logger()
    total = b1 + b2 + b3
    logger.log_progress(f"Aggregating results: {b1} + {b2} + {b3} = {total}")
    return total


# Build parallel processing pipeline
fetch_data >> [process_batch_1, process_batch_2, process_batch_3]
[fetch_data, process_batch_1, process_batch_2, process_batch_3] >> aggregate

# Execute
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Flowkit - Parallel Processing Example")
    print("=" * 70 + "\n")
    
    import time
    start_time = time.time()
    
    dag = DAG("parallel_processing", max_workers=3)
    results = dag.run(executor="thread")
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)
    print(f"  Final total: {results['aggregate']}")
    print(f"  Execution time: {elapsed:.2f}s")
    print(f"  Note: Batches processed in parallel!")
    print()

