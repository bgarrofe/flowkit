"""
Comprehensive Functional API Example

This example demonstrates advanced features of the Functional API including:
- Multiple inputs and outputs
- Complex branching and merging
- Retry logic
- Parallel execution
- Real-world use case (data processing pipeline)
"""

import time
import random
from flowkit import task, Layer, FunctionalFlow, Task, configure_logging, LogLevel

# Configure logging
configure_logging(level=LogLevel.INFO, use_colors=True)

# Clear any previous tasks
Task.clear_registry()


# -----------------------------
# Data Ingestion Tasks
# -----------------------------

@task(retries=2)
def fetch_raw_data():
    """Simulate fetching raw data from a source."""
    print("Fetching raw data from database...")
    time.sleep(1)
    return {
        "records": [
            {"id": 1, "value": 100, "category": "A"},
            {"id": 2, "value": 200, "category": "B"},
            {"id": 3, "value": 150, "category": "A"},
            {"id": 4, "value": 300, "category": "C"},
        ]
    }


@task(retries=2)
def fetch_metadata():
    """Simulate fetching metadata."""
    print("Fetching metadata...")
    time.sleep(0.5)
    return {
        "source": "production_db",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0"
    }


@task(retries=2)
def fetch_config():
    """Simulate fetching configuration."""
    print("Fetching configuration...")
    time.sleep(0.3)
    return {
        "threshold": 150,
        "categories": ["A", "B", "C"],
        "output_format": "json"
    }


# -----------------------------
# Data Processing Tasks
# -----------------------------

@task()
def validate_data(fetch_raw_data, fetch_config):
    """Validate data against configuration."""
    print("Validating data...")
    time.sleep(0.5)
    
    data = fetch_raw_data
    config = fetch_config
    
    valid_records = [
        r for r in data["records"]
        if r["category"] in config["categories"]
    ]
    
    return {
        "valid_records": valid_records,
        "total": len(data["records"]),
        "valid": len(valid_records),
        "invalid": len(data["records"]) - len(valid_records)
    }


@task()
def filter_high_value(validate_data, fetch_config):
    """Filter records above threshold."""
    print("Filtering high-value records...")
    time.sleep(0.3)
    
    validation = validate_data
    config = fetch_config
    
    high_value = [
        r for r in validation["valid_records"]
        if r["value"] > config["threshold"]
    ]
    
    return high_value


@task()
def calculate_statistics(validate_data):
    """Calculate statistics on validated data."""
    print("Calculating statistics...")
    time.sleep(0.4)
    
    records = validate_data["valid_records"]
    
    if not records:
        return {"count": 0, "total": 0, "average": 0}
    
    values = [r["value"] for r in records]
    return {
        "count": len(values),
        "total": sum(values),
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values)
    }


@task()
def group_by_category(validate_data):
    """Group records by category."""
    print("Grouping by category...")
    time.sleep(0.3)
    
    records = validate_data["valid_records"]
    groups = {}
    
    for record in records:
        cat = record["category"]
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(record)
    
    return groups


# -----------------------------
# Output Generation Tasks
# -----------------------------

@task()
def generate_summary_report(calculate_statistics, group_by_category, fetch_metadata):
    """Generate summary report."""
    print("Generating summary report...")
    time.sleep(0.5)
    
    stats = calculate_statistics
    groups = group_by_category
    metadata = fetch_metadata
    
    report = {
        "metadata": metadata,
        "statistics": stats,
        "categories": {
            cat: len(records) for cat, records in groups.items()
        },
        "report_type": "summary"
    }
    
    return report


@task()
def generate_detailed_report(filter_high_value, group_by_category, fetch_metadata):
    """Generate detailed report."""
    print("Generating detailed report...")
    time.sleep(0.6)
    
    high_value = filter_high_value
    groups = group_by_category
    metadata = fetch_metadata
    
    report = {
        "metadata": metadata,
        "high_value_count": len(high_value),
        "high_value_records": high_value,
        "category_breakdown": {
            cat: [r["value"] for r in records]
            for cat, records in groups.items()
        },
        "report_type": "detailed"
    }
    
    return report


@task()
def generate_audit_log(validate_data, fetch_metadata):
    """Generate audit log."""
    print("Generating audit log...")
    time.sleep(0.2)
    
    validation = validate_data
    metadata = fetch_metadata
    
    return {
        "timestamp": metadata["timestamp"],
        "source": metadata["source"],
        "total_processed": validation["total"],
        "valid_records": validation["valid"],
        "invalid_records": validation["invalid"],
        "status": "success"
    }


# -----------------------------
# Main Execution
# -----------------------------

def main():
    """Build and execute the comprehensive pipeline."""
    print("=" * 70)
    print("Comprehensive Functional API Example - Data Processing Pipeline")
    print("=" * 70)
    print()
    
    # Wrap tasks as layers
    RawDataLayer = Layer(fetch_raw_data)
    MetadataLayer = Layer(fetch_metadata)
    ConfigLayer = Layer(fetch_config)
    ValidateLayer = Layer(validate_data)
    FilterLayer = Layer(filter_high_value)
    StatsLayer = Layer(calculate_statistics)
    GroupLayer = Layer(group_by_category)
    SummaryLayer = Layer(generate_summary_report)
    DetailedLayer = Layer(generate_detailed_report)
    AuditLayer = Layer(generate_audit_log)
    
    # Build the computational graph
    # Input nodes (data sources)
    raw_data = RawDataLayer()
    metadata = MetadataLayer()
    config = ConfigLayer()
    
    # Processing nodes
    validation = ValidateLayer(raw_data, config)
    high_value = FilterLayer(validation, config)
    statistics = StatsLayer(validation)
    groups = GroupLayer(validation)
    
    # Output nodes (multiple outputs)
    summary_report = SummaryLayer(statistics, groups, metadata)
    detailed_report = DetailedLayer(high_value, groups, metadata)
    audit_log = AuditLayer(validation, metadata)
    
    # Create functional flow with multiple inputs and outputs
    flow = FunctionalFlow(
        inputs=(raw_data, metadata, config),
        outputs=(summary_report, detailed_report, audit_log),
        name="data_processing_pipeline"
    )
    
    # Visualize the flow structure
    print("Pipeline Structure:")
    print(flow.visualize())
    print()
    
    # Execute the pipeline
    print("Executing pipeline...")
    print("-" * 70)
    
    start_time = time.time()
    summary, detailed, audit = flow.run(executor="thread")
    elapsed = time.time() - start_time
    
    # Display results
    print()
    print("=" * 70)
    print("Pipeline Results")
    print("=" * 70)
    print()
    
    print("📊 Summary Report:")
    print(f"  - Total records: {summary['statistics']['count']}")
    print(f"  - Average value: {summary['statistics']['average']:.2f}")
    print(f"  - Categories: {', '.join(summary['categories'].keys())}")
    print()
    
    print("📋 Detailed Report:")
    print(f"  - High-value records: {detailed['high_value_count']}")
    print(f"  - Category breakdown: {len(detailed['category_breakdown'])} categories")
    print()
    
    print("📝 Audit Log:")
    print(f"  - Status: {audit['status']}")
    print(f"  - Valid records: {audit['valid_records']}/{audit['total_processed']}")
    print(f"  - Source: {audit['source']}")
    print()
    
    print(f"⏱️  Total execution time: {elapsed:.2f}s")
    print()


if __name__ == "__main__":
    main()

