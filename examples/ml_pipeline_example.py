"""
Real-World Machine Learning Pipeline Example

This example demonstrates a complete ML workflow:
- Download CSV data from public source
- Data cleaning and transformation
- Train/test split
- Model training
- Inference on test set
- Evaluation metrics and confusion matrix
"""

import os
import time
import urllib.request

# the following imports will be installed inside the docker container
import pandas as pd # type: ignore
import numpy as np # type: ignore
from sklearn.model_selection import train_test_split # type: ignore
from sklearn.ensemble import RandomForestClassifier # type: ignore
from sklearn.preprocessing import StandardScaler # type: ignore
from sklearn.metrics import ( # type: ignore
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

from flowkit import task, Layer, FunctionalFlow, Task, configure_logging, LogLevel

# Configure logging
configure_logging(level=LogLevel.INFO, use_colors=True)

# Clear any previous tasks
Task.clear_registry()


# -----------------------------
# Data Download Task
# -----------------------------

@task(retries=3)
def download_dataset():
    """
    Download Wine Quality dataset from UCI ML repository.
    This is a publicly available dataset for wine quality classification.
    """
    print("Downloading Wine Quality dataset from UCI ML repository...")
    
    # URL for Wine Quality dataset (red wine)
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv"
    
    # Local file path
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, "winequality-red.csv")
    
    # Download if not exists
    if not os.path.exists(file_path):
        print(f"Downloading from {url}...")
        urllib.request.urlretrieve(url, file_path)
        print(f"Downloaded to {file_path}")
    else:
        print(f"File already exists at {file_path}")
    
    return {"file_path": file_path, "url": url}


# -----------------------------
# Data Loading Task
# -----------------------------

@task()
def load_data(download_dataset):
    """
    Load the CSV file into a pandas DataFrame.
    """
    print("Loading CSV data into DataFrame...")
    
    file_path = download_dataset["file_path"]
    df = pd.read_csv(file_path, sep=';')
    
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns")
    print(f"Columns: {', '.join(df.columns.tolist())}")
    
    return {"dataframe": df, "shape": df.shape}


# -----------------------------
# Data Cleaning Tasks
# -----------------------------

@task()
def clean_data(load_data):
    """
    Perform data cleaning operations:
    - Remove duplicates
    - Handle missing values
    - Remove outliers (using IQR method)
    """
    print("Cleaning data...")
    
    df = load_data["dataframe"].copy()
    original_shape = df.shape
    
    # Remove duplicates
    duplicates_before = len(df)
    df = df.drop_duplicates()
    duplicates_removed = duplicates_before - len(df)
    print(f"  - Removed {duplicates_removed} duplicate rows")
    
    # Check for missing values
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(f"  - Found missing values: {missing[missing > 0].to_dict()}")
        df = df.dropna()
    else:
        print("  - No missing values found")
    
    # Remove outliers using IQR method for numerical columns
    numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # Don't remove outliers from target variable
    if 'quality' in numerical_cols:
        numerical_cols.remove('quality')
    
    outliers_removed = 0
    for col in numerical_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        before = len(df)
        df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        outliers_removed += before - len(df)
    
    if outliers_removed > 0:
        print(f"  - Removed {outliers_removed} outlier rows")
    
    final_shape = df.shape
    print(f"  - Original shape: {original_shape} -> Final shape: {final_shape}")
    
    return {"dataframe": df, "cleaning_stats": {
        "duplicates_removed": duplicates_removed,
        "outliers_removed": outliers_removed,
        "original_shape": original_shape,
        "final_shape": final_shape
    }}


# -----------------------------
# Data Transformation Tasks
# -----------------------------

@task()
def transform_data(clean_data):
    """
    Perform data transformations:
    - Separate features and target
    - Create binary classification target (good wine: quality >= 6)
    - Normalize features (optional, but good practice)
    """
    print("Transforming data...")
    
    df = clean_data["dataframe"].copy()
    
    # Separate features and target
    # Target is 'quality' column
    target_col = 'quality'
    feature_cols = [col for col in df.columns if col != target_col]
    
    X = df[feature_cols].copy()
    y_original = df[target_col].copy()
    
    # Create binary classification target
    # Good wine: quality >= 6, Bad wine: quality < 6
    y = (y_original >= 6).astype(int)
    
    print(f"  - Features: {len(feature_cols)} columns")
    print("  - Target distribution:")
    print(f"    - Good wine (quality >= 6): {y.sum()} samples ({y.sum()/len(y)*100:.1f}%)")
    print(f"    - Bad wine (quality < 6): {(y==0).sum()} samples ({(y==0).sum()/len(y)*100:.1f}%)")
    
    # Feature normalization (standardization)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=feature_cols)
    
    print("  - Features standardized using StandardScaler")
    
    return {
        "X": X_scaled,
        "y": y,
        "feature_names": feature_cols,
        "scaler": scaler,
        "original_quality": y_original
    }


