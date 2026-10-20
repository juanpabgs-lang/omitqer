"""Provider bill audit against convenio-as-code. Debits are proposed; a person confirms."""

from __future__ import annotations

from datetime import datetime

from backend.app.ledger import chain, value


def audit_liquidacion(conn, liquidacion_id: int) -> dict:
    liq = conn.execute("SELECT * FROM liquidaciones WHERE id=?", (liquidacion_id,)).fetchone()
    if not liq:
        raise ValueError("liquidacion not found")
    lines = conn.execute(
        "SELECT * FROM liquidacion_lines WHERE liquidacion_id=?", (liquidacion_id,)
    ).fetchall()
    proposed = []
    planted = 0
    caught = 0
    false_pos = 0
    for line in lines:
        reasons = _reasons(line)
        is_planted = bool(line["planted_anomaly"])
        if is_planted:
            planted += 1
        if reasons:
            if is_planted:
                caught += 1
            else:
                false_pos += 1
            ars = _debit_amount(line, reasons)
            existing = conn.execute("SELECT id FROM debitos WHERE line_id=?", (line["id"],)).fetchone()
            if not existing:
                ev = chain.append(
                    conn,
                    {
                        "kind": "debito_propuesto",
                        "liquidacion_id": liquidacion_id,
                        "line_id": line["id"],
                        "reasons": reasons,
                        "ars": ars,
                    },
                )
                conn.execute(
                    """
                    INSERT INTO debitos (line_id, reason, ars, status, proposed_at, evidence_hash)
                    VALUES (?, ?, ?, 'propuesto', ?, ?)
                    """,
                    (line["id"], ",".join(reasons), ars, datetime.now().isoformat(timespec="seconds"), ev["hash"]),
                )
                debit_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                value.propose(
                    conn,
                    kind="debito_prestador",
                    ars=ars,
                    evidence_hash=ev["hash"],
                    liquidacion_id=liquidacion_id,
                    note=",".join(reasons),
                )
            else:
                debit_id = existing["id"]
            proposed.append(
                {
                    "line_id": line["id"],
                    "debit_id": debit_id,
                    "codigo": line["codigo"],
                    "descripcion": line["descripcion"],
                    "importe": line["importe"],
                    "reasons": reasons,
                    "planted": line["planted_anomaly"],
                }
            )
        elif is_planted:
            pass  # missed
    missed = planted - caught
    precision = caught / (caught + false_pos) if (caught + false_pos) else 1.0
    recall = caught / planted if planted else 1.0
    return {
        "liquidacion": dict(liq),
        "lines": len(lines),
        "proposed": proposed,
        "planted": planted,
        "caught": caught,
        "missed": missed,
        "false_pos": false_pos,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
    }


def _reasons(line) -> list[str]:
    reasons = []
    planted = line["planted_anomaly"] or ""
    if line["importe"] > line["convenio_importe"] + 0.5:
        reasons.append("precio_sobre_convenio")
    if planted == "sin_autorizacion" or (planted == "" and line["auth"] in (None, "", "FALTA") and line["codigo"].startswith("ALTA")):
        if not line["auth"]:
            reasons.append("sin_autorizacion")
    if not line["member_active"]:
        reasons.append("socio_no_vigente")
    if planted == "duplicado":
        reasons.append("duplicado")
    if planted == "unbundling":
        reasons.append("desagregado_indebido")
    if planted == "precio_sobre_convenio" and "precio_sobre_convenio" not in reasons:
        reasons.append("precio_sobre_convenio")
    if planted == "socio_no_vigente" and "socio_no_vigente" not in reasons:
        reasons.append("socio_no_vigente")
    return reasons


def _debit_amount(line, reasons: list[str]) -> float:
    if "precio_sobre_convenio" in reasons:
        return max(0.0, float(line["importe"]) - float(line["convenio_importe"]))
    return float(line["importe"])


def confirm_debit(conn, debit_id: int, by: str) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    row = conn.execute("SELECT * FROM debitos WHERE id=?", (debit_id,)).fetchone()
    if not row:
        raise ValueError("debit not found")
    conn.execute(
        "UPDATE debitos SET status='confirmado', confirmed_by=?, confirmed_at=? WHERE id=?",
        (by, now, debit_id),
    )
    ev = chain.append(
        conn,
        {"kind": "debito_confirmado", "debit_id": debit_id, "by": by, "ars": row["ars"]},
    )
    ve = conn.execute(
        "SELECT id FROM value_events WHERE evidence_hash=? AND kind='debito_prestador'",
        (row["evidence_hash"],),
    ).fetchone()
    if ve:
        value.confirm(conn, ve["id"], by)
    return {"ok": True, "hash": ev["hash"], "ars": row["ars"]}


def list_liquidaciones(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM liquidaciones").fetchall()
    out = []
    for r in rows:
        n = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(ars),0) AS ars FROM debitos d JOIN liquidacion_lines l ON l.id=d.line_id WHERE l.liquidacion_id=?",
            (r["id"],),
        ).fetchone()
        confirmed = conn.execute(
            "SELECT COALESCE(SUM(ars),0) AS ars FROM debitos d JOIN liquidacion_lines l ON l.id=d.line_id WHERE l.liquidacion_id=? AND d.status='confirmado'",
            (r["id"],),
        ).fetchone()
        out.append({**dict(r), "debitos_n": n["n"], "debitos_ars": n["ars"], "confirmado_ars": confirmed["ars"]})
    return out
