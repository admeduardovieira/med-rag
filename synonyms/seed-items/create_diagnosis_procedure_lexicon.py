#!/usr/bin/env python3
"""
Create Diagnosis and Procedure Lexicon JSON Files

This script converts the synonym CSV files into the final JSON lexicon format
for diagnoses and procedures, including semantic types and database links.
"""

import sqlite3
import pandas as pd
import json
import re
from pathlib import Path
import sys
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# Add root directory to path for logging_setup import
sys.path.append(str(Path(__file__).parent.parent.parent))
from logging_setup import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


class DiagnosisProcedureLexiconCreator:
    def __init__(self, umls_db_path: str, mimic_db_path: str):
        self.umls_db_path = umls_db_path
        self.mimic_db_path = mimic_db_path
        self.umls_conn = None
        self.mimic_conn = None

    def connect_databases(self):
        """Connect to both UMLS and MIMIC databases."""
        try:
            self.umls_conn = sqlite3.connect(self.umls_db_path)
            self.mimic_conn = sqlite3.connect(self.mimic_db_path)
            logger.info("Successfully connected to both databases")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to databases: {e}")
            raise

    def close_connections(self):
        """Close database connections."""
        if self.umls_conn:
            self.umls_conn.close()
        if self.mimic_conn:
            self.mimic_conn.close()

    def get_semantic_types(self, cui: str) -> List[str]:
        """Get semantic types for a CUI from UMLS."""
        sql = "SELECT STY FROM MRSTY WHERE CUI=?"
        cursor = self.umls_conn.execute(sql, (cui,))
        return [row[0] for row in cursor.fetchall()]

    def get_existing_diagnosis_codes(self, icd9_codes: List[str]) -> List[str]:
        """Get ICD9 codes that actually exist in the MIMIC diagnoses table."""
        if not icd9_codes:
            return []

        placeholders = ",".join(["?" for _ in icd9_codes])
        sql = f"""
        SELECT DISTINCT ICD9_CODE 
        FROM diagnoses 
        WHERE ICD9_CODE IN ({placeholders})
        """

        cursor = self.mimic_conn.execute(sql, icd9_codes)
        return [row[0] for row in cursor.fetchall()]

    def get_existing_procedure_codes(self, icd9_codes: List[str]) -> List[str]:
        """Get ICD9 codes that actually exist in the MIMIC procedures table."""
        if not icd9_codes:
            return []

        # Convert to strings since procedures.ICD9_CODE is INTEGER
        placeholders = ",".join(["?" for _ in icd9_codes])
        sql = f"""
        SELECT DISTINCT CAST(ICD9_CODE AS TEXT) as code
        FROM procedures 
        WHERE CAST(ICD9_CODE AS TEXT) IN ({placeholders})
        """

        cursor = self.mimic_conn.execute(sql, icd9_codes)
        return [row[0] for row in cursor.fetchall()]

    def get_all_icd9_codes_for_cui(self, cui: str) -> List[str]:
        """Get all ICD9 codes associated with a CUI from UMLS."""
        sql = """
        SELECT DISTINCT CODE 
        FROM MRCONSO 
        WHERE CUI=? AND SAB='ICD9CM' AND SUPPRESS='N'
        """

        cursor = self.umls_conn.execute(sql, (cui,))
        return [row[0] for row in cursor.fetchall()]

    def clean_synonyms(self, synonyms: List[str]) -> List[str]:
        """Clean and filter synonyms."""
        cleaned = set()

        # Words to exclude (qualifiers that add specificity)
        exclude_patterns = [
            r"\bunspecified\b",
            r"\bother\b",
            r"\bnot elsewhere classified\b",
            r"\binitial episode\b",
            r"\with mention of\b",
            r"\without mention of\b",
            r"\btype i\b",
            r"\btype ii\b",
            r"\bstage\b",
            r"\bepisode\b",
        ]

        for syn in synonyms:
            syn_clean = syn.lower().strip()

            # Skip if contains exclusion patterns
            if any(
                re.search(pattern, syn_clean, re.IGNORECASE)
                for pattern in exclude_patterns
            ):
                continue

            # Skip very long terms (likely too specific)
            if len(syn_clean) > 60:
                continue

            # Skip if starts with numbers (likely codes)
            if re.match(r"^\d", syn_clean):
                continue

            cleaned.add(syn_clean)

        return sorted(list(cleaned))[:15]  # Limit to 15 best synonyms

    def process_diagnosis_synonyms(self, csv_file: str) -> List[Dict]:
        """Process diagnosis synonyms CSV and create lexicon entries."""
        logger.info(f"Processing diagnosis synonyms from {csv_file}")

        # Read CSV data
        df = pd.read_csv(csv_file)

        # Group by ICD9_CODE and CUI
        grouped = defaultdict(
            lambda: {
                "long_title": "",
                "count": 0,
                "cuis": set(),
                "synonyms": [],
                "sources": set(),
                "icd9_formatted": "",
            }
        )

        for _, row in df.iterrows():
            icd9_code = str(row["ICD9_CODE"])
            key = icd9_code

            grouped[key]["long_title"] = row["LONG_TITLE"]
            grouped[key]["count"] = row["n"]
            grouped[key]["cuis"].add(row["CUI"])
            grouped[key]["synonyms"].append(row["SYNONYM"])
            grouped[key]["sources"].add(f"{row['SOURCE']}.{row['TERM_TYPE']}")
            grouped[key]["icd9_formatted"] = row["ICD9_FORMATTED"]

        # Create lexicon entries
        lexicon_entries = []

        for icd9_code, data in grouped.items():
            logger.info(f"Processing diagnosis: {icd9_code} - {data['long_title']}")

            cuis = list(data["cuis"])

            # Get semantic types for first CUI
            semtypes = []
            if cuis:
                semtypes = self.get_semantic_types(cuis[0])

            # Clean synonyms
            clean_syns = self.clean_synonyms(data["synonyms"])

            # Get all ICD9 codes for this CUI from UMLS and filter by what exists in MIMIC
            all_related_codes = []
            for cui in cuis:
                cui_codes = self.get_all_icd9_codes_for_cui(cui)
                all_related_codes.extend(cui_codes)

            # Remove duplicates and get only codes that exist in MIMIC
            unique_codes = list(set(all_related_codes + [icd9_code]))
            existing_codes = self.get_existing_diagnosis_codes(unique_codes)

            if existing_codes:
                # Use the most common synonym as canonical, or fall back to cleaned title
                canonical = clean_syns[0] if clean_syns else data["long_title"].lower()

                entry = {
                    "canonical": canonical,
                    "cuis": cuis,
                    "semtypes": semtypes,
                    "surface_forms": clean_syns,
                    "db_links": {"diagnoses": {"icd9_exact": existing_codes}},
                    "provenance": {
                        "sources": sorted(list(data["sources"])),
                        "original_title": data["long_title"],
                        "icd9_formatted": data["icd9_formatted"],
                        "mimic_count": int(data["count"]),
                    },
                }

                lexicon_entries.append(entry)
                logger.info(
                    f"✅ Created entry for {icd9_code} -> {len(existing_codes)} codes"
                )
            else:
                logger.warning(f"❌ No existing codes found for {icd9_code}")

        return lexicon_entries

    def process_procedure_synonyms(self, csv_file: str) -> List[Dict]:
        """Process procedure synonyms CSV and create lexicon entries."""
        logger.info(f"Processing procedure synonyms from {csv_file}")

        # Read CSV data
        df = pd.read_csv(csv_file)

        # Group by ICD9_CODE and CUI
        grouped = defaultdict(
            lambda: {
                "long_title": "",
                "count": 0,
                "cuis": set(),
                "synonyms": [],
                "sources": set(),
                "icd9_formatted": "",
            }
        )

        for _, row in df.iterrows():
            icd9_code = str(row["ICD9_CODE"])
            key = icd9_code

            grouped[key]["long_title"] = row["LONG_TITLE"]
            grouped[key]["count"] = row["n"]
            grouped[key]["cuis"].add(row["CUI"])
            grouped[key]["synonyms"].append(row["SYNONYM"])
            grouped[key]["sources"].add(f"{row['SOURCE']}.{row['TERM_TYPE']}")
            grouped[key]["icd9_formatted"] = row["ICD9_FORMATTED"]

        # Create lexicon entries
        lexicon_entries = []

        for icd9_code, data in grouped.items():
            logger.info(f"Processing procedure: {icd9_code} - {data['long_title']}")

            cuis = list(data["cuis"])

            # Get semantic types for first CUI
            semtypes = []
            if cuis:
                semtypes = self.get_semantic_types(cuis[0])

            # Clean synonyms
            clean_syns = self.clean_synonyms(data["synonyms"])

            # Get all ICD9 codes for this CUI from UMLS and filter by what exists in MIMIC
            all_related_codes = []
            for cui in cuis:
                cui_codes = self.get_all_icd9_codes_for_cui(cui)
                all_related_codes.extend(cui_codes)

            # Remove duplicates and get only codes that exist in MIMIC
            unique_codes = list(set(all_related_codes + [icd9_code]))
            existing_codes = self.get_existing_procedure_codes(unique_codes)

            if existing_codes:
                # Use the most common synonym as canonical, or fall back to cleaned title
                canonical = clean_syns[0] if clean_syns else data["long_title"].lower()

                entry = {
                    "canonical": canonical,
                    "cuis": cuis,
                    "semtypes": semtypes,
                    "surface_forms": clean_syns,
                    "db_links": {"procedures": {"icd9_exact": existing_codes}},
                    "provenance": {
                        "sources": sorted(list(data["sources"])),
                        "original_title": data["long_title"],
                        "icd9_formatted": data["icd9_formatted"],
                        "mimic_count": int(data["count"]),
                    },
                }

                lexicon_entries.append(entry)
                logger.info(
                    f"✅ Created entry for {icd9_code} -> {len(existing_codes)} codes"
                )
            else:
                logger.warning(f"❌ No existing codes found for {icd9_code}")

        return lexicon_entries


