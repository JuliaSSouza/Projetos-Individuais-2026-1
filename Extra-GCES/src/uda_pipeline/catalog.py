from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .config import DB_PATH, ensure_data_dirs
from .schemas import MetricRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    source_url TEXT NOT NULL,
    url_hash TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL UNIQUE,
    local_path TEXT NOT NULL,
    year INTEGER,
    quarter INTEGER,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    company TEXT NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    raw_label TEXT NOT NULL,
    value REAL,
    unit TEXT,
    currency TEXT,
    source_excerpt TEXT NOT NULL,
    page INTEGER,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metrics_period
ON metrics(company, year, quarter);
"""


class Catalog:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        ensure_data_dirs()
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def find_document(self, url_hash: str, content_hash: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM documents WHERE url_hash = ? OR content_hash = ?",
            (url_hash, content_hash),
        ).fetchone()

    def add_document(
        self,
        company: str,
        source_url: str,
        url_hash: str,
        content_hash: str,
        local_path: str,
        year: int | None,
        quarter: int | None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO documents
              (company, source_url, url_hash, content_hash, local_path, year, quarter)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (company, source_url, url_hash, content_hash, local_path, year, quarter),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def set_document_status(self, document_id: int, status: str) -> None:
        self.conn.execute("UPDATE documents SET status = ? WHERE id = ?", (status, document_id))
        self.conn.commit()

    def add_metrics(self, document_id: int, metrics: Iterable[MetricRecord]) -> None:
        rows = [
            (
                document_id,
                metric.company,
                metric.year,
                metric.quarter,
                metric.metric_name.value,
                metric.raw_label,
                metric.value,
                metric.unit,
                metric.currency,
                metric.source_excerpt,
                metric.page,
                metric.confidence,
            )
            for metric in metrics
        ]
        self.conn.executemany(
            """
            INSERT INTO metrics
              (document_id, company, year, quarter, metric_name, raw_label, value,
               unit, currency, source_excerpt, page, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def query_metrics(
        self,
        empresa: str | None = None,
        ano: int | None = None,
        trimestre: int | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if empresa:
            clauses.append("m.company = ?")
            params.append(empresa)
        if ano:
            clauses.append("m.year = ?")
            params.append(ano)
        if trimestre:
            clauses.append("m.quarter = ?")
            params.append(trimestre)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"""
            SELECT m.*, d.source_url, d.content_hash
            FROM metrics m
            JOIN documents d ON d.id = m.document_id
            {where}
            ORDER BY m.company, m.year, m.quarter, m.metric_name
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def list_documents(self) -> list[dict]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM documents ORDER BY id DESC")]
