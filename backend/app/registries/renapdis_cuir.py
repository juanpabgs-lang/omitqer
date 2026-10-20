"""Illustrative ReNaPDiS / CUIR validator.

The CUIR format used here is illustrative, not the official identifier.
"""

from __future__ import annotations

import re

CUIR_RE = re.compile(r"^CUIR-AR-\d{4}-\d{8}-\d{2}$")

# Seeded valid orders for the demo (synthetic).
VALID: dict[str, dict] = {
    "CUIR-AR-2026-00018422-07": {
        "tipo": "orden_kinesiologia",
        "sesiones": 10,
        "profesional": "MN 118422",
        "valid": True,
    }
}


def validate(cuir: str | None) -> dict:
    request = {"repositorio": "ReNaPDiS", "cuir": cuir, "formato": "illustrative"}
    if not cuir:
        return {"valid": False, "reason": "sin CUIR", "request": request, "response": {}, "sandbox": True}
    if cuir in VALID:
        return {
            "valid": True,
            "cuir": cuir,
            "request": request,
            "response": VALID[cuir],
            "sandbox": True,
            "note": "Formato CUIR ilustrativo (Res. 1959/2024 y 2214/2025).",
        }
    if CUIR_RE.match(cuir):
        return {
            "valid": True,
            "cuir": cuir,
            "request": request,
            "response": {"valid": True, "lookup": "sandbox-accept"},
            "sandbox": True,
            "note": "Formato CUIR ilustrativo.",
        }
    return {
        "valid": False,
        "reason": "formato no reconocido",
        "request": request,
        "response": {"valid": False},
        "sandbox": True,
    }
