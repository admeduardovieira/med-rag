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


def format_icd9_diagnosis_code(icd9_code: str) -> str:
    """
    Format ICD-9 diagnosis code with proper decimal placement.

    ICD-9 diagnosis code format:
    - Regular codes: 3 chars: XXX, 4 chars: XXX.X, 5 chars: XXX.XX
    - E-codes: 4 chars: EXXX, 5 chars: EXXX.X
    - V-codes: 3 chars: VXX, 4 chars: VXX.X, 5 chars: VXX.XX

    Args:
        icd9_code: Raw ICD-9 diagnosis code (integer as string)

    Returns:
        Properly formatted ICD-9 diagnosis code with decimal
    """
    icd9_code = icd9_code.strip()

    # Handle E-codes (External cause codes)
    if icd9_code.startswith("E"):
        if len(icd9_code) == 4:
            return icd9_code  # EXXX (no decimal)
        elif len(icd9_code) == 5:
            return f"{icd9_code[:4]}.{icd9_code[4:]}"  # EXXX.X
        else:
            return icd9_code

    # Handle V-codes and regular diagnosis codes
    else:
        if len(icd9_code) == 3:
            return icd9_code  # XXX or VXX (no decimal)
        elif len(icd9_code) == 4:
            return f"{icd9_code[:3]}.{icd9_code[3:]}"  # XXX.X or VXX.X
        elif len(icd9_code) == 5:
            return f"{icd9_code[:3]}.{icd9_code[3:]}"  # XXX.XX or VXX.XX
        else:
            # For unusual lengths, return as-is
            return icd9_code


def format_icd9_procedure_code(icd9_code: str) -> str:
    """
    Format ICD-9 procedure code with proper decimal placement.

    ICD-9 procedure code format:
    - 2 chars: XX (no decimal)
    - 3 chars: XX.X (e.g., 966 → 96.6)
    - 4 chars: XX.XX (e.g., 3893 → 38.93)

    Args:
        icd9_code: Raw ICD-9 procedure code (integer as string)

    Returns:
        Properly formatted ICD-9 procedure code with decimal
    """
    icd9_code = icd9_code.strip()

    if len(icd9_code) == 2:
        return icd9_code  # XX (no decimal)
    elif len(icd9_code) == 3:
        return f"{icd9_code[:2]}.{icd9_code[2:]}"  # XX.X
    elif len(icd9_code) == 4:
        return f"{icd9_code[:2]}.{icd9_code[2:]}"  # XX.XX
    else:
        # For unusual lengths, return as-is
        return icd9_code


def query_cui_for_icd9(
    conn: sqlite3.Connection, icd9_code: str, code_type: str = "diagnosis"
) -> list:
    """
    Query UMLS database for CUI given an ICD-9 code.

    Args:
        conn: SQLite connection to UMLS database
        icd9_code: ICD-9 code to search for
        code_type: Either "diagnosis" or "procedure"

    Returns:
        List of CUIs found for the given ICD-9 code
    """
    # Format the ICD-9 code with proper decimal placement based on type
    if code_type == "diagnosis":
        formatted_code = format_icd9_diagnosis_code(icd9_code)
    elif code_type == "procedure":
        formatted_code = format_icd9_procedure_code(icd9_code)
    else:
        raise ValueError(
            f"Invalid code_type: {code_type}. Must be 'diagnosis' or 'procedure'"
        )

    query = """
    SELECT DISTINCT CUI
    FROM MRCONSO
    WHERE SAB = 'ICD9CM'
      AND SUPPRESS = 'N'
      AND CODE = ?;
    """

    try:
        cursor = conn.cursor()
        cursor.execute(query, (formatted_code,))
        results = cursor.fetchall()
        cuis = [row[0] for row in results]
        logger.debug(
            f"Formatted {code_type} {icd9_code} → {formatted_code}, found {len(cuis)} CUIs"
        )
        return cuis
    except sqlite3.Error as e:
        logger.error(
            f"Error querying database for ICD-9 {code_type} code {icd9_code} (formatted: {formatted_code}): {e}"
        )
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


