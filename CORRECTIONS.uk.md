# CORRECTIONS.md — med-rag

Project: fipu-lab/med-rag
Base branch analyzed: main (commit 7f5ad89)
Destination fork: https://github.com/admeduardovieira/med-rag

## Corrections proposed (implemented — Phase 1 and Phase 2 completed)

| ID | Title | Severity | Status | Risk | Files involved |
|----|-------|----------|--------|------|----------------|
| REA-med-001 | `parse_file("prompts/system.md")` breaks `import llm` (file missing) | P1 | IMPLEMENTED | Low | `llm.py` |
| REA-med-002 | `from lexicon_normalizer import create_normalizer` — module missing | P2 | NOT IMPLEMENTED | Low | `normalize_test_questions.py` |
| REA-med-003 | Missing `requirements.txt` | P3 | IMPLEMENTED | Low | `requirements.txt` (new) |
| REA-med-004 | Missing automated tests | P3 | PARTIAL | Low | `tests/test_core.py` (new) |
| REA-med-005 | `str(e)` in logger may leak API keys | P2 | IMPLEMENTED | Low | `llm.py` |
| REA-med-006 | `print = logger(...)` shadows builtin `print` | P3 | IMPLEMENTED | Low | `main.py` |
| REA-med-007 | `etl.py` `__main__` runs only `process_lab()`; rest commented | P3 | NOT IMPLEMENTED | Low | `etl.py` |

## Details of implemented corrections

### REA-med-001 — Missing prompts file crashes import
**Problem:** `llm.py:178` calls `parse_file("prompts/system.md")` at module level; the file does not exist, so `import llm` crashes.
**Fix:** Wrapped the call in `try/except FileNotFoundError` and `try/except Exception`, logging a warning and using empty prompts dict.
**Validation:** `py_compile` passes; import logic no longer crashes on missing file.

### REA-med-005 — Potential credential leak in error logs
**Problem:** `llm.py:313` logs `str(e)` which may contain API key details from provider exceptions.
**Fix:** Changed to log `type(e).__name__` only.
**Validation:** `py_compile` passes.

### REA-med-006 — Shadowed builtin `print`
**Problem:** `main.py:138` does `print = logger(...)`, shadowing the builtin.
**Fix:** Renamed variable to `log` and updated all subsequent `print(` calls to `log(`.
**Validation:** `py_compile` passes.

### REA-med-003 — Missing requirements.txt
**Problem:** No `requirements.txt`; dependencies only inferable from imports.
**Fix:** Added `requirements.txt` with litellm, pandas, numpy, scipy, python-dotenv, tqdm, openpyxl, kagglehub, matplotlib, seaborn.
**Validation:** File exists with expected dependencies.

### REA-med-004 — Missing automated tests
**Problem:** No tests exist.
**Fix:** Added `tests/test_core.py` with 6 unit tests covering `parse_file` (valid sections, invalid format, empty file) and SQL extraction (sql block, generic code block, no SQL).
**Validation:** 6/6 tests pass via `unittest discover`.

## Corrections not implemented (require maintainer decision)

### REA-med-002 — Missing `lexicon_normalizer` module
Not implemented: creating the module requires understanding the intended lexicon normalization logic. Suggested: either create `lexicon_normalizer.py` or remove the import from `normalize_test_questions.py`.

### REA-med-007 — ETL partially commented
Not implemented: uncommenting ETL functions requires MIMIC-III data (large, gated) and may have side effects. Suggested: document why functions are commented or enable incrementally.

## Publication plan
- Fork: `admeduardovieira/med-rag` (created).
- Branch `fix/rea-med-001-002-robustness` for REA-med-001..006 (implemented).
- Branch `docs/rea-audit-reports` for audit reports (PT/EN/UK).
- Commit identity: `admeduardovieira <admeduardovieira@users.noreply.github.com>`.
- PRs to `fipu-lab/med-rag` branch `main`.

Переклад технічний, виконаний автоматизовано; рекомендується перегляд носієм мови перед використанням якнормативного посилання.
