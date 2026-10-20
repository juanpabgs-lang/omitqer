"""Value events. Only status=confirmado counts toward ROI."""

from __future__ import annotations

from datetime import datetime


PROPOSED = "propuesto"
CONFIRMED = "confirmado"


def propose(
    conn,
    *,
    kind: str,
    ars: float,
    evidence_hash: str,
    claim_id: int | None = None,
    liquidacion_id: int | None = None,
    note: str | None = None,
    created_at: str | None = None,
) -> int:
    created_at = created_at or datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO value_events (kind, ars, status, evidence_hash, claim_id, liquidacion_id, created_at, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (kind, ars, PROPOSED, evidence_hash, claim_id, liquidacion_id, created_at, note),
    )
    return int(cur.lastrowid)


def confirm(conn, event_id: int, by: str) -> dict | None:
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE value_events SET status=?, confirmed_by=?, confirmed_at=?
        WHERE id=? AND status=?
        """,
        (CONFIRMED, by, now, event_id, PROPOSED),
    )
    row = conn.execute("SELECT * FROM value_events WHERE id=?", (event_id,)).fetchone()
    return dict(row) if row else None


def totals(conn) -> dict:
    rows = conn.execute(
        """
        SELECT status, kind, SUM(ars) AS ars, COUNT(*) AS n
        FROM value_events
        GROUP BY status, kind
        """
    ).fetchall()
    confirmed = 0.0
    proposed = 0.0
    by_kind: dict[str, dict] = {}
    for r in rows:
        bucket = confirmed if r["status"] == CONFIRMED else proposed
        if r["status"] == CONFIRMED:
            confirmed += r["ars"]
        else:
            proposed += r["ars"]
        by_kind.setdefault(r["kind"], {"propuesto": 0.0, "confirmado": 0.0, "n": 0})
        by_kind[r["kind"]][r["status"]] = r["ars"]
        by_kind[r["kind"]]["n"] += r["n"]
    return {
        "confirmado_ars": confirmed,
        "propuesto_ars": proposed,
        "by_kind": by_kind,
        "rule": "Solo los eventos confirmados por una persona cuentan para el ROI.",
    }


def recent(conn, limit: int = 40) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM value_events ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
