"""
Functional API Example - Multiple Inputs and Outputs

This example demonstrates the Keras-style Functional API that supports
multiple inputs and multiple outputs. This is useful for complex workflows
where you need fine-grained control over the computational graph.

The Functional API provides:
- Multiple input nodes
- Multiple output nodes
- Explicit graph construction
- Parallel execution where possible
"""

import time
from flowkit import task, Layer, FunctionalFlow, Task

# Clear any previous tasks
Task.clear_registry()


# -----------------------------
# Define Tasks
# -----------------------------

@task(retries=2)
def fetch_user():
    """Simulate fetching user data."""
    print("Fetching user data...")
    time.sleep(2)
    return {"id": 123, "name": "Alice"}


@task(retries=2)
def fetch_orders():
    """Simulate fetching orders."""
    print("Fetching orders...")
    time.sleep(3)
    return ["order1", "order2"]


@task(retries=2)
def fetch_recommendations():
    """Simulate fetching recommendations."""
    print("Fetching recommendations...")
    time.sleep(1.5)
    return ["bookA", "movieX"]


@task()
def build_profile(fetch_user, fetch_orders):
    """Build user profile from user data and orders."""
    print("Building profile...")
    time.sleep(0.5)
    return {"profile": fetch_user, "past_orders": fetch_orders}


@task()
def generate_recommendations(fetch_user, fetch_recommendations):
    """Generate personalized recommendations."""
    print("Generating personalized recommendations...")
    time.sleep(0.5)
    return {"personalized": ["itemX", "itemY"], "base": fetch_recommendations}


@task()
def summarize(build_profile, generate_recommendations):
    """Create final summary."""
    print("Creating final summary...")
    time.sleep(0.3)
    return {
        "user": build_profile["profile"]["name"],
        "recs": generate_recommendations["personalized"]
    }


@task()
def log_activity(build_profile, generate_recommendations):
    """Log user activity."""
    print("Logging activity...")
    time.sleep(0.2)
    return "Activity logged successfully"


# -----------------------------
# Build Functional Model
# -----------------------------

def main():
    """Main execution function."""
    print("=" * 60)
    print("Functional API Example - Multiple Inputs & Outputs")
    print("=" * 60)
    print()
    
    # Wrap tasks as layers
    UserLayer = Layer(fetch_user)
    OrdersLayer = Layer(fetch_orders)
    RecsLayer = Layer(fetch_recommendations)
    ProfileLayer = Layer(build_profile)
    GenRecsLayer = Layer(generate_recommendations)
    SummaryLayer = Layer(summarize)
    LogLayer = Layer(log_activity)
    
    # Build model — just like Keras Functional API!
    user = UserLayer()
    orders = OrdersLayer()
    recs = RecsLayer()
    
    # Multi-input tasks
    profile = ProfileLayer(user, orders)
    personalized_recs = GenRecsLayer(user, recs)
    
    # Multiple outputs
    summary = SummaryLayer(profile, personalized_recs)
    activity_log = LogLayer(profile, personalized_recs)
    
    # Define model with multiple inputs and multiple outputs
    model = FunctionalFlow(
        inputs=(user, orders, recs),
        outputs=(summary, activity_log),
        name="multi_head_user_pipeline"
    )
    
    # Visualize the model structure
    print("Model Structure:")
    print(model.visualize())
    print()
    
    # Run — fully parallel where possible!
    print("Executing model...")
    print("-" * 60)
    
    summary_result, log_result = model.run(executor="thread")
    
    # Display results
    print()
    print("=" * 60)
    print("Model Results")
    print("=" * 60)
    print(f"Summary: {summary_result}")
    print(f"Activity Log: {log_result}")
    print()


if __name__ == "__main__":
    main()

