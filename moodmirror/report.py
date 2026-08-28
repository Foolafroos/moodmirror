"""Suivi par cycles — jour / semaine / mois / année.

Le cœur du suivi quotidien : pour chaque fenêtre temporelle, on agrège
- consommation (visites, valence moyenne des contenus analysés)
- humeur (check-ins, moyenne, variance)
- corrélation contenu × humeur (Pearson sur les points horodatés)

Chaque calcul produit un *snapshot* stocké dans la table `snapshots`
(upsert par cycle), ce qui permet de reconstruire l'historique des
tendances au fil du temps — le check est reproductible et auditable.

Tout est local, aucune donnée ne quitte la machine.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Fenêtres temporelles (fuseau local de la machine)
# ---------------------------------------------------------------------------

def _local(ts: float) -> datetime:
    return datetime.fromtimestamp(ts)


def period_key(dt: datetime, period: str) -> str:
    """Clé canonique du cycle contenant `dt`."""
    if period == "daily":
        return dt.strftime("%Y-%m-%d")
    if period == "weekly":
        # Semaine ISO (lundi = début), cohérent avec strftime %G-W%V
        return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
    if period == "monthly":
        return dt.strftime("%Y-%m")
    if period == "yearly":
        return dt.strftime("%Y")
    raise ValueError(f"période inconnue : {period}")


def window_bounds(period: str, ref_dt: datetime) -> tuple[float, float]:
    """Bornes [début, fin) du cycle de `ref_dt`, en unix seconds."""
    if period == "daily":
        start = ref_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif period == "weekly":
        start = ref_dt - timedelta(days=ref_dt.weekday())  # lundi
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    elif period == "monthly":
        start = ref_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 1er du mois suivant
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    elif period == "yearly":
        start = ref_dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
    else:
        raise ValueError(f"période inconnue : {period}")
    return start.timestamp(), end.timestamp()


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def _stdev(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Corrélation de Pearson. None si < 3 points ou variance nulle."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sx, sy = _stdev(xs), _stdev(ys)
    if sx is None or sy is None or sx == 0 or sy == 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / ((len(xs) - 1) * sx * sy)


# ---------------------------------------------------------------------------
# Calcul d'un cycle
# ---------------------------------------------------------------------------

def compute_cycle(conn, period: str, ref_ts: float | None = None) -> dict:
    """Agrège un cycle et le stocke (upsert). Retourne les stats."""
    now = time.time() if ref_ts is None else ref_ts
    ref_dt = _local(now)
    pkey = period_key(ref_dt, period)
    start, end = window_bounds(period, ref_dt)

    # --- consommation ---
    row = conn.execute(
        """SELECT COUNT(*) FROM visits v
           WHERE v.ts >= ? AND v.ts < ?""", (start, end)).fetchone()
    visits = row[0]

    row = conn.execute(
        """SELECT a.valence, a.confidence, a.method, v.source
           FROM analyses a JOIN visits v ON v.id = a.visit_id
           WHERE v.ts >= ? AND v.ts < ?""", (start, end)).fetchall()
    valences = [r[0] for r in row if r[0] is not None]
    by_conf = {}
    for _, conf, method, _src in row:
        by_conf[conf] = by_conf.get(conf, 0) + 1

    # top sources
    src_rows = conn.execute(
        """SELECT source, COUNT(*) FROM visits
           WHERE ts >= ? AND ts < ? GROUP BY source ORDER BY 2 DESC""",
        (start, end)).fetchall()
    top_sources = {s: c for s, c in src_rows}

    # --- humeur ---
    moods = [r[0] for r in conn.execute(
        """SELECT mood FROM mood_checks WHERE ts >= ? AND ts < ?""",
        (start, end)).fetchall()]

    val_mean = _mean(valences)
    val_sd = _stdev(valences) if len(valences) >= 2 else None
    mood_mean = _mean(moods)
    mood_sd = _stdev(moods) if len(moods) >= 2 else None

    # --- corrélation contenu × humeur ---
    # Points horodatés : chaque visite analysée + le check-in le plus proche.
    # On ne corrèle que si les deux séries existent dans la fenêtre.
    pairs = conn.execute(
        """SELECT v.ts, a.valence FROM analyses a
           JOIN visits v ON v.id = a.visit_id
           WHERE v.ts >= ? AND v.ts < ? AND a.valence IS NOT NULL""",
        (start, end)).fetchall()
    mood_rows = conn.execute(
        """SELECT ts, mood FROM mood_checks WHERE ts >= ? AND ts < ?""",
        (start, end)).fetchall()

    xs: list[float] = []
    ys: list[float] = []
    if pairs and mood_rows:
        # pour chaque contenu, humeur du check-in le plus proche (± 12 h)
        for vts, val in pairs:
            nearest = min(mood_rows, key=lambda m: abs(m[0] - vts))
            if abs(nearest[0] - vts) <= 12 * 3600:
                xs.append(val)
                ys.append(float(nearest[1]))

    corr = pearson(xs, ys)

    def _corr_note(c: float | None, n: int) -> str:
        if c is None or n < 3:
            return "insuffisant"
        a = abs(c)
        mag = "forte" if a >= 0.7 else "modérée" if a >= 0.4 else "faible"
        sens = "positive" if c > 0 else "négative"
        return f"{mag} {sens}" if a >= 0.2 else "quasi-nulle"

    stats = {
        "period": period,
        "period_key": pkey,
        "window": [int(start), int(end)],
        "consumption": {
            "visits": visits,
            "analyzed": len(row),
            "valence_mean": round(val_mean, 3) if val_mean is not None else None,
            "valence_stdev": round(val_sd, 3) if val_sd is not None else None,
            "by_confidence": by_conf,
            "top_sources": top_sources,
        },
        "mood": {
            "checks": len(moods),
            "mean": round(mood_mean, 3) if mood_mean is not None else None,
            "stdev": round(mood_sd, 3) if mood_sd is not None else None,
            "min": min(moods) if moods else None,
            "max": max(moods) if moods else None,
        },
        "correlation": {
            "pearson": round(corr, 3) if corr is not None else None,
            "points": len(xs),
            "note": _corr_note(corr, len(xs)),
        },
    }

    conn.execute(
        """INSERT INTO snapshots (period, period_key, computed_at, stats)
           VALUES (?,?,?,?)
           ON CONFLICT(period, period_key) DO UPDATE SET
             computed_at = excluded.computed_at,
             stats = excluded.stats""",
        (period, pkey, int(now), json.dumps(stats, ensure_ascii=False)))
    conn.commit()
    return stats


# ---------------------------------------------------------------------------
# Rendu lisible
# ---------------------------------------------------------------------------

_PERIOD_LABELS = {
    "daily": "Jour", "weekly": "Semaine", "monthly": "Mois", "yearly": "Année",
}


def _fmt_corr(c: dict) -> str:
    if c["pearson"] is None:
        return f"n/a ({c['points']} pts — min 3 requis)"
    p = c["pearson"]
    arrow = "↘" if p < -0.2 else "↗" if p > 0.2 else "→"
    return f"{p:+.2f} {arrow} ({c['points']} pts, {c['note']})"


def render_cycle(stats: dict) -> str:
    label = _PERIOD_LABELS[stats["period"]]
    c = stats["consumption"]
    m = stats["mood"]
    v = f"{c['valence_mean']:+.2f}" if c["valence_mean"] is not None else "n/a"
    lines = [
        f"── {label} {stats['period_key']} " + "─" * max(0, 34 - len(stats['period_key'])),
        f"  Consommation : {c['visits']} visites, {c['analyzed']} analysés — valence moy. {v}",
    ]
    if c["by_confidence"]:
        conf = ", ".join(f"{k}:{n}" for k, n in sorted(c["by_confidence"].items()))
        lines.append(f"  Confiance    : {conf}")
    if c["top_sources"]:
        src = ", ".join(f"{s}:{n}" for s, n in c["top_sources"].items())
        lines.append(f"  Sources      : {src}")
    if m["checks"]:
        mv = f"{m['mean']:.2f}" if m["mean"] is not None else "n/a"
        lines.append(f"  Humeur       : {m['checks']} check-ins — moy. {mv}/5 (min {m['min']}, max {m['max']})")
    else:
        lines.append("  Humeur       : aucun check-in sur cette fenêtre")
    lines.append(f"  Corrél.      : {_fmt_corr(stats['correlation'])}")
    return "\n".join(lines)


def render_history(conn, period: str, limit: int = 8) -> str:
    """Historique des cycles passés (tendance dans le temps)."""
    rows = conn.execute(
        """SELECT period_key, computed_at, stats FROM snapshots
           WHERE period = ? ORDER BY period_key DESC LIMIT ?""",
        (period, limit)).fetchall()
    if not rows:
        return f"Aucun snapshot {period} encore — lance `python -m moodmirror report {period}`."
    label = _PERIOD_LABELS[period]
    out = [f"── Historique {label.lower()} (tendance) " + "─" * 18]
    for pkey, _, stats_json in reversed(rows):  # chronologique
        s = json.loads(stats_json)
        c = s["consumption"]
        m = s["mood"]
        v = f"{c['valence_mean']:+.2f}" if c["valence_mean"] is not None else " n/a"
        mv = f"{m['mean']:.1f}" if m["mean"] is not None else " n/a"
        corr = s["correlation"]["pearson"]
        cs = f"{corr:+.2f}" if corr is not None else "  n/a"
        out.append(f"  {pkey}  valence={v}  humeur={mv}/5  visits={c['visits']:>3}  corr={cs}")
    return "\n".join(out)


def run_report(periods: list[str], with_history: bool = True) -> str:
    """Calcule les cycles demandés + historique. Retourne le rapport."""
    from .db import connect
    conn = connect()
    out: list[str] = []
    for p in periods:
        stats = compute_cycle(conn, p)
        out.append(render_cycle(stats))
        if with_history:
            out.append("")
            out.append(render_history(conn, p))
        out.append("")
    conn.close()
    return "\n".join(out).rstrip()
