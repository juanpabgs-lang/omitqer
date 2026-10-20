"""Court / regulator evidence pack as PDF + JSON."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from backend.app.ledger.chain import canonical_json, public_key_pem


def build_pack(conn, claim_id: int) -> dict:
    claim = conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if not claim:
        raise ValueError("claim not found")
    member = conn.execute("SELECT * FROM members WHERE id=?", (claim["member_id"],)).fetchone()
    checks = conn.execute("SELECT * FROM claim_checks WHERE claim_id=?", (claim_id,)).fetchall()
    events = conn.execute(
        "SELECT * FROM claim_events WHERE claim_id=? ORDER BY id", (claim_id,)
    ).fetchall()
    contract = conn.execute(
        "SELECT * FROM contracts WHERE member_id=? ORDER BY id DESC LIMIT 1",
        (claim["member_id"],),
    ).fetchone()
    ledger = conn.execute(
        "SELECT * FROM ledger_events WHERE payload LIKE ? ORDER BY seq",
        (f'%\"claim_id\": {claim_id}%',),
    ).fetchall()
    pack = {
        "claim": dict(claim),
        "member": {
            "socio_nro": member["socio_nro"] if member else None,
            "nombre": f"{member['nombre']} {member['apellido']}" if member else None,
            "plan": member["plan"] if member else None,
            "dni": member["dni"] if member else None,
        },
        "contract": (
            {
                "version": contract["version"],
                "sha256": contract["sha256"],
                "signed_at": contract["signed_at"],
                "plan": contract["plan"],
            }
            if contract
            else None
        ),
        "checks": [dict(c) for c in checks],
        "timeline": [dict(e) for e in events],
        "ledger": [
            {"seq": r["seq"], "hash": r["hash"], "prev_hash": r["prev_hash"], "created_at": r["created_at"]}
            for r in ledger
        ],
        "public_key": public_key_pem(),
    }
    pack["pack_sha256"] = hashlib.sha256(canonical_json(pack).encode()).hexdigest()
    return pack


def render_pdf(pack: dict) -> bytes:
    buf = BytesIO()
    c = Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFillColorRGB(0.0, 0.145, 0.514)
    c.rect(0, h - 28 * mm, w, 28 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(18 * mm, h - 14 * mm, "Expediente de evidencia · OMINT Reintegros")
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, h - 21 * mm, f"Claim {pack['claim']['public_id']}  ·  SHA-256 {pack['pack_sha256'][:16]}…")

    y = h - 40 * mm
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "Socio y contrato")
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    m = pack["member"]
    c.drawString(18 * mm, y, f"{m.get('nombre')}  ·  Socio {m.get('socio_nro')}  ·  Plan {m.get('plan')}")
    y -= 5 * mm
    if pack.get("contract"):
        ct = pack["contract"]
        c.drawString(18 * mm, y, f"Contrato {ct['version']}  firmado {ct['signed_at']}  hash {ct['sha256'][:20]}…")
        y -= 6 * mm
    else:
        c.drawString(18 * mm, y, "Contrato: no archivado")
        y -= 6 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "Verificaciones")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    for chk in pack["checks"][:18]:
        mark = "OK" if chk.get("ok") else "OBS"
        line = f"[{mark}] {chk.get('name')} — {chk.get('result')}  ({chk.get('source')})"
        c.drawString(18 * mm, y, line[:110])
        y -= 4.2 * mm
        if y < 30 * mm:
            c.showPage()
            y = h - 20 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "Cadena de integridad")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    for ev in pack["ledger"][:12]:
        c.drawString(18 * mm, y, f"#{ev['seq']}  {ev['hash'][:28]}…  prev {ev['prev_hash'][:16]}…")
        y -= 4.2 * mm
        if y < 24 * mm:
            break

    c.setFont("Helvetica", 7)
    c.drawString(18 * mm, 14 * mm, "Sello Ed25519 · datos sintéticos · Ley 25.326 · no es un documento oficial de OMINT")
    c.showPage()
    c.save()
    return buf.getvalue()


def write_pack_files(pack: dict, dest: Path) -> tuple[Path, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    j = dest / f"{pack['claim']['public_id']}.json"
    p = dest / f"{pack['claim']['public_id']}.pdf"
    j.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    p.write_bytes(render_pdf(pack))
    return j, p
