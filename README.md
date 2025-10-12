# Robust Clinical Querying with Local LLMs: Lexical Challenges in NL2SQL and Retrieval-Augmented QA on EHRs

## Abstract

Electronic health records (EHRs) are typically stored in relational databases, making them difficult to query for nontechnical users, especially under privacy constraints. We evaluate two practical clinical NLP workflows, natural language to SQL (NL2SQL) for EHR querying and retrieval-augmented generation for clinical question answering (RAG-QA), with a focus on privacy-preserving deployment. We benchmark nine large language models, spanning open-weight options (DeepSeek V3/V3.1, Llama-3.3-70B, Qwen2.5-32B, Mixtral-8 × 22B, BioMistral-7B, and GPT-OSS-20B) and proprietary APIs (GPT-4o and GPT-5). The models were chosen to represent a diverse cross-section spanning sparse MoE, dense general-purpose, domain-adapted, and proprietary LLMs. On MIMICSQL (27,000 generations; nine models × three runs), the best NL2SQL execution accuracy (EX) is 66.1% (GPT-4o), followed by 64.6% (GPT-5). Among open-weight models, DeepSeek V3.1 reaches 59.8% EX, while DeepSeek V3 reaches 58.8%, with Llama-3.3-70B at 54.5% and BioMistral-7B achieving only 11.8%, underscoring a persistent gap relative to general-domain benchmarks. We introduce SQL-EC, a deterministic SQL error-classification framework with adjudication, revealing string mismatches as the dominant failure (86.3%), followed by query-join misinterpretations (49.7%), while incorrect aggregation-function usage accounts for only 6.7%. This highlights lexical/ontology grounding as the key bottleneck for NL2SQL in the biomedical domain. For RAG-QA, evaluated on 100 synthetic patient records across 20 questions (54,000 reference–generation pairs; three runs), BLEU and ROUGE-L fluctuate more strongly across models, whereas BERTScore remains high on most, with DeepSeek V3.1 and GPT-4o among the top performers; pairwise t-tests confirm that significant differences were observed among the LLMs. Cost–performance analysis based on measured token usage shows per-query costs ranging from USD 0.000285 (GPT-OSS-20B) to USD 0.005918 (GPT-4o); DeepSeek V3.1 offers the best open-weight cost–accuracy trade-off, and GPT-5 provides a balanced API alternative. Overall, the privacy-conscious RAG-QA attains strong semantic fidelity, whereas the clinical NL2SQL remains brittle under lexical variation. SQL-EC pinpoints actionable failure modes, motivating ontology-aware normalization and schema-linked prompting for robust clinical querying.

## Key Tasks

This study focuses on three primary tasks:

1.  **Natural Language to SQL (NL2SQL):** Generating SQL queries from natural language questions. Performance is evaluated using SQL execution accuracy on the MIMIC-III and MIMICSQL datasets.
2.  **Retrieval-Augmented Generation Question Answering (RAG-QA):** Answering questions based on synthetic patient records using a RAG approach. Evaluated using BLEU, ROUGE-L, and BERTScore metrics.
3.  **SQL Error Classification (SQL-EC):** Classifying erroneous SQL outputs into predefined error categories based on expert annotation. This is a multi-label classification task.

## Models Benchmarked

The following Large Language Models (LLMs) were benchmarked:

- **DeepSeek-V3**
- **DeepSeek-V3.1**
- **Llama3.3-70B**
- **BioMistral-7B**
- **Mixtral-8x22b-instruct**
- **QWEN2.5-32B-instruct**
- **GPT-4o**
- **GPT-5**
- **GPT-OSS-20B**

## Acknowledgements

This research is (partly) supported by "European Digital Innovation Hub Adriatic Croatia (EDIH Adria) (project no. 101083838)" under the European Commission's Digital Europe Programme, SPIN project "INFOBIP Konverzacijski Order Management (IP.1.1.03.0120)", SPIN project "Projektiranje i razvoj nove generacije laboratorijskog informacijskog sustava (iLIS)" (IP.1.1.03.0158), SPIN project "Istraživanje i razvoj inovativnog sustava preporuka za napredno gostoprimstvo u turizmu (InnovateStay)" (IP.1.1.03.0039), and the FIPU project "Sustav za modeliranje i provedbu poslovnih procesa u heterogenom i decentraliziranom računalnom sustavu".
