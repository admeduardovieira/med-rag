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

METRICS = ["score_bleu", "score_rouge_l", "score_bert"]
METRIC_DISPLAY_NAMES = {
    "score_bleu": "BLEU Score",
    "score_rouge_l": "ROUGE-L Score",
    "score_bert": "BERT Score",
}

# New title mapping for cleaner titles
METRIC_TITLE_NAMES = {
    "score_bleu": "BLEU",
    "score_rouge_l": "ROUGE-L",
    "score_bert": "BERT",
}


def load_rag_data():
    """Load RAG evaluation data from the analysis CSV file"""
    try:
        df = pd.read_csv("output/questions_v2_100/analysis.csv")
        print(f"Loaded {len(df)} RAG evaluation records")

        # Filter to only include models we want to analyze
        df = df[df["model"].isin(MODEL_ORDER)]
        print(f"Filtered to {len(df)} records for {len(MODEL_ORDER)} models")

        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def perform_pairwise_ttests(df, metric):
    """Perform pairwise t-tests between all model pairs for a given metric"""
    models = MODEL_ORDER
    print(f"Performing pairwise t-tests for {len(models)} models on {metric}")

    # Create pivot table: rows = queries, columns = models, values = metric score
    pivot_df = df.pivot_table(
        index=["patient_id", "question_id"],
        columns="model",
        values=metric,
        aggfunc="first",  # Take first result if multiple runs
    )

    print(f"Pivot table shape: {pivot_df.shape}")

    # Initialize results matrix (9x9)
    results_matrix = pd.DataFrame(0, index=models, columns=models, dtype=int)
    ttest_results = []

    # Perform pairwise t-tests
    for model1, model2 in combinations(models, 2):
        if model1 in pivot_df.columns and model2 in pivot_df.columns:
            # Get scores for both models (only for queries both answered)
            scores1 = pivot_df[model1].dropna()
            scores2 = pivot_df[model2].dropna()

            # Find common queries
            common_queries = scores1.index.intersection(scores2.index)
            if len(common_queries) < 10:  # Need minimum sample size
                print(
                    f"Warning: Only {len(common_queries)} common queries for {model1} vs {model2}"
                )
                continue

            scores1_common = scores1.loc[common_queries]
            scores2_common = scores2.loc[common_queries]

            # Perform paired t-test (since we're comparing the same queries)
            try:
                t_stat, p_value = stats.ttest_rel(scores1_common, scores2_common)
            except Exception as e:
                print(f"Error in t-test for {model1} vs {model2}: {e}")
                continue

            # Calculate means
            mean1 = scores1_common.mean()
            mean2 = scores2_common.mean()

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


def create_confusion_matrix_heatmap(results_matrix, metric, ax=None):
    """Create a heatmap visualization of the confusion matrix for a given metric"""
    if ax is None:
        plt.figure(figsize=(14, 12))
        ax = plt.gca()

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
        ax=ax,
    )

    ax.set_title(
        f"RAG-QA Pairwise Model Comparison Matrix - {METRIC_TITLE_NAMES[metric]}\n(α < 0.05 significance level)",
        fontsize=16,
        pad=15,
    )
    ax.set_xlabel("Model B", fontsize=16)
    ax.set_ylabel("Model A", fontsize=16)

    # Rotate x-axis labels
    ax.tick_params(axis="x", rotation=45, labelsize=14)
    ax.tick_params(axis="y", labelsize=14)


def create_combined_rag_heatmap(results_matrices, filename):
    """Create a combined heatmap with all three metrics side by side"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    # Create each subplot
    for i, metric in enumerate(METRICS):
        create_confusion_matrix_heatmap(results_matrices[metric], metric, axes[i])

    plt.tight_layout()
    plt.savefig(f"figures/{filename}.pdf", bbox_inches="tight", dpi=300)
    print(f"Combined RAG heatmap saved to figures/{filename}.pdf")
    plt.close()


def print_summary_statistics(results_matrix, ttest_df, metric):
    """Print summary statistics of the pairwise comparisons for a given metric"""
    print("\n" + "=" * 80)
    print(f"RAG-QA PAIRWISE COMPARISON SUMMARY - {METRIC_DISPLAY_NAMES[metric]}")
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

        print(".4f")


def main():
    """Main function to run the pairwise comparison analysis for all RAG metrics"""
    try:
        os.makedirs("figures", exist_ok=True)

        # Load data
        print("Loading RAG evaluation data...")
        df = load_rag_data()
        if df is None:
            return

        # Store results matrices for combined plot
        results_matrices = {}

        # Process each metric
        for metric in METRICS:
            print(f"\n{'='*60}")
            print(f"Processing {METRIC_DISPLAY_NAMES[metric]}")
            print(f"{'='*60}")

            # Perform pairwise t-tests
            print(f"\nPerforming pairwise t-tests...")
            results_matrix, ttest_df, pivot_df = perform_pairwise_ttests(df, metric)
            results_matrices[metric] = results_matrix

            # Print summary statistics
            print_summary_statistics(results_matrix, ttest_df, metric)

            # Save results matrix to CSV
            results_matrix.to_csv(
                f"output/rag_pairwise_comparison_{metric}_results.csv"
            )
            print(
                f"\nResults matrix saved to output/rag_pairwise_comparison_{metric}_results.csv"
            )

            # Save t-test results to CSV
            ttest_df.to_csv(
                f"output/rag_pairwise_ttest_{metric}_results.csv", index=False
            )
            print(
                f"T-test results saved to output/rag_pairwise_ttest_{metric}_results.csv"
            )

        # Create separate heatmaps for each metric
        print("\nCreating separate RAG heatmaps...")
        for metric in METRICS:
            print(f"Creating heatmap for {METRIC_DISPLAY_NAMES[metric]}...")
            create_confusion_matrix_heatmap(results_matrices[metric], metric)
            plt.tight_layout()
            plt.savefig(
                f"figures/rag_pairwise_comparison_{metric}.pdf",
                bbox_inches="tight",
                dpi=300,
            )
            print(
                f"Individual heatmap saved to figures/rag_pairwise_comparison_{metric}.pdf"
            )
            plt.close()

        print("\nRAG-QA pairwise comparison analysis completed for all metrics!")

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
