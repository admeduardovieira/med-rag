#!/usr/bin/env python3
"""
Transfer script to replace specific model logs from one file to another.

This script replaces logs for deepseek-v3.1, gpt-5, and gpt-oss-20b models
from the source file to the target file, while preserving all other model
entries in the target file.
"""

import re
import sys
from typing import Dict, List, Optional


def parse_log_file(file_path: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Parse a log file and extract cases with their model entries.

    Returns:
        Dict[case_id, Dict[model_name, List[lines]]]
        Where lines include the LLM response, MODEL, USAGE, and ANSWER lines
    """
    cases = {}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by case separators
    case_blocks = content.split("******************************")

    for block in case_blocks:
        block = block.strip()
        if not block or "CASE:" not in block:
            continue

        lines = block.split("\n")
        case_id = None
        current_model = None
        current_llm_lines = []
        models = {}

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Extract case ID
            if line.startswith("CASE:"):
                case_id = line.split("CASE:")[1].strip()

            # Check for LLM entry
            elif line.startswith("LLM [") and "]:" in line:
                # Save previous model if exists
                if current_model and current_llm_lines:
                    models[current_model] = current_llm_lines[:]

                # Extract model name from LLM [model_name]:
                model_match = re.match(r"LLM \[([^\]]+)\]:", line)
                if model_match:
                    current_model = model_match.group(1)
                    current_llm_lines = [line]
                else:
                    current_model = None
                    current_llm_lines = []

            elif current_model and (
                line.startswith("MODEL:")
                or line.startswith("USAGE:")
                or line.startswith("ANSWER:")
            ):
                current_llm_lines.append(line)

                # If this is ANSWER line, we've completed this model entry
                if line.startswith("ANSWER:"):
                    models[current_model] = current_llm_lines[:]
                    current_model = None
                    current_llm_lines = []

            elif current_model and line:
                # Continuation of LLM response (could be multi-line)
                current_llm_lines.append(line)

            i += 1

        # Save last model if exists
        if current_model and current_llm_lines:
            models[current_model] = current_llm_lines[:]

        if case_id and models:
            cases[case_id] = models

    return cases


def reconstruct_case(
    case_id: str, question_block: str, models: Dict[str, List[str]]
) -> str:
    """
    Reconstruct a case block with the given models.
    """
    result = []
    result.append(f"CASE: {case_id}")
    result.append(question_block)
    result.append("")

    # Add all model entries
    for model_name, lines in models.items():
        for line in lines:
            result.append(line)
        result.append("")  # Empty line after each model

    return "\n".join(result)


def extract_question_block(content: str, case_id: str) -> str:
    """
    Extract the QUESTION and TRUE answer block for a given case.
    """
    # Find the case block
    case_pattern = f"CASE: {re.escape(case_id)}"
    case_start = content.find(case_pattern)
    if case_start == -1:
        return ""

    # Find the end of the question/true block (before first LLM entry)
    llm_pattern = r"\nLLM \["
    llm_match = re.search(llm_pattern, content[case_start:])
    if not llm_match:
        return ""

    question_end = case_start + llm_match.start()
    question_block = content[case_start:question_end].strip()

    # Remove the "CASE: ..." line as it will be added back in reconstruct_case
    lines = question_block.split("\n")
    return "\n".join(lines[1:]).strip()


def transfer_models(
    source_file: str, target_file: str, output_file: str, models_to_transfer: List[str]
):
    """
    Transfer specific models from source file to target file.
    """
    print(f"Parsing source file: {source_file}")
    source_cases = parse_log_file(source_file)
    print(f"Found {len(source_cases)} cases in source file")

    print(f"Parsing target file: {target_file}")
    target_cases = parse_log_file(target_file)
    print(f"Found {len(target_cases)} cases in target file")

    # Read target file to extract headers and question blocks
    with open(target_file, "r", encoding="utf-8") as f:
        target_content = f.read()

    # Extract header (everything before first case)
    first_case_match = re.search(r"\*+\s*\n\s*CASE:", target_content)
    if first_case_match:
        header = target_content[: first_case_match.start()].strip()
    else:
        header = ""

    # Process each case
    result_blocks = []
    processed_cases = 0
    transferred_models = 0

    for case_id in target_cases:
        # Get question block from target file
        question_block = extract_question_block(target_content, case_id)

        # Start with target case models
        merged_models = target_cases[case_id].copy()

        # Replace with source models if available
        if case_id in source_cases:
            for model in models_to_transfer:
                if model in source_cases[case_id]:
                    merged_models[model] = source_cases[case_id][model]
                    transferred_models += 1
                    print(f"Transferred {model} for case {case_id}")

        # Reconstruct the case
        case_block = reconstruct_case(case_id, question_block, merged_models)
        result_blocks.append(case_block)
        processed_cases += 1

    # Write result
    with open(output_file, "w", encoding="utf-8") as f:
        if header:
            f.write(header + "\n\n")

        for i, block in enumerate(result_blocks):
            f.write("******************************\n\n")
            f.write(block)
            f.write("\n\n")

    print(f"\nTransfer completed!")
    print(f"Processed {processed_cases} cases")
    print(f"Transferred {transferred_models} model entries")
    print(f"Output written to: {output_file}")


def main():
    source_file = "/Users/lukablaskovic/Github/med-rag/output/gpt-5-gpt-oss-20b-deepseek-v3.1-output_batch_size=5&n=1000&exclude=none&take=2.log"
    target_file = "/Users/lukablaskovic/Github/med-rag/output/original_output_batch_size=5&n=1000&exclude=none&take=2.log"
    output_file = "/Users/lukablaskovic/Github/med-rag/output/merged_output_batch_size=5&n=1000&exclude=none&take=2.log"

    models_to_transfer = ["deepseek-v3.1", "gpt-5", "gpt-oss-20b"]

    print("Starting model transfer...")
    print(f"Source: {source_file}")
    print(f"Target: {target_file}")
    print(f"Output: {output_file}")
    print(f"Models to transfer: {', '.join(models_to_transfer)}")
    print()

    try:
        transfer_models(source_file, target_file, output_file, models_to_transfer)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
