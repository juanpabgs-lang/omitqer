"""Refund-side leakage checks: duplicates, amount drift, unlicensed, cap errors."""

from __future__ import annotations


def scan(conn) -> list[dict]:
    out: list[dict] = []
    # duplicates by CAE across family
    rows = conn.execute(
        """
        SELECT i.cae, COUNT(*) AS n, GROUP_CONCAT(c.public_id) AS ids
        FROM claims c
        JOIN invoices i ON i.id = c.invoice_id
        WHERE c.historical = 1 AND i.cae IS NOT NULL
        GROUP BY i.cae
        HAVING n > 1
        LIMIT 40
        """
    ).fetchall()
    for r in rows:
        out.append(
            {
                "kind": "duplicado",
                "detail": f"CAE {r['cae']} en {r['n']} reclamos: {r['ids']}",
                "cae": r["cae"],
            }
        )
    # unlicensed
    rows = conn.execute(
        """
        SELECT c.public_id, p.nombre, p.refeps_estado
        FROM claims c
        JOIN professionals p ON p.id = c.professional_id
        WHERE p.refeps_estado != 'HABILITADO' AND c.historical = 1
        LIMIT 40
        """
    ).fetchall()
    for r in rows:
        out.append(
            {
                "kind": "matricula_inhabilitada",
                "detail": f"{r['public_id']} · {r['nombre']} · {r['refeps_estado']}",
            }
        )
    # amount mismatches stored as bounce_reason
    rows = conn.execute(
        """
        SELECT public_id, bounce_reason, importe
        FROM claims
        WHERE bounce_reason IN ('importe_alterado', 'tope_mal_aplicado') AND historical = 1
        LIMIT 40
        """
    ).fetchall()
    for r in rows:
        out.append(
            {
                "kind": r["bounce_reason"],
                "detail": f"{r['public_id']} · $ {r['importe']:,.0f}",
            }
        )
    return out
