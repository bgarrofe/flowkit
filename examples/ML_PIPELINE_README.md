# Machine Learning Pipeline Example

This example demonstrates a complete end-to-end machine learning pipeline using FlowKit's functional API.

## Overview

The pipeline performs the following steps:

1. **Download Dataset**: Downloads the Wine Quality dataset from UCI ML repository
2. **Load Data**: Loads the CSV file into a pandas DataFrame
3. **Clean Data**: Removes duplicates, handles missing values, and removes outliers
4. **Transform Data**: Separates features and target, creates binary classification target, normalizes features
5. **Split Data**: Splits data into 80/20 train/test sets
6. **Train Model**: Trains a Random Forest classifier
7. **Run Inference**: Makes predictions on the test set
8. **Evaluate Model**: Calculates accuracy, precision, recall, F1 score, and confusion matrix
9. **Generate Summary**: Creates a comprehensive report with all results

## Dataset

The example uses the **Wine Quality Dataset** from the UCI Machine Learning Repository:
- **Source**: https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/
- **Task**: Binary classification (good wine: quality >= 6, bad wine: quality < 6)
- **Features**: 11 wine characteristics (acidity, sugar, alcohol, etc.)
- **Target**: Wine quality (converted to binary)

## Running Locally

### Prerequisites

Install the required dependencies:

```bash
pip install numpy pandas scikit-learn
```

Or if using Poetry:

```bash
poetry add numpy pandas scikit-learn
```

### Execute the Pipeline

```bash
python examples/ml_pipeline_example.py
```

Or with Poetry:

```bash
poetry run python examples/ml_pipeline_example.py
```

## Running with Docker

### Build the Docker Image

```bash
docker build -t flowkit-ml-pipeline .
```

### Run the Container

```bash
docker run --rm flowkit-ml-pipeline
```

### Run with Volume Mount (to persist downloaded data)

```bash
docker run --rm -v $(pwd)/data:/app/data flowkit-ml-pipeline
```

### Interactive Mode

To explore the container interactively:

```bash
docker run --rm -it flowkit-ml-pipeline /bin/bash
```

## Expected Output

The pipeline will:

1. Download the dataset (if not already present)
2. Process and clean the data
3. Train a Random Forest model
4. Evaluate on the test set
5. Display comprehensive metrics including:
   - Accuracy, Precision, Recall, F1 Score
   - Confusion Matrix
   - Training and inference times
   - Data cleaning statistics

## Output Files

- `data/winequality-red.csv`: Downloaded dataset (created automatically)

## Customization

You can modify the example to:

- Use a different dataset by changing the URL in `download_dataset()`
- Try different models by modifying `train_model()` (e.g., Logistic Regression, SVM, XGBoost)
- Adjust train/test split ratio in `split_data()`
- Change classification threshold (currently quality >= 6)
- Add more data transformations or feature engineering

## Notes

- The dataset is downloaded automatically on first run
- The pipeline uses stratified train/test split to maintain class distribution
- StandardScaler is used for feature normalization
- Random Forest with 100 trees and max_depth=10 is used as the default model

