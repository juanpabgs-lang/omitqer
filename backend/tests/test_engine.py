from datetime import date

from backend.app.calendar_ar import add_business_days, business_days_between, is_business_day
from backend.app.ingest.qr_arca import ArcaQr, decode_image, parse_url
from backend.app.ingest.render import render_factura
from backend.app.rules.engine import Route, evaluate, router_outcomes
from backend.app.rules.plans import PLANS


def test_router_has_no_reject():
    assert "reject" not in router_outcomes()
    assert "rechazo" not in router_outcomes()
    assert set(router_outcomes()) == {"via_rapida", "falta_doc", "revision"}


def test_days_75_applies_90():
    ev = evaluate(
        plan=PLANS["GLOBAL"],
        tipo="consulta",
        fecha_prestacion=date(2026, 8, 6),
        today=date(2026, 10, 20),
        billed=80_000,
        member_active=True,
        fields_present={k: True for k in ["fecha", "nombre_socio", "diagnostico", "profesional", "detalle", "importe", "firma_sello"]},
        wscdc={"Resultado": "A"},
        refeps={"estado": "HABILITADO"},
        padron={"active": True},
    )
    assert (date(2026, 10, 20) - date(2026, 8, 6)).days == 75
    assert any("90 días" in c.result for c in ev.checks if c.name == "plazo_90")
    assert any("60" in x for x in ev.conflicts)
    assert ev.route == Route.VIA_RAPIDA


def test_missing_diagnosis_falta_doc():
    ev = evaluate(
        plan=PLANS["GLOBAL"],
        tipo="consulta",
        fecha_prestacion=date(2026, 10, 10),
        today=date(2026, 10, 20),
        billed=80_000,
        member_active=True,
        fields_present={
            "fecha": True,
            "nombre_socio": True,
            "diagnostico": False,
            "profesional": True,
            "detalle": True,
            "importe": True,
            "firma_sello": True,
        },
        wscdc={"Resultado": "A"},
        refeps={"estado": "HABILITADO"},
        padron={"active": True},
    )
    assert ev.route == Route.FALTA_DOCUMENTACION
    assert "diagnostico" in ev.missing


def test_wscdc_r_goes_to_review():
    ev = evaluate(
        plan=PLANS["GLOBAL"],
        tipo="consulta",
        fecha_prestacion=date(2026, 10, 10),
        today=date(2026, 10, 20),
        billed=80_000,
        member_active=True,
        fields_present={k: True for k in ["fecha", "nombre_socio", "diagnostico", "profesional", "detalle", "importe", "firma_sello"]},
        wscdc={"Resultado": "R"},
        refeps={"estado": "HABILITADO"},
        padron={"active": True},
    )
    assert ev.route == Route.REVISION_HUMANA


def test_qr_roundtrip():
    qr = ArcaQr(
        ver=1,
        fecha="2026-10-15",
        cuit=20123456789,
        ptoVta=1,
        tipoCmp=11,
        nroCmp=44,
        importe=85000,
        moneda="PES",
        ctz=1,
        tipoCodAut="E",
        codAut=12345678901234,
        tipoDocRec=96,
        nroDocRec=30111222,
    )
    parsed = parse_url(qr.url())
    assert parsed.cuit == qr.cuit
    assert parsed.codAut == qr.codAut
    img = render_factura(
        qr,
        profesional="Dr/a. Prueba",
        matricula="111",
        especialidad="Clínica médica",
        paciente="Socio Demo",
        socio_nro="400001",
        detalle="Consulta",
        diagnostico="Sintético",
    )
    back = decode_image(img)
    assert back is not None
    assert back.nroCmp == 44
    assert back.importe == 85000


def test_business_days_around_november():
    assert not is_business_day(date(2026, 11, 20))
    assert not is_business_day(date(2026, 11, 21))  # sábado
    assert not is_business_day(date(2026, 11, 22))  # domingo
    assert not is_business_day(date(2026, 11, 23))
    assert is_business_day(date(2026, 11, 24))
    assert add_business_days(date(2026, 11, 19), 1) == date(2026, 11, 24)
    assert business_days_between(date(2026, 11, 19), date(2026, 11, 24)) == 1
