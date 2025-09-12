#!/usr/bin/env python3
"""
Script to create separate test files using normalized questions from option1 and option2 files.

Creates two output files:
- test_option1_normalized.json: Uses option1 normalized questions when available/changed, original otherwise
- test_option2_normalized.json: Uses option2 normalized questions when available/changed, original otherwise
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

# Import custom logger
from logging_setup import setup_logging, get_logger

# Setup logger
setup_logging()
logger = get_logger(__name__)


def load_json_lines(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load JSON lines file and return dictionary keyed by 'key' field."""
    data = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if "key" not in entry:
                        logger.warning(
                            f"Line {line_num} in {file_path} missing 'key' field"
                        )
                        continue
                    data[entry["key"]] = entry
                except json.JSONDecodeError as e:
                    logger.error(
                        f"JSON decode error at line {line_num} in {file_path}: {e}"
                    )
                    continue
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return {}

    logger.info(f"Loaded {len(data)} entries from {file_path}")
    return data


def create_option_dataset(
    original_data: Dict[str, Dict[str, Any]],
    option_data: Dict[str, Dict[str, Any]],
    option_name: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Create a dataset using normalized questions from the specified option.
    Use normalized question if available and changed, otherwise keep original.
    """
    result_data = {}
    stats = {
        "total": 0,
        "used_normalized": 0,
        "kept_original": 0,
        "missing_in_option": 0,
    }

    for key, original_entry in original_data.items():
        stats["total"] += 1
        result_entry = original_entry.copy()

        # Check if normalized version is available and changed
        if key in option_data:
            option_entry = option_data[key]
            if option_entry.get("output") == "changed" and "normalized" in option_entry:
                result_entry["question_refine"] = option_entry["normalized"]
                stats["used_normalized"] += 1
                logger.debug(f"Key {key}: Used {option_name} normalized question")
            else:
                stats["kept_original"] += 1
                logger.debug(
                    f"Key {key}: Kept original question ({option_name} unchanged)"
                )
        else:
            stats["missing_in_option"] += 1
            stats["kept_original"] += 1
            logger.debug(
                f"Key {key}: Kept original question ({option_name} not available)"
            )

        result_data[key] = result_entry

    logger.info(f"{option_name} statistics: {stats}")
    return result_data


def save_json_lines(data: Dict[str, Dict[str, Any]], output_path: Path) -> bool:
    """Save data as JSON lines file."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in data.values():
                json.dump(entry, f, ensure_ascii=False, separators=(",", ":"))
                f.write("\n")
        logger.info(f"Successfully saved {len(data)} entries to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving to {output_path}: {e}")
        return False


def main():
    """Main function to create separate test files for option1 and option2."""
    # Define file paths
    dataset_dir = Path(__file__).parent / "dataset"
    original_file = dataset_dir / "test.json"
    option1_file = dataset_dir / "test_normalized_option1.json"
    option2_file = dataset_dir / "test_normalized_option2.json"
    output_option1_file = dataset_dir / "test_option1_normalized.json"
    output_option2_file = dataset_dir / "test_option2_normalized.json"

    logger.info("Starting dataset creation process...")
    logger.info(f"Original file: {original_file}")
    logger.info(f"Option1 file: {option1_file}")
    logger.info(f"Option2 file: {option2_file}")
    logger.info(f"Output Option1 file: {output_option1_file}")
    logger.info(f"Output Option2 file: {output_option2_file}")

    # Load all files
    logger.info("Loading data files...")
    original_data = load_json_lines(original_file)
    option1_data = load_json_lines(option1_file)
    option2_data = load_json_lines(option2_file)

    if not original_data:
        logger.error("No data loaded from original file. Exiting.")
        return

    # Create option1 dataset
    logger.info("Creating Option1 dataset...")
    option1_dataset = create_option_dataset(original_data, option1_data, "Option1")

    # Create option2 dataset
    logger.info("Creating Option2 dataset...")
    option2_dataset = create_option_dataset(original_data, option2_data, "Option2")

    # Save both results
    logger.info("Saving datasets...")
    success_count = 0

    if save_json_lines(option1_dataset, output_option1_file):
        logger.info(f"Successfully created Option1 file: {output_option1_file}")
        success_count += 1
    else:
        logger.error("Failed to save Option1 file")

    if save_json_lines(option2_dataset, output_option2_file):
        logger.info(f"Successfully created Option2 file: {output_option2_file}")
        success_count += 1
    else:
        logger.error("Failed to save Option2 file")

    if success_count == 2:
        logger.info("All datasets created successfully!")
    else:
        logger.warning(f"Only {success_count}/2 datasets created successfully")


if __name__ == "__main__":
    main()
