"""SQLite local — schéma + connexion.

La base vit dans ~/.moodmirror/moodmirror.db (hors repo, jamais commitée).
Aucune donnée ne quitte la machine.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".moodmirror" / "moodmirror.db"

SCHEMA = """
-- Pages vues (historique navigateur, dédupliqué par source+url)
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY,
    ts INTEGER NOT NULL,              -- unix seconds (premier visit retenu)
    url TEXT NOT NULL,
    title TEXT,
    source TEXT NOT NULL,             -- chrome | safari
    UNIQUE(source, url)
);
CREATE INDEX IF NOT EXISTS idx_visits_ts ON visits(ts);

-- Compréhension du contenu (valence locale, thème, méthode)
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    fetched_at INTEGER NOT NULL,      -- unix seconds
    text_excerpt TEXT,                -- extrait analysé (borné, ~2k chars)
    valence REAL,                     -- -1..+1
    topic TEXT,                       -- proxy de thème (mot-clés dominants)
    method TEXT NOT NULL,             -- lexicon | llm | title-only
    confidence TEXT NOT NULL DEFAULT 'medium',  -- high | medium | low
    meta TEXT                         -- JSON libre (type média, erreurs...)
);
CREATE INDEX IF NOT EXISTS idx_analyses_visit ON analyses(visit_id);

-- Check-ins d'humeur (1 = terrible ... 5 = excellent)
CREATE TABLE IF NOT EXISTS mood_checks (
    id INTEGER PRIMARY KEY,
    ts INTEGER NOT NULL,
    mood INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 5),
    note TEXT
);

-- État du sync (clé/valeur) — pour la collecte incrémentale
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
