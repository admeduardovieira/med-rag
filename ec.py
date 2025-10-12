"""
SQL Error Classification Tool

This tool uses the Excel results file to identify failed queries,
then maps them back to the log file to get actual SQL queries for classification.
"""

import pandas as pd
import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set
import os
from logging_setup import get_logger

logger = get_logger(__name__)


class SQLErrorClassifier:
    def __init__(self):
        # u grubo
        self.error_categories = {
            "SCHEMA_MISMATCH": "Schema-related errors (table/column names, syntax)",
            "INCORRECT_AGGREGATION": "Wrong aggregation functions or usage",
            "JOIN_ERRORS": "Wrong number or type of joins",
            "JOIN_MISINTERPRETATION": "Wrong join keys or conditions",
            "STRING_MISMATCH": "String literal or case sensitivity issues",
        }

    def load_failed_queries_from_excel(self, excel_file: str) -> pd.DataFrame:
        """Load failed queries from the Excel results file"""
        df = pd.read_excel(excel_file)
        failed_queries = df[df["is_correct"] == False].copy()

        logger.info(f"Total queries: {len(df)}")
        logger.info(f"Failed queries: {len(failed_queries)}")
        logger.info(f"Failure rate: {len(failed_queries)/len(df)*100:.1f}%")

        return failed_queries

    def parse_log_file_for_failed_queries(
        self, log_file: str, failed_queries_df: pd.DataFrame
    ) -> Dict:
        """Parse log file to extract SQL queries for failed cases only"""

        failed_lookups = set()
        for _, row in failed_queries_df.iterrows():
            failed_lookups.add((row["observation_id"], row["model"]))

        logger.info(f"Looking for {len(failed_lookups)} failed query cases in log file")

        cases = {}

        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        case_blocks = content.split("*" * 30)

        for block in case_blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            case_id = None
            question = None
            true_sql = None
            models_data = {}

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                if line.startswith("CASE:"):
                    case_id = line.replace("CASE:", "").strip()
                elif line.startswith("QUESTION:"):
                    question = line.replace("QUESTION:", "").strip()
                elif line.startswith("TRUE:"):
                    true_sql = line.replace("TRUE:", "").strip()
                elif line.startswith("LLM [") and "]:" in line:
                    # Extract model and SQL
                    model_name = line.split("[")[1].split("]")[0]
                    predicted_sql = line.split("]:")[1].strip()

                    if (case_id, model_name) in failed_lookups:
                        models_data[model_name] = {
                            "predicted_sql": predicted_sql,
                            "true_sql": true_sql,
                            "question": question,
                        }

                i += 1

            # Only false queries
            if case_id and models_data:
                cases[case_id] = {
                    "question": question,
                    "true_sql": true_sql,
                    "failed_models": models_data,
                }

        logger.info(f"Found SQL queries for {len(cases)} failed cases")
        return cases

    def classify_sql_error(
        self, predicted_sql: str, true_sql: str
    ) -> Tuple[List[str], List[str]]:
        """Classify SQL errors by comparing predicted vs true SQL"""

        error_categories = []
        explanations = []

        if not predicted_sql or predicted_sql.strip() == "":
            error_categories.append("SCHEMA_MISMATCH")
            explanations.append("Empty or missing SQL query")
            return error_categories, explanations

        pred_sql_upper = predicted_sql.upper()
        true_sql_upper = true_sql.upper()

        #  Schema mismatch: Check table usage
        pred_tables = set(re.findall(r'\bFROM\s+(["\w]+)', pred_sql_upper))
        pred_tables.update(re.findall(r'\bJOIN\s+(["\w]+)', pred_sql_upper))

        true_tables = set(re.findall(r'\bFROM\s+(["\w]+)', true_sql_upper))
        true_tables.update(re.findall(r'\bJOIN\s+(["\w]+)', true_sql_upper))

        pred_tables = {t.replace('"', "") for t in pred_tables}
        true_tables = {t.replace('"', "") for t in true_tables}

        if pred_tables != true_tables:
            error_categories.append("SCHEMA_MISMATCH")
            explanations.append(
                f"Table mismatch: predicted {pred_tables}, expected {true_tables}"
            )

        # Join errors: Check join count
        pred_join_count = len(re.findall(r"\bJOIN\b", pred_sql_upper))
        true_join_count = len(re.findall(r"\bJOIN\b", true_sql_upper))

        if pred_join_count != true_join_count:
            error_categories.append("JOIN_ERRORS")
            explanations.append(
                f"Join count mismatch: predicted {pred_join_count}, expected {true_join_count}"
            )

        # Join condition errors: Check join keys
        if pred_join_count > 0 and true_join_count > 0:
            pred_join_conds = re.findall(
                r"ON\s+([^(\s]+\s*=\s*[^(\s]+)", pred_sql_upper
            )
            true_join_conds = re.findall(
                r"ON\s+([^(\s]+\s*=\s*[^(\s]+)", true_sql_upper
            )

            if pred_join_conds != true_join_conds:
                error_categories.append("JOIN_MISINTERPRETATION")
                explanations.append(
                    f"Join condition mismatch: predicted {pred_join_conds}, expected {true_join_conds}"
                )

                # Check for specific HADM_ID vs SUBJECT_ID issues
                pred_join_str = " ".join(pred_join_conds)
                true_join_str = " ".join(true_join_conds)

                if "SUBJECT_ID" in pred_join_str and "HADM_ID" in true_join_str:
                    explanations.append("Used SUBJECT_ID join instead of HADM_ID")
                elif "HADM_ID" in pred_join_str and "SUBJECT_ID" in true_join_str:
                    explanations.append("Used HADM_ID join instead of SUBJECT_ID")

        # Aggregation errors
        pred_aggs = set(
            re.findall(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\([^)]*\)", pred_sql_upper)
        )
        true_aggs = set(
            re.findall(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\([^)]*\)", true_sql_upper)
        )

        if pred_aggs != true_aggs:
            error_categories.append("INCORRECT_AGGREGATION")
            explanations.append(
                f"Aggregation mismatch: predicted {pred_aggs}, expected {true_aggs}"
            )

            if (
                "COUNT(DISTINCT" in true_sql_upper
                and "COUNT(DISTINCT" not in pred_sql_upper
            ):
                explanations.append("Missing COUNT DISTINCT")
            elif (
                "COUNT(DISTINCT" in pred_sql_upper
                and "COUNT(DISTINCT" not in true_sql_upper
            ):
                explanations.append("Unnecessary COUNT DISTINCT")

        pred_strings = set(re.findall(r"'([^']*)'", predicted_sql))
        true_strings = set(re.findall(r"'([^']*)'", true_sql))

        if pred_strings != true_strings:
            error_categories.append("STRING_MISMATCH")
            explanations.append(
                f"String literal mismatch: predicted {pred_strings}, expected {true_strings}"
            )

            pred_strings_lower = {s.lower() for s in pred_strings}
            true_strings_lower = {s.lower() for s in true_strings}

            if pred_strings_lower == true_strings_lower:
                explanations.append("Case sensitivity issue in string literals")

        if "CAST(" in true_sql_upper and "CAST(" not in pred_sql_upper:
            if "JOIN_MISINTERPRETATION" not in error_categories:
                error_categories.append("JOIN_MISINTERPRETATION")
            explanations.append("Missing CAST operation (likely for lab.HADM_ID)")

        if not error_categories:
            error_categories.append("SCHEMA_MISMATCH")
            explanations.append("Query failed but no specific error pattern detected")

        return error_categories, explanations

    def generate_report(self, excel_file: str, log_file: str) -> Dict:
        failed_queries_df = self.load_failed_queries_from_excel(excel_file)

        failed_cases = self.parse_log_file_for_failed_queries(
            log_file, failed_queries_df
        )

        results = {
            "total_queries": len(pd.read_excel(excel_file)),
            "failed_queries": len(failed_queries_df),
            "error_distribution": defaultdict(int),
            "model_performance": defaultdict(
                lambda: {"total": 0, "failed": 0, "errors": defaultdict(int)}
            ),
            "detailed_errors": [],
        }

        # Get model performance from Excel
        all_queries_df = pd.read_excel(excel_file)
        model_stats = (
            all_queries_df.groupby("model")["is_correct"]
            .agg(["count", "sum"])
            .reset_index()
        )
        model_stats.columns = ["model", "total", "correct"]
        model_stats["failed"] = model_stats["total"] - model_stats["correct"]
        model_stats["accuracy"] = model_stats["correct"] / model_stats["total"]

        for _, row in model_stats.iterrows():
            model = row["model"]
            results["model_performance"][model]["total"] = row["total"]
            results["model_performance"][model]["failed"] = row["failed"]
            results["model_performance"][model]["accuracy"] = row["accuracy"]

        # Classify errors for cases where we have SQL queries
        classified_count = 0
        for case_id, case_data in failed_cases.items():
            for model_name, model_data in case_data["failed_models"].items():
                predicted_sql = model_data["predicted_sql"]
                true_sql = model_data["true_sql"]
                question = model_data["question"]

                error_categories, explanations = self.classify_sql_error(
                    predicted_sql, true_sql
                )
                classified_count += 1

                for category in error_categories:
                    results["error_distribution"][category] += 1
                    results["model_performance"][model_name]["errors"][category] += 1

                results["detailed_errors"].append(
                    {
                        "case_id": case_id,
                        "model": model_name,
                        "question": (
                            question[:100] + "..." if len(question) > 100 else question
                        ),
                        "error_categories": error_categories,
                        "explanations": explanations,
                        "predicted_sql": (
                            predicted_sql[:200] + "..."
                            if len(predicted_sql) > 200
                            else predicted_sql
                        ),
                        "true_sql": (
                            true_sql[:200] + "..." if len(true_sql) > 200 else true_sql
                        ),
                    }
                )

        logger.info(f"Successfully classified {classified_count} failed queries")
        results["classified_queries"] = classified_count

        return results

    def save_report(self, results: Dict, output_file: str):
        """Save the error classification report"""

        # Save detailed results
        detailed_df = pd.DataFrame(results["detailed_errors"])
        detailed_df.to_csv(output_file, index=False)

        # Save summary report
        summary_file = output_file.replace(".csv", "_summary.txt")
        with open(summary_file, "w") as f:
            f.write("=== CORRECTED SQL Error Classification Report ===\n\n")
            f.write(f"Total Queries: {results['total_queries']}\n")
            f.write(f"Failed Queries: {results['failed_queries']}\n")
            f.write(f"Successfully Classified: {results['classified_queries']}\n")
            f.write(
                f"Overall Accuracy: {(results['total_queries'] - results['failed_queries']) / results['total_queries']:.2%}\n\n"
            )

            f.write("ACTUAL Model Performance (from Excel):\n")
            for model, perf in sorted(
                results["model_performance"].items(),
                key=lambda x: x[1]["accuracy"],
                reverse=True,
            ):
                f.write(
                    f"  {model}: {perf['accuracy']:.1%} accuracy ({perf['total'] - perf['failed']}/{perf['total']})\n"
                )

            f.write("\nError Category Distribution (from classified queries):\n")
            total_classified = sum(results["error_distribution"].values())
            for category, count in sorted(
                results["error_distribution"].items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (
                    count / total_classified * 100 if total_classified > 0 else 0
                )
                f.write(f"  {category}: {count} ({percentage:.1f}%)\n")

            f.write("\nError Distribution by Model:\n")
            for model, perf in sorted(results["model_performance"].items()):
                if perf["errors"]:
                    f.write(f"\n  {model} (accuracy: {perf['accuracy']:.1%}):\n")
                    for category, count in sorted(
                        perf["errors"].items(), key=lambda x: x[1], reverse=True
                    ):
                        f.write(f"    {category}: {count}\n")

        logger.info(f"Report saved to {output_file}")
        logger.info(f"Summary saved to {summary_file}")


def main():
    """Main function"""

    excel_file = "output/results_questions_v2_100.xlsx"
    log_file = "output/questions_v2_100/nl2sql_9models_direct/output_batch_size=5&n=1000&exclude=none&take=1.log"
    output_file = "sql_error_classification_CORRECTED_report.csv"

    if not os.path.exists(excel_file):
        logger.error(f"Excel file not found: {excel_file}")
        return

    if not os.path.exists(log_file):
        logger.error(f"Log file not found: {log_file}")
        return

    classifier = SQLErrorClassifier()

    logger.info("Generating CORRECTED SQL error classification report...")
    results = classifier.generate_report(excel_file, log_file)

    logger.info("Saving report...")
    classifier.save_report(results, output_file)

    # Print summary
    print("\n=== CORRECTED SQL Error Classification Report ===")
    print(f"Total Queries: {results['total_queries']}")
    print(f"Failed Queries: {results['failed_queries']}")
    print(f"Successfully Classified: {results['classified_queries']}")
    print(
        f"Overall Accuracy: {(results['total_queries'] - results['failed_queries']) / results['total_queries']:.2%}"
    )

    print("\nACTUAL Model Performance:")
    for model, perf in sorted(
        results["model_performance"].items(),
        key=lambda x: x[1]["accuracy"],
        reverse=True,
    ):
        print(
            f"  {model}: {perf['accuracy']:.1%} accuracy ({perf['total'] - perf['failed']}/{perf['total']})"
        )

    print("\nError Distribution (from classified queries):")
    total_classified = sum(results["error_distribution"].values())
    for category, count in sorted(
        results["error_distribution"].items(), key=lambda x: x[1], reverse=True
    ):
        percentage = count / total_classified * 100 if total_classified > 0 else 0
        print(f"  {category}: {count} ({percentage:.1f}%)")


if __name__ == "__main__":
    main()
