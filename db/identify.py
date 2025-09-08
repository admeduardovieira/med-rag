import sqlite3
import argparse
import os, sys
import logging

# This will allow us to import the logging_setup module from the root directory
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from logging_setup import setup_logging, get_logger

setup_logging(level=logging.DEBUG)
logger = get_logger(__name__)


def main(database_name):
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    # Get all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    logger.info(f"Database: {database_name}")
    logger.info("=" * 50)

    if not tables:
        logger.error("No tables found in the database.")
        return

    logger.info(f"Found {len(tables)} table(s):")

    for table in tables:
        table_name = table[0]

        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()

        # Count rows in the table
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        row_count = cursor.fetchone()[0]

        logger.warning("-" * 50)
        logger.warning(f"Table: {table_name}")

        logger.info(f"  Rows: {row_count}")
        logger.info(f"  Columns ({len(columns)}):")

        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            pk_marker = " (PRIMARY KEY)" if pk else ""
            not_null_marker = " NOT NULL" if not_null else ""
            logger.debug(f"    - {col_name}: {col_type}{not_null_marker}{pk_marker}")
    logger.warning("-" * 50)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite database operations")
    parser.add_argument("database", help="Name of the database file")

    args = parser.parse_args()
    main(args.database)
