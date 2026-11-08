"""Core unit tests for med-rag."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

# Mock litellm before importing llm/main so tests can run without it installed
sys.modules["litellm"] = MagicMock()
sys.modules["litellm"].acompletion = MagicMock()
sys.modules["litellm"].aembedding = MagicMock()
sys.modules["litellm"].enable_cache = MagicMock()

sys.modules["dotenv"] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()

# Mock logging_setup
sys.modules["logging_setup"] = MagicMock()
sys.modules["logging_setup"].setup_logging = MagicMock()
sys.modules["logging_setup"].get_logger = MagicMock(return_value=MagicMock())

# Mock tqdm
sys.modules["tqdm"] = MagicMock()
sys.modules["tqdm"].tqdm = MagicMock(side_effect=lambda iterable, **kwargs: iterable)

# Ensure the repository root is on the path so `llm` and `main` can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestParseFile(unittest.TestCase):
    """Tests for llm.parse_file behavior."""

    def test_parse_file_valid_sections(self):
        """parse_file should parse sections delimited by [SectionName] headers."""
        from llm import parse_file

        content = """[Section One]
content for section one

[Section Two]
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
            # parse_file includes the [Section Name] header in content
            self.assertIn("content for section one", result["Section One"])
            self.assertIn("content for section two", result["Section Two"])
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


class TestExtractSqlFromResponse(unittest.TestCase):
    """Tests for extract_sql_from_response behavior."""

    def test_extract_sql_from_code_block(self):
        """extract_sql_from_response should find SQL inside ```sql blocks."""
        from llm import extract_sql_from_response

        response = """Here is the query:
```sql
SELECT * FROM patients WHERE id = 1;
```
Done."""
        result = extract_sql_from_response(response)
        self.assertIsNotNone(result)
        self.assertIn("SELECT", result)
        self.assertIn("patients", result)

    def test_extract_sql_from_generic_code_block(self):
        """extract_sql_from_response should fall back to generic ``` blocks."""
        from llm import extract_sql_from_response

        response = """Query:
```
SELECT name FROM doctors;
```
"""
        result = extract_sql_from_response(response)
        self.assertIsNotNone(result)
        self.assertIn("SELECT", result)

    def test_extract_sql_no_sql(self):
        """extract_sql_from_response should return None when no SQL is present."""
        from llm import extract_sql_from_response

        response = "No SQL here, just text."
        result = extract_sql_from_response(response)
        self.assertIsNone(result)


class TestQueryErrorPaths(unittest.TestCase):
    """Tests for query() error handling and log writing."""

    def setUp(self):
        self.log_calls = []

    def _make_log_fn(self):
        def log_fn(*args, **kwargs):
            self.log_calls.append((args, kwargs))
        return log_fn

    def test_query_invalid_sql_calls_log_fn(self):
        """query() with invalid SQL should call log_fn and return None."""
        from main import query

        log_fn = self._make_log_fn()
        result = query("SELECT * FROM nonexistent_table WHERE 1=1", log_fn=log_fn)

        self.assertIsNone(result)
        self.assertGreaterEqual(len(self.log_calls), 1)
        # The first arg should contain "Error:"
        first_args = self.log_calls[0][0]
        self.assertTrue(any("Error" in str(a) for a in first_args))

    def test_query_nonexistent_db_calls_log_fn(self):
        """query() with nonexistent DB path should call log_fn and return None."""
        from main import query, db_path as orig_db_path

        log_fn = self._make_log_fn()
        # Override db_path to a nonexistent path
        import main
        main.db_path = "/nonexistent/path/to/database.db"
        try:
            result = query("SELECT 1", log_fn=log_fn, timeout=1)
        finally:
            main.db_path = orig_db_path

        self.assertIsNone(result)
        self.assertGreaterEqual(len(self.log_calls), 1)

    def test_query_valid_sql_returns_results(self):
        """query() with valid SQL on an in-memory DB should return results."""
        import sqlite3
        import os

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        try:
            conn = sqlite3.connect(tmp.name)
            conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO t VALUES (1, 'foo')")
            conn.commit()
            conn.close()

            # Temporarily override db_path
            import main
            orig_db_path = main.db_path
            main.db_path = tmp.name
            try:
                log_fn = self._make_log_fn()
                result = main.query("SELECT * FROM t", log_fn=log_fn)
                self.assertIsNotNone(result)
                self.assertEqual(len(result), 1)
                self.assertEqual(len(self.log_calls), 0)
            finally:
                main.db_path = orig_db_path
                os.unlink(tmp.name)
        except Exception:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise


if __name__ == "__main__":
    unittest.main()
