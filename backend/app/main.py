"""OMINT Reintegros demo API. Port 8018. Synthetic data only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from backend.app import services
from backend.app.db import DB_PATH, connect, init_db
from backend.app.defensa import service as defensa
from backend.app.directo import service as directo
from backend.app.integrity import provider_audit, refund_checks
from backend.app.ledger import chain, value
from backend.app.ledger.pack_pdf import build_pack, render_pdf
from backend.app.market import price_map
from backend.app.payments import rail
from backend.app.roi import model as roi_model
from backend.app.rules.registry import conflicts, rules_as_dicts
from backend.app.sap import outbox
from backend.app.seed import seed
from backend.app import discapacidad

app = FastAPI(title="OMINT Reintegros", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5178", "http://localhost:5178"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_CONN = None


def db():
    global _CONN
    if _CONN is None:
        if not DB_PATH.exists():
            seed()
        _CONN = connect()
        init_db(_CONN)
    return _CONN


@app.on_event("startup")
def _startup():
    db()


@app.get("/api/health")
def health():
    return {"ok": True, "synthetic": True, "ley": "25.326"}


@app.get("/api/samples")
def samples():
    rows = db().execute("SELECT key, title, subtitle, expected_route FROM samples").fetchall()
    return [dict(r) for r in rows]


class PrecheckIn(BaseModel):
    sample_key: str | None = None
    overrides: dict | None = None


@app.post("/api/precheck")
def precheck(body: PrecheckIn):
    conn = db()
    try:
        if not body.sample_key:
            raise HTTPException(400, "sample_key requerido")
        return services.precheck(conn, sample_key=body.sample_key, overrides=body.overrides)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/precheck/upload")
async def precheck_upload(file: UploadFile = File(...)):
    conn = db()
    try:
        data = await file.read()
        return services.precheck(conn, upload={"data": data, "filename": file.filename or ""})
    except ValueError as e:
        raise HTTPException(400, str(e))


class SubmitIn(BaseModel):
    sample_key: str
    overrides: dict | None = None
    attestation_id: int | None = None


@app.post("/api/claims")
def create_claim(body: SubmitIn):
    conn = db()
    bundle = services.precheck(conn, sample_key=body.sample_key, overrides=body.overrides)
    try:
        result = services.submit(conn, bundle, attestation_id=body.attestation_id)
        conn.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/claims")
def list_claims(queue: str | None = None, limit: int = 80):
    conn = db()
    q = """
        SELECT c.*, m.nombre, m.apellido, m.socio_nro, m.plan
        FROM claims c JOIN members m ON m.id=c.member_id
        WHERE c.historical=0
    """
    args: list = []
    if queue == "revision":
        q += " AND c.status IN ('en_revision','auditoria_medica')"
    elif queue == "falta":
        q += " AND c.status='falta_documentacion'"
    elif queue == "via_rapida":
        q += " AND c.route='via_rapida'"
    elif queue == "pagados":
        q += " AND c.status='pagado'"
    q += " ORDER BY c.id DESC LIMIT ?"
    args.append(limit)
    rows = conn.execute(q, args).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: int, audit: bool = False):
    detail = services.claim_detail(db(), claim_id, include_diagnosis=audit)
    if not detail:
        raise HTTPException(404, "no existe")
    return detail


class ActionIn(BaseModel):
    action: str
    by: str
    reason: str | None = None
    second: str | None = None


@app.post("/api/claims/{claim_id}/actions")
def claim_action(claim_id: int, body: ActionIn):
    try:
        result = services.act(db(), claim_id, body.action, by=body.by, reason=body.reason, second=body.second)
        db().commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/expediente/{claim_id}/evidencia")
def evidencia(claim_id: int):
    pack = build_pack(db(), claim_id)
    return pack


@app.get("/api/expediente/{claim_id}/evidencia.pdf")
def evidencia_pdf(claim_id: int):
    pack = build_pack(db(), claim_id)
    return Response(render_pdf(pack), media_type="application/pdf")


@app.get("/api/verificar/{digest}")
def verificar(digest: str):
    conn = db()
    row = conn.execute("SELECT * FROM ledger_events WHERE hash=?", (digest,)).fetchone()
    chain_ok = chain.verify_chain(conn)
    return {"found": row is not None, "event": dict(row) if row else None, "chain": chain_ok, "public_key": chain.public_key_pem()}


@app.get("/api/ledger/valor")
def ledger_valor():
    return {"totals": value.totals(db()), "recent": value.recent(db(), 50), "chain": chain.verify_chain(db())}


class ConfirmIn(BaseModel):
    by: str


@app.post("/api/ledger/valor/{event_id}/confirmar")
def confirm_value(event_id: int, body: ConfirmIn):
    row = value.confirm(db(), event_id, body.by)
    db().commit()
    if not row:
        raise HTTPException(404, "evento no propuesto")
    return row


@app.get("/api/integridad/reintegros")
def integridad_reintegros():
    return refund_checks.scan(db())


@app.get("/api/integridad/liquidaciones")
def integridad_liqs():
    return provider_audit.list_liquidaciones(db())


@app.get("/api/integridad/liquidaciones/{lid}")
def integridad_liq(lid: int):
    return provider_audit.audit_liquidacion(db(), lid)


@app.post("/api/integridad/debitos/{debit_id}/confirmar")
def confirmar_debito(debit_id: int, body: ConfirmIn):
    try:
        out = provider_audit.confirm_debit(db(), debit_id, body.by)
        db().commit()
        return out
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/roi")
def roi():
    computed = roi_model.compute()
    mc = roi_model.monte_carlo()
    return {
        **computed,
        "monte_carlo": mc,
        "ramp": roi_model.ramp(computed["run_rate_ars"]),
        "flywheel": [roi_model.flywheel(m) for m in (0, 3, 6, 12, 18)],
    }


class RoiSimIn(BaseModel):
    inputs: dict[str, float]


@app.post("/api/roi/simular")
def roi_sim(body: RoiSimIn):
    base = {i.key: i for i in roi_model.DEFAULTS}
    varied = []
    for k, item in base.items():
        val = body.inputs.get(k, item.value)
        varied.append(roi_model.Input(item.key, val, item.unit, item.label, item.provenance, item.source))
    computed = roi_model.compute(varied)
    return {**computed, "monte_carlo": roi_model.monte_carlo(varied), "ramp": roi_model.ramp(computed["run_rate_ars"])}


@app.get("/api/direccion/stalls")
def stalls():
    conn = db()
    rows = conn.execute(
        """
        SELECT stall_stage AS stage, COUNT(*) AS n,
               AVG(CASE WHEN days_to_pay IS NOT NULL THEN days_to_pay END) AS avg_days,
               SUM(bounced) AS bounced
        FROM claims WHERE historical=1
        GROUP BY stall_stage
        """
    ).fetchall()
    reasons = conn.execute(
        """
        SELECT bounce_reason AS reason, COUNT(*) AS n
        FROM claims WHERE historical=1 AND bounce_reason IS NOT NULL
        GROUP BY bounce_reason ORDER BY n DESC
        """
    ).fetchall()
    sla = conn.execute(
        """
        SELECT
          SUM(CASE WHEN days_to_pay IS NOT NULL AND days_to_pay <= 7 THEN 1 ELSE 0 END) AS within_7,
          SUM(CASE WHEN days_to_pay IS NOT NULL THEN 1 ELSE 0 END) AS paid,
          COUNT(*) AS n
        FROM claims WHERE historical=1
        """
    ).fetchone()
    return {"stages": [dict(r) for r in rows], "reasons": [dict(r) for r in reasons], "sla": dict(sla)}


@app.get("/api/direccion/churn")
def churn():
    conn = db()
    rows = conn.execute(
        """
        SELECT plan, COUNT(*) AS n,
               SUM(churned) AS bajas,
               AVG(churn_risk) AS risk,
               SUM(CASE WHEN churn_reason='reintegro' THEN 1 ELSE 0 END) AS por_reintegro
        FROM members GROUP BY plan
        """
    ).fetchall()
    at_risk = conn.execute(
        """
        SELECT socio_nro, nombre, apellido, plan, zona, tenure_months, churn_risk, holdout
        FROM members WHERE churned=0 AND churn_risk > 0.42
        ORDER BY churn_risk DESC LIMIT 30
        """
    ).fetchall()
    return {
        "by_plan": [dict(r) for r in rows],
        "at_risk": [dict(r) for r in at_risk],
        "holdout": "El 1/7 de socios es holdout: no reciben outreach de retención. El pago rápido nunca se retacea.",
        "note": "Sin datos de salud. Etiquetas sintéticas. Con datos reales se mide.",
    }


@app.get("/api/mercado")
def mercado():
    return price_map.build(db())


class CapSimIn(BaseModel):
    plan: str
    tope: float


@app.post("/api/mercado/simular-tope")
def sim_tope(body: CapSimIn):
    return price_map.simulate_cap(db(), body.plan, body.tope)


@app.get("/api/socio/presupuesto")
def presupuesto(especialidad: str, zona: str, plan: str, professional_id: int | None = None):
    return price_map.estimate_out_of_pocket(db(), especialidad, zona, plan, professional_id)


class OnboardIn(BaseModel):
    cuit: str
    matricula: str
    cbu: str


@app.post("/api/directo/onboard")
def directo_onboard(body: OnboardIn):
    out = directo.onboard(db(), body.cuit, body.matricula, body.cbu)
    db().commit()
    return out


@app.get("/api/directo/doctors")
def directo_docs(only: bool = False):
    return directo.list_doctors(db(), directo_only=only)


class VisitIn(BaseModel):
    professional_id: int
    socio_nro: str


@app.post("/api/directo/atender")
def directo_atender(body: VisitIn):
    out = directo.start_visit(db(), body.professional_id, body.socio_nro)
    db().commit()
    return out


class AttestIn(BaseModel):
    attestation_id: int
    socio_nro: str


@app.post("/api/directo/attest")
def directo_attest(body: AttestIn):
    out = directo.attest(db(), body.attestation_id, body.socio_nro)
    db().commit()
    return out


@app.get("/api/directo/payouts/{professional_id}")
def directo_payouts(professional_id: int):
    return directo.payouts(db(), professional_id)


@app.get("/api/defensa/denuncias")
def denuncias():
    return defensa.list_denuncias(db())


@app.post("/api/defensa/{denuncia_id}/descargo")
def hacer_descargo(denuncia_id: int):
    try:
        out = defensa.descargo(db(), denuncia_id)
        db().commit()
        out.pop("pdf_bytes", None)
        return out
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/contratos/{member_id}")
def contratos(member_id: int):
    return defensa.contract_vault(db(), member_id)


@app.get("/api/reglas")
def reglas():
    return {"rules": rules_as_dicts(), "conflicts": conflicts()}


@app.get("/api/sap/outbox")
def sap_outbox():
    return outbox.list_outbox(db())


class ClawbackIn(BaseModel):
    claim_id: int
    amount: float
    reason: str
    by: str


@app.post("/api/clawbacks")
def clawback(body: ClawbackIn):
    out = rail.request_clawback(db(), claim_id=body.claim_id, amount=body.amount, reason=body.reason, by=body.by)
    db().commit()
    return out


class ClawbackApprove(BaseModel):
    by: str


@app.post("/api/clawbacks/{cid}/aprobar")
def clawback_ok(cid: int, body: ClawbackApprove):
    try:
        out = rail.approve_clawback(db(), cid, body.by)
        db().commit()
        return out
    except ValueError as e:
        raise HTTPException(400, str(e))


class SignIn(BaseModel):
    by: str


@app.get("/api/discapacidad/planillas")
def disc_list():
    return discapacidad.list_sheets(db())


@app.post("/api/discapacidad/planillas/{sheet_id}/firmar")
def disc_sign(sheet_id: int, body: SignIn):
    out = discapacidad.sign_sheet(db(), sheet_id, body.by)
    db().commit()
    return out


class CrossIn(BaseModel):
    fingerprint: str
    payer: str = "OMINT"


@app.post("/api/cross-payer")
def cross_payer(body: CrossIn):
    out = discapacidad.cross_payer_register(db(), body.fingerprint, body.payer)
    db().commit()
    return out


@app.get("/api/cross-payer/{fingerprint}")
def cross_get(fingerprint: str):
    return discapacidad.cross_payer_lookup(db(), fingerprint)


@app.get("/api/story")
def story():
    return {
        "chapters": [
            {"id": "hub", "path": "/", "title": "La ventaja que no se copia"},
            {"id": "socio", "path": "/socio", "title": "El socio ve el monto y lo que falta"},
            {"id": "prestador", "path": "/prestador", "title": "OMINT Directo"},
            {"id": "integridad", "path": "/integridad", "title": "Integridad de pago"},
            {"id": "caso", "path": "/caso", "title": "El dinero, medido"},
            {"id": "direccion", "path": "/direccion", "title": "Dirección"},
            {"id": "operaciones", "path": "/operaciones", "title": "Mesa"},
            {"id": "defensa", "path": "/defensa", "title": "Res. 951/2026"},
            {"id": "sap", "path": "/sap", "title": "SAP clean core"},
        ]
    }


def run():
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8018, reload=False)


if __name__ == "__main__":
    run()
