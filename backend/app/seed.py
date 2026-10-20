"""Seed a fully synthetic OMINT world. No real members or health data."""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.app.calendar_ar import add_business_days
from backend.app.db import DATA_DIR, DB_PATH, SAMPLES_DIR, init_db
from backend.app.ingest.qr_arca import ArcaQr
from backend.app.ingest.render import render_factura, save_png
from backend.app.integrity import provider_audit
from backend.app.ledger import chain, value
from backend.app.rules.plans import PLAN_WEIGHTS, PLANS, SPECIALTIES

TODAY = date(2026, 10, 20)

FIRST = "Martina Sofía Valentina Camila Lucía Emilia Julieta Catalina Benjamín Mateo Thiago Felipe Lautaro Santiago Nicolás Joaquín Tomás".split()
LAST = "Gómez Rodríguez Fernández López Díaz Martínez Pérez Álvarez Romero Suárez Castro Vega Navarro Molina Herrera Aguilar Blanco".split()
ZONES = ["CABA", "GBA Norte", "GBA Sur", "GBA Oeste", "Rosario", "Córdoba", "Mendoza"]
JURIS = {"CABA": "CABA", "GBA Norte": "Buenos Aires", "GBA Sur": "Buenos Aires", "GBA Oeste": "Buenos Aires", "Rosario": "Santa Fe", "Córdoba": "Córdoba", "Mendoza": "Mendoza"}
TIPOS = ["consulta", "consulta", "consulta", "kinesiologia", "odontologia", "psicologia", "laboratorio", "consulta"]


def _name(rng: random.Random) -> tuple[str, str]:
    return rng.choice(FIRST), rng.choice(LAST)


def _dni(rng: random.Random) -> str:
    return str(rng.randint(18_000_000, 45_000_000))


def _cbu(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(22))


def _cuit(rng: random.Random) -> str:
    body = f"{rng.randint(20, 27)}{rng.randint(10_000_000, 39_999_999)}"
    return body + str(rng.randint(0, 9))


