from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY,
    story_key TEXT,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    worker_id INTEGER,
    acceptance_criteria TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_dependencies (
    story_id INTEGER NOT NULL,
    depends_on_id INTEGER NOT NULL,
    PRIMARY KEY (story_id, depends_on_id),
    FOREIGN KEY(story_id) REFERENCES stories(id),
    FOREIGN KEY(depends_on_id) REFERENCES stories(id)
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
"""


def apply_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
