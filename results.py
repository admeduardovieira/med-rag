import re
import os
import json
import pandas as pd
from types import SimpleNamespace as sn
from llm import models
import argparse

parser = argparse.ArgumentParser(description="Obtain results")

parser.add_argument(
    "--task",
    type=str,
    default="questions_v2_100",
    help="Name of task to process",
)

parser.add_argument(
    "--llms",
    type=str,
    default="gpt-5 deepseek-v3 deepseek-v3.1 llama3.3-70b gpt-4o gpt-5 gpt-oss-20b qwen2p5-vl-32b-instruct mixtral-8x22b-instruct bio-mistral-7b",
    help="Space-separated list of LLM names to include in parsing",
)

parser.add_argument(
    "--filter_false",
    action="store_true",
    help="Filter out false results and save them to a separate log file",
)

args = parser.parse_args()

print(f"Processing task: {args.task}")

if any(
    llm
    not in [
        "gpt-5",
        "deepseek-v3.1",
        "deepseek-v3",
        "llama3.3-70b",
        "gpt-4o",
        "gpt-oss-20b",
        "qwen2p5-vl-32b-instruct",
        "mixtral-8x22b-instruct",
        "bio-mistral-7b",
    ]
    for llm in args.llms.split()
):
    raise ValueError(f"Invalid LLM name: {args.llms}")

print(f"Including LLMs: {args.llms}")


included_llms = args.llms.split()

if args.task != "main":
    # Special-case: for questions_v2_100, read all matching log files from nl2sql_9models_direct
    if args.task == "questions_v2_100":
        task_dir = os.path.join("output", "questions_v2_100", "nl2sql_9models_direct")
        if os.path.exists(task_dir):
            log_files = [
                os.path.join(task_dir, f)
                for f in os.listdir(task_dir)
                if f.endswith(".log")
                and "output_batch_size=5&n=1000&exclude=none&take=" in f
            ]
        else:
            log_files = []
    else:
        log_files = [
            os.path.join("output", args.task, f)
            for f in os.listdir(os.path.join("output", args.task))
        ]
else:
    # Recursively find all .log files in output directory and subdirectories
    log_files = []
    for root, dirs, files in os.walk("output"):
        # Skip "old" directories
        dirs[:] = [d for d in dirs if d != "old"]
        for file in files:
            if file.endswith(".log"):
                log_files.append(os.path.join(root, file))


def parse_content(file_content):
    if "=" * 30 in file_content:
        content = file_content.split("=" * 30)[1]
    else:
        content = file_content

    questions = content.split("*" * 30)
    results = []

    for question in questions:
        if not question.strip():
            continue

        lines = question.strip().split("\n")
        true_result = None
        model_results = []

        case_id = None
        for i, line in enumerate(lines):
            if line.startswith("CASE: "):
                if match := re.search(r"CASE: (.*)", line):
                    case_id = match.group(1)

            if line.startswith("LLM ["):
                model_name = re.search(r"LLM \[(.+?)\]:", line).group(1)
                if model_name not in included_llms:
                    continue
                if i + 3 < len(lines) and lines[i + 1].startswith("MODEL:"):
                    if match := re.search(r"USAGE: (.+)", lines[i + 2]):
                        usage = json.loads(match.group(1))

                    model_result = ""
                    model_len = ""
                    true_result = -1
                    true_len = -1

                    if match := re.search(r"ANSWER: \[(.+?)\] \[(.+?)\]", lines[i + 3]):
                        model_result = match.group(1)
                        true_result = match.group(2)
                        model_results.append((model_name, model_result, true_result))

                    if match := re.search(
                        r"ANSWER: \((.+?)\) \((.+?)\) \((.+?)\) \((.+?)\)", lines[i + 3]
                    ):
                        model_result = match.group(1)
                        true_result = match.group(3)
                        model_len = match.group(2)
                        true_len = match.group(4)

                result = sn(
                    model=model_name,
                    observation_id=case_id,
                    predict=model_result + model_len,
                    true=str(true_result) + str(true_len),
                    tokens_in=usage["in"] if usage["in"] > 0 else -1,
                    tokens_out=usage["out"] if usage["out"] > 0 else -1,
                )

                sorted_predict = "".join(sorted(result.predict))
                sorted_true = "".join(sorted(result.true))
                result.is_correct = sorted_predict == sorted_true
                results.append(result)

    return results


