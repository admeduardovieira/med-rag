import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy import stats
from itertools import combinations
import os

# Define the same visual style as other plots
MODEL_ORDER = [
    "deepseek-v3",
    "deepseek-v3.1",
    "llama3.3-70b",
    "qwen2p5-vl-32b-instruct",
    "mixtral-8x22b-instruct",
    "bio-mistral-7b",
    "gpt-4o",
    "gpt-5",
    "gpt-oss-20b",
]

MODEL_DISPLAY_NAMES = {
    "deepseek-v3": "DeepSeek V3",
    "deepseek-v3.1": "DeepSeek V3.1",
    "llama3.3-70b": "Llama 3.3-70B",
    "qwen2p5-vl-32b-instruct": "Qwen2.5-32B-instruct",
    "mixtral-8x22b-instruct": "Mixtral-8x22B-instruct",
    "bio-mistral-7b": "BioMistral-7B",
    "gpt-4o": "GPT-4o",
    "gpt-5": "GPT-5",
    "gpt-oss-20b": "GPT-OSS-20B",
}


def load_accuracy_data():
    """Load per-query accuracy data from the results Excel file"""
    try:
        df = pd.read_excel("output/results_questions_v2_100.xlsx")
        print(f"Loaded {len(df)} accuracy records")

        # Filter to only include models we want to analyze
        df = df[df["model"].isin(MODEL_ORDER)]
        print(f"Filtered to {len(df)} records for {len(MODEL_ORDER)} models")

        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def perform_pairwise_ttests(df):
    """Perform pairwise t-tests between all model pairs"""
    models = MODEL_ORDER
    print(f"Performing pairwise t-tests for {len(models)} models")

    # Create pivot table: rows = queries, columns = models, values = accuracy (0/1)
    pivot_df = df.pivot_table(
        index="observation_id",
        columns="model",
        values="is_correct",
        aggfunc="first",  # Take first result if multiple runs
    )

    print(f"Pivot table shape: {pivot_df.shape}")

    # Initialize results matrix (9x9)
    results_matrix = pd.DataFrame(0, index=models, columns=models, dtype=int)
    ttest_results = []

    # Perform pairwise t-tests
    for model1, model2 in combinations(models, 2):
        if model1 in pivot_df.columns and model2 in pivot_df.columns:
            # Get accuracy values for both models (only for queries both answered)
            acc1 = pivot_df[model1].dropna()
            acc2 = pivot_df[model2].dropna()

            # Find common queries
            common_queries = acc1.index.intersection(acc2.index)
            if len(common_queries) < 10:  # Need minimum sample size
                print(
                    f"Warning: Only {len(common_queries)} common queries for {model1} vs {model2}"
                )
                continue

            acc1_common = acc1.loc[common_queries].astype(int)
            acc2_common = acc2.loc[common_queries].astype(int)

            # Perform paired t-test (since we're comparing the same queries)
            try:
                t_stat, p_value = stats.ttest_rel(acc1_common, acc2_common)
            except Exception as e:
                print(f"Error in t-test for {model1} vs {model2}: {e}")
                continue

            # Calculate means
            mean1 = acc1_common.mean()
            mean2 = acc2_common.mean()

            # Store t-test results
            ttest_results.append(
                {
                    "model1": model1,
                    "model2": model2,
                    "mean1": mean1,
                    "mean2": mean2,
                    "t_statistic": t_stat,
                    "p_value": p_value,
                    "sample_size": len(common_queries),
                }
            )

            # Fill the results matrix
            if p_value < 0.05:  # Significant difference
                if mean1 > mean2:
                    results_matrix.loc[model1, model2] = 1  # model1 better than model2
                    results_matrix.loc[model2, model1] = -1  # model2 worse than model1
                else:
                    results_matrix.loc[model1, model2] = -1  # model1 worse than model2
                    results_matrix.loc[model2, model1] = 1  # model2 better than model1
            else:
                # No significant difference
                results_matrix.loc[model1, model2] = 0
                results_matrix.loc[model2, model1] = 0

    ttest_df = pd.DataFrame(ttest_results)
    return results_matrix, ttest_df, pivot_df


