
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "pinscope.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                keyword TEXT PRIMARY KEY,
                category TEXT NOT NULL DEFAULT 'Uncategorized',
                sample_score REAL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS saved_keywords (
                keyword TEXT PRIMARY KEY
            )
        """)


def save_keyword_dataset(data):
    cleaned = data.copy()

    cleaned["keyword"] = (
        cleaned["keyword"].fillna("").astype(str).str.strip().str.lower()
    )
    cleaned = cleaned[cleaned["keyword"] != ""]

    if "category" not in cleaned.columns:
        cleaned["category"] = "Uncategorized"

    if "sample_score" not in cleaned.columns:
        cleaned["sample_score"] = None

    cleaned["category"] = (
        cleaned["category"].fillna("Uncategorized").astype(str)
    )
    cleaned["sample_score"] = pd.to_numeric(
        cleaned["sample_score"], errors="coerce"
    )

    cleaned = cleaned.drop_duplicates("keyword")

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT INTO keywords (keyword, category, sample_score)
            VALUES (?, ?, ?)
            ON CONFLICT(keyword) DO UPDATE SET
                category = excluded.category,
                sample_score = excluded.sample_score
            """,
            [
                (
                    row.keyword,
                    row.category,
                    (
                        float(row.sample_score)
                        if pd.notna(row.sample_score)
                        else None
                    ),
                )
                for row in cleaned.itertuples(index=False)
            ],
        )


def load_keyword_dataset():
    with get_connection() as connection:
        return pd.read_sql_query(
            """
            SELECT keyword, category, sample_score
            FROM keywords
            ORDER BY keyword
            """,
            connection,
        )


def save_keywords(keywords):
    cleaned = list(
        dict.fromkeys(
            str(word).strip().lower()
            for word in keywords
            if str(word).strip()
        )
    )

    with get_connection() as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO saved_keywords (keyword) VALUES (?)",
            [(word,) for word in cleaned],
        )


def load_saved_keywords():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT keyword FROM saved_keywords ORDER BY keyword"
        ).fetchall()

    return [row[0] for row in rows]


def clear_saved_keywords():
    with get_connection() as connection:
        connection.execute("DELETE FROM saved_keywords")


initialize_database()