def classify_results(results):
    classification = {}
    for model, evaluations in results.items():
        total = len(evaluations)
        correct = sum(evaluations)
        classification[model] = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total else 0,
        }
    return classification


def bundle_logs_by_case(log_files, filter_false=False, included_llms=None):
    """Bundle logs by unique CASE, QUESTION, TRUE pairs and optionally filter false results."""
    if included_llms is None:
        included_llms = []

    bundled_cases = {}

    for file_name in log_files:
        if not file_name.endswith(".log"):
            continue

        with open(file_name, "r") as f:
            file_content = f.read()

        cases = file_content.split("*" * 30)

        for case in cases:
            if not case.strip():
                continue

            lines = case.strip().split("\n")
            case_id = None
            question = None
            true_query = None
            llm_sections = []

            current_llm_section = []
            current_llm_name = None

            for line in lines:
                if line.startswith("CASE: "):
                    case_id = line.split("CASE: ")[1].strip()
                elif line.startswith("QUESTION: "):
                    question = line.split("QUESTION: ")[1].strip()
                elif line.startswith("TRUE: "):
                    true_query = line.split("TRUE: ")[1].strip()
                elif line.startswith("LLM ["):
                    if current_llm_section:
                        if current_llm_name in included_llms:
                            llm_sections.append("\n".join(current_llm_section))
                    current_llm_section = [line]

                    if match := re.search(r"LLM \[(.+?)\]", line):
                        current_llm_name = match.group(1)
                elif (
                    line.startswith("MODEL:")
                    or line.startswith("USAGE:")
                    or line.startswith("ANSWER:")
                ):
                    current_llm_section.append(line)

            if current_llm_section and current_llm_name in included_llms:
                llm_sections.append("\n".join(current_llm_section))

            if case_id and question and true_query:
                case_key = (case_id, question, true_query)
                if case_key not in bundled_cases:
                    bundled_cases[case_key] = {
                        "case_id": case_id,
                        "question": question,
                        "true_query": true_query,
                        "llm_sections": [],
                    }
                bundled_cases[case_key]["llm_sections"].extend(llm_sections)

    output_dir = "output/false_logs" if filter_false else "output/bundled_logs"
    os.makedirs(output_dir, exist_ok=True)

    false_cases = []
    for case_key, case_data in bundled_cases.items():
        case_id = case_data["case_id"]
        question = case_data["question"]
        true_query = case_data["true_query"]
        llm_sections = case_data["llm_sections"]

        has_incorrect = False
        incorrect_sections = []

        for section in llm_sections:
            lines = section.split("\n")
            current_llm_name = None

            for line in lines:
                if line.startswith("LLM ["):
                    if match := re.search(r"LLM \[(.+?)\]", line):
                        current_llm_name = match.group(1)
                        break

            if current_llm_name not in included_llms:
                continue

            for i, line in enumerate(lines):
                if line.startswith("ANSWER:"):
                    if "[" in line:
                        if match := re.search(r"ANSWER: \[(.+?)\] \[(.+?)\]", line):
                            model_result = match.group(1)
                            true_result = match.group(2)
                            sorted_predict = "".join(sorted(model_result))
                            sorted_true = "".join(sorted(true_result))
                            if sorted_predict != sorted_true:
                                has_incorrect = True
                                incorrect_sections.append(section)
                                break
                    elif "(" in line:
                        if match := re.search(
                            r"ANSWER: \((.+?)\) \((.+?)\) \((.+?)\) \((.+?)\)", line
                        ):
                            model_result = match.group(1)
                            true_result = match.group(3)
                            sorted_predict = "".join(sorted(model_result))
                            sorted_true = "".join(sorted(true_result))
                            if sorted_predict != sorted_true:
                                has_incorrect = True
                                incorrect_sections.append(section)
                                break

        if filter_false and not has_incorrect:
            continue

        case_content = f"CASE: {case_id}\n"
        case_content += f"QUESTION: {question}\n"
        case_content += f"TRUE: {true_query}\n\n"

        for section in incorrect_sections if filter_false else llm_sections:
            case_content += section + "\n\n"

        if filter_false:
            false_cases.append(case_content)
        else:
            output_file = os.path.join(output_dir, f"case_{case_id}.log")
            with open(output_file, "w") as f:
                f.write(case_content)

    if filter_false and false_cases:
        output_file = os.path.join(output_dir, "all_false_cases.log")
        with open(output_file, "w") as f:
            f.write(("*" * 30 + "\n\n").join(false_cases))
        print(f"Saved {len(false_cases)} false cases to {output_file}")
    elif filter_false:
        print("No false cases found!")


