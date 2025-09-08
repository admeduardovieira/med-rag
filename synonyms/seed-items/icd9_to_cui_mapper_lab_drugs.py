#!/usr/bin/env python3
"""
Lab and Drug Mapping Script for UMLS-MIMIC Lexicon Creation

This script:
1. Maps lab labels and drug names to UMLS CUIs
2. Collects synonyms for each CUI
3. Maps synonyms back to actual MIMIC database values (ITEMIDs for labs, drug strings for drugs)
4. Creates the final lexicon entries in JSON format
"""

import sqlite3
import pandas as pd
import json
import re
from pathlib import Path
import sys
from typing import Dict, List, Set, Tuple, Optional

# Add root directory to path for logging_setup import
sys.path.append(str(Path(__file__).parent.parent.parent))
from logging_setup import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


class LabDrugMapper:
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

    def find_lab_cuis(self, label: str) -> List[str]:
        """Find CUIs for a lab label using LOINC in UMLS."""
        sql = """
        SELECT DISTINCT CUI
        FROM MRCONSO
        WHERE LAT='ENG' AND SAB='LNC' AND SUPPRESS='N'
          AND LOWER(STR) LIKE '%' || LOWER(?) || '%'
        LIMIT 5
        """

        cursor = self.umls_conn.execute(sql, (label,))
        cuis = [row[0] for row in cursor.fetchall()]

        # If no LOINC results, try broader search
        if not cuis:
            sql_broad = """
            SELECT DISTINCT CUI
            FROM MRCONSO
            WHERE LAT='ENG' AND SUPPRESS='N'
              AND LOWER(STR) LIKE '%' || LOWER(?) || '%'
              AND SAB IN ('SNOMEDCT_US', 'MSH')
            LIMIT 5
            """
            cursor = self.umls_conn.execute(sql_broad, (label,))
            cuis = [row[0] for row in cursor.fetchall()]

        return cuis

    def find_drug_cuis(self, drug: str) -> List[str]:
        """Find CUIs for a drug using RxNorm in UMLS."""
        # Try exact match first
        sql_exact = """
        SELECT DISTINCT CUI, TTY
        FROM MRCONSO
        WHERE LAT='ENG' AND SAB='RXNORM' AND SUPPRESS='N'
          AND UPPER(STR)=UPPER(?)
          AND TTY IN ('IN','BN','SCD','SBD')
        """

        cursor = self.umls_conn.execute(sql_exact, (drug,))
        results = cursor.fetchall()
        cuis = [row[0] for row in results]

        # If no exact match, try partial match
        if not cuis:
            sql_partial = """
            SELECT DISTINCT CUI
            FROM MRCONSO
            WHERE LAT='ENG' AND SAB='RXNORM' AND SUPPRESS='N'
              AND UPPER(STR) LIKE '%' || UPPER(?) || '%'
              AND TTY IN ('IN','BN','SCD','SBD')
            LIMIT 5
            """
            cursor = self.umls_conn.execute(sql_partial, (drug,))
            cuis = [row[0] for row in cursor.fetchall()]

        return cuis

    def get_synonyms_for_cui(self, cui: str) -> List[Dict[str, str]]:
        """Get English synonyms for a CUI."""
        sql = """
        SELECT STR, SAB, TTY
        FROM MRCONSO
        WHERE CUI=? AND LAT='ENG' AND SUPPRESS='N'
          AND SAB IN ('SNOMEDCT_US','MSH','RXNORM','LNC','ICD9CM')
          AND TTY IN ('PT','SY','FN','BN','IN')
        LIMIT 50
        """

        cursor = self.umls_conn.execute(sql, (cui,))
        synonyms = []

        for row in cursor.fetchall():
            synonyms.append({"synonym": row[0], "source": row[1], "term_type": row[2]})

        return synonyms

    def clean_synonyms(self, synonyms: List[Dict[str, str]]) -> List[str]:
        """Clean and filter synonyms."""
        cleaned = set()

        # Words to exclude (qualifiers that add specificity)
        exclude_patterns = [
            r"\bacute\b",
            r"\bchronic\b",
            r"\bleft\b",
            r"\bright\b",
            r"\bupper\b",
            r"\blower\b",
            r"\bhours?\b",
            r"\bdays?\b",
            r"\>96\b",
            r"\<96\b",
            r"\bunspecified\b",
            r"\bother\b",
        ]

        for syn_data in synonyms:
            syn = syn_data["synonym"].lower().strip()

            # Skip if contains exclusion patterns
            if any(
                re.search(pattern, syn, re.IGNORECASE) for pattern in exclude_patterns
            ):
                continue

            # Skip very long terms (likely too specific)
            if len(syn) > 50:
                continue

            # Skip if contains parentheses (often qualifiers)
            if "(" in syn:
                continue

            cleaned.add(syn)

        return sorted(list(cleaned))[:10]  # Limit to 10 best synonyms

    def map_lab_synonyms_to_itemids(self, synonyms: List[str]) -> List[int]:
        """Map lab synonyms to actual ITEMIDs in MIMIC database."""
        itemids = set()

        for synonym in synonyms:
            sql = """
            SELECT DISTINCT ITEMID, COUNT(*) as count
            FROM lab
            WHERE LOWER(LABEL) LIKE '%' || LOWER(?) || '%'
            GROUP BY ITEMID
            HAVING count >= 10
            """

            cursor = self.mimic_conn.execute(sql, (synonym,))
            for row in cursor.fetchall():
                itemids.add(row[0])

        return sorted(list(itemids))

    def map_drug_synonyms_to_drugs(self, synonyms: List[str]) -> List[str]:
        """Map drug synonyms to actual DRUG strings in MIMIC database."""
        drug_strings = set()

        for synonym in synonyms:
            sql = """
            SELECT DISTINCT UPPER(DRUG) as drug_upper
            FROM prescriptions
            WHERE UPPER(DRUG) = UPPER(?)
               OR UPPER(DRUG) LIKE '%' || UPPER(?) || '%'
            """

            cursor = self.mimic_conn.execute(sql, (synonym, synonym))
            for row in cursor.fetchall():
                drug_strings.add(row[0])

        return sorted(list(drug_strings))

    def process_labs(self, lab_file: str) -> List[Dict]:
        """Process lab file and create lexicon entries."""
        logger.info(f"Processing labs from {lab_file}")

        # Read lab data
        df = pd.read_csv(lab_file)
        lexicon_entries = []

        for _, row in df.iterrows():
            label = row["LABEL"]
            count = row["n"]

            logger.info(f"Processing lab: {label} (count: {count})")

            # Find CUIs
            cuis = self.find_lab_cuis(label)
            if not cuis:
                logger.warning(f"No CUIs found for lab: {label}")
                continue

            # Get synonyms for first CUI (or merge if multiple)
            all_synonyms = []
            for cui in cuis[:2]:  # Limit to first 2 CUIs
                synonyms = self.get_synonyms_for_cui(cui)
                all_synonyms.extend(synonyms)

            # Clean synonyms
            clean_syns = self.clean_synonyms(all_synonyms)
            if not clean_syns:
                clean_syns = [label.lower()]  # Use original label as fallback

            # Map to ITEMIDs
            itemids = self.map_lab_synonyms_to_itemids(clean_syns + [label])

            if itemids:
                entry = {
                    "canonical": label.lower(),
                    "cuis": cuis[:2],
                    "surface_forms": clean_syns,
                    "db_links": {"labs": {"itemids": itemids}},
                    "provenance": {"original_label": label, "mimic_count": int(count)},
                }
                lexicon_entries.append(entry)
                logger.info(f"✅ Mapped {label} -> {len(itemids)} ITEMIDs")
            else:
                logger.warning(f"❌ No ITEMIDs found for {label}")

        return lexicon_entries

    def process_drugs(self, drug_file: str) -> List[Dict]:
        """Process drug file and create lexicon entries."""
        logger.info(f"Processing drugs from {drug_file}")

        # Read drug data
        df = pd.read_csv(drug_file)
        lexicon_entries = []

        for _, row in df.iterrows():
            drug = row["DRUG"]
            count = row["n"]

            logger.info(f"Processing drug: {drug} (count: {count})")

            # Find CUIs
            cuis = self.find_drug_cuis(drug)
            if not cuis:
                logger.warning(f"No CUIs found for drug: {drug}")
                continue

            # Get synonyms for first CUI
            all_synonyms = []
            for cui in cuis[:2]:  # Limit to first 2 CUIs
                synonyms = self.get_synonyms_for_cui(cui)
                all_synonyms.extend(synonyms)

            # Clean synonyms
            clean_syns = self.clean_synonyms(all_synonyms)
            if not clean_syns:
                clean_syns = [drug.lower()]  # Use original drug as fallback

            # Map to drug strings
            drug_strings = self.map_drug_synonyms_to_drugs(clean_syns + [drug])

            if drug_strings:
                entry = {
                    "canonical": drug.lower(),
                    "cuis": cuis[:2],
                    "surface_forms": clean_syns,
                    "db_links": {"drugs": {"drug_strings": drug_strings}},
                    "provenance": {"original_drug": drug, "mimic_count": int(count)},
                }
                lexicon_entries.append(entry)
                logger.info(f"✅ Mapped {drug} -> {len(drug_strings)} drug strings")
            else:
                logger.warning(f"❌ No drug strings found for {drug}")

        return lexicon_entries


