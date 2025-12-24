from flowkit import task, Task, configure_logging, LogLevel, get_logger, Flow

# Clear any previous tasks
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
def transform(extract):
    """Transform the data."""
    logger = get_logger()
    logger.log_progress(f"Transforming {len(extract)} items...")
    return [x * 2 for x in extract]


@task()
def load(transform):
    """Load data to destination."""
    logger = get_logger()
    logger.log_progress(f"Loading {len(transform)} items to database...")
    total = sum(transform)
    return f"Loaded successfully. Total: {total}"


def main():
    """Main execution function."""
    print("=" * 60)
    print("Keras-Style Basic ETL Pipeline Example")
    print("=" * 60)
    print()
    
    # Build the pipeline using method chaining
    pipeline = (
        Flow("basic_etl", max_workers=2)
        .add(extract)
        .add(transform)
        .add(load)
    )
    
    print("Pipeline Structure:")
    print(pipeline.visualize())
    print()
    
    # Run the pipeline with parallel execution
    print("Executing pipeline...")
    print("-" * 60)
    results = pipeline.run(executor="thread")
    
    # Display results
    print()
    print("=" * 60)
    print("Pipeline Results")
    print("=" * 60)
    print(f"Final result: {results.get('send_summary')}")
    print(f"Total tasks executed: {len(results)}")
    print()


if __name__ == "__main__":
    main()