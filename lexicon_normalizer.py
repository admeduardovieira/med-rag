import json
import re
from typing import Dict, List, Tuple, Optional, Set
from difflib import SequenceMatcher
from logging_setup import get_logger

logger = get_logger(__name__)


class LexiconNormalizer:
    """
    Enhanced medical lexicon normalizer with two approaches:

    Option 1: Pre-normalize questions by detecting surface forms and annotating with codes
    Option 2: Generate mini glossary with term mappings

    Features:
    - Fuzzy matching for typos and variations
    - Question type filtering (only medical tables)
    - Relaxed word boundaries
    - Case-insensitive matching
    """

    def __init__(self, lexicon_path: str, fuzzy_threshold: float = 0.85):
        """Initialize normalizer with lexicon file."""
        self.lexicon_path = lexicon_path
        self.fuzzy_threshold = fuzzy_threshold
        self.surface_form_map = {}
        self.glossary_entries = {}

        # Keywords that indicate medical table queries
        self.medical_keywords = {
            "diagnosis",
            "diagnoses",
            "diagnosed",
            "icd9",
            "icd-9",
            "procedure",
            "procedures",
            "surgery",
            "operation",
            "drug",
            "drugs",
            "medication",
            "prescription",
            "prescriptions",
            "lab",
            "labs",
            "laboratory",
            "test",
            "tests",
            "results",
            "itemid",
            "formulary",
        }

        self._load_lexicon()
        self._build_lookup_structures()

    def _load_lexicon(self):
        """Load the combined lexicon from JSON file."""
        logger.info(f"Loading lexicon from {self.lexicon_path}")
        try:
            with open(self.lexicon_path, "r") as f:
                self.lexicon = json.load(f)
            logger.info(f"Loaded {len(self.lexicon)} lexicon entries")
        except Exception as e:
            logger.error(f"Failed to load lexicon: {e}")
            raise

    def _build_lookup_structures(self):
        """Build efficient lookup structures for surface forms and glossary."""
        logger.info("Building surface form lookup structures and glossary...")

        for entry in self.lexicon:
            surface_forms = entry.get("surface_forms", [])
            canonical = entry.get("canonical", "")
            db_links = entry.get("db_links", {})

            # Add canonical form as a surface form if it exists
            if canonical:
                surface_forms = surface_forms + [canonical]

            # Build surface form map for exact matching
            for surface_form in surface_forms:
                if (
                    surface_form and len(surface_form.strip()) > 2
                ):  # Skip very short terms
                    # Store in lowercase for case-insensitive lookup
                    key = surface_form.lower().strip()

                    # Store the mapping with original case and db_links
                    self.surface_form_map[key] = {
                        "original": surface_form,
                        "canonical": canonical,
                        "db_links": db_links,
                        "length": len(surface_form),  # For longest match
                    }

            # Build glossary entries for option 2
            if canonical and db_links:
                # Create simplified codes for glossary
                codes = []
                if "diagnoses" in db_links:
                    icd9_codes = db_links["diagnoses"].get("icd9_exact", [])
                    if icd9_codes:
                        codes.append(
                            f"diagnoses.ICD9_CODE IN ({','.join(repr(c) for c in icd9_codes)})"
                        )

                if "procedures" in db_links:
                    icd9_codes = db_links["procedures"].get("icd9_exact", [])
                    if icd9_codes:
                        codes.append(
                            f"procedures.ICD9_CODE IN ({','.join(repr(c) for c in icd9_codes)})"
                        )

                if "labs" in db_links:
                    itemids = db_links["labs"].get("itemids", [])
                    if itemids:
                        codes.append(f"lab.ITEMID IN ({','.join(map(str, itemids))})")

                if "drugs" in db_links:
                    drug_strings = db_links["drugs"].get("drug_strings", [])
                    if drug_strings:
                        codes.append(
                            f"prescriptions.DRUG IN ({','.join(repr(d) for d in drug_strings)})"
                        )

                if codes:
                    for surface_form in surface_forms:
                        if surface_form and len(surface_form.strip()) > 2:
                            self.glossary_entries[surface_form.lower().strip()] = {
                                "canonical": canonical,
                                "codes": codes,
                            }

        logger.info(
            f"Built lookup structures for {len(self.surface_form_map)} surface forms and {len(self.glossary_entries)} glossary entries"
        )

    def _is_medical_question(self, question: str) -> bool:
        """Check if question is about medical tables (diagnoses, procedures, labs, drugs)."""
        question_lower = question.lower()

        # Check for medical keywords
        for keyword in self.medical_keywords:
            if keyword in question_lower:
                return True

        # Check for table names
        table_indicators = ["diagnoses", "procedures", "prescriptions", "lab"]
        for indicator in table_indicators:
            if indicator in question_lower:
                return True

        return False

    def _fuzzy_match(self, term1: str, term2: str) -> float:
        """Calculate fuzzy match similarity between two terms."""
        return SequenceMatcher(None, term1.lower(), term2.lower()).ratio()

    def _find_fuzzy_matches(self, text: str) -> List[Tuple[int, int, Dict]]:
        """Find matches using fuzzy matching for typos and variations."""
        text_lower = text.lower()
        words = re.findall(r"\b\w+(?:\s+\w+)*\b", text_lower)
        matches = []

        for word_phrase in words:
            # Try different phrase lengths (1-4 words)
            word_list = word_phrase.split()
            for i in range(len(word_list)):
                for j in range(
                    i + 1, min(i + 5, len(word_list) + 1)
                ):  # Up to 4-word phrases
                    phrase = " ".join(word_list[i:j])

                    # Find best fuzzy match
                    best_match = None
                    best_score = 0

                    for surface_key, surface_info in self.surface_form_map.items():
                        similarity = self._fuzzy_match(phrase, surface_key)
                        if (
                            similarity >= self.fuzzy_threshold
                            and similarity > best_score
                        ):
                            best_score = similarity
                            best_match = surface_info

                    if best_match:
                        # Find position in original text
                        start_pos = text_lower.find(phrase)
                        if start_pos != -1:
                            end_pos = start_pos + len(phrase)
                            matches.append((start_pos, end_pos, best_match))

        return matches

    def _find_matches(self, text: str) -> List[Tuple[int, int, Dict]]:
        """
        Find all surface form matches using exact and fuzzy matching.

        Returns list of (start_pos, end_pos, match_info) tuples.
        """
        text_lower = text.lower()
        matches = []

        # First pass: exact matches
        for surface_form_lower, match_info in self.surface_form_map.items():
            start_pos = 0
            while True:
                pos = text_lower.find(surface_form_lower, start_pos)
                if pos == -1:
                    break

                end_pos = pos + len(surface_form_lower)

                # Relaxed word boundary check
                if self._is_relaxed_word_boundary_match(
                    text, pos, end_pos, surface_form_lower
                ):
                    matches.append((pos, end_pos, match_info))

                start_pos = pos + 1

        # Second pass: fuzzy matches (only if exact matches are few)
        if (
            len(matches) < 3
        ):  # Only do fuzzy matching if we didn't find many exact matches
            fuzzy_matches = self._find_fuzzy_matches(text)
            matches.extend(fuzzy_matches)

        # Sort by position, then by length (longest first) for conflict resolution
        matches.sort(key=lambda x: (x[0], -x[2]["length"]))

        # Remove overlapping matches, keeping longest/highest quality ones
        filtered_matches = []
        for start, end, info in matches:
            # Check if this match overlaps with any existing match
            overlaps = False
            for existing_start, existing_end, _ in filtered_matches:
                if not (end <= existing_start or start >= existing_end):
                    overlaps = True
                    break

            if not overlaps:
                filtered_matches.append((start, end, info))

        return sorted(filtered_matches)  # Sort by position

    def _is_word_boundary_match(self, text: str, start: int, end: int) -> bool:
        """Check if match occurs at word boundaries (original strict version)."""
        # Check character before start
        if start > 0 and text[start - 1].isalnum():
            return False

        # Check character after end
        if end < len(text) and text[end].isalnum():
            return False

        return True

    def _is_relaxed_word_boundary_match(
        self, text: str, start: int, end: int, surface_form: str
    ) -> bool:
        """
        Relaxed word boundary matching that allows partial matches in some cases.

        This helps with medical terms that might be part of compound words or
        have variations in spelling/spacing.
        """
        # For single characters or very short terms, be strict
        if len(surface_form) <= 2:
            return self._is_word_boundary_match(text, start, end)

        # For medical terms, allow some flexibility
        # Check if we're inside a word but at reasonable boundaries
        before_char = text[start - 1] if start > 0 else " "
        after_char = text[end] if end < len(text) else " "

        # Allow matches that start after certain characters
        allowed_before = {" ", "-", "(", "[", ",", ".", "/", "\\", "_"}
        allowed_after = {
            " ",
            "-",
            ")",
            "]",
            ",",
            ".",
            "/",
            "\\",
            "_",
            "s",
            "e",
            "d",
        }  # Allow plural/past tense

        if before_char in allowed_before or start == 0:
            if after_char in allowed_after or end == len(text):
                return True

        # For common medical abbreviations, be more flexible
        if len(surface_form) >= 4 and surface_form.replace(" ", "").isalpha():
            # Check if it's a reasonable word boundary
            if not before_char.isalpha() or not after_char.isalpha():
                return True

        return False

    def _format_annotation(self, db_links: Dict, canonical: str) -> str:
        """Format the annotation string for detected surface forms."""
        annotations = []

        # Handle diagnoses
        if "diagnoses" in db_links:
            icd9_codes = db_links["diagnoses"].get("icd9_exact", [])
            if icd9_codes:
                if len(icd9_codes) == 1:
                    annotations.append(f"ICD9:{icd9_codes[0]}")
                else:
                    codes_str = ",".join(icd9_codes)
                    annotations.append(f"ICD9:({codes_str})")

        # Handle procedures
        if "procedures" in db_links:
            icd9_codes = db_links["procedures"].get("icd9_exact", [])
            if icd9_codes:
                if len(icd9_codes) == 1:
                    annotations.append(f"PROC_ICD9:{icd9_codes[0]}")
                else:
                    codes_str = ",".join(icd9_codes)
                    annotations.append(f"PROC_ICD9:({codes_str})")

        # Handle drugs
        if "drugs" in db_links:
            drug_strings = db_links["drugs"].get("drug_strings", [])
            if drug_strings:
                if len(drug_strings) == 1:
                    annotations.append(f"DRUG:{drug_strings[0]}")
                else:
                    drugs_str = ",".join(drug_strings)
                    annotations.append(f"DRUG:({drugs_str})")

        # Handle lab items
        if "labs" in db_links:
            itemids = db_links["labs"].get("itemids", [])
            if itemids:
                if len(itemids) == 1:
                    annotations.append(f"ITEMID:{itemids[0]}")
                else:
                    itemids_str = ",".join(map(str, itemids))
                    annotations.append(f"ITEMID:({itemids_str})")

        if annotations:
            annotation_str = " | ".join(annotations)
            return f"{canonical} [{annotation_str}]"
        else:
            return canonical

    def normalize_question(self, question: str, approach: str = "option1") -> str:
        """
        Normalize a question using the specified approach.

        Args:
            question: The natural language question to normalize
            approach: "option1" (pre-normalize) or "option2" (mini glossary)

        Returns:
            Normalized question with annotations or glossary
        """
        # Only normalize medical questions
        if not self._is_medical_question(question):
            return question

        if approach == "option1":
            return self._normalize_option1(question)
        elif approach == "option2":
            return self._normalize_option2(question)
        else:
            raise ValueError(f"Unknown approach: {approach}")

    def _normalize_option1(self, question: str) -> str:
        """
        Option 1: Pre-normalize by detecting surface forms and annotating with codes.
        """
        matches = self._find_matches(question)

        if not matches:
            return question

        # Build normalized question by replacing matches
        result = []
        last_end = 0

        for start, end, match_info in matches:
            # Add text before this match
            result.append(question[last_end:start])

            # Add normalized form with annotation
            canonical = match_info["canonical"]
            db_links = match_info["db_links"]
            annotation = self._format_annotation(db_links, canonical)

            result.append(annotation)
            last_end = end

        # Add remaining text
        result.append(question[last_end:])

        normalized = "".join(result)

        # Log the normalization if changes were made
        if normalized != question:
            logger.info(f"Normalized (Option 1): '{question}' -> '{normalized}'")

        return normalized

    def _normalize_option2(self, question: str) -> str:
        """
        Option 2: Append mini glossary without rewriting the question.
        """
        matches = self._find_matches(question)

        if not matches:
            return question

        # Build glossary entries
        glossary_items = []
        seen_terms = set()

        for start, end, match_info in matches:
            original_term = question[start:end].lower()
            canonical = match_info["canonical"]

            # Avoid duplicates
            if original_term not in seen_terms:
                seen_terms.add(original_term)

                # Get SQL hints from glossary
                if original_term in self.glossary_entries:
                    entry = self.glossary_entries[original_term]
                    glossary_items.append(
                        f'"{original_term}" ≡ "{entry["canonical"]}" → {" OR ".join(entry["codes"])}'
                    )

        if glossary_items:
            glossary = "\n\nGlossary:\n- " + "\n- ".join(glossary_items)
            result = question + glossary
            logger.info(f"Added glossary to: '{question}'")
            return result

        return question


