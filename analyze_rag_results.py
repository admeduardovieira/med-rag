import pandas as pd
import numpy as np

# Load the analysis data
csv_file = "output/questions_v2_100/analysis.csv"
df = pd.read_csv(csv_file)

print("=" * 60)
print("RAG MODEL PERFORMANCE ANALYSIS")
print("=" * 60)

# Compute statistics grouped by model
stats = df.groupby("model")[["score_bleu", "score_rouge_l", "score_bert"]].agg(
    ["mean", "std", "count"]
)

# Flatten column names
stats.columns = [f"{col[0]}_{col[1]}" for col in stats.columns]

# Get total number of patients and questions
n_patients = df["patient_id"].nunique()
n_questions = df["question_id"].nunique()
total_samples = len(df)

print(
    f"Dataset: {n_patients} patients × {n_questions} questions = {total_samples} total evaluations"
)
print()

# Print results for each model
for model in stats.index:
    print(f"MODEL: {model}")
    print("-" * 40)

    for metric in ["score_bleu", "score_rouge_l", "score_bert"]:
        mean_val = stats.loc[model, f"{metric}_mean"]
        std_val = stats.loc[model, f"{metric}_std"]
        count = stats.loc[model, f"{metric}_count"]

        metric_name = {
            "score_bleu": "BLEU",
            "score_rouge_l": "ROUGE-L",
            "score_bert": "BERT",
        }[metric]

        print(f"  {metric_name}: {mean_val:.4f} ± {std_val:.4f} (n={int(count)})")

    print()

print("=" * 60)
print("SUMMARY TABLE")
print("=" * 60)

# Create formatted summary table
summary_data = []
for model in stats.index:
    row = {"Model": model}
    for metric in ["score_bleu", "score_rouge_l", "score_bert"]:
        mean_val = stats.loc[model, f"{metric}_mean"]
        std_val = stats.loc[model, f"{metric}_std"]
        row[metric] = f"{mean_val:.4f} ± {std_val:.4f}"
    summary_data.append(row)

summary_df = pd.DataFrame(summary_data)
summary_df = summary_df.set_index("Model")
summary_df.columns = ["BLEU", "ROUGE-L", "BERT"]

print(summary_df)
print()
print(f"Total evaluations: {total_samples}")
print(f"Number of models: {len(stats)}")
