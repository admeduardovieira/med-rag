import qdrant_client
import asyncio
import llm
import hashlib
import os
import re
from pprint import pprint

import nltk
from nltk.translate.bleu_score import sentence_bleu
from rouge_score import rouge_scorer
import bert_score

from rag.parser import text, get_sections
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

client = qdrant_client.QdrantClient(path="qdrant_db")

collection_name = "patients"

if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config={"size": 512, "distance": "Cosine"},
    )


def index_patients(patients):
    for patient in patients:
        sections = patient.get("sections")

        new_sections = []
        for s in sections:
            point_id = (
                str(patient["patient_id"])
                + "0000"
                + hashlib.md5(s.encode()).hexdigest()
            )
            result = client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
            )
            if len(result) == 0:
                new_sections.append(s)

        if len(new_sections):
            print(f"There are {len(new_sections)} new sections...")

        results = asyncio.run(llm.ai_embeddings(new_sections))

        client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=hashlib.md5(section.encode()).hexdigest(),
                    vector=result["embedding"],
                    payload={
                        "patient_id": patient["patient_id"],
                        "section": section,
                    },
                )
                for section, result in zip(new_sections, results["data"])
            ],
        )


def search(patient_id, query_text, limit=10):

    query_vector = asyncio.run(llm.ai_embeddings([query_text]))["data"][0]["embedding"]

    search_filter = Filter(
        must=[FieldCondition(key="patient_id", match=MatchValue(value=patient_id))]
    )

    search_results = client.query_points(
        collection_name=collection_name,
        query_filter=search_filter,
        query=query_vector,
        limit=limit,
    )

    return search_results.points


def test():
    ...
    # sections = get_sections(text)

    # if not client.collection_exists(collection_name):
    #     client.create_collection(
    #         collection_name=collection_name,
    #         vectors_config={"size": 512, "distance": "Cosine"},
    #     )

    # patients = [
    #     {
    #         "patient_id": 1,
    #         "sections": ["Random fox", "Black rabbit", "Easy nest"],
    #     },
    #     {
    #         "patient_id": 2,
    #         "sections": ["Green turtle", "Flash back"],
    #     },
    # ]

    # query_text = "Random rabbit"
    # patient_id = 1

    # index_patients(patients)


def load_correct_answers(patient_id, folder="dataset/synthetic_patients_v2_100"):
    with open(os.path.join(folder, f"patient_{patient_id}_answers.md")) as f:
        contents = f.read()

        answers = re.findall(r"\d+\.\s(.*?)(?=\n\d+\.|\Z)", contents, re.DOTALL)
        return [ans.strip() for ans in answers]


if __name__ == "__main__":

    questions = [
        "What is the patient's chief complaint?",
        "Who referred the patient for admission?",
        "What medications is the patient currently taking?",
        "What is the patient's gynecological history?",
        "Has the patient experienced any recent surgical procedures?",
        "What is the patient's preferred method of billing?",
        "What diagnostic studies have been performed?",
        "What is the attending physician's name?",
        "What is the patient's age?",
        "What is included in the patient's treatment plan?",
        "What is the patient's marital status?",
        "What is the patient's occupation?",
        "Who are the patient's emergency contacts and their contact information?",
        "What is the patient's family medical history?",
        "What are the patient's social habits including smoking, alcohol use, and exercise?",
        "What are the patient's vital signs?",
        "What is the patient's BMI and general physical appearance?",
        "What does the physical examination reveal?",
        "What is the patient's assessment or diagnosis?",
        "What is the patient's follow-up plan?",
    ]

    with open("prompts/rag.md", "r") as f:
        system_prompt_template = f.read()

    top_rag_k = 3
    patient_id = 1

    answers = load_correct_answers(patient_id)

    for query_text in questions[:1]:
        print()
        print("#" * 10)
        print()
        print("Q:", query_text)
        results = search(patient_id, query_text, limit=20)

        for r in results[:3]:
            print()
            print(r.score, r.payload["section"][:20])
            print()

        rag_documentation = "\n---\n".join(
            r.payload["section"] for r in results[:top_rag_k]
        )

        system_prompt = system_prompt_template.format(
            rag_documentation=rag_documentation
        )
        print(system_prompt)

        result = asyncio.run(
            llm.ai_query(
                message=query_text,
                system=system_prompt,
                model="deepseek-v3",
                max_tokens=500,
                prefix=None,
                sql=False,
            )
        )

        print(result.text)
        print(answers[0])

        reference = "The cat sat on the mat with calm."
        candidate = "The cat is sitting on the mat with precision."

        # BLEU Score
        reference_tokens = [reference.split()]
        candidate_tokens = candidate.split()
        bleu_score = sentence_bleu(reference_tokens, candidate_tokens)
        print(f"BLEU Score: {bleu_score:.4f}")

        # ROUGE-L Score
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        rouge_scores = scorer.score(reference, candidate)
        rouge_l_score = rouge_scores["rougeL"].fmeasure
        print(f"ROUGE-L Score: {rouge_l_score:.4f}")

        # BERTScore
        _, _, F1 = bert_score.score([candidate], [reference], lang="en")
        print(f"BERTScore (F1): {F1.item():.4f}")
