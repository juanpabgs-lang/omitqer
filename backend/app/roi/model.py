"""ROI model. Every input is labeled assumption | source | measured."""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass

USD_ARS = 1525.0  # mayorista 20-oct-2026
MODULE_ARS = 435_748.51  # haber mínimo oct-2026, Res. 951 Anexo III art. 10


@dataclass
class Input:
    key: str
    value: float
    unit: str
    label: str
    provenance: str  # assumption | source | measured
    source: str


DEFAULTS: list[Input] = [
    Input("members", 262_620, "socios", "Padrón SSSalud jun-2026", "source", "SSSalud RNEMP jun-2026"),
    Input("ars_pmpm", 420_000, "ARS/socio/mes", "Prima media (mix corporativo/individual)", "assumption", "Broker CABA 30 años, mix no publicado"),
    Input("medical_ratio", 0.82, "ratio", "Siniestralidad médica", "assumption", "Rango sectorial; OMINT no publica P&L"),
    Input("auditable_share", 0.60, "ratio", "Gasto médico auditable por convenio", "assumption", "Cartilla + clínicas propias"),
    Input("extra_debit_rate", 0.005, "ratio", "Débito incremental por el motor", "assumption", "Caso hospitalario publicado: 6,43% debitado"),
    Input("gross_churn", 0.16, "ratio", "Baja bruta anual", "assumption", "Caída neta 275.329→262.620 dic-25/jun-26"),
    Input("churn_claims_share", 0.12, "ratio", "Bajas donde el reintegro pesa", "assumption", "Encuesta MiObraSocial abr-jun 2026 n=2000"),
    Input("churn_reduction", 0.35, "ratio", "Reducción lograda en ese segmento", "assumption", "Holdout; con datos reales se mide"),
    Input("margin", 0.12, "ratio", "Margen de contribución por socio retenido", "assumption", "No hay EBITDA público"),
    Input("minutes_saved", 11.0, "min", "Minutos ahorrados por reclamo", "assumption", "Mesa actual vs expediente pre-armado"),
    Input("claims_per_year", 262_600, "reclamos", "Volumen anual de reintegros", "assumption", "1 reclamo / socio / año en planes abiertos, extrapolado"),
    Input("hours_fte_year", 1760.0, "h", "Horas FTE / año (8×220)", "assumption", "Convenio de comercio"),
    Input("cost_per_fte", 32_900_000.0, "ARS/año", "Costo cargado por FTE de mesa", "assumption", "Para que 27 FTE ≈ ARS 0,9B"),
    Input("refund_spend", 11_800_000_000.0, "ARS", "Gasto anual en reintegros", "assumption", "≈0,9% de prima"),
    Input("refund_leak", 0.03, "ratio", "Fuga en reintegros (duplicados, importes, matrículas)", "assumption", "Neurotech Brasil marca hasta 8%"),
    Input("refund_catch", 0.60, "ratio", "Proporción de fuga detectada", "assumption", "Precisión/recall del sandbox"),
    Input("complaints", 80.0, "casos", "Denuncias SSSalud / año", "assumption", "Sin serie pública OMINT"),
    Input("modules_per_sanction", 15.0, "módulos", "Multa media en módulos", "assumption", "Anexo III no publica la tabla; módulo = haber mínimo"),
    Input("sanction_rate_now", 0.25, "ratio", "Probabilidad de sanción hoy", "assumption", "Res. 951/2026: silencio = presunción"),
    Input("sanction_rate_after", 0.05, "ratio", "Probabilidad de sanción con expediente", "assumption", "Respuesta en horas + pack sellado"),
    Input("float_cost", 100_000_000.0, "ARS", "Costo de float por pagar antes", "assumption", "Días ganados × tasa"),
    Input("guarantee_credits", 100_000_000.0, "ARS", "Créditos de garantía / clawbacks", "assumption", "Recupero por próxima factura"),
    Input("solution_usd", 450_000.0, "USD", "Costo año 1 (build + operate)", "assumption", "Ancla Siblings Software USD 25–180k/tipo doc"),
    Input("usd_ars", USD_ARS, "ARS/USD", "Dólar mayorista 20-oct-2026", "source", "Ámbito / Infobae 20-oct-2026"),
    Input("module_ars", MODULE_ARS, "ARS", "Valor del módulo Res. 951", "source", "ANSES Res. 284/2026 · $435.748,51"),
]


def _idx(inputs: list[Input]) -> dict[str, Input]:
    return {i.key: i for i in inputs}


