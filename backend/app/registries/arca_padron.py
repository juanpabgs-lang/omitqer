"""Sandbox taxpayer registry (padrón) keyed by CUIT."""

from __future__ import annotations


def lookup(conn, cuit: str | int) -> dict:
    cuit = str(cuit).replace("-", "")
    row = conn.execute("SELECT * FROM professionals WHERE cuit=?", (cuit,)).fetchone()
    request = {"cuit": cuit, "servicio": "PadronA13"}
    if not row:
        return {
            "found": False,
            "cuit": cuit,
            "estado": "NO_INSCRIPTO",
            "razon": None,
            "request": request,
            "response": {"error": "no inscripto"},
            "sandbox": True,
        }
    resp = {
        "cuit": cuit,
        "razonSocial": row["nombre"],
        "estadoClave": "ACTIVO",
        "impuestos": ["Monotributo"],
    }
    return {
        "found": True,
        "cuit": cuit,
        "estado": "ACTIVO",
        "razon": row["nombre"],
        "request": request,
        "response": resp,
        "sandbox": True,
    }
