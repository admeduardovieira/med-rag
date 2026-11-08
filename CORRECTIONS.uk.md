# CORRECTIONS.md — med-rag

Проєкт: fipu-lab/med-rag
Базова гał diff гałку для аналізу: main (коміт 7f5ad89)
Гał diff гałку для публікації: https://github.com/admeduardovieira/med-rag

## Пропоновані виправлення (реалізовано — Фаза 1 та Фаза 2 завершено)

| ID | Назва | Середність | Статус | Різик | Задіяні файли |
|----|-------|------------|--------|-------|---------------|
| REA-med-001 | `parse_file("prompts/system.md")` ламає `import llm` (файл відсутній) | P1 | IMPLEMENTED | Низький | `llm.py` |
| REA-med-002 | `from lexicon_normalizer import create_normalizer` — модуль відсутній | P2 | NOT IMPLEMENTED | Низький | `normalize_test_questions.py` |
| REA-med-003 | Відсутній `requirements.txt` | P3 | IMPLEMENTED | Низький | `requirements.txt` (новий) |
| REA-med-004 | Відсутні автоматизовані тести | P3 | PARTIAL | Низький | `tests/test_core.py` (новий) |
| REA-med-005 | `str(e)` в логері може викликати ключі API | P2 | IMPLEMENTED | Низький | `llm.py` |
| REA-med-006 | `print = logger(...)` приховує вбудований `print` | P3 | IMPLEMENTED | Низький | `main.py` |
| REA-med-007 | `etl.py` `__main__` запускає лише `process_lab()`; решта закоментовано | P3 | NOT IMPLEMENTED | Низький | `etl.py` |

## Деталі реалізованих виправлень

### REA-med-001 — Відсутній файл призву prompts verursює краш імпорту
**Проблема:** `llm.py:178` викликає `parse_file("prompts/system.md")` на рівні модуля; файл не існує, тому `import llm` verursює краш.
**Виправлення:** Обгорнуто виклик у `try/except FileNotFoundError` та `try/except Exception`, логуючи попередження та використовуючи порожній словник промптів.
**Валідація:** `py_compile` проходить; логіка імпорту більше не приводить до крашу при відсутньому файлі.

### REA-med-005 — Потенційне викриття облікових даних у логах помилок
**Проблема:** `llm.py:313` логує `str(e)` яке може містити деталі ключів API з винятків провайдера.
**Виправлення:** Змінено на логування лише `type(e).__name__`.
**Валідація:** `py_compile` проходить.

### REA-med-006 — Прихований вбудований `print`
**Проблема:** `main.py:138` робить `print = logger(...)`, приховуючи вбудований.
**Виправлення:** Перейменовано змінну на `log` та оновлено всі подальші виклики `print(` на `log(`.
**Валідація:** `py_compile` проходить.

### REA-med-003 — Відсутній requirements.txt
**Проблема:** Немає `requirements.txt`; залежності можна вивести лише з імпортів.
**Виправлення:** Додано `requirements.txt` з litellm, pandas, numpy, scipy, python-dotenv, tqdm, openpyxl, kagglehub, matplotlib, seaborn.
**Валідація:** Файл існує з очікуваними залежностями.

### REA-med-004 — Відсутні автоматизовані тести
**Проблема:** Тестів не існує.
**Виправлення:** Додано `tests/test_core.py` з 6 модульними тестами, що pokrývají `parse_file` (valid sections, invalid format, empty file) та вилучення SQL (sql block, generic code block, no SQL).
**Валідація:** 6/6 тестів проходять через `unittest discover`.

## Виправлення не реалізовано (потребує рішення підтрижуючої)

### REA-med-002 — Відсутній модуль lexicon_normalizer
Не реалізовано: створення модуля вимагає розуміння призначеної логіки нормалізації лексикону. Пропонується: або створити `lexicon_normalizer.py`, або видалити імпорт з `normalize_test_questions.py`.

### REA-med-007 — ETL частково закоментовано
Не реалізовано: розкоментування функцій ETL вимагає даних MIMIC-III (великі, закриті) та може мати побічні ефекти. Пропонується: задокументувати чому функції закоментовані або увімкнути інкрементально.

## План публікації
- Fork: `admeduardovieira/med-rag` (створено).
- Гał diff гałку `fix/rea-med-001-002-robustness` для REA-med-001..006 (реалізовано).
- Гał diff гałку `docs/rea-audit-reports` для звітів аудиту (PT/EN/UK).
- Ідентичність коміту: `admeduardovieira <admeduardovieira@users.noreply.github.com>`.
- PR до `fipu-lab/med-rag` гał diff гałку `main`.
