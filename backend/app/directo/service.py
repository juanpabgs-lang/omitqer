"""OMINT Directo: doctor onboarding, member attestation, born-complete claims."""

from __future__ import annotations

from datetime import datetime

from backend.app.ledger import chain
from backend.app.payments import rail
from backend.app.registries import arca_padron, sisa_refeps


def onboard(conn, cuit: str, matricula: str, cbu: str) -> dict:
    padron = arca_padron.lookup(conn, cuit)
    refeps = sisa_refeps.get_profesional(conn, matricula=matricula, cuit=cuit)
    if not padron.get("found"):
        return {"ok": False, "reason": "CUIT no aparece en el padrón ARCA sandbox", "padron": padron, "refeps": refeps}
    if refeps.get("estado") != "HABILITADO":
        return {"ok": False, "reason": "Matrícula no habilitada en REFEPS", "padron": padron, "refeps": refeps}
    if not cbu or len(cbu.replace("-", "")) < 22:
        return {"ok": False, "reason": "CBU inválido"}
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE professionals SET en_directo=1, cbu=?, onboarded_at=? WHERE cuit=?",
        (cbu, now, str(cuit).replace("-", "")),
    )
    ev = chain.append(conn, {"kind": "directo_alta", "cuit": cuit, "matricula": matricula})
    row = conn.execute("SELECT * FROM professionals WHERE cuit=?", (str(cuit).replace("-", ""),)).fetchone()
    return {"ok": True, "doctor": dict(row), "hash": ev["hash"], "padron": padron, "refeps": refeps}


def start_visit(conn, professional_id: int, socio_nro: str) -> dict:
    member = conn.execute("SELECT * FROM members WHERE socio_nro=?", (socio_nro,)).fetchone()
    doc = conn.execute("SELECT * FROM professionals WHERE id=?", (professional_id,)).fetchone()
    if not member or not doc:
        return {"ok": False, "reason": "socio o profesional inexistente"}
    if not doc["en_directo"]:
        return {"ok": False, "reason": "el profesional no está en OMINT Directo"}
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """
        INSERT INTO attestations (member_id, professional_id, created_at)
        VALUES (?, ?, ?)
        """,
        (member["id"], professional_id, now),
    )
    return {
        "ok": True,
        "attestation_id": cur.lastrowid,
        "member": {"nombre": f"{member['nombre']} {member['apellido']}", "plan": member["plan"], "socio_nro": member["socio_nro"]},
        "doctor": {"nombre": doc["nombre"], "especialidad": doc["especialidad"]},
        "pending": "El socio debe confirmar en su propia app. No hay login compartido (guarda contra reembolso assistido).",
    }


def attest(conn, attestation_id: int, socio_nro: str) -> dict:
    att = conn.execute("SELECT * FROM attestations WHERE id=?", (attestation_id,)).fetchone()
    member = conn.execute("SELECT * FROM members WHERE socio_nro=?", (socio_nro,)).fetchone()
    if not att or not member or att["member_id"] != member["id"]:
        return {"ok": False, "reason": "la confirmación tiene que ser del socio, en su app"}
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("UPDATE attestations SET confirmed_at=? WHERE id=?", (now, attestation_id))
    ev = chain.append(conn, {"kind": "atestacion_socio", "attestation_id": attestation_id, "member_id": member["id"]})
    return {"ok": True, "confirmed_at": now, "hash": ev["hash"]}


def require_attestation(conn, attestation_id: int | None) -> bool:
    if not attestation_id:
        return False
    row = conn.execute("SELECT confirmed_at FROM attestations WHERE id=?", (attestation_id,)).fetchone()
    return bool(row and row["confirmed_at"])


def list_doctors(conn, directo_only: bool = False) -> list[dict]:
    q = "SELECT * FROM professionals"
    if directo_only:
        q += " WHERE en_directo=1"
    q += " ORDER BY en_directo DESC, id LIMIT 200"
    return [dict(r) for r in conn.execute(q).fetchall()]


def payouts(conn, professional_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM payments WHERE professional_id=? ORDER BY id DESC LIMIT 40",
        (professional_id,),
    ).fetchall()
    return [dict(r) for r in rows]