def create_confusion_matrix_heatmap(results_matrix, filename):
    """Create a heatmap visualization of the confusion matrix"""
    plt.figure(figsize=(14, 12))

    # Create mask for upper triangle (since matrix is symmetric)
    mask = np.triu(np.ones_like(results_matrix, dtype=bool))

    # Create discrete colormap: red for better (+1), blue for worse (-1), white for equal (0)
    import matplotlib.colors as mcolors

    # Define discrete colors for each value
    colors = ["#d73027", "#ffffff", "#4575b4"]  # Red, White, Blue
    cmap = mcolors.ListedColormap(colors)
    bounds = [-1.5, -0.5, 0.5, 1.5]  # Boundaries for discrete values
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    # Create the heatmap
    sns.heatmap(
        results_matrix,
        annot=True,
        fmt="d",
        cmap=cmap,
        norm=norm,
        square=True,
        mask=mask,
        cbar=False,
        xticklabels=[MODEL_DISPLAY_NAMES.get(m, m) for m in results_matrix.columns],
        yticklabels=[MODEL_DISPLAY_NAMES.get(m, m) for m in results_matrix.index],
        linewidths=0.8,
        linecolor="black",
    )

    plt.title(
        "NL2SQL Pairwise Model Comparison Matrix\n(α < 0.05 significance level)",
        fontsize=16,
        pad=20,
    )
    plt.xlabel("Model B", fontsize=16)
    plt.ylabel("Model A", fontsize=16)

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha="right", fontsize=14)
    plt.yticks(fontsize=14)

    plt.tight_layout()
    plt.savefig(f"figures/{filename}.pdf", bbox_inches="tight", dpi=300)
    print(f"Confusion matrix saved to figures/{filename}.pdf")
    plt.close()


def print_summary_statistics(results_matrix, ttest_df):
    """Print summary statistics of the pairwise comparisons"""
    print("\n" + "=" * 80)
    print("NL2SQL PAIRWISE COMPARISON SUMMARY")
    print("=" * 80)

    print(f"\nTotal pairwise comparisons: {len(ttest_df)}")
    print(
        f"Significant differences (p < 0.05): {len(ttest_df[ttest_df['p_value'] < 0.05])}"
    )
    print(f"No significant differences: {len(ttest_df[ttest_df['p_value'] >= 0.05])}")

    # Calculate win/loss statistics for each model
    model_stats = {}
    for model in MODEL_ORDER:
        wins = (results_matrix.loc[model] == 1).sum()
        losses = (results_matrix.loc[model] == -1).sum()
        ties = (results_matrix.loc[model] == 0).sum()
        total_comparisons = wins + losses + ties

        model_stats[model] = {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "win_rate": wins / total_comparisons if total_comparisons > 0 else 0,
        }

    print("\nModel Performance Rankings:")
    print("-" * 50)
    sorted_models = sorted(
        model_stats.items(), key=lambda x: x[1]["win_rate"], reverse=True
    )
    for i, (model, stats) in enumerate(sorted_models, 1):
        display_name = MODEL_DISPLAY_NAMES.get(model, model)
        print("2d")

    print("\nTop Significant Differences (p < 0.001):")
    print("-" * 50)
    significant_results = ttest_df[ttest_df["p_value"] < 0.001].copy()
    significant_results["mean_diff"] = (
        significant_results["mean1"] - significant_results["mean2"]
    ).abs()
    significant_results = significant_results.sort_values("mean_diff", ascending=False)

    for _, row in significant_results.head(10).iterrows():
        better_model = row["model1"] if row["mean1"] > row["mean2"] else row["model2"]
        worse_model = row["model2"] if row["mean1"] > row["mean2"] else row["model1"]
        mean_diff = abs(row["mean1"] - row["mean2"])

        better_name = MODEL_DISPLAY_NAMES.get(better_model, better_model)
        worse_name = MODEL_DISPLAY_NAMES.get(worse_model, worse_model)

        print(".3f")


def main():
    """Main function to run the pairwise comparison analysis"""
    try:
        os.makedirs("figures", exist_ok=True)

        # Load data
        print("Loading NL2SQL accuracy data...")
        df = load_accuracy_data()
        if df is None:
            return

        # Perform pairwise t-tests
        print("\nPerforming pairwise t-tests...")
        results_matrix, ttest_df, pivot_df = perform_pairwise_ttests(df)

        # Create confusion matrix heatmap
        print("\nCreating confusion matrix heatmap...")
        create_confusion_matrix_heatmap(
            results_matrix, "nl2sql_pairwise_comparison_matrix"
        )

        # Print summary statistics
        print_summary_statistics(results_matrix, ttest_df)

        # Save results matrix to CSV
        results_matrix.to_csv("output/nl2sql_pairwise_comparison_results.csv")
        print("\nResults matrix saved to output/nl2sql_pairwise_comparison_results.csv")

        # Save t-test results to CSV
        ttest_df.to_csv("output/nl2sql_pairwise_ttest_results.csv", index=False)
        print("T-test results saved to output/nl2sql_pairwise_ttest_results.csv")

        print("\nNL2SQL pairwise comparison analysis completed!")

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