def create_normalizer(
    lexicon_path: str = "synonyms/seed-items/filtered/lexicon_entries/combined_lexicon.json",
    fuzzy_threshold: float = 0.85,
) -> LexiconNormalizer:
    """Factory function to create a normalizer instance."""
    return LexiconNormalizer(lexicon_path, fuzzy_threshold)


# Example usage and testing
if __name__ == "__main__":
    # Test the enhanced normalizer
    normalizer = create_normalizer()

    # Test cases from actual dataset
    test_questions = [
        "give me the number of patients who have been diagnosed with tobacco use disorder.",
        "how many patients were admitted with a heart attack in 2008?",
        "How many patients have a diphenhydramine prescription?",
        "how many patients used the drug name capso fungin?",  # typo test
        "find the number of patients diagnosed with mitral valve disorders.",
        "how many patients use the drug zyrtec?",
        "give me the number of patients who had single internal mammary-coronary artery bypass.",
        "how many patients were born before the year 2060?",  # non-medical test
        "List patients with hypertension and diabetes",
        "Show me all the hemoglobin lab results",
    ]

    print("=== Testing Enhanced Lexicon Normalizer ===\n")

    for question in test_questions:
        print(f"Original: {question}")

        # Test Option 1 (pre-normalize)
        normalized1 = normalizer.normalize_question(question, approach="option1")
        print(f"Option 1: {normalized1}")

        # Test Option 2 (mini glossary)
        normalized2 = normalizer.normalize_question(question, approach="option2")
        print(f"Option 2: {normalized2}")

        print("-" * 80)
        print()
