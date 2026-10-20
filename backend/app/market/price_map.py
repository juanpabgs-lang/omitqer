"""Verified private-market price map from ARCA-checked claims."""

from __future__ import annotations

from collections import defaultdict

from backend.app.rules.plans import PLANS


INFLATION_M = 0.017  # ~1.7% / month 2026
CAP_ASOF = "2026-04-01"
GALENO_CONSULTA = 14_000  # Plan 550, published


def build(conn) -> dict:
    rows = conn.execute(
        """
        SELECT p.especialidad, p.zona, c.importe, c.fecha_prestacion, p.en_directo,
               p.nombre, p.id AS professional_id, p.precio_base, m.plan
        FROM claims c
        JOIN professionals p ON p.id = c.professional_id
        JOIN members m ON m.id = c.member_id
        WHERE c.tipo IN ('consulta', 'kinesiologia', 'odontologia', 'psicologia')
        """
    ).fetchall()
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    doctors: dict[int, dict] = {}
    for r in rows:
        buckets[(r["especialidad"], r["zona"])].append(r["importe"])
        d = doctors.setdefault(
            r["professional_id"],
            {
                "id": r["professional_id"],
                "nombre": r["nombre"],
                "especialidad": r["especialidad"],
                "zona": r["zona"],
                "en_directo": r["en_directo"],
                "precio_base": r["precio_base"],
                "n": 0,
                "sum": 0.0,
                "visits": 0,
            },
        )
        d["n"] += 1
        d["sum"] += r["importe"]
        d["visits"] += 1

    cells = []
    for (esp, zona), prices in sorted(buckets.items()):
        prices = sorted(prices)
        n = len(prices)
        mid = prices[n // 2]
        p25 = prices[int(n * 0.25)]
        p75 = prices[min(n - 1, int(n * 0.75))]
        cells.append(
            {
                "especialidad": esp,
                "zona": zona,
                "n": n,
                "p25": p25,
                "median": mid,
                "p75": p75,
            }
        )

    # cap erosion vs April update
    months = 6
    erosion = (1 + INFLATION_M) ** months - 1
    caps = []
    for plan in PLANS.values():
        if not plan.open_system:
            continue
        market = 85_000  # CABA specialist mid
        caps.append(
            {
                "plan": plan.name,
                "tope_consulta": plan.consulta_tope,
                "mercado_mediana": market,
                "brecha": market - plan.consulta_tope,
                "cobertura_pct": plan.consulta_tope / market,
                "updated": plan.last_cap_update,
                "inflation_since": erosion,
                "galeno_550": GALENO_CONSULTA,
            }
        )

    recruit = []
    for d in doctors.values():
        if d["en_directo"]:
            continue
        if d["visits"] < 8:
            continue
        recruit.append(
            {
                **d,
                "avg": d["sum"] / d["n"],
                "why": "Los socios de planes abiertos ya lo eligen. Sumarlo a Directo baja el out-of-pocket a cero sobre el tope.",
            }
        )
    recruit.sort(key=lambda x: -x["visits"])
    return {
        "cells": cells,
        "caps": caps,
        "recruit": recruit[:20],
        "inflation_m": INFLATION_M,
        "note": "Un precio nominado de un médico solo se muestra si está en OMINT Directo. El resto son rangos por especialidad y zona.",
        "galeno": {"plan": "550", "consulta": GALENO_CONSULTA, "source": "cartilla Galeno publicada"},
    }


def estimate_out_of_pocket(conn, especialidad: str, zona: str, plan_code: str, professional_id: int | None = None) -> dict:
    from backend.app.rules.plans import plan_for, tope_for

    plan = plan_for(plan_code)
    tope = tope_for(plan, "consulta")
    named = None
    if professional_id:
        doc = conn.execute("SELECT * FROM professionals WHERE id=?", (professional_id,)).fetchone()
        if doc and doc["en_directo"]:
            named = {"nombre": doc["nombre"], "precio": doc["precio_base"], "en_directo": True}
            billed = doc["precio_base"]
            return {
                "named": named,
                "range": None,
                "tope": tope,
                "omint_paga": min(tope, billed) if plan.open_system else 0,
                "socio_paga": max(0, billed - tope) if plan.open_system else billed,
                "directo": True,
            }
    rows = conn.execute(
        """
        SELECT c.importe FROM claims c
        JOIN professionals p ON p.id=c.professional_id
        WHERE p.especialidad=? AND p.zona=? AND c.tipo='consulta'
        """,
        (especialidad, zona),
    ).fetchall()
    prices = sorted(r["importe"] for r in rows) or [80_000]
    mid = prices[len(prices) // 2]
    return {
        "named": None,
        "range": {"p25": prices[int(len(prices) * 0.25)], "median": mid, "p75": prices[min(len(prices) - 1, int(len(prices) * 0.75))]},
        "tope": tope,
        "omint_paga": min(tope, mid) if plan.open_system else 0,
        "socio_paga": max(0, mid - tope) if plan.open_system else mid,
        "directo": False,
    }


def simulate_cap(conn, plan_code: str, new_consulta_tope: float) -> dict:
    from backend.app.rules.plans import plan_for

    plan = plan_for(plan_code)
    current = plan.consulta_tope
    rows = conn.execute(
        """
        SELECT c.importe FROM claims c
        JOIN members m ON m.id=c.member_id
        WHERE m.plan=? AND c.tipo='consulta' AND c.historical=1
        """,
        (plan_code,),
    ).fetchall()
    n = len(rows) or 1
    paid_now = sum(min(r["importe"], current) for r in rows)
    paid_new = sum(min(r["importe"], new_consulta_tope) for r in rows)
    coverage_now = sum(1 for r in rows if r["importe"] <= current) / n
    coverage_new = sum(1 for r in rows if r["importe"] <= new_consulta_tope) / n
    return {
        "plan": plan_code,
        "current": current,
        "proposed": new_consulta_tope,
        "extra_spend_sample": paid_new - paid_now,
        "coverage_now": coverage_now,
        "coverage_new": coverage_new,
        "n": n,
        "note": "Simulación sobre reclamos sintéticos históricos. No es un costo de producción.",
    }