def process_icd9_file(
    input_file: str, output_file: str, umls_db_path: str, code_type: str = "diagnosis"
):
    """
    Process the ICD-9 CSV file and create a new file with CUI mappings.

    Args:
        input_file: Path to input CSV file with ICD-9 codes
        output_file: Path to output CSV file with CUI mappings
        umls_db_path: Path to UMLS database
        code_type: Either "diagnosis" or "procedure"
    """
    logger.info(f"Starting processing of {code_type} file: {input_file}")

    # Read the input CSV
    try:
        df = pd.read_csv(input_file)
        logger.info(
            f"Successfully loaded {len(df)} {code_type} codes from {input_file}"
        )
    except Exception as e:
        logger.error(f"Error reading input file {input_file}: {e}")
        return

    # Connect to UMLS database
    conn = connect_to_umls_db(umls_db_path)

    # Initialize lists to store results
    cui_mappings = []
    mapping_status = []
    formatted_codes = []

    # Process each ICD-9 code
    logger.info(f"Starting ICD-9 {code_type} to CUI mapping process...")
    for idx, row in df.iterrows():
        icd9_code = str(row["ICD9_CODE"]).strip()
        long_title = row["LONG_TITLE"]
        count = row["n"]

        # Format the code for display based on type
        if code_type == "diagnosis":
            formatted_code = format_icd9_diagnosis_code(icd9_code)
        elif code_type == "procedure":
            formatted_code = format_icd9_procedure_code(icd9_code)
        else:
            raise ValueError(f"Invalid code_type: {code_type}")

        formatted_codes.append(formatted_code)

        logger.debug(
            f"Processing {idx+1}/{len(df)}: {icd9_code} → {formatted_code} - {long_title}"
        )

        # Query for CUIs
        cuis = query_cui_for_icd9(conn, icd9_code, code_type)

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
    df["ICD9_FORMATTED"] = formatted_codes
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
    logger.info(f"=== {code_type.title()} Mapping Summary ===")
    logger.info(f"Total {code_type} codes processed: {len(df)}")
    for status, count in status_counts.items():
        percentage = (count / len(df)) * 100
        logger.info(f"{status}: {count} ({percentage:.1f}%)")

    logger.info(f"{code_type.title()} mapping process completed successfully!")


def main():
    """Main function to run the ICD-9 to CUI mapping for both diagnoses and procedures."""

    # Define file paths
    script_dir = Path(__file__).parent

    # Input files
    diagnoses_input = script_dir / "filtered" / "top-diagnoses_limit100.csv"
    procedures_input = script_dir / "filtered" / "top-procedures_limit100.csv"

    # Output files (in w_cui_mapped folder)
    output_dir = script_dir / "filtered" / "w_cui_mapped"
    diagnoses_output = output_dir / "top-diagnoses_limit100_with_cui.csv"
    procedures_output = output_dir / "top-procedures_limit100_with_cui.csv"

    # UMLS database
    umls_db_path = script_dir.parent.parent / "db" / "umls.db"

    # Verify UMLS database exists
    if not umls_db_path.exists():
        logger.error(f"UMLS database not found: {umls_db_path}")
        return 1

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)

    # Process diagnoses
    if diagnoses_input.exists():
        logger.info("=" * 60)
        logger.info("PROCESSING DIAGNOSES")
        logger.info("=" * 60)
        logger.info(f"Input file: {diagnoses_input}")
        logger.info(f"Output file: {diagnoses_output}")
        logger.info(f"UMLS database: {umls_db_path}")

        try:
            process_icd9_file(
                str(diagnoses_input),
                str(diagnoses_output),
                str(umls_db_path),
                "diagnosis",
            )
            logger.info("Diagnoses processing completed successfully!")
        except Exception as e:
            logger.error(f"Error during diagnoses processing: {e}")
            return 1
    else:
        logger.warning(f"Diagnoses input file not found: {diagnoses_input}")

    # Process procedures
    if procedures_input.exists():
        logger.info("=" * 60)
        logger.info("PROCESSING PROCEDURES")
        logger.info("=" * 60)
        logger.info(f"Input file: {procedures_input}")
        logger.info(f"Output file: {procedures_output}")
        logger.info(f"UMLS database: {umls_db_path}")

        try:
            process_icd9_file(
                str(procedures_input),
                str(procedures_output),
                str(umls_db_path),
                "procedure",
            )
            logger.info("Procedures processing completed successfully!")
        except Exception as e:
            logger.error(f"Error during procedures processing: {e}")
            return 1
    else:
        logger.warning(f"Procedures input file not found: {procedures_input}")

    logger.info("=" * 60)
    logger.info("ALL PROCESSING COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
