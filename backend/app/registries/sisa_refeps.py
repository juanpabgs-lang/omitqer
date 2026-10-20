"""SISA REFEPS sandbox shaped like WS020 getProfesional."""

from __future__ import annotations


def get_profesional(conn, matricula: str | None = None, cuit: str | None = None) -> dict:
    request = {"servicio": "WS020", "method": "getProfesional", "matricula": matricula, "cuit": cuit}
    row = None
    if cuit:
        row = conn.execute("SELECT * FROM professionals WHERE cuit=?", (str(cuit).replace("-", ""),)).fetchone()
    if row is None and matricula:
        row = conn.execute("SELECT * FROM professionals WHERE matricula=?", (str(matricula),)).fetchone()
    if row is None:
        return {
            "estado": "NO_ENCONTRADO",
            "detalle": "Profesional no hallado en REFEPS sandbox",
            "request": request,
            "response": {"resultado": "NO_ENCONTRADO"},
            "sandbox": True,
        }
    estado = row["refeps_estado"]
    resp = {
        "apellidoNombre": row["nombre"],
        "matricula": row["matricula"],
        "profesion": "Médico",
        "especialidad": row["especialidad"],
        "jurisdiccion": row["jurisdiccion"],
        "estadoHabilitacion": estado,
    }
    return {
        "estado": estado,
        "detalle": f"{row['nombre']} · {row['especialidad']} · {estado}",
        "profesional_id": row["id"],
        "request": request,
        "response": resp,
        "sandbox": True,
    }
