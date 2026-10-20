"""Cited-rule evaluator, estimator and never-deny router."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

from backend.app.calendar_ar import add_business_days, as_date, business_days_between
from backend.app.rules.plans import Plan, tope_for
from backend.app.rules.registry import REQUIRED_FIELDS


class Route(StrEnum):
    VIA_RAPIDA = "via_rapida"
    FALTA_DOCUMENTACION = "falta_doc"
    REVISION_HUMANA = "revision"


# Invariant: no reject / deny outcome exists on this enum.
assert "reject" not in Route.__members__
assert "rechazo" not in {m.lower() for m in Route.__members__}
assert set(Route) == {Route.VIA_RAPIDA, Route.FALTA_DOCUMENTACION, Route.REVISION_HUMANA}


SPECIAL_TIPOS = {"quirurgico", "internacion", "discapacidad", "exterior"}


@dataclass
class Check:
    name: str
    ok: bool
    result: str
    source: str
    citation: str | None = None
    raw_request: dict | None = None
    raw_response: dict | None = None
    missing: bool = False
    blocks_auto: bool = False


@dataclass
class Estimate:
    billed: float
    tope: float
    recognized: float
    out_of_pocket: float
    sesiones_restantes: int | None
    anual_restante: float | None
    currency: str = "ARS"
    notes: list[str] = field(default_factory=list)


@dataclass
class Evaluation:
    route: Route
    checks: list[Check]
    estimate: Estimate
    missing: list[str]
    conflicts: list[str]
    sla_business_days: int
    pay_on: date
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.value,
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "result": c.result,
                    "source": c.source,
                    "citation": c.citation,
                    "raw_request": c.raw_request,
                    "raw_response": c.raw_response,
                    "missing": c.missing,
                    "blocks_auto": c.blocks_auto,
                }
                for c in self.checks
            ],
            "estimate": {
                "billed": self.estimate.billed,
                "tope": self.estimate.tope,
                "recognized": self.estimate.recognized,
                "out_of_pocket": self.estimate.out_of_pocket,
                "sesiones_restantes": self.estimate.sesiones_restantes,
                "anual_restante": self.estimate.anual_restante,
                "currency": self.estimate.currency,
                "notes": self.estimate.notes,
            },
            "missing": self.missing,
            "conflicts": self.conflicts,
            "sla_business_days": self.sla_business_days,
            "pay_on": self.pay_on.isoformat(),
            "summary": self.summary,
        }


def evaluate(
    *,
    plan: Plan,
    tipo: str,
    fecha_prestacion: date | str,
    today: date | str,
    billed: float,
    member_active: bool,
    open_plan_ok: bool | None = None,
    fields_present: dict[str, bool],
    wscdc: dict | None,
    refeps: dict | None,
    padron: dict | None,
    cuir: dict | None = None,
    duplicate: bool = False,
    amount_mismatch: bool = False,
    currency: str = "ARS",
    fx_rate: float = 1.0,
    used_sesiones: int = 0,
    used_anual: float = 0,
    attestation: bool = False,
    historical: bool = False,
) -> Evaluation:
    today_d = as_date(today)
    fecha = as_date(fecha_prestacion)
    days = (today_d - fecha).days
    checks: list[Check] = []
    missing: list[str] = []
    conflicts: list[str] = []

    open_ok = plan.open_system if open_plan_ok is None else open_plan_ok
    checks.append(
        Check(
            name="plan_abierto",
            ok=open_ok,
            result="Plan con modalidad abierta" if open_ok else "El plan no contempla sistema abierto",
            source="CARTILLA-4021-A",
            citation="Cartilla 4021 req. (a)",
            blocks_auto=not open_ok,
        )
    )
    checks.append(
        Check(
            name="padron",
            ok=member_active,
            result="Socio activo en padrón OMINT" if member_active else "Socio no vigente",
            source="CARTILLA-4021-E",
            citation="Cartilla 4021 req. (e)",
            blocks_auto=not member_active,
        )
    )

    # 60 vs 90
    within_90 = days <= 90
    within_60 = days <= 60
    if days > 60:
        conflicts.append(
            "Cartilla 4021 nota (b) vence a 60 días; req. (g) y flyer v42 dan 90. Se aplica 90 (Ley 24.240 art. 37)."
        )
    checks.append(
        Check(
            name="plazo_90",
            ok=within_90,
            result=f"{days} días desde la prestación; ventana aplicada: 90 días",
            source="CARTILLA-4021-G-90",
            citation="Cartilla 4021 req. (g) · flyer v42 · Ley 24.240 art. 37",
            blocks_auto=not within_90,
        )
    )
    checks.append(
        Check(
            name="plazo_60_contradicho",
            ok=within_60,
            result="Dentro de 60 días" if within_60 else "Fuera de 60 días (cláusula no aplicada)",
            source="CARTILLA-4021-NOTE-B-60",
            citation="Cartilla 4021 nota (b) — contradicción",
        )
    )

    req = REQUIRED_FIELDS.get(tipo, REQUIRED_FIELDS["consulta"])
    for fname in req:
        present = bool(fields_present.get(fname))
        if not present:
            missing.append(fname)
        checks.append(
            Check(
                name=f"campo_{fname}",
                ok=present,
                result="Presente" if present else "Falta",
                source="FLYER-V42-CAMPOS",
                citation="Flyer v42 / Cartilla cuadro pp. 62–63",
                missing=not present,
            )
        )

    wscdc = wscdc or {}
    w_ok = wscdc.get("Resultado") == "A"
    checks.append(
        Check(
            name="arca_wscdc",
            ok=w_ok,
            result=f"WSCDC {wscdc.get('Resultado', '—')}",
            source="ARCA-WSCDC",
            citation="WSCDC ComprobanteConstatar",
            raw_request=wscdc.get("request"),
            raw_response=wscdc.get("response") or wscdc,
            blocks_auto=not w_ok,
        )
    )
    if w_ok:
        conflicts.append(
            "Cartilla exige original en papel (RG 1415/03). El comprobante electrónico constatado en ARCA lo sustituye."
        )

    refeps = refeps or {}
    r_ok = refeps.get("estado") == "HABILITADO"
    checks.append(
        Check(
            name="refeps",
            ok=r_ok,
            result=refeps.get("detalle") or refeps.get("estado") or "sin dato",
            source="SISA-REFEPS",
            citation="SISA WS020 getProfesional",
            raw_request=refeps.get("request"),
            raw_response=refeps.get("response") or refeps,
            blocks_auto=not r_ok,
        )
    )

    if tipo in {"kinesiologia", "laboratorio", "fonoaudiologia"}:
        cuir = cuir or {}
        c_ok = bool(cuir.get("valid"))
        if not c_ok and not fields_present.get("orden_medica") and "orden_medica" not in missing:
            missing.append("orden_medica")
        checks.append(
            Check(
                name="orden_cuir",
                ok=c_ok or bool(fields_present.get("orden_medica")),
                result="CUIR válido" if c_ok else ("Orden adjunta" if fields_present.get("orden_medica") else "Falta orden médica / CUIR"),
                source="RENAPDIS-CUIR",
                citation="Res. 1959/2024 · 2214/2025",
                raw_response=cuir,
                missing=not (c_ok or fields_present.get("orden_medica")),
            )
        )

    if duplicate:
        checks.append(
            Check(
                name="duplicado",
                ok=False,
                result="CAE ya presentado por el grupo familiar",
                source="INTEGRIDAD-DUPLICADO",
                citation="Control interno de integridad",
                blocks_auto=True,
            )
        )
    if amount_mismatch:
        checks.append(
            Check(
                name="importe_alterado",
                ok=False,
                result="Importe impreso ≠ QR ≠ ARCA",
                source="INTEGRIDAD-IMPORTE",
                citation="Cruce QR / OCR / WSCDC",
                blocks_auto=True,
            )
        )

    billed_ars = billed * fx_rate if currency != "ARS" else billed
    tope = float(tope_for(plan, tipo))
    recognized = min(billed_ars, tope) if tope else 0.0
    if not plan.open_system:
        recognized = 0.0
    anual_restante = max(0.0, plan.anual_tope - used_anual) if plan.anual_tope else None
    if anual_restante is not None:
        recognized = min(recognized, anual_restante)
    sesiones_restantes = None
    if tipo in {"kinesiologia", "fonoaudiologia"}:
        sesiones_restantes = max(0, plan.kinesio_sesiones - used_sesiones)
    if tipo in {"psicologia", "psiquiatria"}:
        sesiones_restantes = max(0, plan.salud_mental_sesiones - used_sesiones)

    notes = []
    if currency != "ARS":
        notes.append(f"Conversión BCRA vendedor × {fx_rate:.2f} (Cartilla nota c).")
    if tope and billed_ars > tope:
        notes.append(f"Tope del plan {plan.name}: $ {tope:,.0f}. El resto queda a cargo del socio.")

    estimate = Estimate(
        billed=billed_ars,
        tope=tope,
        recognized=recognized,
        out_of_pocket=max(0.0, billed_ars - recognized),
        sesiones_restantes=sesiones_restantes,
        anual_restante=anual_restante,
        notes=notes,
    )

    hard_block = any(c.blocks_auto and not c.ok for c in checks)
    has_missing = bool(missing)
    special = tipo in SPECIAL_TIPOS
    if special or (not open_ok) or (currency != "ARS" and not attestation):
        route = Route.REVISION_HUMANA
    elif hard_block:
        route = Route.REVISION_HUMANA
    elif has_missing:
        route = Route.FALTA_DOCUMENTACION
    else:
        route = Route.VIA_RAPIDA

    sla = 0 if route == Route.VIA_RAPIDA else 1
    # demo: via rápida in minutes (0 business days); else 24h = next business day
    pay_on = today_d if sla == 0 else add_business_days(today_d, sla)

    if route == Route.VIA_RAPIDA:
        summary = "Documentación completa y verificada. Pago por vía rápida."
    elif route == Route.FALTA_DOCUMENTACION:
        summary = f"Te falta {len(missing)} {'cosa' if len(missing) == 1 else 'cosas'} para enviar."
    else:
        summary = "Lo estamos verificando. El expediente llega a mesa ya armado."

    return Evaluation(
        route=route,
        checks=checks,
        estimate=estimate,
        missing=missing,
        conflicts=conflicts,
        sla_business_days=sla,
        pay_on=pay_on,
        summary=summary,
    )


def router_outcomes() -> set[str]:
    return {r.value for r in Route}
