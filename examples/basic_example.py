"""Basic example demonstrating flowkit usage."""

from flowkit import task, DAG, Task, configure_logging, LogLevel, get_logger

# Clear any previous tasks (useful in interactive environments)
Task.clear_registry()

# Configure colored logging
configure_logging(level=LogLevel.INFO, use_colors=True)


@task(retries=2)
def extract():
    """Extract data from source."""
    logger = get_logger()
    logger.log_progress("Extracting data from source...")
    return [1, 2, 3, 4, 5]


@task()
def transform(data):
    """Transform the data."""
    logger = get_logger()
    logger.log_progress(f"Transforming {len(data)} items...")
    return [x * 2 for x in data]


@task()
def load(data):
    """Load data to destination."""
    logger = get_logger()
    logger.log_progress(f"Loading {len(data)} items to database...")
    total = sum(data)
    return f"Loaded successfully. Total: {total}"


# Define pipeline using >> operator
extract >> transform >> load

# Execute the pipeline
if __name__ == "__main__":
    logger = get_logger()
    
    print("\n" + "=" * 70)
    print("Flowkit - Basic ETL Pipeline Example")
    print("=" * 70 + "\n")
    
    dag = DAG("basic_etl", max_workers=2)
    results = dag.run()
    
    print("\n" + "=" * 70)
    print("Pipeline Results:")
    print("=" * 70)
    for task_name, result in results.items():
        print(f"  {task_name}: {result}")
    print()

