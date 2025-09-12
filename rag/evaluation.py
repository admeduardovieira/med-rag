from transformers import logging

logging.set_verbosity_error()

import polars as pl
import os
from tqdm import tqdm

from nltk.translate.bleu_score import sentence_bleu
from rouge_score import rouge_scorer
import bert_score


verbose = False
experiment_variation = "questions_v2_100"

input_schema = {
    "patient_id": pl.Int32,
    "question_id": pl.Int32,
    "question": pl.Utf8,
    "label": pl.Utf8,
    "predict": pl.Utf8,
    "model": pl.Utf8,
    "tokens_in": pl.Int32,
    "tokens_out": pl.Int32,
}

output_schema = {
    "patient_id": pl.Int32,
    "question_id": pl.Int32,
    "model": pl.Utf8,
    "score_bleu": pl.Float32,
    "score_rouge_l": pl.Float32,
    "score_bert": pl.Float32,
}

output_path = os.path.join("output", experiment_variation)
input_csv_file = os.path.join(output_path, "output.csv")
csv_file = os.path.join(output_path, "analysis.csv")

try:
    input_df = pl.read_csv(
        input_csv_file,
        schema=input_schema,
        infer_schema_length=100000,
        ignore_errors=True,
    )
    df = pl.read_csv(csv_file, schema=output_schema)
except FileNotFoundError:
    df = pl.DataFrame([], schema=output_schema)
except Exception as e:
    print(f"Error reading CSV: {e}")
    print("Trying to read without strict schema...")
    try:
        input_df = pl.read_csv(
            input_csv_file, infer_schema_length=100000, ignore_errors=True
        )
        print("CSV columns:", input_df.columns)
        print("Data types:")
        print(input_df.dtypes)
        print("First few rows:")
        print(input_df.head())

        # Convert string columns to appropriate types
        input_df = input_df.with_columns(
            [
                pl.col("patient_id").cast(pl.Int32),
                pl.col("question_id").cast(pl.Int32),
                pl.col("tokens_in").cast(pl.Int32),
                pl.col("tokens_out").cast(pl.Int32),
            ]
        )
        print("After conversion:")
        print(input_df.head())
    except Exception as e2:
        print(f"Still failed: {e2}")
        raise

existing_pairs = set(
    zip(df["patient_id"].to_list(), df["question_id"].to_list(), df["model"].to_list())
)

patient_ids = []
output_data = []

try:
    for row in tqdm(input_df.iter_rows(named=True)):

        patient_id = row["patient_id"]
        question_id = row["question_id"]
        model = row["model"]

        if (patient_id, question_id, model) in existing_pairs:
            continue

        reference = row["label"]
        candidate = row["predict"]

        # BLEU Score
        reference_tokens = [reference.split()]
        candidate_tokens = candidate.split()
        bleu_score = sentence_bleu(reference_tokens, candidate_tokens)
        if verbose:
            tqdm.write(f"BLEU Score: {bleu_score:.4f}")

        # ROUGE-L Score
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        rouge_scores = scorer.score(reference, candidate)
        rouge_l_score = rouge_scores["rougeL"].fmeasure
        if verbose:
            tqdm.write(f"ROUGE-L Score: {rouge_l_score:.4f}")

        # BERTScore
        _, _, F1 = bert_score.score([candidate], [reference], lang="en")
        if verbose:
            tqdm.write(f"BERTScore (F1): {F1.item():.4f}")

        new_data = [
            {
                "patient_id": patient_id,
                "question_id": question_id,
                "model": model,
                "tokens_in": row["tokens_in"],
                "tokens_out": row["tokens_out"],
                "score_bleu": bleu_score,
                "score_rouge_l": rouge_l_score,
                "score_bert": F1,
            }
        ]

        new_df = pl.DataFrame(new_data, schema=output_schema)

        df = pl.concat([df, new_df])
        df.write_csv(csv_file, quote_style="non_numeric")
except KeyboardInterrupt:
    print("Terminating...")
