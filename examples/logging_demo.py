"""Demo of the new logging system with colored output."""

from flowkit import task, DAG, Task, configure_logging, LogLevel
import time

# Clear any previous tasks
Task.clear_registry()

# Configure logging with colors
configure_logging(level=LogLevel.INFO, use_colors=True)


@task()
def fetch_data_api():
    """Simulate fetching data from an API."""
    logger = __import__('flowkit').get_logger()
    logger.log_progress("Resolving endpoint api.data-provider.com")
    time.sleep(0.1)
    logger.log_progress("Connection established. Handshake successful.")
    time.sleep(0.1)
    logger._log(LogLevel.WARNING, "Response latency higher than expected (450ms).")
    time.sleep(0.1)
    logger.log_progress("Streaming data chunks", percentage=100)
    time.sleep(0.2)
    logger.log_progress("Received 14,502 records.")
    time.sleep(0.1)
    logger.log_progress("Validating schema integrity...")
    time.sleep(0.1)
    return {"records": 14502, "size_mb": 45}


@task()
def process_data(data):
    """Process the fetched data."""
    logger = __import__('flowkit').get_logger()
    logger.log_progress("Processing records...")
    time.sleep(0.2)
    logger.log_progress("Applying transformations...")
    time.sleep(0.2)
    return {"processed": data["records"], "size_mb": data["size_mb"]}


@task()
def save_results(data):
    """Save processed results."""
    logger = __import__('flowkit').get_logger()
    logger.log_progress("Writing to database...")
    time.sleep(0.2)
    return f"Saved {data['processed']} records"


# Build pipeline
fetch_data_api >> process_data >> save_results

# Execute
if __name__ == "__main__":
    from flowkit import get_logger
    
    logger = get_logger()
    
    print("\n" + "=" * 70)
    print("Flowkit Logging Demo - Colored Terminal Output")
    print("=" * 70 + "\n")
    
    dag = DAG("data_pipeline", max_workers=1)
    
    try:
        results = dag.run()
        logger.log_system("Worker released.")
        
        print("\n" + "=" * 70)
        print("Pipeline completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        logger._log(LogLevel.ERROR, f"Pipeline failed: {e}")

