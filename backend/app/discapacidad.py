"""Digital disability attendance sheet. Replaces handwritten INS-SER-DIS-004."""

from __future__ import annotations

from datetime import datetime

from backend.app.ledger import chain


def seed_sheet(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS disability_sheets (
            id INTEGER PRIMARY KEY,
            member_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            period TEXT NOT NULL,
            days TEXT NOT NULL,
            signed_by TEXT,
            signed_at TEXT,
            cud TEXT,
            cud_ok INTEGER
        )
        """
    )
    exists = conn.execute("SELECT COUNT(*) AS n FROM disability_sheets").fetchone()["n"]
    if exists:
        return
    member = conn.execute("SELECT id FROM members WHERE plan='PREMIUM' LIMIT 1").fetchone()
    if not member:
        return
    conn.execute(
        """
        INSERT INTO disability_sheets (member_id, provider, period, days, cud, cud_ok)
        VALUES (?, 'Centro Sintético Sur', '2026-09', ?, 'CUD-SYN-88421', 1)
        """,
        (member["id"], "1,2,3,4,5,8,9,10"),
    )


def list_sheets(conn) -> list[dict]:
    seed_sheet(conn)
    rows = conn.execute(
        """
        SELECT s.*, m.nombre, m.apellido, m.socio_nro
        FROM disability_sheets s JOIN members m ON m.id=s.member_id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def sign_sheet(conn, sheet_id: int, by: str) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE disability_sheets SET signed_by=?, signed_at=? WHERE id=?",
        (by, now, sheet_id),
    )
    ev = chain.append(conn, {"kind": "planilla_discapacidad", "sheet_id": sheet_id, "by": by})
    return {"ok": True, "hash": ev["hash"], "signed_at": now}


def cross_payer_lookup(conn, invoice_fingerprint: str) -> dict:
    """Hashed CAE registry. No health data. Later: multi-payer."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cross_payer (
            fingerprint TEXT PRIMARY KEY,
            payer TEXT NOT NULL,
            seen_at TEXT NOT NULL
        )
        """
    )
    row = conn.execute("SELECT * FROM cross_payer WHERE fingerprint=?", (invoice_fingerprint,)).fetchone()
    return {"seen": bool(row), "entry": dict(row) if row else None}


def cross_payer_register(conn, invoice_fingerprint: str, payer: str = "OMINT") -> dict:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cross_payer (
            fingerprint TEXT PRIMARY KEY,
            payer TEXT NOT NULL,
            seen_at TEXT NOT NULL
        )
        """
    )
    now = datetime.now().isoformat(timespec="seconds")
    existing = cross_payer_lookup(conn, invoice_fingerprint)
    if existing["seen"]:
        return {"duplicate": True, **existing, "note": "El mismo comprobante ya fue presentado a otro pagador."}
    conn.execute(
        "INSERT INTO cross_payer (fingerprint, payer, seen_at) VALUES (?, ?, ?)",
        (invoice_fingerprint, payer, now),
    )
    return {"duplicate": False, "payer": payer, "seen_at": now}
