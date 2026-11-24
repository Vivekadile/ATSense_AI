import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "atsense.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                ats_score REAL NOT NULL,
                result_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_analysis(filename: str, ats_score: float, result: dict):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO analyses (filename, ats_score, result_json) VALUES (?, ?, ?)",
            (filename, ats_score, json.dumps(result)),
        )
        return cursor.lastrowid

def get_history():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, filename, ats_score, created_at FROM analyses ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

def get_analysis(analysis_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, filename, ats_score, result_json, created_at "
            "FROM analyses WHERE id = ?",
            (analysis_id,),
        ).fetchone()

        if row is None:
            return None

        record = dict(row)
        record["result"] = json.loads(record.pop("result_json"))
        return record
