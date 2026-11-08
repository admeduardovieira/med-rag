# REVERSE_ENGINEERING_REPORT — med-rag

## A. Diagnóstico geral

### Arquitetura identificada
Projeto Python de avaliação de LLMs para dois fluxos clínicos: NL2SQL (natural language to SQL sobre EHRs MIMIC-III/MIMICSQL) e RAG-QA (question answering com geração aumentada por recuperação sobre prontuários sintéticos). Arquitetura em camadas:

- `main.py`: orquestra experimentos em lote, chama `llm.ai_query` para cada modelo, executa SQL no SQLite (`db/database_full.db`), imprime resultados.
- `llm.py`: cliente LLM via LiteLLM (`acompletion`, `aembedding`), suporte a 9 modelos (DeepSeek, Llama, GPT, Mixtral, Qwen, BioMistral), extração de SQL de respostas, retry com backoff, cache de embeddings em disco.
- `etl.py`: ETL de MIMIC-III (demográfico, diagnósticos, procedimentos, prescrições, exames) para CSV e depois SQLite.
- `ec.py`: classificador de erros SQL (SCHEMA_MISMATCH, JOIN_ERRORS, STRING_MISMATCH, INCORRECT_AGGREGATION, etc.) comparando SQL predito vs verdadeiro.
- `analyze_rag_results.py`, `nl2sql_statistical_analysis.py`: análise estatística de resultados (testes t pareados, matriz de performance).
- `complete_patient_answers.py`: completa respostas de pacientes sintéticos com LLM.
- `normalize_test_questions.py`, `merge_normalized_questions.py`: normalização de perguntas de teste.

### Tecnologias e dependências
- Python (versão não declarada explicitamente; Pipfile ausente)
- Dependências de runtime inferidas: `litellm`, `pandas`, `numpy`, `scipy`, `python-dotenv`, `tqdm`, `openpyxl`, `kagglehub`, `matplotlib`, `seaborn`
- Não há `requirements.txt`, não há `setup.py`/`pyproject.toml`, não há Pipfile
- Não há CI configurado

### Estado de manutenção
Último commit: `7f5ad89 Update README.md`. Branch default upstream: `main`. Repositório: `https://github.com/fipu-lab/med-rag`. Histórico ativo (vários commits sobre lexicon, normalização, ETL).

### Mecanismos de testes existentes
Nenhum teste automatizado encontrado. Nenhuma pasta `tests/`, nenhum `test_*.py`, nenhuma configuração pytest.

### Limitações da investigação
- litellm, pandas e outras dependências não instaladas; execução do `import llm` não testada diretamente (confirmação via leitura estática de que `prompts/system.md` não existe).
- Não foram executadas chamadas de LLM (requerem chaves de API e custam dinheiro).
- REA 6.7.0 não operacional neste ambiente; análise estática + terminal.

## B. Problemas encontrados

| ID | Título | Severidade | Status | Localização |
|----|--------|------------|--------|-------------|
| REA-med-001 | `parse_file("prompts/system.md")` quebra o `import llm` (arquivo ausente) | P1 | CONFIRMADO | `llm.py:178` |
| REA-med-002 | `from lexicon_normalizer import create_normalizer` — módulo inexistente | P2 | CONFIRMADO | `normalize_test_questions.py:8` |
| REA-med-003 | Ausência de `requirements.txt` | P3 | CONFIRMADO | raiz do repo |
| REA-med-004 | Ausência de testes automatizados | P3 | CONFIRMADO | raiz do repo |
| REA-med-005 | `logger.error(..., str(e))` pode vazar chaves de API | P2 | PROVÁVEL | `llm.py:313` |
| REA-med-006 | `print = logger(...)` sombra builtin `print` | P3 | CONFIRMADO | `main.py:138` |
| REA-med-007 | `etl.py` `__main__` roda apenas `process_lab()`; resto comentado | P3 | CONFIRMADO | `etl.py:229-236` |

### Detalhes dos problemas confirmados

