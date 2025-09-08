import polars as pl
import asyncio
import os
import re
import llm
from tqdm import tqdm
from rag.search import load_correct_answers, search

experiment_variation = "questions_v2_100"
input_folder = "dataset/synthetic_patients_v2_100"
index_folder = "qdrant_db"

models = [
    "llama3.3-70b",
    "deepseek-v3",
    "gpt-4o",
]

top_k = 3
questions = [
    "What is the patient's chief complaint?",
    "Who referred the patient for admission?",
    "What medications is the patient currently taking?",
    "What is the patient's gynecological history?",
    "Has the patient experienced any recent surgical procedures?",
    "What is the patient's preferred method of billing?",
    "What diagnostic studies have been performed?",
    "What is the attending physician's name?",
    "What is the patient's age?",
    "What is included in the patient's treatment plan?",
]

schema = {
    "patient_id": pl.Int8,
    "question_id": pl.Int8,
    "question": pl.Utf8,
    "label": pl.Utf8,
    "predict": pl.Utf8,
    "model": pl.Utf8,
    "tokens_in": pl.Int32,
    "tokens_out": pl.Int32,
}

with open("prompts/rag.md", "r") as f:
    system_prompt_template = f.read()

output_path = os.path.join("output", experiment_variation)

os.makedirs(output_path, exist_ok=True)
csv_file = os.path.join(output_path, "output.csv")

# Load existing data
try:
    df = pl.read_csv(csv_file, schema=schema)
except FileNotFoundError:
    df = pl.DataFrame([], schema=schema)

existing_pairs = set(
    zip(df["patient_id"].to_list(), df["question_id"].to_list(), df["model"].to_list())
)

patient_ids = []
new_data = []

for file_path in os.listdir(input_folder):
    m = re.fullmatch(r"patient_(\d+)_answers\.md", file_path)
    if m:
        patient_id = int(m.group(1))
        patient_ids.append(patient_id)

try:
    for model in models:
        for patient_id in tqdm(sorted(patient_ids)):
            answers = load_correct_answers(patient_id)

            for question_id, question in enumerate(questions):

                if (patient_id, question_id, model) in existing_pairs:
                    continue

                label = answers[question_id]
                results = search(patient_id, question, limit=top_k)

                rag_documentation = "\n---\n".join(
                    r.payload["section"] for r in results[:top_k]
                )
                system_prompt = system_prompt_template.format(
                    rag_documentation=rag_documentation
                )

                tqdm.write(
                    f"[{model}] Patient id: {patient_id}, question {question_id}"
                )

                result = asyncio.run(
                    llm.ai_query(
                        message=question,
                        system=system_prompt,
                        model=model,
                        max_tokens=500,
                        prefix=None,
                        sql=False,
                    )
                )

                new_data = [
                    {
                        "patient_id": patient_id,
                        "question_id": question_id,
                        "question": question,
                        "label": label,
                        "predict": result.text,
                        "model": result.meta.model,
                        "tokens_in": result.meta.usage.prompt_tokens,
                        "tokens_out": result.meta.usage.completion_tokens,
                    }
                ]

                new_df = pl.DataFrame(new_data, schema=schema)

                df = pl.concat([df, new_df])
                df.write_csv(csv_file, quote_style="non_numeric")

except KeyboardInterrupt:
    print("Terminating...")
