# REVERSE_ENGINEERING_REPORT — med-rag

Примітка: переклад технічний, виконаний з автоматичною допомогою; рекомендується перегляд rodsnym мовцем перед використанням як нормативного довідника.

## A. Загальний діагноз

### Виявлена архітектура
Проєкт Python для оцінки LLM на двох клінічних потоках: NL2SQL ( природна мова до SQL над EHR MIMIC-III/MIMICSQL) та RAG-QA (question answering з генерацією, збільшеною через пошук, над синтетичними записами). Архітектура в шарах:

- `main.py`: оркеструє пакетні експерименти, викликає `llm.ai_query` для кожної моделі, виконує SQL у SQLite (`db/database_full.db`), виводить результати.
- `llm.py`: клієнт LLM через LiteLLM (`acompletion`, `aembedding`), підтримка 9 моделей (DeepSeek, Llama, GPT, Mixtral, Qwen, BioMistral), вилучення SQL з відповідей, повтор з backoff, кеш embeddings на диску.
- `etl.py`: ETL MIMIC-III (demографія, діагнози, процедури, рецепти, огляди) до CSV та потім SQLite.
- `ec.py`: класифікатор помилок SQL (SCHEMA_MISMATCH, JOIN_ERRORS, STRING_MISMATCH, INCORRECT_AGGREGATION тощо) порівняння передбаченого SQL з істиною.
- `analyze_rag_results.py`, `nl2sql_statistical_analysis.py`: статистичний аналіз результатів (попарні t-тести, матриця продуктивності).
- `complete_patient_answers.py`: завершує синтетичні відповіді пацієнтів через LLM.
- `normalize_test_questions.py`, `merge_normalized_questions.py`: нормалізація тестових питань.

### Технології та залежності
- Python (версія не оголошена явно; Pipfile відсутній)
- Залежності часу виконання, виведені з імпортів: `litellm`, `pandas`, `numpy`, `scipy`, `python-dotenv`, `tqdm`, `openpyxl`, `kagglehub`, `matplotlib`, `seaborn`
- Немає `requirements.txt`, немає `setup.py`/`pyproject.toml`, немає Pipfile
- Немає CI

### Стан обслуговування
Останній коміт: `7f5ad89 Update README.md`. Гał diff гałку upstream: `main`. Репозиторій: `https://github.com/fipu-lab/med-rag`. Активна історія (декілька комітів про lexicon, нормалізацію, ETL).

### Існуючі механізми тестування
Автоматизованих тестів не знайдено. Немає папки `tests/`, немає `test_*.py`, немає конфігурації pytest.

### Обмеження дослідження
- litellm, pandas та інші залежності не встановлені; прямой `import llm` не протестовано (підтверджено через статичне читання, що `prompts/system.md` не існує).
- Виклики LLM не виконані (потребують ключів API та коштів).
- REA 6.7.0 не операційний в цьому середовищі; статичний аналіз + термінал.

## B. Виявлені проблеми

| ID | Назва | Середність | Статус | Місцезнаходження |
|----|-------|------------|--------|------------------|
| REA-med-001 | `parse_file("prompts/system.md")` ламає `import llm` (файл відсутній) | P1 | CONFIRMED | `llm.py:178` |
| REA-med-002 | `from lexicon_normalizer import create_normalizer` — модуль відсутній | P2 | CONFIRMED | `normalize_test_questions.py:8` |
| REA-med-003 | Відсутній `requirements.txt` | P3 | CONFIRMED | корінь репозиторію |
| REA-med-004 | Відсутні автоматизовані тести | P3 | CONFIRMED | корінь репозиторію |
| REA-med-005 | `logger.error(..., str(e))` може викликати ключі API | P2 | PROVÁBLE | `llm.py:313` |
| REA-med-006 | `print = logger(...)` приховує вбудований `print` | P3 | CONFIRMED | `main.py:138` |
| REA-med-007 | `etl.py` `__main__` запускає лише `process_lab()`; решта закоментовано | P3 | CONFIRMED | `etl.py:229-236` |

### Деталі підтверджених проблем

