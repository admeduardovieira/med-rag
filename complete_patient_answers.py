#!/usr/bin/env python3
"""
Script to complete patient answers for the remaining 10 questions using DeepSeek LLM.
This script processes all 100 patients in synthetic_patients_v2_100 and answers
questions 11-20, then overwrites the existing patient_n_answers.md files.
"""

import os
import re
import asyncio
import llm
from tqdm import tqdm
from logging_setup import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Questions from experiment.py
ALL_QUESTIONS = [
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

# The remaining 10 questions (11-20)
REMAINING_QUESTIONS = ALL_QUESTIONS[10:]

# Configuration
INPUT_FOLDER = "dataset/synthetic_patients_v2_100"
MODEL = "deepseek-v3.1"  # Using DeepSeek as requested
MAX_TOKENS = 500

# System prompt for answering medical questions
SYSTEM_PROMPT = """You are a medical assistant tasked with answering specific questions about patient records. 

Given a patient record, answer the provided question based ONLY on the information explicitly stated in the record. 

Guidelines:
- Be concise and direct in your answers
- Only use information that is clearly stated in the patient record
- If information is not available in the record, state "Not specified in the record"
- Maintain medical accuracy and professionalism
- Format your answer as a clear, complete sentence or short paragraph
- Do not make assumptions or inferences beyond what is explicitly stated

Patient Record:
{patient_record}

Question: {question}

Answer:"""


def get_patient_ids():
    """Get all patient IDs from the input folder."""
    patient_ids = []
    for file_path in os.listdir(INPUT_FOLDER):
        m = re.fullmatch(r"patient_(\d+)\.md", file_path)
        if m:
            patient_id = int(m.group(1))
            patient_ids.append(patient_id)
    return sorted(patient_ids)


def read_patient_record(patient_id):
    """Read the patient record file."""
    record_path = os.path.join(INPUT_FOLDER, f"patient_{patient_id}.md")
    try:
        with open(record_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Patient record not found: {record_path}")
        return None


def read_existing_answers(patient_id):
    """Read existing answers from patient_n_answers.md file."""
    answers_path = os.path.join(INPUT_FOLDER, f"patient_{patient_id}_answers.md")
    try:
        with open(answers_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(
            f"Existing answers not found for patient {patient_id}, will create new file"
        )
        return ""


def save_complete_answers(patient_id, all_answers):
    """Save all 20 answers to the patient_n_answers.md file."""
    answers_path = os.path.join(INPUT_FOLDER, f"patient_{patient_id}_answers.md")

    with open(answers_path, "w", encoding="utf-8") as f:
        f.write(f"# Answers for Patient (ID: {patient_id})\n\n")

        for i, answer in enumerate(all_answers, 1):
            f.write(f"{i}. {answer}\n\n")


async def answer_question(patient_record, question):
    """Use DeepSeek LLM to answer a question about a patient record."""
    system_prompt = SYSTEM_PROMPT.format(
        patient_record=patient_record, question=question
    )

    try:
        result = await llm.ai_query(
            message=question,
            system=system_prompt,
            model=MODEL,
            max_tokens=MAX_TOKENS,
            prefix=None,
            sql=False,
        )
        return result.text.strip()
    except Exception as e:
        logger.error(f"Error answering question '{question}': {e}")
        return f"Error generating answer: {str(e)}"


async def process_patient(patient_id):
    """Process a single patient and generate answers for all 20 questions."""
    logger.info(f"Processing patient {patient_id}")

    # Read patient record
    patient_record = read_patient_record(patient_id)
    if not patient_record:
        logger.error(f"Could not read record for patient {patient_id}")
        return False

    # Read existing answers (first 10 questions)
    existing_answers_text = read_existing_answers(patient_id)
    existing_answers = []

    # Parse existing answers (questions 1-10)
    if existing_answers_text:
        lines = existing_answers_text.split("\n")
        for line in lines:
            # Look for lines that start with a number followed by a period
            match = re.match(r"^(\d+)\.\s*(.+)$", line.strip())
            if match:
                answer_num = int(match.group(1))
                answer_text = match.group(2).strip()
                if 1 <= answer_num <= 10:
                    existing_answers.append(answer_text)

    # Ensure we have exactly 10 existing answers
    while len(existing_answers) < 10:
        existing_answers.append("Answer not found in existing file")

    # Generate answers for remaining questions (11-20)
    new_answers = []
    for i, question in enumerate(REMAINING_QUESTIONS, 11):
        logger.info(f"  Answering question {i}/20: {question}")
        answer = await answer_question(patient_record, question)
        new_answers.append(answer)

    # Combine all answers (first 10 + new 10)
    all_answers = existing_answers + new_answers

    # Save complete answers
    save_complete_answers(patient_id, all_answers)
    logger.info(f"Completed patient {patient_id} - saved all 20 answers")

    return True


async def main():
    """Main function to process all patients."""
    logger.info("Starting patient answer completion process")
    logger.info(f"Using model: {MODEL}")
    logger.info(f"Processing folder: {INPUT_FOLDER}")
    logger.info(f"Remaining questions to answer: {len(REMAINING_QUESTIONS)}")

    # Get all patient IDs
    patient_ids = get_patient_ids()
    logger.info(f"Found {len(patient_ids)} patients to process")

    if not patient_ids:
        logger.error("No patient records found!")
        return

    # Process each patient
    successful = 0
    failed = 0

    for patient_id in tqdm(patient_ids, desc="Processing patients"):
        try:
            success = await process_patient(patient_id)
            if success:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to process patient {patient_id}: {e}")
            failed += 1

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("PROCESSING COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Total patients: {len(patient_ids)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {successful/len(patient_ids)*100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
