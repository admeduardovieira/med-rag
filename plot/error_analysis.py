import pandas as pd
import matplotlib.pyplot as plt
import ast
import os
import numpy as np

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

colors = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
    "#e6ab02",
    "#a6761d",
    "#666666",
    "#1f78b4",
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
    "**",
]

# Error categories from ec.py
ERROR_CATEGORIES = [
    "SCHEMA_MISMATCH",
    "INCORRECT_AGGREGATION",
    "JOIN_ERRORS",
    "JOIN_MISINTERPRETATION",
    "STRING_MISMATCH",
]


def load_error_data(csv_file):
    """Load and process the error classification CSV"""
    df = pd.read_csv(csv_file)

    # Filter out any invalid rows
    df = df[df["model"] != "model"]

    # Parse error_categories (stored as string representations of lists)
    df["error_categories"] = df["error_categories"].apply(ast.literal_eval)

    return df


def count_errors_by_category_and_model(df):
    """Count errors for each category and model"""
    error_counts = {}

    for category in ERROR_CATEGORIES:
        error_counts[category] = {}

        for model in MODEL_ORDER:
            model_df = df[df["model"] == model]
            count = 0

            for categories in model_df["error_categories"]:
                if category in categories:
                    count += 1

            error_counts[category][model] = count

    return error_counts


def create_error_category_plot(error_counts, category, filename):
    """Create a bar plot for a specific error category"""
    plt.figure(figsize=(12, 6))

    models = MODEL_ORDER
    counts = [error_counts[category][model] for model in models]

    bars = []
    for i, (model, count) in enumerate(zip(models, counts)):
        display_name = MODEL_DISPLAY_NAMES.get(model, model)
        bar = plt.bar(
            display_name,
            count,
            color=colors[i % len(colors)],
            edgecolor="black",
            alpha=0.8,
            hatch=hatches[i % len(hatches)],
            zorder=3,
        )
        bars.append(bar[0])

        # Add value labels on top of bars
        plt.text(
            i,
            count + max(counts) * 0.01,  # Position slightly above the bar
            f"{int(count)}",  # Format as integer
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            rotation=0,
        )

    # Format category name for title
    if category == "JOIN_MISINTERPRETATION":
        category_display = "Join Misinterpretation"
    else:
        category_display = category.replace("_", " ").title()

    plt.ylabel("Error Count", fontsize=16)
    plt.title(f"NL2SQL Error Analysis: {category_display}", fontsize=16)
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=14)
    plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)

    # Adjust y-axis to make room for text labels
    if counts:
        plt.ylim(0, max(counts) * 1.15)  # Add 15% padding for labels

    plt.tight_layout()
    plt.savefig(f"figures/{filename}.pdf", bbox_inches="tight")
    print(f"Plot saved to figures/{filename}.pdf")
    plt.close()


def main():
    """Main function to generate all error analysis plots"""
    try:
        os.makedirs("figures", exist_ok=True)

        # Load error data
        csv_file = "sql_error_classification_CORRECTED_report.csv"
        df = load_error_data(csv_file)
        print(f"Loaded {len(df)} error records")

        # Count errors by category and model
        error_counts = count_errors_by_category_and_model(df)

        # Print summary statistics
        print("\nError counts by category and model:")
        for category in ERROR_CATEGORIES:
            print(f"\n{category}:")
            for model in MODEL_ORDER:
                count = error_counts[category][model]
                print(f"  {model}: {count}")

        # Create plots for each error category
        category_filenames = [
            "sql_error_schema_mismatch",
            "sql_error_incorrect_aggregation",
            "sql_error_join_errors",
            "sql_error_join_misinterpretation",
            "sql_error_string_mismatch",
        ]

        for category, filename in zip(ERROR_CATEGORIES, category_filenames):
            create_error_category_plot(error_counts, category, filename)

        # Create combined LLM-wise plot
        create_combined_error_plot(error_counts)

        # Create stacked error composition plot
        create_stacked_error_plot(error_counts)

        print("\nAll error analysis plots have been created!")

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise


def create_combined_error_plot(error_counts):
    """Create a combined plot showing all error categories for each LLM"""
    plt.figure(figsize=(16, 8))

    models = MODEL_ORDER
    categories = ERROR_CATEGORIES
    n_models = len(models)
    n_categories = len(categories)

    # Set up positions for grouped bars
    bar_width = 0.15
    group_width = n_categories * bar_width
    index = np.arange(n_models) * (group_width + 0.2)

    bars = []
    for i, category in enumerate(categories):
        offset = i * bar_width
        counts = [error_counts[category][model] for model in models]

        bar_group = plt.bar(
            index + offset,
            counts,
            bar_width,
            color=colors[i % len(colors)],
            edgecolor="black",
            alpha=0.8,
            hatch=hatches[i % len(hatches)],
            zorder=3,
            label=category.replace("_", " ").title(),
        )
        bars.append(bar_group[0])

        # Add value labels on top of bars
        for j, count in enumerate(counts):
            plt.text(
                index[j] + offset,
                count + max(counts) * 0.01,
                f"{int(count)}",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                rotation=90,
            )

    plt.ylabel("Error Count", fontsize=16)
    plt.title("SQL-EC Error Analysis: All Categories by LLM", fontsize=18)
    plt.xticks(
        index + (n_categories - 1) * bar_width / 2,
        [MODEL_DISPLAY_NAMES.get(model, model) for model in models],
        rotation=45,
        fontsize=12,
    )
    plt.yticks(fontsize=14)
    plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)

    # Adjust y-axis to make room for text labels
    all_counts = [error_counts[cat][model] for cat in categories for model in models]
    if all_counts:
        plt.ylim(0, max(all_counts) * 1.15)

    plt.legend(title="Error Category", fontsize=10, loc="upper right")
    plt.tight_layout()
    plt.savefig("figures/sql_error_combined_llm_wise.pdf", bbox_inches="tight")
    print("Combined LLM-wise plot saved to figures/sql_error_combined_llm_wise.pdf")
    plt.close()


def create_stacked_error_plot(error_counts):
    """Create a stacked bar plot showing error composition for each LLM"""
    plt.figure(figsize=(14, 8))

    models = MODEL_ORDER
    categories = ERROR_CATEGORIES

    # Prepare data for stacking
    data = []
    for model in models:
        model_data = [error_counts[category][model] for category in categories]
        data.append(model_data)

    data = np.array(data).T  # Transpose for stacking

    # Create stacked bars
    bottom = np.zeros(len(models))
    bars = []

    for i, (category, category_data) in enumerate(zip(categories, data)):
        bar = plt.bar(
            range(len(models)),
            category_data,
            bottom=bottom,
            color=colors[i % len(colors)],
            edgecolor="black",
            alpha=0.8,
            hatch=hatches[i % len(hatches)],
            zorder=3,
            label=category.replace("_", " ").title(),
        )
        bars.append(bar[0])
        bottom += category_data

    plt.ylabel("Error Count", fontsize=16)
    plt.title("SQL-EC Error Analysis: Error Composition by LLM", fontsize=18)
    plt.xticks(
        range(len(models)),
        [MODEL_DISPLAY_NAMES.get(model, model) for model in models],
        rotation=45,
        fontsize=12,
    )
    plt.yticks(fontsize=14)
    plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)

    # Add total error count labels on top of bars
    for i, model in enumerate(models):
        total = sum(error_counts[cat][model] for cat in categories)
        plt.text(
            i,
            total + max(bottom) * 0.01,
            f"{int(total)}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    plt.legend(title="Error Category", fontsize=10, loc="upper right")
    plt.tight_layout()
    plt.savefig("figures/sql_error_stacked_by_llm.pdf", bbox_inches="tight")
    print("Stacked plot saved to figures/sql_error_stacked_by_llm.pdf")
    plt.close()


if __name__ == "__main__":
    main()