def compute(inputs: list[Input] | None = None) -> dict:
    inp = _idx(inputs or DEFAULTS)
    v = {k: i.value for k, i in inp.items()}
    revenue = v["members"] * v["ars_pmpm"] * 12
    integrity = revenue * v["medical_ratio"] * v["auditable_share"] * v["extra_debit_rate"]
    kept = v["members"] * v["gross_churn"] * v["churn_claims_share"] * v["churn_reduction"]
    retention = kept * v["ars_pmpm"] * 12 * v["margin"]
    hours = v["minutes_saved"] * v["claims_per_year"] / 60
    fte = hours / v["hours_fte_year"]
    capacity = fte * v["cost_per_fte"]
    refund = v["refund_spend"] * v["refund_leak"] * v["refund_catch"]
    sanction_delta = v["sanction_rate_now"] - v["sanction_rate_after"]
    regulatory = v["complaints"] * sanction_delta * v["modules_per_sanction"] * v["module_ars"]
    gross = integrity + retention + capacity + refund + regulatory
    costs = v["float_cost"] + v["guarantee_credits"]
    run_rate = gross - costs
    solution_ars = v["solution_usd"] * v["usd_ars"]
    year1 = run_rate - solution_ars
    usd = run_rate / v["usd_ars"]
    payback_months = (solution_ars / (run_rate / 12)) if run_rate > 0 else None
    levers = [
        {
            "id": "integridad_prestadores",
            "name": "Integridad de pago a prestadores de cartilla",
            "ars": integrity,
            "formula": "prima × siniestralidad × % auditable × débito incremental",
            "note": "El caso hospitalario publicado debitó 6,43% de lo facturado. El default usa 0,5%.",
        },
        {
            "id": "retencion",
            "name": "Retención de socios de plan abierto",
            "ars": retention,
            "formula": "socios × baja bruta × share reintegro × reducción × margen",
            "note": f"{kept:,.0f} socios retenidos / año",
        },
        {
            "id": "capacidad",
            "name": "Capacidad de mesa reasignada a servicio",
            "ars": capacity,
            "formula": "minutos × reclamos / 60 / horas FTE × costo FTE",
            "note": f"{fte:.1f} FTE liberados. No es un recorte: se reasignan.",
        },
        {
            "id": "reintegros",
            "name": "Integridad de reintegros",
            "ars": refund,
            "formula": "gasto reintegros × fuga × captura",
            "note": "Duplicados, importes alterados, matrículas, topes mal aplicados.",
        },
        {
            "id": "regulatorio",
            "name": "Exposición Res. 951/2026",
            "ars": regulatory,
            "formula": "denuncias × ΔP(sanción) × módulos × valor módulo",
            "note": "Pagar después de una INTIMA es regularización extemporánea (art. 4).",
        },
    ]
    return {
        "inputs": [asdict(i) for i in inp.values()],
        "revenue_ars": revenue,
        "levers": levers,
        "gross_ars": gross,
        "costs_ars": costs,
        "run_rate_ars": run_rate,
        "run_rate_usd": usd,
        "solution_ars": solution_ars,
        "year1_ars": year1,
        "payback_months": payback_months,
        "kept_members": kept,
        "fte_freed": fte,
        "disclaimer": "Simulado. Cada input es supuesto, fuente o medido. OMINT no publica ingresos: la prima es un supuesto editable.",
    }


def monte_carlo(inputs: list[Input] | None = None, n: int = 800, seed: int = 42) -> dict:
    base = _idx(inputs or DEFAULTS)
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        varied = []
        for item in base.values():
            if item.provenance == "source":
                varied.append(item)
                continue
            # log-normal-ish jitter ±35%
            factor = math.exp(rng.gauss(0, 0.18))
            varied.append(Input(item.key, item.value * factor, item.unit, item.label, item.provenance, item.source))
        samples.append(compute(varied)["run_rate_ars"])
    samples.sort()
    def pct(p: float) -> float:
        i = min(len(samples) - 1, max(0, int(p * (len(samples) - 1))))
        return samples[i]
    return {
        "n": n,
        "p10": pct(0.10),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "mean": sum(samples) / len(samples),
    }


def ramp(run_rate: float, months: int = 12) -> list[dict]:
    # 20% m1, 45% m3, 75% m6, 100% m12
    curve = []
    for m in range(1, months + 1):
        if m <= 1:
            frac = 0.20
        elif m <= 3:
            frac = 0.20 + 0.25 * ((m - 1) / 2)
        elif m <= 6:
            frac = 0.45 + 0.30 * ((m - 3) / 3)
        else:
            frac = 0.75 + 0.25 * ((m - 6) / 6)
        curve.append({"month": m, "frac": round(frac, 3), "ars": run_rate * frac / 12})
    return curve


def flywheel(month: int = 12) -> dict:
    # doctors, born-complete share, STP
    doctors = min(80 + month * 18, 600)
    born_complete = min(0.12 + month * 0.04, 0.62)
    stp = min(0.45 + month * 0.022, 0.70)
    return {
        "month": month,
        "doctors_directo": doctors,
        "born_complete": born_complete,
        "stp": stp,
        "projection": "Cada decisión humana recalibra umbrales. Brasil = 40% automático.",
    }
