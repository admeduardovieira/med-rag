# Enhancing Healthcare Efficiency with Local AI: Leveraging DeepSeek for Medical Data Processing

## Abstract

The digitization of healthcare records and the emergence of large language models (LLMs) offer new avenues for automating clinical and administrative workflows. However, real-world adoption remains constrained by concerns around data privacy, cost, and computational infrastructure. This study benchmarks the performance of open-source, locally deployable LLMs, DeepSeek-V3 and Llama3.3-70B, alongside a proprietary, API-based model, GPT-4o, across three tasks: (1) natural language to SQL query generation (NL2SQL), (2) question answering using retrieval-augmented generation (RAG-QA) over synthetic patient records, and (3) multi-label classification of erroneous SQL outputs into predefined error categories (SQL-EC). The NL2SQL task was evaluated using SQL execution accuracy on the MIMIC-III and MIMICSQL datasets; the question answering task employed BLEU, ROUGE-L, and BERTScore metrics; the classification task involved assigning one or more error classes to each faulty SQL query based on expert annotation. DeepSeek-V3 attained 62.9% SQL execution accuracy compared to GPT-4o's 68.8%, with a 65% reduction in deployment costs. Error analysis identified schema mismatches and lexical inconsistencies as prevalent failure modes. While reliance on synthetic data limits generalizability, findings indicate that cost-efficient, locally deployable models like DeepSeek-V3 can facilitate responsible AI integration within healthcare settings. In the Croatian healthcare system, marked by workforce shortages and demographic strain, such models hold potential to support digital transformation efforts while preserving data sovereignty and clinical fidelity.

## Key Tasks

This study focuses on three primary tasks:

1.  **Natural Language to SQL (NL2SQL):** Generating SQL queries from natural language questions. Performance is evaluated using SQL execution accuracy on the MIMIC-III and MIMICSQL datasets.
2.  **Retrieval-Augmented Generation Question Answering (RAG-QA):** Answering questions based on synthetic patient records using a RAG approach. Evaluated using BLEU, ROUGE-L, and BERTScore metrics.
3.  **SQL Error Classification (SQL-EC):** Classifying erroneous SQL outputs into predefined error categories based on expert annotation. This is a multi-label classification task.

## Models Benchmarked

The following Large Language Models (LLMs) were benchmarked:

- **DeepSeek-V3:** An open-source, locally deployable model.
- **Llama3.3-70B:** Another open-source, locally deployable model.
- **GPT-4o:** A proprietary, API-based model, used as a baseline.

## Key Findings & Contributions

- **Performance:** DeepSeek-V3 achieved 62.9% SQL execution accuracy in the NL2SQL task, compared to GPT-4o's 68.8%.
- **Cost-Effectiveness:** DeepSeek-V3 demonstrated a 65% reduction in deployment costs compared to API-based models like GPT-4o.
- **Error Analysis:** The study identified schema mismatches and lexical inconsistencies as common reasons for NL2SQL failures.
- **Local AI for Healthcare:** The findings suggest that cost-efficient, locally deployable models like DeepSeek-V3 can be viable for responsible AI integration in healthcare, particularly in contexts like the Croatian healthcare system, which faces workforce shortages and demographic challenges.
- **Data Sovereignty:** Local models help maintain data sovereignty and clinical fidelity, which are crucial in healthcare.
- **Limitations:** The study acknowledges that the reliance on synthetic data for RAG-QA limits generalizability to real-world patient data.

## Setup and Installation

1.  **Clone & Navigate:** `git clone https://github.com/fipu-lab/med-rag.git && cd ai_medicine_deepseek` (or your project root).
2.  **Environment & Dependencies:** Create a Python virtual environment (e.g., `python3 -m venv venv && source venv/bin/activate`) and install packages: `pip install -r requirements.txt`.
3.  **Environment Variables:** Create a `.env` file for API keys, database URLs, etc. (see example in previous versions or comments in scripts).
4.  **Datasets & DBs:** Download datasets (potentially using `python download.py`). Set up databases (e.g., MIMIC-SQL) and Qdrant for RAG-QA (e.g., via Docker `docker run -p 6333:6333 qdrant/qdrant`) as needed. Ensure paths and credentials are correct.

**Typical Workflow:**

1.  Setup environment & dependencies.
2.  Prepare data (`etl.py` or `make data_prepare`).
3.  Run experiments (`main.py` or `make` targets for specific tasks).
4.  Generate plots (`plot_*.py` scripts or `make plots`).

## Acknowledgements

This research is (partly) supported by "European Digital Innovation Hub Adriatic Croatia (EDIH Adria) (project no. 101083838)" under the European Commission's Digital Europe Programme, SPIN project "INFOBIP Konverzacijski Order Management (IP.1.1.03.0120)", SPIN project "Projektiranje i razvoj nove generacije laboratorijskog informacijskog sustava (iLIS)" (IP.1.1.03.0158), SPIN project "Istraživanje i razvoj inovativnog sustava preporuka za napredno gostoprimstvo u turizmu (InnovateStay)" (IP.1.1.03.0039), and the FIPU project "Sustav za modeliranje i provedbu poslovnih procesa u heterogenom i decentraliziranom računalnom sustavu".
