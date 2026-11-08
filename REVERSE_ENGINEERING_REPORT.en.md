# REVERSE_ENGINEERING_REPORT — med-rag

## A. General diagnosis

### Architecture identified
Python project for LLM evaluation on two clinical workflows: NL2SQL (natural language to SQL over EHRs MIMIC-III/MIMICSQL) and RAG-QA (question answering with retrieval-augmented generation on synthetic patient records). Layered architecture:

- `main.py`: orchestrates batched experiments, calls `llm.ai_query` per model, executes SQL on SQLite (`db/database_full.db`), prints results.
- `llm.py`: LLM client via LiteLLM (`acompletion`, `aembedding`), support for 9 models (DeepSeek, Llama, GPT, Mixtral, Qwen, BioMistral), SQL extraction from responses, retry with backoff, disk cache for embeddings.
- `etl.py`: ETL of MIMIC-III (demographic, diagnoses, procedures, prescriptions, lab) to CSV and then SQLite.
- `ec.py`: SQL error classifier (SCHEMA_MISMATCH, JOIN_ERRORS, STRING_MISMATCH, INCORRECT_AGGREGATION, etc.) comparing predicted vs true SQL.
- `analyze_rag_results.py`, `nl2sql_statistical_analysis.py`: statistical analysis of results (pairwise t-tests, performance matrix).
- `complete_patient_answers.py`: completes synthetic patient answers with LLM.
- `normalize_test_questions.py`, `merge_normalized_questions.py`: test question normalization.

### Technologies and dependencies
- Python (version not explicitly declared; no Pipfile)
- Runtime dependencies inferred: `litellm`, `pandas`, `numpy`, `scipy`, `python-dotenv`, `tqdm`, `openpyxl`, `kagglehub`, `matplotlib`, `seaborn`
- No `requirements.txt`, no `setup.py`/`pyproject.toml`, no Pipfile
- No CI configured

### Maintenance state
Last commit: `7f5ad89 Update README.md`. Upstream default branch: `main`. Repository: `https://github.com/fipu-lab/med-rag`. Active history (several commits on lexicon, normalization, ETL).

### Existing testing mechanisms
No automated tests found. No `tests/` folder, no `test_*.py`, no pytest configuration.

### Investigation limitations
- litellm, pandas and other dependencies not installed; direct `import llm` execution not tested (confirmed via static reading that `prompts/system.md` does not exist).
- No LLM calls performed (require API keys and cost money).
- REA 6.7.0 not operational in this environment; static analysis + terminal only.

## B. Problems found

| ID | Title | Severity | Status | Location |
|----|-------|----------|--------|----------|
| REA-med-001 | `parse_file("prompts/system.md")` breaks `import llm` (file missing) | P1 | CONFIRMED | `llm.py:178` |
| REA-med-002 | `from lexicon_normalizer import create_normalizer` — module missing | P2 | CONFIRMED | `normalize_test_questions.py:8` |
| REA-med-003 | Missing `requirements.txt` | P3 | CONFIRMED | repo root |
| REA-med-004 | Missing automated tests | P3 | CONFIRMED | repo root |
| REA-med-005 | `logger.error(..., str(e))` may leak API keys | P2 | PROBABLE | `llm.py:313` |
| REA-med-006 | `print = logger(...)` shadows builtin `print` | P3 | CONFIRMED | `main.py:138` |
| REA-med-007 | `etl.py` `__main__` runs only `process_lab()`; rest commented | P3 | CONFIRMED | `etl.py:229-236` |

### Details of confirmed problems

**REA-med-001 (P1, CONFIRMED)**: `llm.py:178` calls `parse_file("prompts/system.md")` at module level. The file `prompts/system.md` does not exist in the repository (verified: not found, not in archive/ or any subdirectory). This causes `import llm` to raise `FileNotFoundError`, breaking all project functionality. It is an import bug preventing any use of the project.

Evidence: `llm.py:178` + absence of `prompts/system.md`.

**REA-med-002 (P2, CONFIRMED)**: `normalize_test_questions.py:8` imports `from lexicon_normalizer import create_normalizer`, but module `lexicon_normalizer` does not exist in the repository. The script cannot run.

**REA-med-003 (P3, CONFIRMED)**: No `requirements.txt`. Dependencies can only be inferred from `import` statements in sources.

**REA-med-004 (P3, CONFIRMED)**: No automated tests.

**REA-med-006 (P3, CONFIRMED)**: `main.py:138` does `print = logger(...)`, shadowing the builtin `print`. All subsequent `print` calls use the logger, which is confusing and may break code expecting the builtin.

**REA-med-007 (P3, CONFIRMED)**: `etl.py:229-236` calls only `process_lab()` in `__main__`; all other processing functions are commented out.

### Details of the probable problem

**REA-med-005 (P2, PROBABLE)**: `llm.py:313` does `logger.error("Model %s request failed: %s", model, str(e))`. If `e` contains details from a LiteLLM/provider authentication exception, the error message may include API key or token fragments, leaking credentials to logs.

## C. Recurring problems
No recurring public issues found for this repository (checked via GitHub API).

## D. Undocumented errors
All items in section B are problems not previously documented by the project.

## E. Performance
`main.py` processes up to 1000 test cases in batches of 5, with async LLM calls (`asyncio.gather`). No significant blocking operations besides network calls. `query()` in `main.py` uses `threading.Timer` for SQL timeout, which is adequate.

## F. Technical improvements
- Add `try/except` when loading `prompts/system.md` (REA-med-001, implemented).
- Create `prompts/system.md` or remove import if unused (REA-med-001).
- Create module `lexicon_normalizer` or remove import (REA-med-002).
- Add `requirements.txt` (REA-med-003, implemented).
- Add automated tests (REA-med-004, partially implemented).
- Log exception type instead of `str(e)` (REA-med-005, implemented).
- Rename shadowed `print` variable (REA-med-006, implemented).
- Uncomment ETL functions or document why commented (REA-med-007).

## G. Execution plan
Independent corrections:
1. REA-med-001, REA-med-005, REA-med-006 — `llm.py` and `main.py` (low risk, done).
2. REA-med-003 — `requirements.txt` (low risk, done).
3. REA-med-004 — tests (partially done, core logic tests).
4. REA-med-002 — create/remove `lexicon_normalizer` (not done; needs more investigation).
5. REA-med-007 — ETL (not done; needs maintainer decision).

## H. Expected outcome
Make the project importable and runnable without crashes, avoid credential leaks, establish reproducible dependencies and test base.

**Tools used:** git, gh, PowerShell/terminal, Python 3.12 (py_compile, unittest), static code inspection.  
**Limitation:** REA 6.7.0 not operational; litellm/pandas not installed.  
**Environment:** Windows, PowerShell 5.1, `C:\Users\User\audit-repos\med-rag` (clone of upstream, branch `main`, commit `7f5ad89`).