# -----------------------------
# Train/Test Split Task
# -----------------------------

@task()
def split_data(transform_data):
    """
    Split data into training and testing sets.
    """
    print("Splitting data into train and test sets...")
    
    X = transform_data["X"]
    y = transform_data["y"]
    
    # 80/20 split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"  - Training set: {len(X_train)} samples ({len(X_train)/len(X)*100:.1f}%)")
    print(f"  - Test set: {len(X_test)} samples ({len(X_test)/len(X)*100:.1f}%)")
    print(f"  - Training target distribution: {y_train.value_counts().to_dict()}")
    print(f"  - Test target distribution: {y_test.value_counts().to_dict()}")
    
    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test
    }


# -----------------------------
# Model Training Task
# -----------------------------

@task()
def train_model(split_data):
    """
    Train a Random Forest classifier on the training data.
    """
    print("Training Random Forest classifier...")
    
    X_train = split_data["X_train"]
    y_train = split_data["y_train"]
    
    # Initialize model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    # Train model
    start_time = time.time()
    model.fit(X_train, y_train)
    training_time = time.time() - start_time
    
    print(f"  - Model trained in {training_time:.2f} seconds")
    print(f"  - Number of trees: {model.n_estimators}")
    print(f"  - Max depth: {model.max_depth}")
    
    # Calculate training accuracy
    train_pred = model.predict(X_train)
    train_accuracy = accuracy_score(y_train, train_pred)
    print(f"  - Training accuracy: {train_accuracy:.4f}")
    
    return {
        "model": model,
        "training_time": training_time,
        "train_accuracy": train_accuracy
    }


# -----------------------------
# Inference Task
# -----------------------------

@task()
def run_inference(split_data, train_model):
    """
    Run inference on the test set.
    """
    print("Running inference on test set...")
    
    X_test = split_data["X_test"]
    y_test = split_data["y_test"]
    model = train_model["model"]
    
    # Make predictions
    start_time = time.time()
    y_pred = model.predict(X_test)
    inference_time = time.time() - start_time
    
    print(f"  - Inference completed in {inference_time:.4f} seconds")
    print(f"  - Predicted {len(y_pred)} samples")
    
    return {
        "y_test": y_test,
        "y_pred": y_pred,
        "inference_time": inference_time
    }


# -----------------------------
# Evaluation Task
# -----------------------------

@task()
def evaluate_model(run_inference):
    """
    Calculate evaluation metrics and confusion matrix.
    """
    print("Evaluating model performance...")
    
    y_test = run_inference["y_test"]
    y_pred = run_inference["y_pred"]
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    
    # Classification report
    report = classification_report(y_test, y_pred, output_dict=True)
    
    print(f"  - Accuracy: {accuracy:.4f}")
    print(f"  - Precision: {precision:.4f}")
    print(f"  - Recall: {recall:.4f}")
    print(f"  - F1 Score: {f1:.4f}")
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": cm,
        "classification_report": report,
        "y_test": y_test,
        "y_pred": y_pred
    }


# -----------------------------
# Summary Report Task
# -----------------------------

@task()
def generate_summary(
    download_dataset,
    clean_data,
    transform_data,
    split_data,
    train_model,
    run_inference,
    evaluate_model
):
    """
    Generate a comprehensive summary report with all results.
    """
    print("Generating summary report...")
    
    # Collect all information
    cleaning_stats = clean_data["cleaning_stats"]
    model_info = train_model
    metrics = evaluate_model
    cm = metrics["confusion_matrix"]
    
    summary = {
        "dataset_info": {
            "source": download_dataset["url"],
            "file_path": download_dataset["file_path"]
        },
        "data_cleaning": {
            "duplicates_removed": cleaning_stats["duplicates_removed"],
            "outliers_removed": cleaning_stats["outliers_removed"],
            "original_shape": cleaning_stats["original_shape"],
            "final_shape": cleaning_stats["final_shape"]
        },
        "data_transformation": {
            "features": transform_data["feature_names"],
            "num_features": len(transform_data["feature_names"]),
            "target_type": "binary_classification"
        },
        "train_test_split": {
            "train_size": len(split_data["X_train"]),
            "test_size": len(split_data["X_test"]),
            "train_ratio": len(split_data["X_train"]) / (len(split_data["X_train"]) + len(split_data["X_test"]))
        },
        "model_training": {
            "model_type": "RandomForestClassifier",
            "n_estimators": model_info["model"].n_estimators,
            "max_depth": model_info["model"].max_depth,
            "training_time": model_info["training_time"],
            "train_accuracy": model_info["train_accuracy"]
        },
        "inference": {
            "inference_time": run_inference["inference_time"],
            "samples_predicted": len(run_inference["y_pred"])
        },
        "evaluation_metrics": {
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": metrics["f1_score"]
        },
        "confusion_matrix": {
            "matrix": cm.tolist(),
            "true_negatives": int(cm[0, 0]),
            "false_positives": int(cm[0, 1]),
            "false_negatives": int(cm[1, 0]),
            "true_positives": int(cm[1, 1])
        }
    }
    
    return summary


