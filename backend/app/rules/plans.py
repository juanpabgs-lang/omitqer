"""Synthetic OMINT plan catalog with reimbursement caps.

Caps were last updated in April 2026 and lag monthly inflation (~1.7%),
so erosion versus the private-market price map is visible in /direccion.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SPECIALTIES = [
    "Clínica médica",
    "Cardiología",
    "Dermatología",
    "Traumatología",
    "Oftalmología",
    "Ginecología",
    "Pediatría",
    "Otorrinolaringología",
    "Neurología",
    "Psiquiatría",
    "Kinesiología",
    "Fonoaudiología",
    "Nutrición",
    "Odontología",
    "Psicología",
]


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    open_system: bool
    cuota_ars: int
    consulta_tope: int
    kinesio_sesiones: int
    kinesio_tope_sesion: int
    odonto_tope: int
    salud_mental_sesiones: int
    salud_mental_tope: int
    anual_tope: int
    last_cap_update: str = "2026-04-01"


PLANS: dict[str, Plan] = {
    "GENESIS": Plan(
        code="GENESIS",
        name="Génesis",
        open_system=False,
        cuota_ars=280_000,
        consulta_tope=0,
        kinesio_sesiones=30,
        kinesio_tope_sesion=0,
        odonto_tope=0,
        salud_mental_sesiones=30,
        salud_mental_tope=0,
        anual_tope=0,
    ),
    "CLASICO": Plan(
        code="CLASICO",
        name="Clásico",
        open_system=False,
        cuota_ars=632_400,
        consulta_tope=0,
        kinesio_sesiones=30,
        kinesio_tope_sesion=0,
        odonto_tope=80_000,
        salud_mental_sesiones=30,
        salud_mental_tope=0,
        anual_tope=0,
    ),
    "GLOBAL": Plan(
        code="GLOBAL",
        name="Global",
        open_system=True,
        cuota_ars=485_750,
        consulta_tope=42_000,
        kinesio_sesiones=40,
        kinesio_tope_sesion=18_000,
        odonto_tope=180_000,
        salud_mental_sesiones=40,
        salud_mental_tope=28_000,
        anual_tope=1_200_000,
    ),
    "PREMIUM": Plan(
        code="PREMIUM",
        name="Premium",
        open_system=True,
        cuota_ars=1_029_627,
        consulta_tope=68_000,
        kinesio_sesiones=50,
        kinesio_tope_sesion=24_000,
        odonto_tope=320_000,
        salud_mental_sesiones=50,
        salud_mental_tope=42_000,
        anual_tope=2_400_000,
    ),
}


PLAN_WEIGHTS = {
    "GENESIS": 0.18,
    "CLASICO": 0.32,
    "GLOBAL": 0.34,
    "PREMIUM": 0.16,
}


def plan_for(code: str) -> Plan:
    return PLANS[code]


def tope_for(plan: Plan, tipo: str) -> int:
    if tipo in {"consulta", "visita_consultorio", "visita_domicilio"}:
        return plan.consulta_tope
    if tipo in {"kinesiologia", "fonoaudiologia"}:
        return plan.kinesio_tope_sesion
    if tipo in {"odontologia"}:
        return plan.odonto_tope
    if tipo in {"psicologia", "psiquiatria"}:
        return plan.salud_mental_tope
    return plan.consulta_tope
