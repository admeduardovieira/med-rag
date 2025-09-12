import pandas as pd
import matplotlib.pyplot as plt
import ast
import os
import numpy as np

# Define the same visual style as other plots
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
]

# Error categories from ec.py
ERROR_CATEGORIES = [
    "SCHEMA_MISMATCH",
    "INCORRECT_AGGREGATION",
    "JOIN_ERRORS",
    "JOIN_MISINTERPRETATION",
    "STRING_MISMATCH",
]

# Display names for better readability
ERROR_DISPLAY_NAMES = {
    "SCHEMA_MISMATCH": "Schema Mismatch",
    "INCORRECT_AGGREGATION": "Incorrect Aggregation",
    "JOIN_ERRORS": "Join Errors",
    "JOIN_MISINTERPRETATION": "Join Misinterpretation",
    "STRING_MISMATCH": "String Mismatch",
}


def load_error_data(csv_file):
    """Load and process the error classification CSV"""
    df = pd.read_csv(csv_file)
    df = df[df["model"] != "model"]
    df["error_categories"] = df["error_categories"].apply(ast.literal_eval)
    return df


def calculate_average_error_rates(df):
    """Calculate average error rates across all models for each category"""
    models = sorted(df["model"].unique())

    # Count total errors per model and error counts by category
    total_errors_per_model = {}
    category_counts = {cat: {} for cat in ERROR_CATEGORIES}

    for model in models:
        model_df = df[df["model"] == model]
        total_errors = len(model_df)
        total_errors_per_model[model] = total_errors

        for category in ERROR_CATEGORIES:
            count = sum(1 for cats in model_df["error_categories"] if category in cats)
            category_counts[category][model] = count

    # Calculate averages across models for each category
    average_rates = {}
    for category in ERROR_CATEGORIES:
        percentages = []
        for model in models:
            if total_errors_per_model[model] > 0:
                percentage = (
                    category_counts[category][model]
                    / total_errors_per_model[model]
                    * 100
                )
                percentages.append(percentage)

        avg_percentage = sum(percentages) / len(percentages) if percentages else 0
        average_rates[category] = avg_percentage

    return average_rates


def create_average_error_plot(average_rates, filename):
    """Create a bar plot showing average error rates across all categories"""
    plt.figure(figsize=(12, 6))

    categories = ERROR_CATEGORIES
    rates = [average_rates[cat] for cat in categories]

    bars = []
    for i, (category, rate) in enumerate(zip(categories, rates)):
        display_name = ERROR_DISPLAY_NAMES.get(
            category, category.replace("_", " ").title()
        )
        bar = plt.bar(
            display_name,
            rate,
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
            rate + 1,  # Position slightly above the bar (fixed offset)
            f"{rate:.1f}%",  # Format as percentage
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            rotation=0,
        )

    plt.ylabel("Average Error Rate (%)", fontsize=16)
    plt.title("SQL Error Types: Average Rates Across All Models", fontsize=16)
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=14)
    plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)

    # Set y-axis to go up to 100
    plt.ylim(0, 100)

    plt.tight_layout()
    plt.savefig(f"figures/{filename}.pdf", bbox_inches="tight")
    print(f"Plot saved to figures/{filename}.pdf")
    plt.close()


def main():
    """Main function to generate the average error types plot"""
    try:
        os.makedirs("figures", exist_ok=True)

        # Load error data
        csv_file = "sql_error_classification_CORRECTED_report.csv"
        df = load_error_data(csv_file)
        print(f"Loaded {len(df)} error records")

        # Calculate average rates
        average_rates = calculate_average_error_rates(df)

        print("\nAverage error rates across all models:")
        for category, rate in average_rates.items():
            display_name = ERROR_DISPLAY_NAMES.get(
                category, category.replace("_", " ").title()
            )
            print(f"{display_name}: {rate:.1f}%")

        # Create the plot
        create_average_error_plot(average_rates, "sql_error_types_average")

        print("\nAverage error types plot has been created!")

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
