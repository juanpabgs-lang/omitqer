"""Sandbox instant payout and clawback via the next OMINT invoice."""

from __future__ import annotations

import uuid
from datetime import datetime


def payout(conn, *, claim_id: int, member_id: int, amount: float, rail: str = "transferencia_instantanea") -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    tx = f"NF-{uuid.uuid4().hex[:10].upper()}"
    conn.execute(
        """
        INSERT INTO payments (claim_id, member_id, amount, rail, status, created_at, tx_ref)
        VALUES (?, ?, ?, ?, 'acreditado', ?, ?)
        """,
        (claim_id, member_id, amount, rail, now, tx),
    )
    conn.execute("UPDATE claims SET paid_at=?, status='pagado' WHERE id=?", (now, claim_id))
    return {"tx_ref": tx, "rail": rail, "amount": amount, "at": now, "sandbox": True}


def payout_doctor(conn, *, claim_id: int, professional_id: int, amount: float) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    tx = f"DIR-{uuid.uuid4().hex[:10].upper()}"
    conn.execute(
        """
        INSERT INTO payments (claim_id, professional_id, amount, rail, status, created_at, tx_ref)
        VALUES (?, ?, ?, 'omint_directo', 'acreditado', ?, ?)
        """,
        (claim_id, professional_id, amount, now, tx),
    )
    return {"tx_ref": tx, "amount": amount, "at": now, "sandbox": True}


def request_clawback(conn, *, claim_id: int, amount: float, reason: str, by: str) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO clawbacks (claim_id, amount, reason, status, requested_by, created_at)
        VALUES (?, ?, ?, 'pendiente_segunda_firma', ?, ?)
        """,
        (claim_id, amount, reason, by, now),
    )
    return {"id": cur.lastrowid, "status": "pendiente_segunda_firma"}


def approve_clawback(conn, clawback_id: int, by: str) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    row = conn.execute("SELECT * FROM clawbacks WHERE id=?", (clawback_id,)).fetchone()
    if not row:
        raise ValueError("clawback not found")
    if row["requested_by"] == by:
        raise ValueError("la segunda firma no puede ser la misma persona")
    conn.execute(
        "UPDATE clawbacks SET status='descontado_proxima_factura', approved_by=? WHERE id=?",
        (by, clawback_id),
    )
    return {"id": clawback_id, "status": "descontado_proxima_factura", "at": now}
