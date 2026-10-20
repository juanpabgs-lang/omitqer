"""OMINT member registry sandbox."""

from __future__ import annotations


def lookup(conn, socio_nro: str | None = None, dni: str | None = None, member_id: int | None = None) -> dict:
    request = {"padron": "OMINT", "socio_nro": socio_nro, "dni": dni}
    row = None
    if member_id:
        row = conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
    elif socio_nro:
        row = conn.execute("SELECT * FROM members WHERE socio_nro=?", (socio_nro,)).fetchone()
    elif dni:
        row = conn.execute("SELECT * FROM members WHERE dni=?", (dni,)).fetchone()
    if row is None:
        return {"active": False, "member": None, "request": request, "response": {"found": False}, "sandbox": True}
    member = dict(row)
    return {
        "active": not bool(member["churned"]),
        "member": member,
        "request": request,
        "response": {
            "socio_nro": member["socio_nro"],
            "plan": member["plan"],
            "estado": "BAJA" if member["churned"] else "ACTIVO",
        },
        "sandbox": True,
    }
