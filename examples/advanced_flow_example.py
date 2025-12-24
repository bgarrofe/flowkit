"""
Advanced Keras-Style Flow Example

This example demonstrates advanced features of the Flow builder:
- Multiple branching and merging
- Complex dependency graphs
- Conditional execution
- Error handling with retries
"""

import time
import random
from flowkit import task, Flow


# -----------------------------
# Define Tasks
# -----------------------------

@task()
def start_pipeline():
    """Initialize the pipeline."""
    print("🚀 Starting data processing pipeline...")
    return {"timestamp": time.time(), "pipeline_id": "advanced_001"}


@task(retries=3, delay=0.5)
def fetch_data_source_a():
    """Fetch data from source A with potential failures."""
    print("📥 Fetching from Source A...")
    time.sleep(1)
    # Simulate occasional failures
    if random.random() < 0.3:
        raise Exception("Source A temporarily unavailable")
    return {"source": "A", "records": 150, "data": [1, 2, 3]}


@task(retries=3, delay=0.5)
def fetch_data_source_b():
    """Fetch data from source B with potential failures."""
    print("📥 Fetching from Source B...")
    time.sleep(1.5)
    if random.random() < 0.3:
        raise Exception("Source B temporarily unavailable")
    return {"source": "B", "records": 200, "data": [4, 5, 6]}


@task(retries=3, delay=0.5)
def fetch_data_source_c():
    """Fetch data from source C with potential failures."""
    print("📥 Fetching from Source C...")
    time.sleep(1.2)
    if random.random() < 0.3:
        raise Exception("Source C temporarily unavailable")
    return {"source": "C", "records": 175, "data": [7, 8, 9]}


@task()
def merge_datasets(fetch_data_source_a, fetch_data_source_b, fetch_data_source_c):
    """Merge all fetched datasets."""
    print("🔀 Merging all datasets...")
    time.sleep(1)
    total_records = (
        fetch_data_source_a["records"] + 
        fetch_data_source_b["records"] + 
        fetch_data_source_c["records"]
    )
    return {
        "sources": ["A", "B", "C"],
        "total_records": total_records,
        "merged_data": (
            fetch_data_source_a["data"] + 
            fetch_data_source_b["data"] + 
            fetch_data_source_c["data"]
        )
    }


@task()
def transform_data(merge_datasets):
    """Apply transformations to merged data."""
    print("🔄 Transforming data...")
    time.sleep(1.5)
    return {
        **merge_datasets,
        "transformed": True,
        "processed_records": merge_datasets["total_records"]
    }


@task()
def generate_report(transform_data):
    """Generate a summary report."""
    print("📊 Generating report...")
    time.sleep(1)
    return {
        "report_type": "summary",
        "total_records": transform_data["total_records"],
        "sources": transform_data["sources"]
    }


@task()
def export_to_database(transform_data):
    """Export transformed data to database."""
    print("💾 Exporting to database...")
    time.sleep(1.5)
    return {
        "exported": True,
        "records_exported": transform_data["processed_records"]
    }


@task()
def send_notifications(generate_report, export_to_database):
    """Send notifications about pipeline completion."""
    print("📧 Sending notifications...")
    time.sleep(0.5)
    return {
        "notification_sent": True,
        "report": generate_report,
        "export_status": export_to_database
    }


# -----------------------------
# Build Advanced Pipeline
# -----------------------------

def main():
    """Main execution function."""
    print("=" * 70)
    print("Advanced Keras-Style Flow Example")
    print("=" * 70)
    print()
    
    # Build a complex pipeline with multiple branches and merges
    pipeline = (
        Flow("advanced_data_pipeline", max_workers=8)
        .add(start_pipeline)
        # Fetch from 3 sources in parallel
        .branch(fetch_data_source_a, fetch_data_source_b, fetch_data_source_c)
        # Merge all fetched data
        .merge(merge_datasets)
        # Transform the merged data
        .add(transform_data)
        # Branch for report and export in parallel
        .branch(generate_report, export_to_database)
        # Final merge: send notifications
        .merge(send_notifications)
    )
    
    # Visualize the pipeline
    print("Pipeline Structure:")
    print(pipeline.visualize())
    print()
    
    # Execute the pipeline
    print("Executing pipeline...")
    print("-" * 70)
    
    try:
        results = pipeline.run(executor="thread")
        
        # Display results
        print()
        print("=" * 70)
        print("Pipeline Completed Successfully!")
        print("=" * 70)
        print(f"✅ Total tasks executed: {len(results)}")
        
        if "send_notifications" in results:
            notification = results["send_notifications"]
            print(f"✅ Notifications sent: {notification['notification_sent']}")
            print(f"✅ Records exported: {notification['export_status']['records_exported']}")
        
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("Pipeline Failed!")
        print("=" * 70)
        print(f"❌ Error: {e}")
        print()


if __name__ == "__main__":
    main()

