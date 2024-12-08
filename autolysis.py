# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "matplotlib",
#     "numpy",
#     "pandas",
#     "requests",
#     "seaborn"
# ]
# ///

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json

# Set your proxy endpoint
API_ENDPOINT = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
MODEL = "gpt-4o-mini"


def get_api_token():
    """Retrieve the API token from the environment variable."""
    token = os.getenv("AIPROXY_TOKEN")
    if not token:
        raise EnvironmentError("AIPROXY_TOKEN environment variable not set.")
    return token


def query_llm(messages, api_token):
    """Query the LLM with the given messages using the provided API endpoint."""
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
    }
    response = requests.post(API_ENDPOINT, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        response.raise_for_status()


def save_chart(fig, chart_name):
    """Save a chart as a PNG file."""
    chart_path = f"{chart_name}.png"
    fig.savefig(chart_path, format="png", bbox_inches="tight")
    plt.close(fig)
    return chart_path


def analyze_data(data):
    """Perform initial analysis and generate summaries."""
    analysis_results = {}

    # Summary statistics
    summary_stats = data.describe(include="all").to_dict()
    analysis_results["summary_statistics"] = summary_stats

    # Missing values
    missing_values = data.isnull().sum().to_dict()
    analysis_results["missing_values"] = missing_values

    # Correlation matrix
    numeric_data = data.select_dtypes(include=["number"])
    if not numeric_data.empty:
        correlation_matrix = numeric_data.corr()
        analysis_results["correlations"] = correlation_matrix.to_dict()

        # Visualize correlation matrix
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
        save_chart(fig, "correlation_matrix")

    return analysis_results


def visualize_suggestions(data, suggestions):
    """Generate visualizations based on LLM suggestions."""
    numeric_data = data.select_dtypes(include=["number"])
    chart_paths = []

    for suggestion in suggestions.split("\n"):
        suggestion = suggestion.lower()

        if "histogram" in suggestion:
            for col in numeric_data.columns:
                fig, ax = plt.subplots(figsize=(6, 4))
                numeric_data[col].hist(bins=20, ax=ax)
                ax.set_title(f"Histogram of {col}")
                chart_paths.append(save_chart(fig, f"histogram_{col}"))

        elif "scatter" in suggestion and numeric_data.shape[1] >= 2:
            cols = numeric_data.columns[:2]
            fig, ax = plt.subplots(figsize=(6, 4))
            sns.scatterplot(x=numeric_data[cols[0]], y=numeric_data[cols[1]], ax=ax)
            ax.set_title(f"Scatterplot of {cols[0]} vs {cols[1]}")
            chart_paths.append(save_chart(fig, "scatterplot"))

        # Add more cases as needed for different suggestions.

    return chart_paths


def main(filename):
    """Main function to handle the workflow."""
    api_token = get_api_token()

    # Load the dataset
    data = pd.read_csv(filename)

    # Generate initial analysis
    analysis_results = analyze_data(data)

    # Get summary for the LLM
    summary = {
        "columns": list(data.columns),
        "dtypes": data.dtypes.astype(str).to_dict(),
        "analysis_results": analysis_results,
    }
    summary_text = json.dumps(summary)

    # Ask LLM for additional suggestions
    suggestions_prompt = [
        {"role": "system", "content": "You are an expert data analyst and visualization specialist."},
        {"role": "user", "content": f"Here is a summary of the dataset:\n{summary_text}\n" +
                                     "Suggest additional analyses or visualizations."}
    ]
    suggestions = query_llm(suggestions_prompt, api_token)

    # Visualize based on suggestions
    additional_charts = visualize_suggestions(data, suggestions)

    # Generate README.md
    narrative_prompt = [
        {"role": "system", "content": "You are an AI assistant creating a story based on data analysis."},
        {"role": "user", "content": f"Here is the analysis summary, initial insights, and additional charts:\n" +
                                     f"Analysis Summary: {analysis_results}\n" +
                                     f"Charts: {additional_charts}\n" +
                                     "Generate a detailed README.md narrative."}
    ]
    narrative = query_llm(narrative_prompt, api_token)

    with open("README.md", "w") as readme_file:
        readme_file.write(narrative)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py dataset.csv")
        sys.exit(1)

    main(sys.argv[1])
