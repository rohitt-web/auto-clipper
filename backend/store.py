import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "jobs.sqlite3"

def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
            message TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL,
            caption_language TEXT NOT NULL DEFAULT 'auto', duration REAL,
            moments_json TEXT NOT NULL DEFAULT '[]', clips_json TEXT NOT NULL DEFAULT '[]',
            error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")

def create_job(job_id: str, url: str, language: str):
    with _connect() as conn:
        conn.execute("INSERT INTO jobs(id,status,progress,message,source_url,caption_language) VALUES(?,?,?,?,?,?)",
                     (job_id, "queued", 0, "Waiting for a worker", url, language))

def update_job(job_id: str, **fields: Any):
    allowed = {"status", "progress", "message", "duration", "moments_json", "clips_json", "error"}
    values = {k: v for k, v in fields.items() if k in allowed}
    if not values:
        return
    for key in ("moments_json", "clips_json"):
        if key in values and not isinstance(values[key], str):
            values[key] = json.dumps(values[key], ensure_ascii=False)
    assignments = ", ".join(f"{key}=?" for key in values)
    with _connect() as conn:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE id=?", (*values.values(), job_id))

def get_job(job_id: str):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["moments"] = json.loads(data.pop("moments_json") or "[]")
    data["clips"] = json.loads(data.pop("clips_json") or "[]")
    return data