**REA-med-001 (P1, CONFIRMED):** `llm.py:178` викликає `parse_file("prompts/system.md")` на рівні модуля. Файл `prompts/system.md` не існує в репозиторії (підтверджено: Test-Path = False, не знайдено в archive/ ani в жодному підкаталозі). Це призводить до того, що `import llm` викликає `FileNotFoundError` та ламає весь додаток. Це помилка імпорту, яка запобігає використанню будь-якої функціональності проєкту.

Докази: `llm.py:178` + відсутність `prompts/system.md`.

**REA-med-002 (P2, CONFIRMED):** `normalize_test_questions.py:8` імпортує `from lexicon_normalizer import create_normalizer`, але модуль `lexicon_normalizer` не існує в репозиторії. Скрипт не може бути виконаний.

**REA-med-003 (P3, CONFIRMED):** Немає `requirements.txt`. Залежності можна вивести лише з імпортів у вихідних кодах.

**REA-med-004 (P3, CONFIRMED):** Немає автоматизованих тестів.

**REA-med-006 (P3, CONFIRMED):** `main.py:138` робить `print = logger(...)`, приховуючи вбудований `print`. Усі подальші виклики `print` використовують логер, що є confusion і може ламати код, що очікує вбудований.

**REA-med-007 (P3, CONFIRMED):** `etl.py:229-236` викликає лише `process_lab()` в `__main__`; всі інші функції обробки (`process_demographic`, `process_diagnoses` тощо) закоментовані.

### Деталі проблемної проблеми

**REA-med-005 (P2, PROVÁBLE):** `llm.py:313` робить `logger.error("Model %s request failed: %s", model, str(e))`. Якщо `e` містить деталі винятку автентифікації LiteLLM/провайдера, повідомлення про помилку може включати частини ключів API або токенів, викриваючи облікові дані у логах.

## C. Повторні проблеми
Повторних публічних проблем не знайдено для цього репозиторію (перевірено через API GitHub).

## D. Невідомі помилки
Усі пункти розділу B — це недокументовані раніше проблеми проєкту.

## E. Продуктивність
`main.py` обробляє до 1000 тестових прикладів у пакетах по 5, з асинхронними викликами LLM (`asyncio.gather`). Немає значних блокуючих операцій крім викликів мережі. `query()` в `main.py` використовує `threading.Timer` для тайм-ауту SQL, що є достатнім.

## F. Технічні вдосконалення
- Додати `try/except` при завантаженні `prompts/system.md` (REA-med-001, реалізовано).
- Створити `prompts/system.md` або видалити імпорт якщо не використовується (REA-med-001).
- Створити модуль `lexicon_normalizer` або видалити імпорт (REA-med-002).
- Додати `requirements.txt` (REA-med-003, реалізовано).
- Додати автоматизовані тести (REA-med-004, реалізовано частично).
- Логувати тип винятку замість `str(e)` (REA-med-005, реалізовано).
- Перейменувати приховану змінну `print` (REA-med-006, реалізовано).
- Розкоментувати функції ETL або задокументувати чому вони закоментовані (REA-med-007).

## G. План виконання
Незалежні виправлення:
1. REA-med-001, REA-med-005, REA-med-006 — `llm.py` та `main.py` (низький ризик, зроблено).
2. REA-med-003 — `requirements.txt` (низький ризик, зроблено).
3. REA-med-004 — тести (зроблено частично, тест core logic).
4. REA-med-002 — створити/видалити `lexicon_normalizer` (не зроблено; потребує подальшого розслідування).
5. REA-med-007 — ETL (не зроблено; потребує рішення підтрижуючої).

## H. Очікуваний результат
Зробити проєкт імпортуватим і виконуваним без крахів, уникнути викриття облікових даних, स्थापіть базу залежностей та відтворюваності тестів.

**Інструменти, що використано:** git, gh, PowerShell/термінал, Python 3.12 (py_compile, unittest), статичний огляд.  
**Обмеження:** REA 6.7.0 не операційний; litellm/pandas не встановлені.  
**Середовище:** Windows, PowerShell 5.1, `C:\Users\User\audit-repos\med-rag` (клон upstream, гał diff гałку `main`, коміт `7f5ad89`).