# -----------------------------
# Main Execution
# -----------------------------

def main():
    """Build and execute the ML pipeline."""
    print("=" * 80)
    print("Real-World Machine Learning Pipeline Example")
    print("=" * 80)
    print()
    
    # Wrap tasks as layers
    DownloadLayer = Layer(download_dataset)
    LoadLayer = Layer(load_data)
    CleanLayer = Layer(clean_data)
    TransformLayer = Layer(transform_data)
    SplitLayer = Layer(split_data)
    TrainLayer = Layer(train_model)
    InferenceLayer = Layer(run_inference)
    EvaluateLayer = Layer(evaluate_model)
    SummaryLayer = Layer(generate_summary)
    
    # Build the computational graph
    download = DownloadLayer()
    load = LoadLayer(download)
    clean = CleanLayer(load)
    transform = TransformLayer(clean)
    split = SplitLayer(transform)
    train = TrainLayer(split)
    inference = InferenceLayer(split, train)
    evaluate = EvaluateLayer(inference)
    summary = SummaryLayer(
        download, clean, transform, split, train, inference, evaluate
    )
    
    # Create functional flow
    flow = FunctionalFlow(
        inputs=(download,),
        outputs=(summary,),
        name="ml_pipeline"
    )
    
    # Visualize the flow structure
    print("Pipeline Structure:")
    print(flow.visualize())
    print()
    
    # Execute the pipeline
    print("Executing ML pipeline...")
    print("-" * 80)
    
    start_time = time.time()
    # Flow returns the output value directly when there's a single output
    summary_result = flow.run(executor="thread")
    elapsed = time.time() - start_time
    
    # Display results
    print()
    print("=" * 80)
    print("ML Pipeline Results Summary")
    print("=" * 80)
    print()
    
    # Dataset info
    print("📊 Dataset Information:")
    print(f"  - Source: {summary_result['dataset_info']['source']}")
    print(f"  - File: {summary_result['dataset_info']['file_path']}")
    print()
    
    # Data cleaning
    print("🧹 Data Cleaning:")
    print(f"  - Original shape: {summary_result['data_cleaning']['original_shape']}")
    print(f"  - Final shape: {summary_result['data_cleaning']['final_shape']}")
    print(f"  - Duplicates removed: {summary_result['data_cleaning']['duplicates_removed']}")
    print(f"  - Outliers removed: {summary_result['data_cleaning']['outliers_removed']}")
    print()
    
    # Model info
    print("🤖 Model Information:")
    print(f"  - Type: {summary_result['model_training']['model_type']}")
    print(f"  - Number of trees: {summary_result['model_training']['n_estimators']}")
    print(f"  - Max depth: {summary_result['model_training']['max_depth']}")
    print(f"  - Training time: {summary_result['model_training']['training_time']:.2f}s")
    print(f"  - Training accuracy: {summary_result['model_training']['train_accuracy']:.4f}")
    print()
    
    # Evaluation metrics
    print("📈 Evaluation Metrics (Test Set):")
    metrics = summary_result['evaluation_metrics']
    print(f"  - Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  - Precision: {metrics['precision']:.4f}")
    print(f"  - Recall:    {metrics['recall']:.4f}")
    print(f"  - F1 Score:  {metrics['f1_score']:.4f}")
    print()
    
    # Confusion matrix
    print("🔢 Confusion Matrix:")
    cm = summary_result['confusion_matrix']
    print(f"  - True Negatives:  {cm['true_negatives']}")
    print(f"  - False Positives: {cm['false_positives']}")
    print(f"  - False Negatives: {cm['false_negatives']}")
    print(f"  - True Positives:  {cm['true_positives']}")
    print()
    print("  Matrix:")
    print(f"    [{cm['true_negatives']:4d}  {cm['false_positives']:4d}]")
    print(f"    [{cm['false_negatives']:4d}  {cm['true_positives']:4d}]")
    print()
    
    # Inference info
    print("⚡ Inference:")
    print(f"  - Samples predicted: {summary_result['inference']['samples_predicted']}")
    print(f"  - Inference time: {summary_result['inference']['inference_time']:.4f}s")
    print()
    
    print(f"⏱️  Total pipeline execution time: {elapsed:.2f}s")
    print()


if __name__ == "__main__":
    main()

