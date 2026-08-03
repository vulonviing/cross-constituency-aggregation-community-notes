from __future__ import annotations

import gzip
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _compress(value: str | None) -> bytes | None:
    if value is None:
        return None
    return gzip.compress(value.encode("utf-8"), compresslevel=6)


def _decompress(value: bytes | None) -> str | None:
    if value is None:
        return None
    return gzip.decompress(value).decode("utf-8")


def _replace(tmp: Path, destination: Path) -> None:
    with tmp.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(tmp, destination)


class CallStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False, timeout=60)
        self._conn.row_factory = sqlite3.Row
        # WAL is unsafe on many NFS implementations. SCCKN stores run state on /work.
        self._conn.execute("PRAGMA journal_mode=DELETE")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA busy_timeout=60000")
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logical_key TEXT NOT NULL,
                stage TEXT NOT NULL,
                note_id TEXT NOT NULL,
                round_no INTEGER NOT NULL,
                run_no INTEGER NOT NULL,
                attempt_no INTEGER NOT NULL,
                seed INTEGER,
                status TEXT NOT NULL,
                error_type TEXT,
                error_message TEXT,
                http_status INTEGER,
                returned_model TEXT,
                finish_reason TEXT,
                label TEXT,
                score INTEGER,
                reason TEXT,
                raw_response_gzip BLOB,
                reasoning_gzip BLOB,
                prompt_tokens INTEGER,
                cached_tokens INTEGER,
                completion_tokens INTEGER,
                reasoning_tokens INTEGER,
                latency_ms INTEGER,
                created_at TEXT NOT NULL,
                UNIQUE(logical_key, attempt_no)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_attempts_stage_note ON attempts(stage, note_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_attempts_logical_status ON attempts(logical_key, status)"
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def integrity_check(self) -> None:
        row = self._conn.execute("PRAGMA integrity_check").fetchone()
        if row is None or str(row[0]).lower() != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {row[0] if row else 'no result'}")

    def attempt_count(self, logical_key: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM attempts WHERE logical_key = ?",
            (logical_key,),
        ).fetchone()
        return int(row["count"])

    def next_attempt_no(self, logical_key: str) -> int:
        return self.attempt_count(logical_key) + 1

    def save_attempt(self, record: dict[str, Any]) -> None:
        values = dict(record)
        values.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        values["raw_response_gzip"] = _compress(values.pop("raw_response", None))
        values["reasoning_gzip"] = _compress(values.pop("reasoning", None))
        columns = [
            "logical_key", "stage", "note_id", "round_no", "run_no",
            "attempt_no", "seed", "status", "error_type", "error_message",
            "http_status", "returned_model", "finish_reason", "label", "score",
            "reason", "raw_response_gzip", "reasoning_gzip", "prompt_tokens",
            "cached_tokens", "completion_tokens", "reasoning_tokens", "latency_ms",
            "created_at",
        ]
        with self._lock:
            self._conn.execute(
                f"INSERT INTO attempts ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                [values.get(column) for column in columns],
            )
            self._conn.commit()

    def valid_call(self, logical_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT * FROM attempts
            WHERE logical_key = ? AND status = 'valid'
            ORDER BY id DESC LIMIT 1
            """,
            (logical_key,),
        ).fetchone()
        return dict(row) if row else None

    def valid_calls(self, stage: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT a.* FROM attempts a
            JOIN (
                SELECT logical_key, MAX(id) AS max_id
                FROM attempts WHERE stage = ? AND status = 'valid'
                GROUP BY logical_key
            ) latest ON a.id = latest.max_id
            ORDER BY a.note_id, a.round_no, a.run_no
            """,
            (stage,),
        ).fetchall()
        return [dict(row) for row in rows]

    def all_attempts(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT id, logical_key, stage, note_id, round_no, run_no,
                   attempt_no, seed, status, error_type, error_message, http_status,
                   returned_model, finish_reason, label, score, reason,
                   CASE WHEN reasoning_gzip IS NOT NULL THEN 1 ELSE 0 END AS reasoning_present,
                   prompt_tokens,
                   cached_tokens, completion_tokens, reasoning_tokens,
                   latency_ms, created_at
            FROM attempts ORDER BY id
            """,
            self._conn,
        )

    def backup(self, destination: Path) -> None:
        tmp = destination.with_name(destination.name + ".tmp")
        tmp.unlink(missing_ok=True)
        target = sqlite3.connect(tmp)
        try:
            with self._lock:
                self._conn.backup(target)
            target.execute("PRAGMA integrity_check")
        finally:
            target.close()
        _replace(tmp, destination)

    def export(self, parquet_path: Path, raw_path: Path) -> None:
        attempts = self.all_attempts()
        parquet_tmp = parquet_path.with_name(parquet_path.stem + ".tmp.parquet")
        attempts.to_parquet(parquet_tmp, index=False)
        _replace(parquet_tmp, parquet_path)

        raw_tmp = raw_path.with_name(raw_path.name + ".tmp")
        rows = self._conn.execute("SELECT * FROM attempts ORDER BY id").fetchall()
        with gzip.open(raw_tmp, "wt", encoding="utf-8") as handle:
            for row in rows:
                value = dict(row)
                value["raw_response"] = _decompress(value.pop("raw_response_gzip"))
                value["reasoning"] = _decompress(value.pop("reasoning_gzip"))
                handle.write(json.dumps(value, ensure_ascii=False) + "\n")
        _replace(raw_tmp, raw_path)
