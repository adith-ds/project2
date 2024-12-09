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
import json
import requests
import matplotlib.pyplot as plt
import seaborn as sns

# Define the API endpoint
API_ENDPOINT = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

def get_api_token():
    """Fetch the API token from the environment variable."""
    api_token = os.getenv("AIPROXY_TOKEN")
    if not api_token:
        raise EnvironmentError("AIPROXY_TOKEN environment variable not set.")
    return api_token

def query_llm(messages, api_token):
    """Query the LLM with a set of messages."""
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7
    }
    response = requests.post(API_ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def analyze_data(data, output_folder):
    """Perform basic analysis on the dataset."""
    analysis_results = {}
    
    # Summary statistics
    summary_stats = data.describe(include="all").to_dict()
    analysis_results["summary_stats"] = summary_stats
    
    # Missing values
    missing_values = data.isnull().sum().to_dict()
    analysis_results["missing_values"] = missing_values
    
    # Correlation matrix and visualization
    numeric_data = data.select_dtypes(include=["number"])
    if not numeric_data.empty:
        try:
            correlation_matrix = numeric_data.corr()
            plt.figure(figsize=(10, 8))
            sns.heatmap(correlation_matrix, annot=True, cmap="coolwarm", fmt=".2f")
            correlation_path = os.path.join(output_folder, "correlation_matrix.png")
            plt.savefig(correlation_path)
            plt.close()
            analysis_results["correlation_matrix"] = "Saved as correlation_matrix.png"
        except Exception as e:
            analysis_results["correlation_matrix_error"] = f"Error generating correlation matrix: {str(e)}"
    else:
        analysis_results["correlation_matrix_error"] = "No numeric columns to calculate correlation."

    return analysis_results

def visualize_suggestions(data, suggestions, output_folder):
    """Generate additional visualizations based on LLM suggestions."""
    charts = []
    # Placeholder: Implement logic to parse and act on suggestions
    return charts

def main(filename):
    """Main function to handle the workflow."""
    api_token = get_api_token()

    # Create folder for outputs
    base_name = os.path.splitext(os.path.basename(filename))[0]
    output_folder = os.path.join(os.getcwd(), base_name)
    os.makedirs(output_folder, exist_ok=True)

    # Load the dataset with encoding handling
    try:
        data = pd.read_csv(filename, encoding="utf-8")
    except UnicodeDecodeError:
        data = pd.read_csv(filename, encoding="ISO-8859-1")

    # Check if the dataset is loaded properly
    if data.empty:
        raise ValueError(f"The dataset '{filename}' is empty or could not be loaded.")

    # Generate initial analysis
    analysis_results = analyze_data(data, output_folder)

    # Get summary for the LLM
    summary = {
        "columns": list(data.columns),
        "dtypes": data.dtypes.astype(str).to_dict(),
        "analysis_results": analysis_results,
    }
    summary_text = json.dumps(summary, indent=2)

    # Ask LLM for additional suggestions
    suggestions_prompt = [
        {"role": "system", "content": "You are an expert data analyst and visualization specialist."},
        {"role": "user", "content": f"Here is a summary of the dataset:\n{summary_text}\n" +
                                     "Suggest additional analyses or visualizations."}
    ]
    suggestions = query_llm(suggestions_prompt, api_token)

    # Visualize based on suggestions
    additional_charts = visualize_suggestions(data, suggestions, output_folder)

    # Generate README.md
    narrative_prompt = [
        {"role": "system", "content": "You are an AI assistant creating a story based on data analysis."},
        {"role": "user", "content": f"Here is the analysis summary, initial insights, and additional charts:\n" +
                                     f"Analysis Summary: {analysis_results}\n" +
                                     f"Charts: {additional_charts}\n" +
                                     "Generate a detailed README.md narrative."}
    ]
    narrative = query_llm(narrative_prompt, api_token)

    readme_path = os.path.join(output_folder, "README.md")
    with open(readme_path, "w") as readme_file:
        readme_file.write(narrative)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py dataset.csv")
        sys.exit(1)
    main(sys.argv[1])