def main():
    """Main function."""
    # Paths
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent.parent

    umls_db_path = root_dir / "db" / "umls.db"
    mimic_db_path = root_dir / "db" / "database.db"

    lab_file = script_dir / "filtered" / "top-lab_limit100.csv"
    drug_file = script_dir / "filtered" / "top-drugs_limit100.csv"

    # Output paths
    output_dir = script_dir / "filtered" / "lexicon_entries"
    output_dir.mkdir(exist_ok=True)

    lab_output = output_dir / "lab_lexicon.json"
    drug_output = output_dir / "drug_lexicon.json"
    combined_output = output_dir / "combined_lexicon.json"

    # Verify files exist
    for path in [umls_db_path, mimic_db_path, lab_file, drug_file]:
        if not path.exists():
            logger.error(f"Required file not found: {path}")
            return 1

    # Initialize mapper
    mapper = LabDrugMapper(str(umls_db_path), str(mimic_db_path))

    try:
        mapper.connect_databases()

        # Process labs
        lab_entries = mapper.process_labs(str(lab_file))
        with open(lab_output, "w") as f:
            json.dump(lab_entries, f, indent=2)
        logger.info(f"Lab lexicon saved to {lab_output} ({len(lab_entries)} entries)")

        # Process drugs
        drug_entries = mapper.process_drugs(str(drug_file))
        with open(drug_output, "w") as f:
            json.dump(drug_entries, f, indent=2)
        logger.info(
            f"Drug lexicon saved to {drug_output} ({len(drug_entries)} entries)"
        )

        # Combine all entries
        all_entries = lab_entries + drug_entries
        with open(combined_output, "w") as f:
            json.dump(all_entries, f, indent=2)
        logger.info(
            f"Combined lexicon saved to {combined_output} ({len(all_entries)} entries)"
        )

        logger.info("✅ Lab and drug mapping completed successfully!")

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return 1
    finally:
        mapper.close_connections()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
