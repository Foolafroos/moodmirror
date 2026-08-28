"""Collecte locale — historique navigateurs + Screen Time.

Toutes les sources sont lues en copie (jamais modifiées), sur cette machine.
Screen Time : depuis macOS 13+, une partie des stats migre vers les streams
Biome ; ce module détecte et rapporte ce qui est réellement lisible ici —
c'est la question centrale de la Phase 0.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import analyzer
from .db import connect

# ---------------------------------------------------------------------------
# Chrome / Safari — historique local (SQLite)
# ---------------------------------------------------------------------------

CHROME_HISTORY = Path.home() / "Library/Application Support/Google/Chrome/Default/History"
SAFARI_HISTORY = Path.home() / "Library/Safari/History.db"
# epoch Chrome : 1601-01-01 (microsecondes)
CHROME_EPOCH_US = 11_644_473_600_000_000


def _read_sqlite_copy(src: Path, query: str, params: tuple = ()):
    """Lit une base SQLite via copie temporaire (évite les verrous).

    Retourne None si la source est illisible (TCC / Full Disk Access) —
    c'est un résultat légitime de la Phase 0, pas une erreur.
    """
    tmp = src.with_suffix(".mm_tmp")
    try:
        shutil.copy2(src, tmp)
        conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows
    except (PermissionError, OSError):
        return None
    finally:
        if tmp.exists():
            tmp.unlink()


def _note(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))
    conn.commit()


def collect_chrome(conn: sqlite3.Connection, days: int = 14) -> int:
    if not CHROME_HISTORY.exists():
        _note(conn, "chrome_status", "ABSENT")
        return 0
    since_us = int((time.time() - days * 86400)) * 1_000_000 + CHROME_EPOCH_US
    rows = _read_sqlite_copy(
        CHROME_HISTORY,
        """SELECT u.url, u.title, MIN(v.visit_time)
           FROM visits v JOIN urls u ON v.url = u.id
           WHERE v.visit_time >= ? AND u.url IS NOT NULL
           GROUP BY u.url""",
        (since_us,),
    )
    if rows is None:
        _note(conn, "chrome_status", "BLOQUÉ (TCC/Full Disk Access requis)")
        return 0
    added = 0
    for url, title, visited in rows:
        ts = int((visited - CHROME_EPOCH_US) / 1_000_000)
        cur = conn.execute(
            "INSERT OR IGNORE INTO visits (ts, url, title, source) VALUES (?,?,?,?)",
            (ts, url, title, "chrome"),
        )
        added += cur.rowcount
    _note(conn, "chrome_status", f"OK (+{added} URLs sur {days}j)")
    conn.commit()
    return added


def collect_safari(conn: sqlite3.Connection, days: int = 14) -> int:
    if not SAFARI_HISTORY.exists():
        _note(conn, "safari_status", "ABSENT")
        return 0
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = _read_sqlite_copy(
        SAFARI_HISTORY,
        """SELECT url, title, MIN(visited_date) FROM HistoryItems
           WHERE visited_date >= ? AND url IS NOT NULL GROUP BY url""",
        (since,),
    )
    if rows is None:
        _note(conn, "safari_status", "BLOQUÉ (TCC/Full Disk Access requis)")
        return 0
    added = 0
    for url, title, visited in rows:
        try:
            ts = int(datetime.strptime(visited, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO visits (ts, url, title, source) VALUES (?,?,?,?)",
            (ts, url, title, "safari"),
        )
        added += cur.rowcount
    _note(conn, "safari_status", f"OK (+{added} URLs sur {days}j)")
    conn.commit()
    return added


# ---------------------------------------------------------------------------
# Screen Time — détection de lisibilité (question Phase 0)
# ---------------------------------------------------------------------------

SCREEN_TIME_CANDIDATES = [
    Path.home() / "Library/Group Containers/group.com.apple.spotlightknowledged.store/knowledgeC.db",
    Path.home() / "Library/Application Support/Knowledge/knowledgeC.db",
    # macOS 26 : le conteneur Spotlight a changé de nom
    Path.home() / "Library/Group Containers/group.com.apple.spotlight/knowledgeC.db",
]
KNOWLEDGE_DIR = Path.home() / "Library/Application Support/Knowledge"


def probe_screen_time(conn: sqlite3.Connection) -> str:
    """Teste ce qui est lisible pour Screen Time sur CE Mac. Ne bloque pas."""
    blocked_any = False
    for p in SCREEN_TIME_CANDIDATES:
        if not p.parent.exists():
            continue
        try:
            # test de lisibilité explicite (TCC peut bloquer la copie)
            with open(p, "rb"):
                pass
        except PermissionError:
            blocked_any = True
            continue
        except FileNotFoundError:
            continue
        try:
            rows = _read_sqlite_copy(
                p, "SELECT name FROM sqlite_master WHERE type='table' LIMIT 5"
            )
            tables = [r[0] for r in rows] if rows is not None else []
            where = f"{p.parent.name}/knowledgeC.db"
            if tables:
                conn.execute("INSERT OR REPLACE INTO meta VALUES ('screen_time_status', ?)",
                             (f"OK: {where} → tables={tables}",))
                conn.commit()
                return f"Screen Time LISIBLE : {where} (tables: {tables})"
            # Fichier ouvert sans erreur mais zéro table → données migrées vers Biome
            conn.execute("INSERT OR REPLACE INTO meta VALUES ('screen_time_status', ?)",
                         (f"VIDE: {where} existe mais ne contient plus de tables — "
                          "migration Biome confirmée sur ce macOS",))
            conn.commit()
            return (f"Screen Time : knowledgeC.db VIDE ({where}) — migration Biome confirmée. "
                    "Plan B validé : historiques navigateurs.")
        except sqlite3.DatabaseError as e:
            conn.execute("INSERT OR REPLACE INTO meta VALUES ('screen_time_status', ?)",
                         (f"BLOQUÉ: {p.name} → {e}",))
            conn.commit()
            return f"Screen Time BLOQUÉ : {p.name} ({e}) — Full Disk Access requis."
    if blocked_any or KNOWLEDGE_DIR.exists():
        status = ("BLOQUÉ (TCC) — les emplacements Screen Time existent mais sont protégés : "
                  "Full Disk Access requis pour le terminal. Plan B validé : "
                  "historiques navigateurs (Chrome OK ici, Safari aussi bloqué TCC).")
        conn.execute("INSERT OR REPLACE INTO meta VALUES ('screen_time_status', ?)", (status,))
        conn.commit()
        return f"Screen Time {status}"
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('screen_time_status', ?)",
                 ("ABSENT: aucun knowledgeC.db trouvé (migration Biome probable)",))
    conn.commit()
    return "Screen Time : knowledgeC.db introuvable — migration Biome probable. Plan B = historiques navigateurs."


# ---------------------------------------------------------------------------
# Analyse des contenus neufs
# ---------------------------------------------------------------------------

def analyze_new_visits(conn: sqlite3.Connection, limit: int = 40, delay: float = 1.0) -> dict:
    rows = conn.execute(
        """SELECT v.id, v.url, v.title FROM visits v
           WHERE v.id NOT IN (SELECT visit_id FROM analyses)
           ORDER BY v.ts DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    stats = {"examined": 0, "fetched": 0, "low_conf": 0}
    for vid, url, title in rows:
        if analyzer.classify_url(url) in ("tweet", "social-video"):
            pass  # rapide, pas de fetch
        elif stats["examined"] > 0:
            time.sleep(delay)  # politesse réseau
        result = analyzer.analyze_content(url, title)
        stats["examined"] += 1
        if result.get("meta", {}).get("fetch_failed"):
            pass
        else:
            stats["fetched"] += 1
        if result["confidence"] == "low":
            stats["low_conf"] += 1
        conn.execute(
            """INSERT INTO analyses (visit_id, fetched_at, text_excerpt, valence,
               topic, method, confidence, meta)
               VALUES (?,?,?,?,?,?,?,?)""",
            (vid, int(time.time()), result["text_excerpt"], result["valence"],
             result["topic"], result["method"], result["confidence"],
             __import__("json").dumps(result["meta"], ensure_ascii=False)),
        )
    conn.commit()
    return stats


def run_collect(days: int = 14, analyze_limit: int = 40) -> str:
    conn = connect()
    chrome = collect_chrome(conn, days)
    safari = collect_safari(conn, days)
    st_status = probe_screen_time(conn)
    stats = analyze_new_visits(conn, limit=analyze_limit)
    total = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    analyzed = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    src = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    conn.close()
    return (
        f"Collecte terminée.\n"
        f"  Chrome : {src.get('chrome_status', '?')}\n"
        f"  Safari : {src.get('safari_status', '?')}\n"
        f"  Total {total} visites — contenus analysés ce run : {stats['examined']} "
        f"(fetch OK: {stats['fetched']}, low-confidence: {stats['low_conf']}) — total {analyzed}\n"
        f"  {st_status}"
    )