if __name__ == "__main__":
    if args.filter_false:
        bundle_logs_by_case(log_files, filter_false=True, included_llms=included_llms)
    else:
        # Original processing logic
        dataframes = []
        for i, file_name in enumerate(log_files):
            if not file_name.endswith(".log"):
                continue
            with open(file_name, "r") as f:
                file_content = f.read()

            results = parse_content(file_content)
            df = pd.DataFrame([vars(ns) for ns in results])
            df["take"] = i
            dataframes.append(df)

        df = pd.concat(dataframes)

        model_prices = {
            model: {
                "in": info.meta.price_in,
                "out": info.meta.price_out,
            }
            for model, info in models.items()
        }

        result_df = (
            df.groupby(["model", "take"])
            .agg(
                num_observations=("observation_id", "count"),
                tokens_in=("tokens_in", "sum"),
                tokens_in_count=("tokens_in", lambda x: x[x > 0].count()),
                tokens_out=("tokens_out", "sum"),
                tokens_out_count=("tokens_out", lambda x: x[x > 0].count()),
                true_observations=("is_correct", "sum"),
                acc=("is_correct", "mean"),
            )
            .reset_index()
            .groupby("model")
            .agg(
                num_observations=("num_observations", "sum"),
                true_observations=("true_observations", "sum"),
                acc_mean=("acc", "mean"),
                acc_stdvar=("acc", "std"),
                tokens_in=("tokens_in", "sum"),
                tokens_in_count=("tokens_in_count", "sum"),
                tokens_out=("tokens_out", "sum"),
                tokens_out_count=("tokens_out_count", "sum"),
            )
            .assign(avg_tokens_in=lambda df: df["tokens_in"] / df["tokens_in_count"])
            .assign(avg_tokens_out=lambda df: df["tokens_out"] / df["tokens_out_count"])
            .assign(
                price_token_in=lambda df: df.index.map(
                    lambda idx: model_prices[idx]["in"]
                )
            )
            .assign(
                price_token_out=lambda df: df.index.map(
                    lambda idx: model_prices[idx]["out"]
                )
            )
            .assign(
                price_in=lambda df: df["avg_tokens_in"] * df["price_token_in"] / 10**6
            )
            .assign(
                price_out=lambda df: df["avg_tokens_out"]
                * df["price_token_out"]
                / 10**6
            )
            .assign(price_total=lambda df: df["price_in"] + df["price_out"])
            .drop(
                columns=[
                    "tokens_in",
                    "tokens_in_count",
                    "tokens_out",
                    "tokens_out_count",
                ]
            )
        )

        result_df["acc_mean"] = result_df["acc_mean"].round(3)

        print(result_df)

        df.to_excel(f"output/results_{args.task}.xlsx")
        result_df.to_excel(f"output/summary_{args.task}.xlsx")
