"""
Simple Functional API Example

This example closely follows the user's specification for a clean,
Keras-style functional API with multiple inputs and outputs.
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
    """Fetch user data."""
    time.sleep(2)
    return {"id": 123, "name": "Alice"}


@task(retries=2)
def fetch_orders():
    """Fetch orders."""
    time.sleep(3)
    return ["order1", "order2"]


@task(retries=2)
def fetch_recommendations():
    """Fetch recommendations."""
    time.sleep(1.5)
    return ["bookA", "movieX"]


@task()
def build_profile(fetch_user, fetch_orders):
    """Build user profile."""
    return {"profile": fetch_user, "past_orders": fetch_orders}


@task()
def generate_recommendations(fetch_user, fetch_recommendations):
    """Generate personalized recommendations."""
    return {"personalized": ["itemX", "itemY"], "base": fetch_recommendations}


@task()
def summarize(build_profile, generate_recommendations):
    """Create summary."""
    print("Final summary created")
    return {"user": build_profile["profile"]["name"], "recs": generate_recommendations["personalized"]}


@task()
def log_activity(build_profile, generate_recommendations):
    """Log activity."""
    print("Activity logged")
    return "logged"


# -----------------------------
# Build Model — Keras Functional API Style
# -----------------------------

if __name__ == "__main__":
    # Wrap as layers
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
    
    profile = ProfileLayer(user, orders)           # multi-input
    personalized_recs = GenRecsLayer(user, recs)   # multi-input, parallel branch
    
    summary = SummaryLayer(profile, personalized_recs)
    activity_log = LogLayer(profile, personalized_recs)
    
    # Define model with multiple inputs and multiple outputs
    model = FunctionalFlow(
        inputs=(user, orders, recs),
        outputs=(summary, activity_log),
        name="multi_head_user_pipeline"
    )
    
    # Run — fully parallel where possible!
    print("Running model...")
    print("-" * 60)
    
    summary_result, log_result = model.run(executor="thread")
    
    print("\nOutputs:")
    print("Summary:", summary_result)
    print("Log:", log_result)

