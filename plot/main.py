import pandas as pd
import matplotlib.pyplot as plt

# Data for the DataFrame
data = pd.read_excel("output/summary_main.xlsx")

# Create the DataFrame
df = pd.DataFrame(data)
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
colors = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
]  # Color-blind friendly palette

# Plot Accuracy Graph
plt.figure(figsize=(8, 6))
for i, (model, acc) in enumerate(zip(df["model"], df["acc_mean"])):
    if model == "deepseek-r1":
        continue
    plt.bar(
        model,
        acc,
        color=colors[i % len(colors)],
        edgecolor="black",
        alpha=0.8,
        hatch=hatches[i m% len(hatches)],
        zorder=3,
    )

plt.ylabel("Accuracy", fontsize=16)
plt.title("Accuracy for Main Dataset", fontsize=16)
plt.xticks(rotation=15, fontsize=14)
plt.yticks(fontsize=14)
plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig("figures/accuracy_main.pdf")
plt.show()

# Plot Total Cost Graph
plt.figure(figsize=(8, 6))
for i, (model, cost) in enumerate(zip(df["model"], df["price_total"])):
    if model == "deepseek-r1":
        continue
    plt.bar(
        model,
        cost,
        color=colors[i % len(colors)],
        edgecolor="black",
        alpha=0.8,
        hatch=hatches[i % len(hatches)],
        zorder=3,
    )

plt.ylabel("Total Cost ($)", fontsize=16)
plt.title("Total Cost for Main Dataset", fontsize=16)
plt.xticks(rotation=15, fontsize=14)
plt.yticks(fontsize=14)
plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig("figures/cost_main.pdf")
plt.show()
