"""MoodMirror CLI — Phase 0.

Usage :
  python -m moodmirror collect [--days 14] [--limit 40]   collecte + analyse
  python -m moodmirror checkin [1-5] [--note "texte"]     check-in d'humeur
  python -m moodmirror status                             état de la base
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from .db import connect


def cmd_collect(args) -> None:
    from .collector import run_collect
    print(run_collect(days=args.days, analyze_limit=args.limit))


def cmd_checkin(args) -> None:
    mood = args.mood
    if mood is None:
        try:
            mood = int(input("Comment tu te sens ? (1=terrible ... 5=excellent) : "))
        except (EOFError, ValueError):
            sys.exit("Mood invalide.")
    if not 1 <= mood <= 5:
        sys.exit("Mood doit être entre 1 et 5.")
    conn = connect()
    conn.execute("INSERT INTO mood_checks (ts, mood, note) VALUES (?,?,?)",
                 (int(time.time()), mood, args.note))
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM mood_checks").fetchone()[0]
    conn.close()
    labels = {1: "terrible", 2: "bof", 3: "neutre", 4: "bien", 5: "excellent"}
    print(f"Check-in enregistré : {mood} ({labels[mood]}) — total {n} check-ins.")


def cmd_status(args) -> None:
    conn = connect()
    rows = conn.execute(
        """SELECT COUNT(*) FROM visits""").fetchone()[0]
    ana = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    mood = conn.execute("SELECT COUNT(*) FROM mood_checks").fetchone()[0]
    by_method = dict(conn.execute(
        "SELECT method, COUNT(*) FROM analyses GROUP BY method").fetchall())
    st = conn.execute("SELECT value FROM meta WHERE key='screen_time_status'").fetchone()
    recent = conn.execute(
        """SELECT v.ts, a.valence, a.confidence, v.title
           FROM analyses a JOIN visits v ON v.id = a.visit_id
           ORDER BY v.ts DESC LIMIT 5""").fetchall()
    conn.close()

    print(f"Visites : {rows} | Analysées : {ana} | Check-ins humeur : {mood}")
    if by_method:
        print("Méthodes d'analyse :", json.dumps(by_method, ensure_ascii=False))
    if st:
        print("Screen Time :", st[0])
    if recent:
        print("\nDerniers contenus analysés :")
        for ts, val, conf, title in recent:
            when = time.strftime("%d/%m %H:%M", time.localtime(ts))
            t = (title or "")[:52]
            v = f"{val:+.2f}" if val is not None else "  n/a"
            print(f"  {when}  valence={v}  conf={conf:<6} {t}")


def main() -> None:
    p = argparse.ArgumentParser(prog="moodmirror", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="collecter + analyser les contenus")
    c.add_argument("--days", type=int, default=14)
    c.add_argument("--limit", type=int, default=40,
                   help="max de contenus à analyser par run (fetch réseau)")
    c.set_defaults(fn=cmd_collect)

    m = sub.add_parser("checkin", help="enregistrer un check-in d'humeur")
    m.add_argument("mood", nargs="?", type=int, choices=[1, 2, 3, 4, 5])
    m.add_argument("--note", default=None)
    m.set_defaults(fn=cmd_checkin)

    s = sub.add_parser("status", help="état de la base locale")
    s.set_defaults(fn=cmd_status)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
