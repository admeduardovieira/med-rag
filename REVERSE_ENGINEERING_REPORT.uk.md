# REVERSE_ENGINEERING_REPORT — med-rag

## A. Загальний діагноз

### Виявлена архітектура
Проєкт Python для оцінки LLM на двох клінічних потоках: NL2SQL (природна мова до SQL над EHR MIMIC-III/MIMICSQL) та RAG-QA (question answering з пошуково-розширеною генерацією над синтетичними пацієнтськими записами). Shарована архітектура:

- `main.py`: оркеструє пакетні екерименти, викликає `llm.ai_query` для кожної моделі, виконує SQL у SQLite (`db/database_full.db`), виводить результати.
- `llm.py`: клієнт LLM через LiteLLM (`acompletion`, `aembedding`), підтримка 9 моделей (DeepSeek, Llama, GPT, Mixtral, Qwen, BioMistral), вилучення SQL з відповідей, повтор з відліком, кеш вбудовувань на диску.
- `etl.py`: ETL MIMIC-III (демографія, діагнози, процедури, рецепти, аналізи) до CSV та потім SQLite.
- `ec.py`: класифікатор помилок SQL (SCHEMA_MISMATCH, JOIN_ERRORS, STRING_MISMATCH, INCORRECT_AGGREGATION тощо), що порівнює передбачений та істинний SQL.
- `analyze_rag_results.py`, `nl2sql_statistical_analysis.py`: статистичний аналіз результатів (попарні t-тести, матриця продуктивності).
- `complete_patient_answers.py`: dovinishuje синітивні відповіді пацієнтів через LLM.
- `normalize_test_questions.py`, `merge_normalized_questions.py`: нормалізація питань тесту.

### Технології та залежності
- Python (версія не вказана явно; немає Pipfile)
- Залежності виконання виведено: `litellm`, `pandas`, `numpy`, `scipy`, `python-dotenv`, `tqdm`, `openpyxl`, `kagglehub`, `matplotlib`, `seaborn`
- Немає `requirements.txt`, немає `setup.py`/`pyproject.toml`, немає Pipfile
- Немає CI

### Стан підтримки
Останній коміт: `7f5ad89 Update README.md`. Галтьова гілка upstream: `main`. Репозиторій: `https://github.com/fipu-lab/med-rag`. Активна історія (коміти про лексикон, нормалізацію, ETL).

### Існуючі механізми тестування
Автоматизованих тестів не виявлено. Немає теки `tests/`, немає файлів `test_*.py`, немає конфігурації pytest.

### Обмеження дослідження
- litellm, pandas та інші залежності не встановлені; безпосереднє виконання `import llm` не тестовано (підтверджено статично, що `prompts/system.md` не існує).
- Виклики LLM не виконувалися (потребують ключів API та коштують грошей).
- REA 6.7.0 не працює в цьому середовищі; лише статичний аналіз + термінал.

## B. Виявлені проблеми

| ID | Заголовок | Severity | Статус | Локація |
|----|-----------|----------|--------|----------|
| REA-med-001 | `parse_file("prompts/system.md")` ламає `import llm` (файл відсутній) | P1 | CONFIRMED | `llm.py:178` |
| REA-med-002 | `from lexicon_normalizer import create_normalizer` — модуль відсутній | P2 | CONFIRMED | `normalize_test_questions.py:8` |
| REA-med-003 | Відсутній `requirements.txt` | P3 | CONFIRMED | корінь проєкту |
| REA-med-004 | Відсутні автоматизовані тести | P3 | CONFIRMED | корінь проєкту |
| REA-med-005 | `logger.error(..., str(e))` може виявляти ключі API | P2 | PROBABLE | `llm.py:313` |
| REA-med-006 | `print = logger(...)` закриває вбудований `print` | P3 | CONFIRMED | `main.py:138` |
| REA-med-007 | `etl.py` `__main__` запускає лише `process_lab()`; інше закоментовано | P3 | CONFIRMED | `etl.py:229-236` |

### Деталі підтверджених проблем

