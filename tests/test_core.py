"""Core unit tests for med-rag."""

import os
import sys
import tempfile
import unittest

# Ensure the repository root is on the path so `llm` can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestParseFile(unittest.TestCase):
    """Tests for llm.parse_file behavior."""

    def test_parse_file_valid_sections(self):
        """parse_file should parse sections delimited by ## headers."""
        from llm import parse_file

        content = """## Section One
content for section one

## Section Two
content for section two
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name

        try:
            result = parse_file(path)
            self.assertIn("Section One", result)
            self.assertIn("Section Two", result)
            self.assertEqual(result["Section One"], "content for section one")
            self.assertEqual(result["Section Two"], "content for section two")
        finally:
            os.unlink(path)

    def test_parse_file_empty(self):
        """parse_file should return an empty dict for an empty file."""
        from llm import parse_file

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            path = f.name

        try:
            result = parse_file(path)
            self.assertEqual(result, {})
        finally:
            os.unlink(path)

    def test_parse_file_missing(self):
        """parse_file should raise FileNotFoundError for a missing file."""
        from llm import parse_file

        with self.assertRaises(FileNotFoundError):
            parse_file("/nonexistent/path/to/file.md")


class TestSqlExtraction(unittest.TestCase):
    """Tests for SQL extraction from LLM responses."""

    def test_extract_sql_from_code_block(self):
        """extract_sql should find SQL inside ```sql blocks."""
        from llm import extract_sql

        response = """Here is the query:
```sql
SELECT * FROM patients WHERE id = 1;
```
Done."""
        result = extract_sql(response)
        self.assertIsNotNone(result)
        self.assertIn("SELECT", result)
        self.assertIn("patients", result)

    def test_extract_sql_from_generic_code_block(self):
        """extract_sql should fall back to generic ``` blocks."""
        from llm import extract_sql

        response = """Query:
```
SELECT name FROM doctors;
```
"""
        result = extract_sql(response)
        self.assertIsNotNone(result)
        self.assertIn("SELECT", result)

    def test_extract_sql_no_sql(self):
        """extract_sql should return None when no SQL is present."""
        from llm import extract_sql

        response = "No SQL here, just text."
        result = extract_sql(response)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
