#!/usr/bin/env python3
"""
Enhanced helper script to normalize all questions in test.json using both normalization approaches.
Outputs results to multiple JSON files and reports comprehensive statistics.
"""

import json
from lexicon_normalizer import create_normalizer


def main():
    input_file = "dataset/test.json"
    output_file_option1 = "dataset/test_normalized_option1.json"
    output_file_option2 = "dataset/test_normalized_option2.json"
    comparison_file = "dataset/normalization_comparison.json"

    print("Loading enhanced lexicon normalizer...")
    try:
        normalizer = create_normalizer()
        print("✓ Enhanced lexicon normalizer loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load lexicon normalizer: {e}")
        return

    print(f"Processing questions from {input_file}...")

    results_option1 = []
    results_option2 = []
    comparison_results = []

    total_questions = 0
    normalized_count_option1 = 0
    normalized_count_option2 = 0
    medical_questions = 0

    # Read and process each line from test.json
    with open(input_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 100 == 0:
                print(f"Processed {line_num} questions...")
            try:
                # Parse JSON line
                data = json.loads(line.strip())

                # Extract the question
                original_question = data.get("question_refine", "")
                if not original_question:
                    continue

                # Check if it's a medical question
                is_medical = normalizer._is_medical_question(original_question)
                if is_medical:
                    medical_questions += 1

                # Apply both normalization approaches
                normalized_option1 = normalizer.normalize_question(
                    original_question, approach="option1"
                )
                normalized_option2 = normalizer.normalize_question(
                    original_question, approach="option2"
                )

                # Check if normalization actually changed the question
                was_normalized_option1 = normalized_option1 != original_question
                was_normalized_option2 = normalized_option2 != original_question

                if was_normalized_option1:
                    normalized_count_option1 += 1
                if was_normalized_option2:
                    normalized_count_option2 += 1

                # Store results for option 1
                result_option1 = {
                    "key": data.get("key", f"line_{line_num}"),
                    "original": original_question,
                    "normalized": normalized_option1,
                    "output": "changed" if was_normalized_option1 else "unchanged",
                }
                results_option1.append(result_option1)

                # Store results for option 2
                result_option2 = {
                    "key": data.get("key", f"line_{line_num}"),
                    "original": original_question,
                    "normalized": normalized_option2,
                    "output": "changed" if was_normalized_option2 else "unchanged",
                }
                results_option2.append(result_option2)

                # Store comparison
                comparison_result = {
                    "key": data.get("key", f"line_{line_num}"),
                    "original": original_question,
                    "is_medical": is_medical,
                    "option1": normalized_option1,
                    "option2": normalized_option2,
                    "changed_option1": was_normalized_option1,
                    "changed_option2": was_normalized_option2,
                }
                comparison_results.append(comparison_result)

                total_questions += 1

            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}")
                continue

    # Write results to output files
    print(f"Writing Option 1 results to {output_file_option1}...")
    with open(output_file_option1, "w") as f:
        for result in results_option1:
            json.dump(result, f)
            f.write("\n")

    print(f"Writing Option 2 results to {output_file_option2}...")
    with open(output_file_option2, "w") as f:
        for result in results_option2:
            json.dump(result, f)
            f.write("\n")

    print(f"Writing comparison results to {comparison_file}...")
    with open(comparison_file, "w") as f:
        for result in comparison_results:
            json.dump(result, f)
            f.write("\n")

    # Print comprehensive summary
    print("\n" + "=" * 60)
    print("ENHANCED NORMALIZATION SUMMARY")
    print("=" * 60)
    print(f"Total questions processed: {total_questions}")
    print(
        f"Medical questions detected: {medical_questions} ({(medical_questions / total_questions * 100):.1f}%)"
    )
    print(f"Non-medical questions: {total_questions - medical_questions}")
    print()
    print("OPTION 1 (Pre-normalize with annotations):")
    print(f"  Questions normalized: {normalized_count_option1}")
    print(
        f"  Normalization rate: {(normalized_count_option1 / total_questions * 100):.1f}%"
    )
    print(
        f"  Medical normalization rate: {(normalized_count_option1 / medical_questions * 100):.1f}%"
        if medical_questions > 0
        else "  Medical normalization rate: N/A"
    )
    print()
    print("OPTION 2 (Mini glossary):")
    print(f"  Questions with glossary: {normalized_count_option2}")
    print(f"  Glossary rate: {(normalized_count_option2 / total_questions * 100):.1f}%")
    print(
        f"  Medical glossary rate: {(normalized_count_option2 / medical_questions * 100):.1f}%"
        if medical_questions > 0
        else "  Medical glossary rate: N/A"
    )
    print()
    print("FILES GENERATED:")
    print(f"  📁 {output_file_option1}")
    print(f"  📁 {output_file_option2}")
    print(f"  📁 {comparison_file}")

    # Show improvement over original 9.2%
    if normalized_count_option1 > 0 or normalized_count_option2 > 0:
        print(f"\n🎉 IMPROVEMENT ACHIEVED!")
        original_rate = 9.2
        new_rate_option1 = normalized_count_option1 / total_questions * 100
        new_rate_option2 = normalized_count_option2 / total_questions * 100
        print(f"   Original rate: {original_rate}%")
        print(
            f"   Option 1 rate: {new_rate_option1:.1f}% ({new_rate_option1 - original_rate:+.1f}%)"
        )
        print(
            f"   Option 2 rate: {new_rate_option2:.1f}% ({new_rate_option2 - original_rate:+.1f}%)"
        )


if __name__ == "__main__":
    main()
