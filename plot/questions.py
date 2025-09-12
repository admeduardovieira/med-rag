import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
csv_file = "output/questions_v2_100/analysis.csv"
df = pd.read_csv(csv_file)

# Exclude the outlier "model" entry
df = df[df["model"] != "model"]

# Compute stats
stats = df.groupby("model").agg(["mean", "std", "count"])
n_patients = df["patient_id"].nunique()
n_questions = df["question_id"].nunique()
total_samples = len(df)

# Define the desired model order
MODEL_ORDER = [
    "deepseek-v3",
    "deepseek-v3.1",
    "llama3.3-70b",
    "qwen2p5-vl-32b-instruct",
    "mixtral-8x22b-instruct",
    "gpt-4o",
    "gpt-5",
    "gpt-oss-20b",
    "bio-mistral-7b",
]

# Display names for better readability
MODEL_DISPLAY_NAMES = {
    "deepseek-v3": "DeepSeek V3",
    "deepseek-v3.1": "DeepSeek V3.1",
    "llama3.3-70b": "Llama 3.3-70B",
    "qwen2p5-vl-32b-instruct": "Qwen2.5-32B-instruct",
    "mixtral-8x22b-instruct": "Mixtral-8x22B-instruct",
    "gpt-4o": "GPT-4o",
    "gpt-5": "GPT-5",
    "gpt-oss-20b": "GPT-OSS-20B",
    "bio-mistral-7b": "BioMistral-7B",
}

# Filter and sort models according to desired order
available_models = [model for model in MODEL_ORDER if model in stats.index]
stats = stats.loc[available_models]

models = stats.index
# Reverse the order so DeepSeek V3 appears on top
models = models[::-1]
stats = stats.loc[models]
metrics = ["score_bleu", "score_rouge_l", "score_bert"]
means = stats.loc[:, (metrics, "mean")].T
std_devs = stats.loc[:, (metrics, "std")].T

# Define hatches and color-blind friendly colors (extended for 9 models)
hatches = [
    "//",
    "xx",
    "\\\\",
    "oo",
    "..",
    "++",
    "||",
    "--",
    "**",
]
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
]  # Color-blind friendly palette extended

# Use the same design as main.py for NL2SQL accuracy plots
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
]  # Color-blind friendly palette extended for 9 models

# Create 3 separate PDF files for each metric
metric_names = ["BLEU Score", "ROUGE-L Score", "BERT Score"]
metric_keys = ["score_bleu", "score_rouge_l", "score_bert"]
filenames = ["rag_bleu_scores.pdf", "rag_rouge_l_scores.pdf", "rag_bert_scores.pdf"]

for idx, (metric_name, metric_key, filename) in enumerate(
    zip(metric_names, metric_keys, filenames)
):
    # Create individual figure for each metric
    fig, ax = plt.subplots(figsize=(14, 8))

    metric_means = [float(means.loc[metric_key, model].iloc[0]) for model in models]
    metric_stds = [float(std_devs.loc[metric_key, model].iloc[0]) for model in models]

    # Create horizontal bars (bars go left-to-right, models stacked vertically)
    y_positions = range(len(models))
    bars = ax.barh(
        y_positions,
        metric_means,
        color=[colors[j % len(colors)] for j in range(len(models))],
        edgecolor="black",
        alpha=0.8,
        zorder=3,
        height=0.7,
    )

    # Add hatches to bars
    for j, bar in enumerate(bars):
        bar.set_hatch(hatches[j % len(hatches)])

    # Add error bars (horizontal bars need xerr instead of yerr)
    ax.errorbar(
        metric_means,
        y_positions,
        xerr=metric_stds,
        fmt="none",
        capsize=5,
        capthick=1.5,
        color="black",
        zorder=4,
    )

    # Add value labels on the right of bars (mean ± std format)
    for j, (mean_val, std_val) in enumerate(zip(metric_means, metric_stds)):
        label_text = f"{mean_val:.3f} ± {std_val:.3f}"
        ax.text(
            mean_val + std_val + 0.02,
            j,
            label_text,
            va="center",
            fontsize=10,
            fontweight="bold",
        )

    # Set labels and title
    ax.set_ylabel("Large language models", fontsize=14)
    ax.set_xlabel("Score", fontsize=14)

    # Create title based on metric
    if "BLEU" in metric_name:
        title_metric = "BLEU Score"
    elif "ROUGE-L" in metric_name:
        title_metric = "ROUGE-L Score"
    elif "BERT" in metric_name:
        title_metric = "BERTScore"
    else:
        title_metric = metric_name

    ax.set_title(
        f"RAG-QA: {title_metric} (3-Run Average)\n(100 patient records × 20 questions)",
        fontsize=16,
        pad=20,
    )

    # Set y-ticks
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(
        [MODEL_DISPLAY_NAMES.get(model, model) for model in models],
        fontsize=11,
    )

    # Add vertical grid lines (horizontal bars need vertical grid)
    ax.grid(axis="x", linestyle=":", alpha=0.5, zorder=0)

    # Set x-axis limits
    ax.set_xlim(0, 1.15)

    plt.tight_layout()
    plt.savefig(
        f"figures/{filename}",
        format="pdf",
        bbox_inches="tight",
        dpi=300,
    )
    print(f"Plot saved to figures/{filename}")
    plt.close()  # Close the figure to save memory

print("All individual metric plots have been created!")
