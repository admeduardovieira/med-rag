import pandas as pd
import matplotlib.pyplot as plt
import re
import numpy as np
import os
import seaborn as sns
from scipy import stats


def parse_log_file(file_path):
    error_data = []
    current_case = None
    current_model = None

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("*"):
                continue

            if line.startswith("CASE:"):
                current_case = line.split()[1]
                continue

            if line.startswith("LLM"):

                model_match = re.match(r"LLM \[(.*?)\]: \[(.*?)\]", line)
                if model_match:
                    current_model = model_match.group(1)
                    error_numbers = [int(x) for x in model_match.group(2).split(",")]
                    for error in error_numbers:
                        if error != 6:
                            error_data.append(
                                {
                                    "case": current_case,
                                    "model": current_model,
                                    "error_type": error,
                                }
                            )

    return pd.DataFrame(error_data)


def create_error_distribution_plot(df):
    # Define colors and hatches (matching plot_main.py style)
    colors = [
        "#1b9e77",
        "#d95f02",
        "#7570b3",
        "#e7298a",
        "#66a61e",
    ]
    hatches = [
        "//",
        "xx",
        "\\",
        "oo",
        "..",
        "++",
        "||",
        "--",
    ]

    plt.figure(figsize=(12, 6))

    error_counts = df.groupby(["model", "error_type"]).size().unstack(fill_value=0)
    error_percentages = error_counts.div(error_counts.sum(axis=1), axis=0) * 100

    error_labels = {
        1: "Schema mismatch",
        2: "Wrong aggregation use",
        3: "Join errors",
        4: "Condition misinterpretation",
        5: "String mismatch",
    }

    n_models = len(error_percentages.index)
    n_errors = len(error_percentages.columns)
    bar_width = 0.15
    index = np.arange(n_models)

    # Plot bars
    for i, (col, label) in enumerate(error_labels.items()):
        offset = i * (bar_width + 0.02)
        plt.bar(
            index + offset,
            error_percentages[col],
            bar_width,
            color=colors[i % len(colors)],
            edgecolor="black",
            alpha=0.8,
            hatch=hatches[i % len(hatches)],
            zorder=3,
            label=f"{col} - {label}",
        )

    plt.title("Error Types Distribution by Model", fontsize=16)
    plt.ylabel("Percentage of Errors", fontsize=14)

    # Set x-axis ticks
    plt.xticks(
        index + (n_errors - 1) / 2 * (bar_width + 0.02),
        error_percentages.index,
        rotation=15,
        fontsize=12,
    )

    plt.yticks(fontsize=12)
    plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    plt.legend(title="Error Type", fontsize=10, loc="upper right")

    plt.ylim(0, 100)

    plt.tight_layout()

    plt.savefig("figures/error_distribution.pdf", bbox_inches="tight")
    print(
        "Error distribution plot saved successfully to figures/error_distribution.pdf"
    )

    plt.show()


def create_cooccurrence_matrix(df):
    # Create a pivot table of cases vs error types
    error_matrix = pd.crosstab(df["case"], df["error_type"])

    cooccurrence = error_matrix.T.dot(error_matrix)

    total_cases = len(df["case"].unique())
    cooccurrence_percent = (cooccurrence / total_cases) * 100

    error_labels = {
        1: "Schema\nmismatch",
        2: "Wrong\naggregation",
        3: "Join\nerrors",
        4: "Condition\nmisinterpretation",
        5: "String\nmismatch",
    }

    plt.figure(figsize=(10, 8))

    sns.heatmap(
        cooccurrence_percent,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        square=True,
        cbar_kws={"label": "Co-occurrence %"},
        xticklabels=[error_labels[i] for i in cooccurrence_percent.columns],
        yticklabels=[error_labels[i] for i in cooccurrence_percent.index],
    )

    plt.title("Error Type Co-occurrence Matrix", fontsize=16, pad=20)
    plt.xlabel("Error Type", fontsize=12)
    plt.ylabel("Error Type", fontsize=12)

    plt.tight_layout()

    plt.savefig("figures/error_cooccurrence.pdf", bbox_inches="tight")
    print("Co-occurrence matrix saved successfully to figures/error_cooccurrence.pdf")

    plt.show()


def create_error_trend_plot(df):
    error_counts = df.groupby(["model", "error_type"]).size().unstack(fill_value=0)

    total_errors = error_counts.sum(axis=1)

    plt.figure(figsize=(12, 6))

    error_counts.plot(kind="area", stacked=True, alpha=0.7)

    plt.title("Error Distribution Trends Across Models", fontsize=16)
    plt.xlabel("Models", fontsize=14)
    plt.ylabel("Number of Errors", fontsize=14)
    plt.xticks(rotation=15)
    plt.grid(True, alpha=0.3)

    plt.legend(title="Error Type", bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.tight_layout()

    plt.savefig("figures/error_trends.pdf", bbox_inches="tight")
    print("Error trends plot saved successfully to figures/error_trends.pdf")

    plt.show()


def print_statistical_summary(df):
    print("\nStatistical Summary:")
    print("\nError counts by model:")
    print(df.groupby("model")["error_type"].value_counts().unstack(fill_value=0))

    print("\nTotal errors by type:")
    print(df["error_type"].value_counts().sort_index())

    contingency_table = pd.crosstab(df["model"], df["error_type"])
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

    print("\nChi-square test for independence:")
    print(f"Chi-square statistic: {chi2:.4f}")
    print(f"p-value: {p_value:.4f}")
    print(f"Degrees of freedom: {dof}")


def main():
    try:
        os.makedirs("figures", exist_ok=True)

        df = parse_log_file("output/cleanup_cat_eval_error_summary.log")

        create_error_distribution_plot(df)
        create_cooccurrence_matrix(df)
        create_error_trend_plot(df)

        print_statistical_summary(df)

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
