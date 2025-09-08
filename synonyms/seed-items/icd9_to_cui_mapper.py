#!/usr/bin/env python3
"""
ICD-9 to CUI Mapping Script

This script maps ICD-9 codes from the top-diagnoses_limit100.csv to UMLS CUIs
using the umls.db database. It handles cases where no CUI is found or multiple
CUIs are found for a given ICD-9 code.
"""

import sqlite3
import pandas as pd
import os
import sys
from pathlib import Path

# Add root directory to path for logging_setup import
sys.path.append(str(Path(__file__).parent.parent.parent))
from logging_setup import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def connect_to_umls_db(db_path: str) -> sqlite3.Connection:
    """Connect to the UMLS database."""
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Successfully connected to UMLS database: {db_path}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to UMLS database: {e}")
        raise


def query_cui_for_icd9(conn: sqlite3.Connection, icd9_code: str) -> list:
    """
    Query UMLS database for CUI given an ICD-9 code.

    Args:
        conn: SQLite connection to UMLS database
        icd9_code: ICD-9 code to search for

    Returns:
        List of CUIs found for the given ICD-9 code
    """
    query = """
    SELECT DISTINCT CUI
    FROM MRCONSO
    WHERE SAB = 'ICD9CM'
      AND SUPPRESS = 'N'
      AND REPLACE(CODE, '.', '') = REPLACE(?, '.', '');
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query, (icd9_code,))
        results = cursor.fetchall()
        cuis = [row[0] for row in results]
        return cuis
    except sqlite3.Error as e:
        logger.error(f"Error querying database for ICD-9 code {icd9_code}: {e}")
        return []


def map_icd9_to_cui(icd9_code: str, cuis: list) -> str:
    """
    Map ICD-9 code to CUI with appropriate handling for different cases.

    Args:
        icd9_code: The ICD-9 code being mapped
        cuis: List of CUIs found for the code

    Returns:
        String representation of the mapping result
    """
    if not cuis:
        logger.warning(f"No CUI found for ICD-9 code: {icd9_code}")
        return "NOT_FOUND"
    elif len(cuis) == 1:
        logger.debug(f"Found single CUI for {icd9_code}: {cuis[0]}")
        return cuis[0]
    else:
        logger.warning(f"Multiple CUIs found for {icd9_code}: {cuis}")
        return f"AMBIGUOUS_MULTIPLE:{';'.join(cuis)}"


def process_diagnoses_file(input_file: str, output_file: str, umls_db_path: str):
    """
    Process the diagnoses CSV file and create a new file with CUI mappings.

    Args:
        input_file: Path to input CSV file with ICD-9 codes
        output_file: Path to output CSV file with CUI mappings
        umls_db_path: Path to UMLS database
    """
    logger.info(f"Starting processing of {input_file}")

    # Read the input CSV
    try:
        df = pd.read_csv(input_file)
        logger.info(f"Successfully loaded {len(df)} diagnoses from {input_file}")
    except Exception as e:
        logger.error(f"Error reading input file {input_file}: {e}")
        return

    # Connect to UMLS database
    conn = connect_to_umls_db(umls_db_path)

    # Initialize lists to store results
    cui_mappings = []
    mapping_status = []

    # Process each ICD-9 code
    logger.info("Starting ICD-9 to CUI mapping process...")
    for idx, row in df.iterrows():
        icd9_code = str(row["ICD9_CODE"]).strip()
        long_title = row["LONG_TITLE"]
        count = row["n"]

        logger.debug(f"Processing {idx+1}/{len(df)}: {icd9_code} - {long_title}")

        # Query for CUIs
        cuis = query_cui_for_icd9(conn, icd9_code)

        # Map the result
        cui_mapping = map_icd9_to_cui(icd9_code, cuis)
        cui_mappings.append(cui_mapping)

        # Track mapping status for statistics
        if cui_mapping == "NOT_FOUND":
            mapping_status.append("NOT_FOUND")
        elif cui_mapping.startswith("AMBIGUOUS_MULTIPLE"):
            mapping_status.append("AMBIGUOUS")
        else:
            mapping_status.append("MAPPED")

    # Close database connection
    conn.close()

    # Add CUI mapping to dataframe
    df["CUI"] = cui_mappings
    df["MAPPING_STATUS"] = mapping_status

    # Save results
    try:
        df.to_csv(output_file, index=False)
        logger.info(f"Successfully saved mapped results to {output_file}")
    except Exception as e:
        logger.error(f"Error saving output file {output_file}: {e}")
        return

    # Print summary statistics
    status_counts = pd.Series(mapping_status).value_counts()
    logger.info("=== Mapping Summary ===")
    logger.info(f"Total diagnoses processed: {len(df)}")
    for status, count in status_counts.items():
        percentage = (count / len(df)) * 100
        logger.info(f"{status}: {count} ({percentage:.1f}%)")

    logger.info(f"Mapping process completed successfully!")


def main():
    """Main function to run the ICD-9 to CUI mapping."""

    # Define file paths
    script_dir = Path(__file__).parent
    input_file = script_dir / "filtered" / "top-diagnoses_limit100.csv"
    output_file = script_dir / "filtered" / "top-diagnoses_limit100_with_cui.csv"
    umls_db_path = script_dir.parent.parent / "db" / "umls.db"

    # Verify input files exist
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return 1

    if not umls_db_path.exists():
        logger.error(f"UMLS database not found: {umls_db_path}")
        return 1

    logger.info(f"Input file: {input_file}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"UMLS database: {umls_db_path}")

    # Process the file
    try:
        process_diagnoses_file(str(input_file), str(output_file), str(umls_db_path))
        return 0
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
