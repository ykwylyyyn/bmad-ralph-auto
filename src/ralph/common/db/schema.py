from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    worker_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    health TEXT NOT NULL,
    worktree_path TEXT NOT NULL,
    pid INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS healing_attempts (
    id INTEGER PRIMARY KEY,
    story_id INTEGER NOT NULL,
    layer TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(story_id) REFERENCES stories(id)
);

CREATE TABLE IF NOT EXISTS diagnostic_reports (
    id INTEGER PRIMARY KEY,
    story_id INTEGER NOT NULL UNIQUE,
    root_cause TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    suggested_fix TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(story_id) REFERENCES stories(id)
);
"""


def apply_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
