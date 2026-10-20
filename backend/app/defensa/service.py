"""Res. SSSalud 951/2026 desk."""

from __future__ import annotations

from datetime import datetime

from backend.app.calendar_ar import add_business_days, as_date, business_days_between
from backend.app.ledger import chain
from backend.app.ledger.pack_pdf import build_pack, render_pdf


def list_denuncias(conn, today: str | None = None) -> list[dict]:
    today = today or datetime.now().date().isoformat()
    rows = conn.execute(
        """
        SELECT d.*, m.nombre, m.apellido, m.socio_nro, m.plan
        FROM denuncias d JOIN members m ON m.id=d.member_id
        ORDER BY d.deadline
        """
    ).fetchall()
    out = []
    for r in rows:
        left = business_days_between(today, r["deadline"])
        out.append({**dict(r), "dias_restantes": left, "vencida": left < 0})
    return out


def descargo(conn, denuncia_id: int) -> dict:
    d = conn.execute("SELECT * FROM denuncias WHERE id=?", (denuncia_id,)).fetchone()
    if not d:
        raise ValueError("denuncia not found")
    member = conn.execute("SELECT * FROM members WHERE id=?", (d["member_id"],)).fetchone()
    contract = conn.execute(
        "SELECT * FROM contracts WHERE member_id=? ORDER BY id DESC LIMIT 1",
        (d["member_id"],),
    ).fetchone()
    pack = None
    pdf = b""
    if d["claim_id"]:
        pack = build_pack(conn, d["claim_id"])
        pdf = render_pdf(pack)
    letter = (
        f"SSSalud — respuesta a denuncia {d['public_id']}\n\n"
        f"OMINT S.A. de Servicios acredita en forma fehaciente, suficiente y documentada "
        f"(Res. 951/2026 art. 4) el cumplimiento de la obligación preexistente relativa a "
        f"{member['nombre']} {member['apellido']}, socio {member['socio_nro']}, plan {member['plan']}.\n\n"
        f"Asunto: {d['asunto']}\n\n"
        f"Se acompaña: (i) contrato {contract['version'] if contract else 'n/d'} hash {contract['sha256'] if contract else 'n/d'}; "
        f"(ii) expediente de evidencia sellado Ed25519; (iii) constancias ARCA/REFEPS.\n\n"
        f"El silencio no opera: esta presentación interrumpe la presunción iuris tantum del art. 2.\n"
    )
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("UPDATE denuncias SET status='respondida', descargo=? WHERE id=?", (letter, denuncia_id))
    ev = chain.append(conn, {"kind": "descargo_951", "denuncia_id": denuncia_id, "public_id": d["public_id"]})
    return {
        "letter": letter,
        "pack": pack,
        "pdf_bytes": pdf,
        "hash": ev["hash"],
        "responded_at": now,
    }


def contract_vault(conn, member_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, version, plan, sha256, signed_at FROM contracts WHERE member_id=? ORDER BY id",
        (member_id,),
    ).fetchall()
    return [dict(r) for r in rows]
