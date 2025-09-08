import pandas as pd
import matplotlib.pyplot as plt

for scenario in ["both", "1shot", "sample"]:
    if scenario == "both":
        title = "1-shot example and data samples"
        ablation_file_path = "output/summary_ablation_1shot_data.xlsx"
        main_file_path = "output/summary_main.xlsx"
    elif scenario == "1shot":
        title = "1-shot example"
        ablation_file_path = "output/summary_ablation_1shot_data.xlsx"
        main_file_path = "output/summary_ablation_data.xlsx"
    elif scenario == "sample":
        title = "data samples"
        ablation_file_path = "output/summary_ablation_1shot_data.xlsx"
        main_file_path = "output/summary_ablation_1shot.xlsx"

    # Load the Excel files
    ablation_df = pd.read_excel(ablation_file_path)
    main_df = pd.read_excel(main_file_path)

    # Merge the two DataFrames on the 'model' column to compare
    merged_df = pd.merge(
        main_df, ablation_df, on="model", suffixes=("_main", "_ablation")
    )

    # Calculate percentage increases
    merged_df["cost_increase (%)"] = (
        (merged_df["price_total_main"] - merged_df["price_total_ablation"])
        / merged_df["price_total_ablation"]
        * 100
    )
    merged_df["performance_increase (%)"] = (
        (merged_df["acc_mean_main"] - merged_df["acc_mean_ablation"])
        / merged_df["acc_mean_ablation"]
        * 100
    )

    # Plot Cost and Performance Increase
    plt.figure(figsize=(10, 6))

    bar_width = 0.35
    index = range(len(merged_df))

    # Bar plots with scientific styling
    plt.bar(
        index,
        merged_df["cost_increase (%)"],
        bar_width,
        color="lightcoral",
        edgecolor="black",
        alpha=0.8,
        hatch="\\\\",
        label="Cost Increase (%)",
        zorder=3,
    )
    plt.bar(
        [i + bar_width for i in index],
        merged_df["performance_increase (%)"],
        bar_width,
        color="blue",
        edgecolor="black",
        alpha=0.8,
        hatch="//",
        label="Performance Increase (%)",
        zorder=3,
    )

    print(scenario)
    print(merged_df[["model", "cost_increase (%)", "performance_increase (%)"]])

    # Labels and title
    plt.ylabel("Percentage Increase (%)", fontsize=16)
    plt.title("Cost and Performance Increase with " + title, fontsize=16)
    plt.xticks(
        [i + bar_width / 2 for i in index], merged_df["model"], rotation=15, fontsize=14
    )
    plt.yticks(fontsize=14)
    plt.legend(fontsize=14)

    # Grid and layout
    plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
    plt.tight_layout()

    # Save the plot as a PDF for use in scientific papers
    plt.savefig(f"figures/cost_performance_increase_{scenario}.pdf")
    # plt.show()
