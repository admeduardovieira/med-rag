import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
csv_file = "output/questions_v2_100/analysis.csv"
df = pd.read_csv(csv_file)

# Compute stats
stats = df.groupby("model").agg(["mean", "std", "count"])
n = int(stats["patient_id"].values[0, 2])

models = stats.index
metrics = ["score_bleu", "score_rouge_l", "score_bert"]
means = stats.loc[:, (metrics, "mean")].T
std_devs = stats.loc[:, (metrics, "std")].T

# Define hatches and color-blind friendly colors
hatches = [
    "//",
    "xx",
    "\\\\",
    "oo",
    "..",
    "++",
    "||",
    "--",
]
colors = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
]  # Color-blind friendly palette

# Create plot
fig, ax = plt.subplots(figsize=(10, 6))
bar_width = 0.3
x = np.arange(len(metrics))

for i, (model, hatch, color) in enumerate(zip(models, hatches, colors)):
    bars = ax.bar(
        x + i * bar_width,
        means[model],
        width=bar_width,
        label=model,
        color=color,
        hatch=hatch,
        edgecolor="black",
        alpha=0.8,
    )
    ax.errorbar(
        x + i * bar_width,
        means[model],
        yerr=std_devs[model],
        fmt="none",
        capsize=10,
        capthick=2,
        color="black",
    )

ax.set_xticks(x + bar_width / 2)
ax.set_xticklabels(["BLEU", "ROUGE-L", "BERT score"])
ax.set_ylabel("Score")
ax.set_title(f"RAG Model Performance (n=352)")
ax.legend(title="Models")

plt.savefig("figures/model_comparison.pdf", format="pdf", bbox_inches="tight")
plt.show()
