"""
Keras-Style Flow Example

This example demonstrates the new Keras-style Flow builder API that makes
pipeline construction feel like building a neural network model.

The Flow API provides:
- Sequential chaining with .add()
- Parallel branching with .branch()
- Merging branches with .merge()
- Automatic dependency resolution
"""

import time
from flowkit import task, Flow


# -----------------------------
# Define Tasks
# -----------------------------

@task(retries=2)
def fetch_user_data():
    """Simulate fetching user data from a database."""
    print("Fetching user data...")
    time.sleep(2)
    return {"user_id": 42, "name": "Alice", "email": "alice@example.com"}


@task(retries=2)
def fetch_orders():
    """Simulate fetching user orders."""
    print("Fetching orders...")
    time.sleep(3)
    return ["order_1", "order_2", "order_3"]


@task(retries=2)
def fetch_recommendations():
    """Simulate fetching product recommendations."""
    print("Fetching recommendations...")
    time.sleep(1.5)
    return ["book_A", "movie_X", "gadget_Z"]


@task()
def enrich_profile(fetch_user_data, fetch_orders, fetch_recommendations):
    """Combine all data sources into an enriched profile."""
    print("Combining all data sources...")
    time.sleep(0.5)
    return {
        "profile": fetch_user_data,
        "orders": fetch_orders,
        "recommendations": fetch_recommendations,
        "enriched_at": time.time()
    }


@task()
def send_summary(enrich_profile):
    """Send a summary email with the enriched profile."""
    print("Sending summary email...")
    time.sleep(1)
    print(f"Email sent for user: {enrich_profile['profile']['name']}")
    return f"Email sent to {enrich_profile['profile']['email']}"


# -----------------------------
# Build Pipeline — Feels Like Keras!
# -----------------------------

def main():
    """Main execution function."""
    print("=" * 60)
    print("Keras-Style Flow Example")
    print("=" * 60)
    print()
    
    # Build the pipeline using method chaining
    pipeline = (
        Flow("user_enrichment_pipeline", max_workers=5)
        .add(fetch_user_data)                           # Start with user data
        .branch(fetch_orders, fetch_recommendations)    # Fetch orders & recommendations in PARALLEL
        .merge(enrich_profile)                          # Wait for ALL three to finish, then merge
        .add(send_summary)                              # Final step
    )
    
    # Visualize the pipeline structure
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

