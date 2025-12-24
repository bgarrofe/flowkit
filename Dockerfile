# Dockerfile for FlowKit ML Pipeline Example
# This Dockerfile sets up the environment to run the ML pipeline example

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy project files (README.md is required by pyproject.toml)
COPY pyproject.toml ./
COPY README.md ./
COPY flowkit/ ./flowkit/

# Install build tools and flowkit package
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir . && \
    pip install --no-cache-dir \
    numpy \
    pandas \
    scikit-learn

# Copy example files
COPY examples/ ./examples/

# Create data directory for downloaded datasets
RUN mkdir -p /app/data

# Set Python path
ENV PYTHONPATH=/app

# Default command: run the ML pipeline example
CMD ["python", "examples/ml_pipeline_example.py"]

