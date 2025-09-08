#!/usr/bin/env python3
"""
Script to collect English synonyms from UMLS database for CUI codes
in the diagnosis and procedures CSV files.

This script reads the CUI-mapped CSV files and queries the UMLS MRCONSO table
to find synonyms for each CUI, then saves the results to new CSV files.
"""

import sqlite3
import pandas as pd
import os
from pathlib import Path
import sys

# Add the parent directory to the path for logging_setup
sys.path.append(str(Path(__file__).parent.parent.parent))
from logging_setup import get_logger

logger = get_logger(__name__)


def connect_to_umls_db(db_path):
    """Connect to the UMLS database."""
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Connected to UMLS database at {db_path}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def get_synonyms_for_cui(conn, cui):
    """
    Get synonyms for a given CUI from the UMLS MRCONSO table.

    Args:
        conn: SQLite database connection
        cui: CUI string to search for

    Returns:
        List of dictionaries containing synonym data
    """
    sql = """
    SELECT STR, SAB, TTY
    FROM MRCONSO
    WHERE CUI=? AND LAT='ENG' AND SUPPRESS='N'
      AND SAB IN ('SNOMEDCT_US','MSH','RXNORM','LNC','ICD9CM')
      AND TTY IN ('PT','SY','FN','BN','IN')
    LIMIT 50;
    """

    try:
        cursor = conn.cursor()
        cursor.execute(sql, (cui,))
        results = cursor.fetchall()

        synonyms = []
        for row in results:
            synonyms.append({"STR": row[0], "SAB": row[1], "TTY": row[2]})

        return synonyms

    except sqlite3.Error as e:
        logger.error(f"Error querying database for CUI {cui}: {e}")
        return []


def process_csv_file(input_file, output_file, umls_conn):
    """
    Process a CUI-mapped CSV file and collect synonyms for each CUI.

    Args:
        input_file: Path to input CSV file with CUI mappings
        output_file: Path to output CSV file for synonyms
        umls_conn: Connection to UMLS database
    """
    logger.info(f"Processing {input_file}")

    # Read the input CSV
    df = pd.read_csv(input_file)
    logger.info(f"Found {len(df)} rows in input file")

    # Filter only mapped entries
    mapped_df = df[df["MAPPING_STATUS"] == "MAPPED"].copy()
    logger.info(f"Found {len(mapped_df)} mapped entries")

    # Collect all synonyms
    all_synonyms = []

    for idx, row in mapped_df.iterrows():
        cui = row["CUI"]
        icd9_code = row["ICD9_CODE"]
        long_title = row["LONG_TITLE"]
        n = row["n"]
        icd9_formatted = row["ICD9_FORMATTED"]

        logger.debug(f"Processing CUI {cui} for ICD9 {icd9_code}")

        # Get synonyms for this CUI
        synonyms = get_synonyms_for_cui(umls_conn, cui)

        # Add context information to each synonym
        for synonym in synonyms:
            all_synonyms.append(
                {
                    "ICD9_CODE": icd9_code,
                    "ICD9_FORMATTED": icd9_formatted,
                    "LONG_TITLE": long_title,
                    "n": n,
                    "CUI": cui,
                    "SYNONYM": synonym["STR"],
                    "SOURCE": synonym["SAB"],
                    "TERM_TYPE": synonym["TTY"],
                }
            )

        if idx % 10 == 0:
            logger.info(f"Processed {idx + 1}/{len(mapped_df)} entries")

    # Create DataFrame and save
    synonyms_df = pd.DataFrame(all_synonyms)
    synonyms_df.to_csv(output_file, index=False)

    logger.info(f"Saved {len(all_synonyms)} synonyms to {output_file}")
    logger.info(f"Found synonyms for {synonyms_df['CUI'].nunique()} unique CUIs")


def main():
    """Main function to process both diagnosis and procedures files."""
    logger.info("Starting UMLS synonym collection")

    # Define paths
    base_dir = Path(__file__).parent
    input_dir = base_dir / "filtered" / "w_cui_mapped"
    output_dir = base_dir / "filtered" / "synonyms_per_cui"
    umls_db_path = base_dir.parent.parent / "db" / "umls.db"

    # Create output directory
    output_dir.mkdir(exist_ok=True, parents=True)
    logger.info(f"Created output directory: {output_dir}")

    # Connect to UMLS database
    conn = connect_to_umls_db(umls_db_path)

    try:
        # Process diagnoses file
        diagnoses_input = input_dir / "top-diagnoses_limit100_with_cui.csv"
        diagnoses_output = output_dir / "top-diagnoses_limit100_synonyms.csv"

        if diagnoses_input.exists():
            process_csv_file(diagnoses_input, diagnoses_output, conn)
        else:
            logger.warning(f"Diagnoses input file not found: {diagnoses_input}")

        # Process procedures file
        procedures_input = input_dir / "top-procedures_limit100_with_cui.csv"
        procedures_output = output_dir / "top-procedures_limit100_synonyms.csv"

        if procedures_input.exists():
            process_csv_file(procedures_input, procedures_output, conn)
        else:
            logger.warning(f"Procedures input file not found: {procedures_input}")

    finally:
        conn.close()
        logger.info("Database connection closed")

    logger.info("UMLS synonym collection completed successfully")


if __name__ == "__main__":
    main()
