import pandas as pd
import matplotlib.pyplot as plt

data = {
    "model": [
        "claude-3.5",
        "gemini-1.5-pro",
        "gpt-4o",
        "gpt-4o-mini",
        "llama3.3-70b",
        "mixtral-8x22b",
        "qwen-2.5-72b",
    ],
    "num_observations": [3000, 3000, 3000, 3000, 3000, 3000, 3000],
    "true_observations": [1302, 1823, 1922, 1609, 1603, 1424, 1728],
    "acc_mean": [
        0.434,
        0.607666666666667,
        0.640666666666667,
        0.536333333333333,
        0.534333333333333,
        0.474666666666667,
        0.576,
    ],
    "avg_tokens_in": [
        1986.052,
        1716.036,
        1710.875,
        1710.875,
        1747.02035368702,
        2365.23,
        1981.154,
    ],
    "avg_tokens_out": [
        70.0846666666667,
        53.653,
        55.88,
        55.1546666666667,
        60.4607941274608,
        91.056,
        61.7466666666667,
    ],
    "price_token_in": [3, 1.25, 2.5, 0.15, 0.9, 0.9, 0.9],
    "price_token_out": [15, 5, 10, 0.6, 0.9, 0.9, 0.9],
    "price_in": [
        0.005958156,
        0.002145045,
        0.0042771875,
        0.00025663125,
        0.00157231831831832,
        0.002128707,
        0.0017830386,
    ],
    "price_out": [
        0.00105127,
        0.000268265,
        0.0005588,
        0.0000330928,
        0.0000544147147147147,
        0.0000819504,
        0.000055572,
    ],
    "price_total": [
        0.007009426,
        0.00241331,
        0.0048359875,
        0.00028972405,
        0.00162673303303303,
        0.0022106574,
        0.0018386106,
    ],
}

df = pd.DataFrame(data)

plt.figure(figsize=(10, 6))
plt.bar(
    df["model"],
    df["acc_mean"],
    color="blue",
    edgecolor="black",
    alpha=0.8,
    hatch="//",
    zorder=3,
)

plt.ylabel("Accuracy", fontsize=16)
plt.title("Accuracy for Main Dataset", fontsize=16)
plt.xticks(rotation=15, fontsize=14)
plt.yticks(fontsize=14)
plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig("accuracy_main.pdf")
plt.show()

plt.figure(figsize=(10, 6))
plt.bar(
    df["model"],
    df["price_total"],
    color="lightcoral",
    edgecolor="black",
    alpha=0.8,
    hatch="\\\\",
    zorder=3,
)
plt.ylabel("Total Cost ($)", fontsize=16)
plt.title("Total Cost for Main Dataset", fontsize=16)
plt.xticks(rotation=15, fontsize=14)
plt.yticks(fontsize=14)
plt.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig("cost_main.pdf")
plt.show()
