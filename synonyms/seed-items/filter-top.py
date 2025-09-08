import os
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logging_setup import setup_logging, get_logger


TOP_COUNTS: Dict[str, int] = {
    "top-diagnoses.csv": 50,
    "top-lab.csv": 25,
    "top-drugs.csv": 15,
    "top-procedures.csv": 10,
}


def filter_csv_in_place(csv_path: Path, top_n: int, output_dir: Path) -> None:
    """
    Read a CSV, sort by column 'n' descending, keep top_n rows, and write to output_dir.
    """
    logger = get_logger(__name__)

    if not csv_path.exists():
        logger.warning(f"File not found, skipping: {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        logger.error(f"Failed to read {csv_path}: {exc}")
        return

    if "n" not in df.columns:
        logger.error(f"Column 'n' not found in {csv_path.name}; skipping.")
        return

    # Ensure numeric sorting on 'n'
    df["n"] = pd.to_numeric(df["n"], errors="coerce")
    before_count = len(df)
    df = df.sort_values("n", ascending=False, kind="mergesort").head(top_n)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / csv_path.name

    try:
        df.to_csv(output_path, index=False)
        logger.info(
            f"Filtered {csv_path.name}: kept {len(df)}/{before_count} rows (top {top_n} by n) → {output_path}"
        )
    except Exception as exc:
        logger.error(f"Failed to write {output_path}: {exc}")


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)

    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir / "filtered"

    for filename, top_n in TOP_COUNTS.items():
        csv_path = script_dir / filename
        logger.info(f"Processing {csv_path} (top {top_n})...")
        filter_csv_in_place(csv_path, top_n, output_dir)


if __name__ == "__main__":
    main()
