"""Claim pipeline: read document, verify, evaluate, persist, pay."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image

from backend.app.calendar_ar import as_date
from backend.app.db import SAMPLES_DIR
from backend.app.directo import service as directo
from backend.app.ingest import ocr, pdf
from backend.app.ingest.qr_arca import ArcaQr, decode_image, parse_url
from backend.app.ledger import chain, value
from backend.app.payments import rail
from backend.app.registries import arca_wscdc, renapdis_cuir, sisa_refeps
from backend.app.registries import padron_omint
from backend.app.rules.engine import Route, evaluate
from backend.app.rules.plans import plan_for
from backend.app.sap import outbox


def _today(conn) -> str:
    row = conn.execute("SELECT v FROM meta WHERE k='today'").fetchone()
    return row["v"] if row else datetime.now().date().isoformat()


def read_document(data: bytes, filename: str = "") -> dict:
    image, pdf_text = pdf.load_image_or_pdf(data, filename)
    qr = decode_image(image) if image is not None else None
    ocr_res = ocr.run_ocr(image) if image is not None else ocr.OcrResult(text=pdf_text)
    sha = hashlib.sha256(data).hexdigest()
    return {
        "qr": qr.to_dict() if qr else None,
        "ocr": ocr_res.as_dict(),
        "sha256": sha,
        "image": image,
        "fuera_sandbox": False,
    }


def precheck(conn, *, sample_key: str | None = None, upload: dict | None = None, overrides: dict | None = None) -> dict:
    today = _today(conn)
    overrides = overrides or {}
    if sample_key:
        sample = conn.execute("SELECT * FROM samples WHERE key=?", (sample_key,)).fetchone()
        if not sample:
            raise ValueError("sample not found")
        path = Path(sample["path"])
        data = path.read_bytes()
        read = read_document(data, path.name)
        member = conn.execute("SELECT * FROM members WHERE id=?", (sample["member_id"],)).fetchone()
        meta = json.loads(conn.execute("SELECT v FROM meta WHERE k=?", (f"sample:{sample_key}",)).fetchone()["v"])
    elif upload:
        read = read_document(upload["data"], upload.get("filename", ""))
        # refuse to persist real uploads
        read["fuera_sandbox"] = True
        member = conn.execute("SELECT * FROM members WHERE plan IN ('GLOBAL','PREMIUM') LIMIT 1").fetchone()
        meta = {"tipo": "consulta", "professional_id": None}
        if read["qr"]:
            qr = ArcaQr(**read["qr"])
            w = arca_wscdc.constat(conn, qr)
            if w["Resultado"] == "A":
                pass
            else:
                # process in memory only
                pass
        return _evaluate_bundle(conn, member=dict(member), read=read, meta=meta, today=today, overrides=overrides, persist=False)
    else:
        raise ValueError("sample_key or upload required")

    return _evaluate_bundle(conn, member=dict(member), read=read, meta=meta, today=today, overrides=overrides, persist=False, sample_key=sample_key)


def _evaluate_bundle(conn, *, member, read, meta, today, overrides, persist, sample_key=None) -> dict:
    tipo = overrides.get("tipo") or meta.get("tipo") or "consulta"
    qr = ArcaQr(**read["qr"]) if read.get("qr") else None
    billed = float(overrides.get("importe") or (qr.importe if qr else meta.get("importe", 0)))
    fecha = overrides.get("fecha") or (qr.fecha if qr else meta.get("fecha") or today)
    prof_id = meta.get("professional_id")
    prof = conn.execute("SELECT * FROM professionals WHERE id=?", (prof_id,)).fetchone() if prof_id else None
    if qr and not prof:
        prof = conn.execute("SELECT * FROM professionals WHERE cuit=?", (str(qr.cuit),)).fetchone()

    wscdc = arca_wscdc.constat(conn, qr) if qr else {"Resultado": "R", "response": {"Resultado": "R", "Observaciones": [{"Code": 100, "Msg": "sin QR"}]}}
    refeps = sisa_refeps.get_profesional(
        conn,
        matricula=overrides.get("matricula") or (prof["matricula"] if prof else None),
        cuit=str(qr.cuit) if qr else (prof["cuit"] if prof else None),
    )
    padron = padron_omint.lookup(conn, member_id=member["id"])
    cuir = renapdis_cuir.validate(overrides.get("cuir") or meta.get("cuir"))

    fields = {
        "fecha": True,
        "nombre_socio": True,
        "diagnostico": bool(meta.get("diagnostico")) or bool(overrides.get("diagnostico")),
        "profesional": prof is not None,
        "detalle": True,
        "importe": billed > 0,
        "firma_sello": not meta.get("missing_stamp"),
        "sesiones": bool(meta.get("sesiones") or overrides.get("sesiones")),
        "orden_medica": bool(overrides.get("cuir") or meta.get("orden_medica") or cuir.get("valid")),
        "pieza": True,
        "pasaporte": tipo != "exterior" or bool(overrides.get("pasaporte")),
        "traduccion": tipo != "exterior" or True,
    }
    if meta.get("force_missing"):
        for k in meta["force_missing"]:
            fields[k] = bool(overrides.get(k) or (k == "orden_medica" and cuir.get("valid")))

    duplicate = bool(meta.get("duplicate"))
    amount_mismatch = bool(meta.get("amount_mismatch"))
    currency = meta.get("currency", "ARS")
    fx = float(meta.get("fx", 1))
    plan = plan_for(member["plan"])
    ev = evaluate(
        plan=plan,
        tipo=tipo,
        fecha_prestacion=fecha,
        today=today,
        billed=billed,
        member_active=padron["active"],
        fields_present=fields,
        wscdc=wscdc,
        refeps=refeps,
        padron=padron,
        cuir=cuir,
        duplicate=duplicate,
        amount_mismatch=amount_mismatch,
        currency=currency,
        fx_rate=fx,
        used_sesiones=int(meta.get("used_sesiones", 4)),
        used_anual=float(meta.get("used_anual", 180_000)),
        attestation=bool(meta.get("attestation")),
    )
    return {
        "member": {
            "id": member["id"],
            "nombre": f"{member['nombre']} {member['apellido']}",
            "socio_nro": member["socio_nro"],
            "plan": member["plan"],
            "zona": member["zona"],
        },
        "professional": dict(prof) if prof else None,
        "read": {k: v for k, v in read.items() if k != "image"},
        "evaluation": ev.as_dict(),
        "meta": {**meta, "tipo": tipo, "fecha": fecha, "importe": billed, "sample_key": sample_key},
        "today": today,
        "fuera_sandbox": read.get("fuera_sandbox", False),
    }


def submit(conn, bundle: dict, *, attestation_id: int | None = None) -> dict:
    if bundle.get("fuera_sandbox"):
        raise ValueError("documento fuera del sandbox: se procesó en memoria y no se guarda")
    ev = bundle["evaluation"]
    member = bundle["member"]
    meta = bundle["meta"]
    today = bundle["today"]
    public_id = f"R-{today.replace('-', '')[2:]}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat(timespec="seconds")
    if attestation_id and not directo.require_attestation(conn, attestation_id):
        raise ValueError("OMINT Directo exige confirmación del socio en su app")
    qr = bundle["read"].get("qr")
    invoice_id = None
    if qr:
        row = conn.execute(
            "SELECT id FROM invoices WHERE cuit=? AND pto_vta=? AND tipo_cmp=? AND nro_cmp=?",
            (str(qr["cuit"]), qr["ptoVta"], qr["tipoCmp"], qr["nroCmp"]),
        ).fetchone()
        invoice_id = row["id"] if row else None
    cur = conn.execute(
        """
        INSERT INTO claims (
            public_id, member_id, professional_id, invoice_id, tipo, route, status,
            importe, estimado, moneda, fecha_prestacion, created_at, sample_key,
            attestation_id, notes, diagnosis_hidden, historical
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            public_id,
            member["id"],
            (bundle.get("professional") or {}).get("id"),
            invoice_id,
            meta["tipo"],
            ev["route"],
            "en_revision" if ev["route"] == Route.REVISION_HUMANA.value else (
                "falta_documentacion" if ev["route"] == Route.FALTA_DOCUMENTACION.value else "aprobado"
            ),
            ev["estimate"]["billed"],
            ev["estimate"]["recognized"],
            ev["estimate"]["currency"],
            meta["fecha"],
            now,
            meta.get("sample_key"),
            attestation_id,
            ev["summary"],
            meta.get("diagnostico"),
        ),
    )
    claim_id = int(cur.lastrowid)
    for chk in ev["checks"]:
        conn.execute(
            """
            INSERT INTO claim_checks (claim_id, name, ok, result, source, citation, raw_request, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                chk["name"],
                int(chk["ok"]),
                chk["result"],
                chk["source"],
                chk.get("citation"),
                json.dumps(chk.get("raw_request") or {}, ensure_ascii=False),
                json.dumps(chk.get("raw_response") or {}, ensure_ascii=False),
            ),
        )
    conn.execute(
        "INSERT INTO claim_events (claim_id, kind, payload, created_at) VALUES (?, ?, ?, ?)",
        (claim_id, "creado", json.dumps({"route": ev["route"]}, ensure_ascii=False), now),
    )
    led = chain.append(conn, {"kind": "claim_creado", "claim_id": claim_id, "public_id": public_id, "route": ev["route"]})
    minutes = 11 if ev["route"] == Route.VIA_RAPIDA.value else 6
    value.propose(
        conn,
        kind="minutos_ahorrados",
        ars=minutes / 60 * (32_900_000 / 1760),
        evidence_hash=led["hash"],
        claim_id=claim_id,
        note=f"{minutes} minutos de mesa",
    )
    paid = None
    if ev["route"] == Route.VIA_RAPIDA.value and ev["estimate"]["recognized"] > 0:
        paid = rail.payout(conn, claim_id=claim_id, member_id=member["id"], amount=ev["estimate"]["recognized"])
        mem = conn.execute("SELECT * FROM members WHERE id=?", (member["id"],)).fetchone()
        outbox.enqueue(conn, {**dict(conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()), "id": claim_id}, dict(mem))
        conn.execute(
            "INSERT INTO claim_events (claim_id, kind, payload, created_at) VALUES (?, ?, ?, ?)",
            (claim_id, "pagado", json.dumps(paid, ensure_ascii=False), paid["at"]),
        )
        chain.append(conn, {"kind": "pago", "claim_id": claim_id, "tx": paid["tx_ref"], "ars": paid["amount"]})
    claim = dict(conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone())
    return {"claim": claim, "evaluation": ev, "payment": paid, "ledger_hash": led["hash"]}


def claim_detail(conn, claim_id: int, *, include_diagnosis: bool = False) -> dict:
    claim = conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if not claim:
        return {}
    member = conn.execute("SELECT * FROM members WHERE id=?", (claim["member_id"],)).fetchone()
    checks = [dict(r) for r in conn.execute("SELECT * FROM claim_checks WHERE claim_id=?", (claim_id,)).fetchall()]
    events = [dict(r) for r in conn.execute("SELECT * FROM claim_events WHERE claim_id=? ORDER BY id", (claim_id,)).fetchall()]
    prof = None
    if claim["professional_id"]:
        prof = conn.execute("SELECT * FROM professionals WHERE id=?", (claim["professional_id"],)).fetchone()
    out = {
        "claim": dict(claim),
        "member": {
            "id": member["id"],
            "nombre": f"{member['nombre']} {member['apellido']}",
            "socio_nro": member["socio_nro"],
            "plan": member["plan"],
            "zona": member["zona"],
            "cbu": member["cbu"],
        },
        "professional": dict(prof) if prof else None,
        "checks": checks,
        "timeline": events,
    }
    if include_diagnosis:
        out["diagnosis"] = claim["diagnosis_hidden"]
    else:
        out["claim"]["diagnosis_hidden"] = None
    return out


def act(conn, claim_id: int, action: str, *, by: str, reason: str | None = None, second: str | None = None) -> dict:
    claim = conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    if not claim:
        raise ValueError("claim not found")
    now = datetime.now().isoformat(timespec="seconds")
    if action == "aprobar":
        conn.execute("UPDATE claims SET status='aprobado' WHERE id=?", (claim_id,))
        mem = conn.execute("SELECT * FROM members WHERE id=?", (claim["member_id"],)).fetchone()
        paid = rail.payout(conn, claim_id=claim_id, member_id=claim["member_id"], amount=claim["estimado"])
        outbox.enqueue(conn, {**dict(claim), "id": claim_id, "estimado": claim["estimado"]}, dict(mem))
        chain.append(conn, {"kind": "aprobado", "claim_id": claim_id, "by": by})
        return {"status": "pagado", "payment": paid}
    if action == "pedir_documentos":
        conn.execute("UPDATE claims SET status='falta_documentacion' WHERE id=?", (claim_id,))
        chain.append(conn, {"kind": "pedido_docs", "claim_id": claim_id, "by": by, "reason": reason})
        return {"status": "falta_documentacion"}
    if action == "auditoria_medica":
        conn.execute("UPDATE claims SET status='auditoria_medica' WHERE id=?", (claim_id,))
        return {"status": "auditoria_medica"}
    if action == "negar":
        if not reason or not second or second == by:
            raise ValueError("una negativa exige motivo citado y segunda firma distinta")
        conn.execute("UPDATE claims SET status='negado_humano', notes=? WHERE id=?", (reason, claim_id))
        chain.append(conn, {"kind": "negado_humano", "claim_id": claim_id, "by": by, "second": second, "reason": reason})
        return {"status": "negado_humano"}
    raise ValueError("acción desconocida")