def main():
    """Main function."""
    # Paths
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent.parent

    umls_db_path = root_dir / "db" / "umls.db"
    mimic_db_path = root_dir / "db" / "database.db"

    diagnosis_csv = (
        script_dir
        / "filtered"
        / "synonyms_per_cui"
        / "top-diagnoses_limit100_synonyms.csv"
    )
    procedure_csv = (
        script_dir
        / "filtered"
        / "synonyms_per_cui"
        / "top-procedures_limit100_synonyms.csv"
    )

    # Output paths
    output_dir = script_dir / "filtered" / "lexicon_entries"
    output_dir.mkdir(exist_ok=True)

    diagnosis_output = output_dir / "diagnosis_lexicon.json"
    procedure_output = output_dir / "procedure_lexicon.json"

    # Verify files exist
    for path in [umls_db_path, mimic_db_path, diagnosis_csv, procedure_csv]:
        if not path.exists():
            logger.error(f"Required file not found: {path}")
            return 1

    # Initialize creator
    creator = DiagnosisProcedureLexiconCreator(str(umls_db_path), str(mimic_db_path))

    try:
        creator.connect_databases()

        # Process diagnoses
        logger.info("=" * 60)
        logger.info("PROCESSING DIAGNOSES")
        logger.info("=" * 60)

        diagnosis_entries = creator.process_diagnosis_synonyms(str(diagnosis_csv))
        with open(diagnosis_output, "w") as f:
            json.dump(diagnosis_entries, f, indent=2)
        logger.info(
            f"Diagnosis lexicon saved to {diagnosis_output} ({len(diagnosis_entries)} entries)"
        )

        # Process procedures
        logger.info("=" * 60)
        logger.info("PROCESSING PROCEDURES")
        logger.info("=" * 60)

        procedure_entries = creator.process_procedure_synonyms(str(procedure_csv))
        with open(procedure_output, "w") as f:
            json.dump(procedure_entries, f, indent=2)
        logger.info(
            f"Procedure lexicon saved to {procedure_output} ({len(procedure_entries)} entries)"
        )

        # Summary
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Diagnosis entries: {len(diagnosis_entries)}")
        logger.info(f"✅ Procedure entries: {len(procedure_entries)}")
        logger.info(
            f"✅ Total entries: {len(diagnosis_entries) + len(procedure_entries)}"
        )
        logger.info(
            "✅ Diagnosis and procedure lexicon creation completed successfully!"
        )

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return 1
    finally:
        creator.close_connections()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