**REA-med-001 (P1, CONFIRMED)**: `llm.py:178` викликає `parse_file("prompts/system.md")` на рівні модуля. Файл `prompts/system.md` не існує в репозиторії (перевірено: не знайдено, не в archive/ або жодному підкаталозі). Це спричиняє `FileNotFoundError` при `import llm`, ламаючи увесь проєкт. Це помилка імпорту, яка запобігає будь-якому використанню проєкту.

Довід: `llm.py:178` + відсутність `prompts/system.md`.

**REA-med-002 (P2, CONFIRMED)**: `normalize_test_questions.py:8` імпортує `from lexicon_normalizer import create_normalizer`, але модуля `lexicon_normalizer` не існує в репозиторії. Скрипт не може виконуватися.

**REA-med-003 (P3, CONFIRMED)**: Немає `requirements.txt`. Залежності можна лише вивести з `import` у джерелах.

**REA-med-004 (P3, CONFIRMED)**: Немає автоматизованих тестів.

**REA-med-006 (P3, CONFIRMED)**: `main.py:138` робить `print = logger(...)`, закриваючи вбудований `print`. Усі подальші виклики `print` використовують логгер, що є спотворюючим і може ламати код, що очікує вбудований `print`.

**REA-med-007 (P3, CONFIRMED)**: `etl.py:229-236` викликає лише `process_lab()` у `__main__`; всі інші функції обробки закоментовано.

### Деталі ймовірної проблеми

**REA-med-005 (P2, PROBABLE)**: `llm.py:313` робить `logger.error("Model %s request failed: %s", model, str(e))`. Якщо `e` містить деталі з винятка автентифікації LiteLLM/провайдера, повідомлення про помилку може включати частини ключів API або токенів, виявляючи облікові дані до логів.

## C. Повторювані проблеми
Повторювалися публічні проблеми для цього репозиторію не знайдено (перевірено через GitHub API).

## D. Недокументовані помилки
Усі пункти розділу B — це проблеми, що раніше не були задокументовано проєктом.

## E. Продуктивність
`main.py` обробляє до 1000 тестових випадків у пачках по 5, з асинхронними викликами LLM (`asyncio.gather`). Немає значущих блокуючих операцій крім мережевих викликів. `query()` у `main.py` використовує `threading.Timer` для тайм-ауту SQL, що є доречним.

## F. Технічні вдосконалення
- Додати `try/except` при завантаженні `prompts/system.md` (REA-med-001, реалізовано).
- Створити `prompts/system.md` або видалити імпорт, якщо не використовується (REA-med-001).
- Створити модуль `lexicon_normalizer` або видалити імпорт (REA-med-002).
- Додати `requirements.txt` (REA-med-003, реалізовано).
- Додати автоматизовані тести (REA-med-004, частково реалізовано).
- Логувати тип винятка замість `str(e)` (REA-med-005, реалізовано).
- Перейменувати закритий змінній `print` (REA-med-006, реалізовано).
- Розкоментувати функції ETL або задокументувати, чому закоментовано (REA-med-007).

## G. План виконання
Самостійні правки:
1. REA-med-001, REA-med-005, REA-med-006 — `llm.py` та `main.py` (низький ризик, зроблено).
2. REA-med-003 — `requirements.txt` (низький ризик, зроблено).
3. REA-med-004 — тести (частково зроблено, тести core logic).
4. REA-med-002 — створити/видалити `lexicon_normalizer` (не зроблено; потрібне більше досліджень).
5. REA-med-007 — ETL (не зроблено; потрібне рішення підтрижувачів).

## H. Очікуваний результат
Зробити проєкт імпортуваним та виконуваним без збоїв, уникнути витоку облікових даних, створити відтворювучу базу залежностей та тестів.

**Інструменти:** git, gh, PowerShell/термінал, Python 3.12 (py_compile, unittest), статичний аналіз коду.  
**Обмеження:** REA 6.7.0 не працює; litellm/pandas не встановлені.  
**Середовище:** Windows, PowerShell 5.1, `C:\Users\User\audit-repos\med-rag` (клон upstream, гілка `main`, коміт `7f5ad89`).

Переклад технічний, виконаний автоматизовано; рекомендується перегляд носієм мови перед використанням якнормативного посилання.
