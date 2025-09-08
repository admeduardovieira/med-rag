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

    unique_combinations = {}

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
                    error_numbers = tuple(
                        sorted(
                            [
                                int(x)
                                for x in model_match.group(2).split(",")
                                if x != "6"
                            ]
                        )
                    )

                    key = (current_case, current_model)
                    if key not in unique_combinations:
                        unique_combinations[key] = set()

                    unique_combinations[key].add(error_numbers)

    for (case, model), error_sets in unique_combinations.items():
        for error_numbers in error_sets:
            for error in error_numbers:
                error_data.append({"case": case, "model": model, "error_type": error})

    return pd.DataFrame(error_data)


def create_cooccurrence_heatmap(df):
    df = df[df["error_type"] != 6]

    error_matrix = pd.crosstab(df["case"], df["error_type"])

    cooccurrence = error_matrix.T.dot(error_matrix)

    total_occurrences = cooccurrence.sum(axis=1)

    row_sums = cooccurrence.sum(axis=1) - np.diag(cooccurrence)

    sorted_indices = row_sums.sort_values(ascending=False).index
    cooccurrence = cooccurrence.loc[sorted_indices, sorted_indices]

    mask = np.triu(np.ones_like(cooccurrence, dtype=bool))

    cooccurrence_percent = pd.DataFrame(
        np.zeros_like(cooccurrence),
        index=cooccurrence.index,
        columns=cooccurrence.columns,
    )

    for i in cooccurrence.index:
        for j in cooccurrence.columns:
            if i != j:
                total_i = total_occurrences[i]
                total_j = total_occurrences[j]
                min_total = min(total_i, total_j)
                if min_total > 0:
                    cooccurrence_percent.loc[i, j] = (
                        cooccurrence.loc[i, j] / min_total
                    ) * 100

    error_labels = {
        1: "Schema\nmismatch",
        2: "Wrong\naggregation",
        3: "Join\nerrors",
        4: "Condition\nmisinterpretation",
        5: "String\nmismatch",
    }

    plt.figure(figsize=(12, 10))

    sns.heatmap(
        cooccurrence_percent,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        square=True,
        mask=mask,
        cbar_kws={"label": "Co-occurrence %"},
        xticklabels=[error_labels[i] for i in cooccurrence_percent.columns],
        yticklabels=[error_labels[i] for i in cooccurrence_percent.index],
        annot_kws={"size": 10},
        linewidths=0.5,
        linecolor="black",
    )

    plt.title("Error Type Co-occurrence Matrix (%)", fontsize=16, pad=20)
    plt.xlabel("Error Type", fontsize=14)
    plt.ylabel("Error Type", fontsize=14)

    plt.tight_layout()

    plt.savefig("figures/error_cooccurrence_heatmap.pdf", bbox_inches="tight", dpi=300)
    print(
        "Co-occurrence heatmap saved successfully to figures/error_cooccurrence_heatmap.pdf"
    )

    plt.show()


def print_cooccurrence_stats(df):
    contingency_table = pd.crosstab(df["case"], df["error_type"])

    chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

    print("\nCo-occurrence Statistics:")
    print("\nChi-square test for independence:")
    print(f"Chi-square statistic: {chi2:.4f}")
    print(f"p-value: {p_value:.4f}")
    print(f"Degrees of freedom: {dof}")

    correlation = contingency_table.corr()
    print("\nError Type Correlation Matrix:")
    print(correlation)


def main():
    try:
        os.makedirs("figures", exist_ok=True)

        df = parse_log_file("output/cleanup_cat_eval_error_summary.log")
        create_cooccurrence_heatmap(df)

        print_cooccurrence_stats(df)

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