def reset(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    for p in SAMPLES_DIR.glob("*"):
        p.unlink()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def seed(path: Path = DB_PATH, n_members: int = 20_000, n_docs: int = 1_500, n_claims: int = 24_000) -> sqlite3.Connection:
    rng = random.Random(20261020)
    conn = reset(path)
    conn.execute("INSERT INTO meta (k,v) VALUES ('today', ?)", (TODAY.isoformat(),))
    conn.execute("INSERT INTO meta (k,v) VALUES ('synthetic', '1')")
    chain.append(conn, {"kind": "genesis", "note": "ledger sintético OMINT reintegros"}, created_at=TODAY.isoformat())

    members = _members(conn, rng, n_members)
    docs = _professionals(conn, rng, n_docs)
    _contracts(conn, rng, members)
    invoices = _claims(conn, rng, members, docs, n_claims)
    _liquidaciones(conn, rng, members)
    _hero(conn, rng, members, docs)
    _denuncias(conn, members)
    _historical_value(conn, rng)
    from backend.app.discapacidad import seed_sheet

    seed_sheet(conn)
    conn.commit()
    return conn


def _members(conn, rng, n) -> list[dict]:
    rows = []
    codes = list(PLAN_WEIGHTS)
    weights = [PLAN_WEIGHTS[c] for c in codes]
    for i in range(1, n + 1):
        fn, ln = _name(rng)
        plan = rng.choices(codes, weights)[0]
        zona = rng.choice(ZONES)
        tenure = rng.randint(3, 180)
        # churn labels: higher if closed plan or long tenure + friction later
        risk = rng.random() * (0.55 if plan in {"GLOBAL", "PREMIUM"} else 0.35)
        churned = 1 if rng.random() < (0.07 if plan in {"GENESIS", "CLASICO"} else 0.04) else 0
        reason = None
        if churned:
            reason = rng.choice(["precio", "reintegro", "cartilla", "otro"])
        holdout = 1 if i % 7 == 0 else 0
        rows.append(
            (
                i,
                f"{400000 + i}",
                fn,
                ln,
                _dni(rng),
                plan,
                zona,
                (i - 1) // 3 + 1,
                tenure,
                _cbu(rng),
                f"{fn}.{ln}{i}@correo.sintetico.ar".lower(),
                risk,
                churned,
                reason,
                holdout,
                (TODAY - timedelta(days=tenure * 30)).isoformat(),
            )
        )
    conn.executemany(
        """
        INSERT INTO members (id, socio_nro, nombre, apellido, dni, plan, zona, familia_id, tenure_months, cbu, email, churn_risk, churned, churn_reason, holdout, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    return [{"id": r[0], "socio_nro": r[1], "nombre": r[2], "apellido": r[3], "plan": r[5], "zona": r[6], "familia_id": r[7], "churned": r[12], "churn_reason": r[13], "cbu": r[9]} for r in rows]


def _professionals(conn, rng, n) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        fn, ln = _name(rng)
        zona = rng.choice(ZONES)
        esp = rng.choice(SPECIALTIES)
        # price drift ~1.7%/month from a Jan base
        base0 = {
            "Clínica médica": 55_000,
            "Dermatología": 70_000,
            "Cardiología": 90_000,
            "Psiquiatría": 140_000,
            "Kinesiología": 28_000,
            "Odontología": 48_000,
            "Psicología": 45_000,
        }.get(esp, 80_000)
        months = rng.randint(0, 9)
        price = int(base0 * ((1.017) ** months) * rng.uniform(0.85, 1.25))
        estado = "HABILITADO"
        riesgo = "bajo"
        if i % 40 == 0:
            estado = "INHABILITADO"
            riesgo = "alto"
        elif i % 33 == 0:
            estado = "SUSPENDIDO"
            riesgo = "medio"
        en_directo = 1 if i <= 80 and estado == "HABILITADO" else 0
        cuit = _cuit(rng)
        rows.append(
            (
                i,
                cuit,
                f"Dr/a. {fn} {ln}",
                str(80_000 + i),
                esp,
                JURIS[zona],
                zona,
                price,
                estado,
                en_directo,
                _cbu(rng) if en_directo else None,
                riesgo,
                TODAY.isoformat() if en_directo else None,
            )
        )
    conn.executemany(
        """
        INSERT INTO professionals (id, cuit, nombre, matricula, especialidad, jurisdiccion, zona, precio_base, refeps_estado, en_directo, cbu, riesgo, onboarded_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    return [
        {
            "id": r[0],
            "cuit": r[1],
            "nombre": r[2],
            "matricula": r[3],
            "especialidad": r[4],
            "zona": r[6],
            "precio_base": r[7],
            "refeps_estado": r[8],
            "en_directo": r[9],
        }
        for r in rows
    ]


def _contracts(conn, rng, members):
    rows = []
    for m in members:
        # one current version; 8% have a prior version (the vault story)
        versions = ["2024.11", "2026.03"] if rng.random() < 0.08 else ["2026.03"]
        for ver in versions:
            body = f"Contrato sintético OMINT plan {m['plan']} socio {m['socio_nro']} versión {ver}"
            sha = hashlib.sha256(body.encode()).hexdigest()
            signed = "2026-03-01" if ver == "2026.03" else "2024-11-12"
            rows.append((m["id"], ver, m["plan"], sha, body, signed))
    conn.executemany(
        "INSERT INTO contracts (member_id, version, plan, sha256, body, signed_at) VALUES (?,?,?,?,?,?)",
        rows,
    )


def _claims(conn, rng, members, docs, n):
    open_members = [m for m in members if m["plan"] in {"GLOBAL", "PREMIUM"} and not m["churned"]]
    invoices = []
    claims = []
    for i in range(1, n + 1):
        m = rng.choice(open_members)
        d = rng.choice(docs)
        tipo = rng.choice(TIPOS)
        days_ago = rng.randint(2, 170)
        fecha = TODAY - timedelta(days=days_ago)
        importe = float(int(d["precio_base"] * rng.uniform(0.9, 1.15)))
        if tipo == "kinesiologia":
            importe = float(int(d["precio_base"] * rng.randint(4, 10) * 0.4))
        cae = 11_000_000_000_000 + i
        pto, nro, tipo_cmp = 1, 1000 + i, 11
        qr = {
            "ver": 1,
            "fecha": fecha.isoformat(),
            "cuit": int(d["cuit"]),
            "ptoVta": pto,
            "tipoCmp": tipo_cmp,
            "nroCmp": nro,
            "importe": importe,
            "moneda": "PES",
            "ctz": 1,
            "tipoCodAut": "E",
            "codAut": cae,
            "tipoDocRec": 96,
            "nroDocRec": int(m["socio_nro"]),
        }
        wscdc = "A"
        bounce = 0
        bounce_reason = None
        stall = "pagado"
        route = "via_rapida"
        status = "pagado"
        days_to_pay = rng.choice([0, 1, 1, 2, 3, 5, 8, 12])
        # inject anomalies at stated rates
        r = rng.random()
        if r < 0.025 or d["refeps_estado"] != "HABILITADO":
            route, status, stall = "revision", "en_revision", "mesa"
            bounce, bounce_reason = 1, "matricula_inhabilitada" if d["refeps_estado"] != "HABILITADO" else "revision"
            days_to_pay = None
        elif r < 0.07:
            route, status, stall = "falta_doc", "falta_documentacion", "socio"
            bounce, bounce_reason = 1, rng.choice(["sin_diagnostico", "sin_orden", "sin_sello"])
            days_to_pay = None
        elif r < 0.085:
            wscdc = "R"
            route, status, stall = "revision", "en_revision", "arca"
            bounce, bounce_reason = 1, "cae_inexistente"
            days_to_pay = None
        elif r < 0.095:
            bounce, bounce_reason = 1, "importe_alterado"
            route, status, stall = "revision", "en_revision", "integridad"
            days_to_pay = None
        elif r < 0.10:
            bounce, bounce_reason = 1, "tope_mal_aplicado"
            route, status = "via_rapida", "pagado"
        elif days_ago > 90:
            route, status, stall = "revision", "en_revision", "plazo"
            bounce, bounce_reason = 1, "fuera_90"
            days_to_pay = None

        # 90 vs 60 conflict band
        if 60 < days_ago <= 90 and rng.random() < 0.4:
            stall = stall if stall != "pagado" else "conflicto_plazo"

        paid_at = None
        if status == "pagado":
            paid_at = (fecha + timedelta(days=(days_to_pay or 2) + 1)).isoformat()
        public_id = f"H-26-{i:06d}"
        invoices.append(
            (
                i,
                d["cuit"],
                pto,
                tipo_cmp,
                nro,
                fecha.isoformat(),
                importe,
                "PES",
                str(cae),
                96,
                m["socio_nro"],
                json.dumps(qr),
                wscdc,
            )
        )
        tope = PLANS[m["plan"]].consulta_tope if tipo == "consulta" else PLANS[m["plan"]].kinesio_tope_sesion
        estimado = min(importe, tope) if tope else 0
        claims.append(
            (
                public_id,
                m["id"],
                d["id"],
                i,
                tipo,
                route,
                status,
                importe,
                estimado,
                "ARS",
                fecha.isoformat(),
                fecha.isoformat(),
                paid_at,
                days_to_pay,
                bounce,
                bounce_reason,
                stall,
                1,
            )
        )
    conn.executemany(
        """
        INSERT INTO invoices (id, cuit, pto_vta, tipo_cmp, nro_cmp, fecha, importe, moneda, cae, tipo_doc_rec, nro_doc_rec, raw_json, resultado_wscdc)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        invoices,
    )
    conn.executemany(
        """
        INSERT INTO claims (public_id, member_id, professional_id, invoice_id, tipo, route, status, importe, estimado, moneda, fecha_prestacion, created_at, paid_at, days_to_pay, bounced, bounce_reason, stall_stage, historical)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        claims,
    )
    # plant a handful of duplicate CAEs
    dupes = conn.execute("SELECT id, cae, cuit, pto_vta, tipo_cmp, nro_cmp FROM invoices ORDER BY id LIMIT 12").fetchall()
    for j, drow in enumerate(dupes):
        conn.execute(
            """
            INSERT INTO invoices (cuit, pto_vta, tipo_cmp, nro_cmp, fecha, importe, moneda, cae, tipo_doc_rec, nro_doc_rec, raw_json, resultado_wscdc)
            VALUES (?, ?, ?, ?, ?, ?, 'PES', ?, 96, '400001', '{}', 'A')
            """,
            (drow["cuit"], drow["pto_vta"], drow["tipo_cmp"], drow["nro_cmp"] + 500000, TODAY.isoformat(), 10_000, drow["cae"]),
        )
        inv_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        m = open_members[j]
        conn.execute(
            """
            INSERT INTO claims (public_id, member_id, professional_id, invoice_id, tipo, route, status, importe, estimado, moneda, fecha_prestacion, created_at, bounced, bounce_reason, stall_stage, historical)
            VALUES (?, ?, 1, ?, 'consulta', 'revision', 'en_revision', 10000, 0, 'ARS', ?, ?, 1, 'duplicado', 'integridad', 1)
            """,
            (f"H-DUP-{j:03d}", m["id"], inv_id, TODAY.isoformat(), TODAY.isoformat()),
        )
    return invoices


def _liquidaciones(conn, rng, members):
    providers = [
        ("Clínica del Sol", {"consulta": 18_400, "lab": 6_200, "rx": 9_800}),
        ("Sanatorio Bazterrica", {"consulta": 21_100, "lab": 7_000, "rx": 11_200}),
        ("Centro Norte Imágenes", {"consulta": 16_800, "lab": 5_400, "rx": 22_500}),
    ]
    active = [m for m in members if not m["churned"]]
    for name, rates in providers:
        convenio = json.dumps(rates, ensure_ascii=False)
        lines = []
        total = 0.0
        for i in range(1500):
            m = rng.choice(active)
            codigo = rng.choice(["CONS", "LAB", "RX", "ALTA1"])
            key = {"CONS": "consulta", "LAB": "lab", "RX": "rx", "ALTA1": "rx"}[codigo]
            conv = rates[key]
            importe = conv
            planted = None
            auth = f"AUT-{rng.randint(10000,99999)}"
            member_active = 1
            roll = rng.random()
            if roll < 0.018:
                planted = "precio_sobre_convenio"
                importe = conv * rng.uniform(1.15, 1.6)
            elif roll < 0.028:
                planted = "sin_autorizacion"
                auth = ""
                codigo = "ALTA1"
            elif roll < 0.034:
                planted = "socio_no_vigente"
                member_active = 0
            elif roll < 0.040:
                planted = "duplicado"
            elif roll < 0.045:
                planted = "unbundling"
                importe = conv * 1.4
            total += importe
            desc = {"CONS": "Consulta en consultorio", "LAB": "Laboratorio de rutina", "RX": "Estudio de imágenes", "ALTA1": "Práctica de alta complejidad"}[codigo]
            lines.append((m["id"], codigo, desc, importe, conv, auth, planted, member_active))
        conn.execute(
            "INSERT INTO liquidaciones (provider_name, period, convenio, total) VALUES (?, '2026-09', ?, ?)",
            (name, convenio, total),
        )
        lid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.executemany(
            """
            INSERT INTO liquidacion_lines (liquidacion_id, member_id, codigo, descripcion, importe, convenio_importe, auth, planted_anomaly, member_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(lid, *ln) for ln in lines],
        )
        provider_audit.audit_liquidacion(conn, lid)


def _hero(conn, rng, members, docs):
    hero_member = next(m for m in members if m["plan"] == "GLOBAL" and not m["churned"])
    kin_member = next(m for m in members if m["id"] != hero_member["id"] and m["plan"] == "PREMIUM" and not m["churned"])
    family = next(m for m in members if m["familia_id"] == hero_member["familia_id"] and m["id"] != hero_member["id"])
    def _pick(pred, fallback_pred=None):
        for d in docs:
            if pred(d):
                return d
        if fallback_pred:
            for d in docs:
                if fallback_pred(d):
                    return d
        return docs[0]

    good_doc = _pick(lambda d: d["refeps_estado"] == "HABILITADO" and d["especialidad"] == "Cardiología", lambda d: d["refeps_estado"] == "HABILITADO")
    kin_doc = _pick(lambda d: d["especialidad"] == "Kinesiología" and d["refeps_estado"] == "HABILITADO", lambda d: d["refeps_estado"] == "HABILITADO")
    bad_doc = _pick(lambda d: d["refeps_estado"] == "INHABILITADO")
    directo_doc = _pick(lambda d: d["en_directo"] == 1)

    specs = [
        {
            "key": "consulta_limpia",
            "title": "Consulta de especialista",
            "subtitle": "Vía rápida · tope del plan · pago en minutos",
            "member": hero_member,
            "doc": good_doc,
            "tipo": "consulta",
            "days": 4,
            "diagnostico": "Control cardiológico (dato sintético)",
            "detalle": "Consulta cardiológica en consultorio",
            "wscdc": "A",
            "route": "via_rapida",
        },
        {
            "key": "kine_sin_orden",
            "title": "10 sesiones de kinesiología",
            "subtitle": "Faltan fechas de sesión y la orden médica",
            "member": kin_member,
            "doc": kin_doc,
            "tipo": "kinesiologia",
            "days": 9,
            "diagnostico": None,
            "detalle": "Tratamiento kinesiológico, 10 sesiones",
            "sesiones": None,
            "force_missing": ["orden_medica", "sesiones", "diagnostico"],
            "wscdc": "A",
            "route": "falta_doc",
        },
        {
            "key": "cae_rechazado",
            "title": "CAE inexistente en ARCA",
            "subtitle": "WSCDC devuelve R · mesa pre-armada",
            "member": hero_member,
            "doc": good_doc,
            "tipo": "consulta",
            "days": 6,
            "diagnostico": "Control (sintético)",
            "detalle": "Consulta clínica",
            "wscdc": "R",
            "route": "revision",
        },
        {
            "key": "matricula_caida",
            "title": "Matrícula no habilitada en REFEPS",
            "subtitle": "El expediente llega a mesa ya completo",
            "member": kin_member,
            "doc": bad_doc,
            "tipo": "consulta",
            "days": 3,
            "diagnostico": "Consulta (sintético)",
            "detalle": "Consulta en consultorio",
            "wscdc": "A",
            "route": "revision",
        },
        {
            "key": "dias_75",
            "title": "Prestación de hace 75 días",
            "subtitle": "Se aplica 90 días · se registra la contradicción 60/90",
            "member": hero_member,
            "doc": good_doc,
            "tipo": "consulta",
            "days": 75,
            "diagnostico": "Control (sintético)",
            "detalle": "Consulta traumatológica",
            "wscdc": "A",
            "route": "via_rapida",
        },
        {
            "key": "foto_celular",
            "title": "Foto de celular",
            "subtitle": "Perspectiva y sombra · confirmación de campos",
            "member": hero_member,
            "doc": good_doc,
            "tipo": "consulta",
            "days": 2,
            "diagnostico": "Control (sintético)",
            "detalle": "Consulta dermatológica",
            "wscdc": "A",
            "warped": True,
            "route": "via_rapida",
        },
        {
            "key": "duplicado_familiar",
            "title": "CAE ya usado por el grupo familiar",
            "subtitle": "Integridad · revisión de fraude",
            "member": family,
            "doc": good_doc,
            "tipo": "consulta",
            "days": 5,
            "diagnostico": "Control (sintético)",
            "detalle": "Consulta",
            "wscdc": "A",
            "duplicate": True,
            "reuse_cae_of": "consulta_limpia",
            "route": "revision",
        },
        {
            "key": "exterior_usd",
            "title": "Gasto en el exterior (USD)",
            "subtitle": "Conversión BCRA · siempre mesa",
            "member": kin_member,
            "doc": good_doc,
            "tipo": "exterior",
            "days": 12,
            "diagnostico": "Urgencia (sintético)",
            "detalle": "Emergency room — Miami, USD 420",
            "wscdc": "A",
            "currency": "USD",
            "fx": 1545.0,
            "importe": 420.0,
            "route": "revision",
        },
    ]

    cae_map = {}
    for i, spec in enumerate(specs, start=1):
        fecha = TODAY - timedelta(days=spec["days"])
        d = spec["doc"]
        m = spec["member"]
        importe = spec.get("importe") or float(d["precio_base"])
        cae = 22_000_000_000_000 + i
        if spec.get("reuse_cae_of"):
            cae = cae_map[spec["reuse_cae_of"]]
        cae_map[spec["key"]] = cae
        pto, nro, tipo_cmp = 3, 8000 + i, 11
        qr = ArcaQr(
            ver=1,
            fecha=fecha.isoformat(),
            cuit=int(d["cuit"]),
            ptoVta=pto,
            tipoCmp=tipo_cmp,
            nroCmp=nro,
            importe=importe,
            moneda="DOL" if spec.get("currency") == "USD" else "PES",
            ctz=spec.get("fx", 1),
            tipoCodAut="E",
            codAut=cae,
            tipoDocRec=96,
            nroDocRec=int(m["socio_nro"]),
        )
        img = render_factura(
            qr,
            profesional=d["nombre"],
            matricula=d["matricula"],
            especialidad=d["especialidad"],
            paciente=f"{m['nombre']} {m['apellido']}",
            socio_nro=m["socio_nro"],
            detalle=spec["detalle"],
            diagnostico=spec.get("diagnostico"),
            sesiones=spec.get("sesiones"),
            warped=bool(spec.get("warped")),
        )
        path = SAMPLES_DIR / f"{spec['key']}.png"
        save_png(img, path)
        conn.execute(
            """
            INSERT INTO invoices (cuit, pto_vta, tipo_cmp, nro_cmp, fecha, importe, moneda, cae, tipo_doc_rec, nro_doc_rec, raw_json, resultado_wscdc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 96, ?, ?, ?)
            """,
            (
                d["cuit"],
                pto,
                tipo_cmp,
                nro,
                fecha.isoformat(),
                importe,
                qr.moneda,
                str(cae),
                m["socio_nro"],
                json.dumps(qr.to_dict()),
                spec["wscdc"],
            ),
        )
        conn.execute(
            "INSERT INTO samples (key, title, subtitle, path, member_id, expected_route) VALUES (?,?,?,?,?,?)",
            (spec["key"], spec["title"], spec["subtitle"], str(path), m["id"], spec["route"]),
        )
        meta = {
            "tipo": spec["tipo"],
            "professional_id": d["id"],
            "diagnostico": spec.get("diagnostico"),
            "fecha": fecha.isoformat(),
            "importe": importe,
            "sesiones": spec.get("sesiones"),
            "force_missing": spec.get("force_missing"),
            "duplicate": spec.get("duplicate", False),
            "currency": spec.get("currency", "ARS"),
            "fx": spec.get("fx", 1),
            "orden_medica": False,
            "cuir": None,
        }
        conn.execute("INSERT INTO meta (k,v) VALUES (?, ?)", (f"sample:{spec['key']}", json.dumps(meta, ensure_ascii=False)))

    # store hero ids
    conn.execute("INSERT INTO meta (k,v) VALUES ('hero_member', ?)", (str(hero_member["id"]),))
    conn.execute("INSERT INTO meta (k,v) VALUES ('directo_doc', ?)", (str(directo_doc["id"]),))


def _denuncias(conn, members):
    open_m = [m for m in members if m["plan"] in {"GLOBAL", "PREMIUM"}][:8]
    tipos = [
        ("denuncia", 5, "Reintegro no acreditado en el plazo prometido"),
        ("denuncia", 5, "Cobertura de prestación ambulatoria"),
        ("falta_formal", 10, "Falta de respuesta a requerimiento registral"),
        ("denuncia", 5, "Contrato no acompañado en causa previa (eco D.B./L.B.)"),
        ("intima", 5, "INTIMA — acreditar cumplimiento prestacional"),
        ("denuncia", 5, "Demora en reintegro de sesiones"),
    ]
    for i, (m, (tipo, days, asunto)) in enumerate(zip(open_m, tipos), start=1):
        opened = TODAY - timedelta(days=i + 1)
        deadline = add_business_days(opened, days)
        conn.execute(
            """
            INSERT INTO denuncias (public_id, member_id, tipo, opened_at, deadline, status, asunto)
            VALUES (?, ?, ?, ?, ?, 'abierta', ?)
            """,
            (f"SSS-2026-{4000 + i}", m["id"], tipo, opened.isoformat(), deadline.isoformat(), asunto),
        )


def _historical_value(conn, rng):
    # Confirmed recoveries so the Valor tab is not empty. Labeled synthetic.
    kinds = [
        ("debito_prestador", 42_000_000),
        ("debito_prestador", 18_500_000),
        ("duplicado_bloqueado", 2_400_000),
        ("importe_alterado", 890_000),
        ("minutos_ahorrados", 6_200_000),
        ("multa_evitada", 3_100_000),
    ]
    for i, (kind, ars) in enumerate(kinds):
        ev = chain.append(conn, {"kind": "valor_historico", "value_kind": kind, "ars": ars}, created_at=f"2026-09-{10+i:02d}T12:00:00")
        vid = value.propose(conn, kind=kind, ars=ars, evidence_hash=ev["hash"], note="histórico sintético confirmado", created_at=f"2026-09-{10+i:02d}T12:00:00")
        value.confirm(conn, vid, "Auditoría demo")


if __name__ == "__main__":
    print("seeding…")
    conn = seed()
    n = conn.execute("SELECT COUNT(*) AS n FROM members").fetchone()["n"]
    c = conn.execute("SELECT COUNT(*) AS n FROM claims").fetchone()["n"]
    print(f"members={n} claims={c} db={DB_PATH}")