**REA-med-001 (P1, CONFIRMADO)**: `llm.py:178` chama `parse_file("prompts/system.md")` no nível do módulo. O arquivo `prompts/system.md` não existe no repositório (verificado: Test-Path = False, não encontrado em archive/ nem em nenhum subdiretório). Isso faz com que `import llm` lance `FileNotFoundError` e quebre toda a aplicação. É um bug de importação que impede o uso de qualquer funcionalidade do projeto.

Evidência: `llm.py:178` + ausência de `prompts/system.md`.

**REA-med-002 (P2, CONFIRMADO)**: `normalize_test_questions.py:8` importa `from lexicon_normalizer import create_normalizer`, mas o módulo `lexicon_normalizer` não existe no repositório. O script não pode ser executado.

**REA-med-003 (P3, CONFIRMADO)**: Não há `requirements.txt`. As dependências só podem ser inferidas a partir dos `import` nos fontes.

**REA-med-004 (P3, CONFIRMADO)**: Não há testes automatizados.

**REA-med-006 (P3, CONFIRMADO)**: `main.py:138` faz `print = logger(...)`, sombreando o builtin `print`. Todas as chamadas subsequentes a `print` usam o logger, o que é confuso e pode quebrar código que espera o builtin.

**REA-med-007 (P3, CONFIRMADO)**: `etl.py:229-236` só chama `process_lab()` no `__main__`; todas as outras funções de processamento (`process_demographic`, `process_diagnoses`, etc.) estão comentadas.

### Detalhes do problema provável

**REA-med-005 (P2, PROVÁVEL)**: `llm.py:313` faz `logger.error("Model %s request failed: %s", model, str(e))`. Se `e` conter detalhes de uma exceção de autenticação da LiteLLM/provedor, a mensagem de erro pode incluir partes de chaves de API ou tokens, vazando credenciais nos logs.

## C. Problemas recorrentes
Nenhum issue recorrente público encontrado para este repositório (verificado via API do GitHub).

## D. Erros não documentados
Todos os itens da seção B são problemas não documentados anteriormente pelo projeto.

## E. Performance
O `main.py` processa até 1000 casos de teste em lotes de 5, com chamadas assíncronas a LLMs (`asyncio.gather`). Não há operações bloqueantes significativas além das chamadas de rede. O `query()` em `main.py` usa um `threading.Timer` para timeout de SQL, o que é adequado.

## F. Melhorias técnicas
- Adicionar `try/except` ao carregar `prompts/system.md` (REA-med-001, implementado).
- Criar `prompts/system.md` ou remover a importação se não for usada (REA-med-001).
- Criar o módulo `lexicon_normalizer` ou remover a importação (REA-med-002).
- Adicionar `requirements.txt` (REA-med-003, implementado).
- Adicionar testes automatizados (REA-med-004, implementado parcialmente).
- Logar tipo de exceção em vez de `str(e)` (REA-med-005, implementado).
- Renomear variável sombreada `print` (REA-med-006, implementado).
- Descomentar funções do ETL ou documentar por que estão comentadas (REA-med-007).

## G. Plano de execução
Correções independentes:
1. REA-med-001, REA-med-005, REA-med-006 — `llm.py` e `main.py` (baixo risco, feito).
2. REA-med-003 — `requirements.txt` (baixo risco, feito).
3. REA-med-004 — testes (feito parcialmente, teste de core logic).
4. REA-med-002 — criar/remover `lexicon_normalizer` (não feito; requer mais investigação).
5. REA-med-007 — ETL (não feito; requer decisão dos mantenedores).

## H. Resultado esperado
Tornar o projeto importável e executável sem crashes, evitar vazamento de credenciais, estabelecer base de dependências e testes reproduzíveis.

**Ferramentas usadas:** git, gh, PowerShell/terminal, Python 3.12 (py_compile, unittest), inspeção estática.  
**Limitação:** REA 6.7.0 não operacional; litellm/pandas não instalados.  
**Ambiente:** Windows, PowerShell 5.1, `C:\Users\User\audit-repos\med-rag` (clone do upstream, branch `main`, commit `7f5ad89`).
