# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "matplotlib",
#     "numpy",
#     "pandas",
#     "requests",
#     "seaborn",
# ]
# ///
import os
import sys
import json
import pandas as pd
import numpy as np
import seaborn as sns # type: ignore
import matplotlib.pyplot as plt
import requests

# API configuration
API_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1"
CHAT_MODEL = "gpt-4o-mini"
EMBEDDINGS_MODEL = "text-embedding-3-small"

# Perform basic analysis
def analyze_data(df):
    analysis = {
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "summary": df.describe(include="all").to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "correlations": df.corr(numeric_only=True).to_dict(),
        "head": df.head().to_dict()
    }
    return analysis

# Query the LLM for insights
def query_llm_for_insights(analysis_summary, api_token):
    # Convert analysis_summary to JSON-serializable format
    def make_serializable(obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict()
        if isinstance(obj, pd.Series):
            return obj.to_list()
        if isinstance(obj, np.generic):
            return obj.item()  # Convert NumPy scalars to Python scalars
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # Convert NumPy arrays to lists
        return obj  # Return the object as-is if it's already serializable

    # Recursively apply the conversion
    def serialize_dict(data):
        if isinstance(data, dict):
            return {key: serialize_dict(value) for key, value in data.items()}
        return make_serializable(data)

    serializable_summary = serialize_dict(analysis_summary)

    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "You are a data analysis assistant."},
            {"role": "user", "content": f"Here is a dataset summary: {json.dumps(serializable_summary)}. "
                                         f"Please suggest insights, function calls, and additional analysis steps."}
        ]
    }
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions", 
            headers=headers, 
            json=payload
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return None

# Visualize data
def visualize_data(df):
    plt.figure(figsize=(10, 8))
    sns.heatmap(df.corr(numeric_only=True), annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Correlation Matrix")
    plt.savefig("correlation_matrix.png")
    plt.close()

# Save insights as README
def save_insights_to_readme(insights):
    with open("README.md", "w") as f:
        f.write(insights)

# Main function
def main():
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <data.csv>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    # Read the CSV file
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

    # Perform analysis
    analysis = analyze_data(df)

    # Generate visualizations
    visualize_data(df)

    # Get the API token
    api_token = os.getenv("AIPROXY_TOKEN")
    if not api_token:
        print("Error: AIPROXY_TOKEN environment variable not set.")
        sys.exit(1)

    # Query LLM for insights
    insights = query_llm_for_insights(analysis, api_token)
    if insights:
        print("Insights generated successfully.")
        save_insights_to_readme(insights)
    else:
        print("Failed to generate insights.")

if __name__ == "__main__":
    main()

