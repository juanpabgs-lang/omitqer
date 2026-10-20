from backend.app.integrity import provider_audit
from backend.app.ledger import chain, value
from backend.app.roi import model as roi
from backend.app.rules.engine import Route


def test_roi_hand_calc():
    c = roi.compute()
    members = 262_620
    pmpm = 420_000
    revenue = members * pmpm * 12
    integrity = revenue * 0.82 * 0.60 * 0.005
    kept = members * 0.16 * 0.12 * 0.35
    retention = kept * pmpm * 12 * 0.12
    hours = 11 * 262_600 / 60
    fte = hours / 1760
    capacity = fte * 32_900_000
    refund = 11_800_000_000 * 0.03 * 0.60
    regulatory = 80 * (0.25 - 0.05) * 15 * 435_748.51
    run = integrity + retention + capacity + refund + regulatory - 100_000_000 - 100_000_000
    assert abs(c["revenue_ars"] - revenue) < 1
    assert abs(c["run_rate_ars"] - run) < 1
    assert 5.0e9 < c["run_rate_ars"] < 6.2e9
    assert c["run_rate_usd"] == c["run_rate_ars"] / 1525


def test_audit_precision_recall(conn):
    lid = conn.execute("SELECT id FROM liquidaciones LIMIT 1").fetchone()["id"]
    report = provider_audit.audit_liquidacion(conn, lid)
    assert report["planted"] > 0
    assert report["recall"] >= 0.7
    assert report["precision"] >= 0.7


def test_ledger_reconciles(conn):
    totals = value.totals(conn)
    confirmed = conn.execute(
        "SELECT COALESCE(SUM(ars),0) AS s FROM value_events WHERE status='confirmado'"
    ).fetchone()["s"]
    assert abs(totals["confirmado_ars"] - confirmed) < 0.01
    v = chain.verify_chain(conn)
    assert v["ok"] is True


def test_ledger_tamper_detected(conn):
    row = conn.execute("SELECT id, hash FROM ledger_events ORDER BY seq DESC LIMIT 1").fetchone()
    conn.execute("UPDATE ledger_events SET hash=? WHERE id=?", ("0" * 64, row["id"]))
    broken = chain.verify_chain(conn)
    assert broken["ok"] is False
    conn.execute("UPDATE ledger_events SET hash=? WHERE id=?", (row["hash"], row["id"]))


def test_directo_requires_attestation(conn):
    from backend.app.directo.service import require_attestation

    assert require_attestation(conn, None) is False
    conn.execute(
        "INSERT INTO attestations (member_id, professional_id, created_at) VALUES (1,1,'2026-10-20T10:00:00')"
    )
    aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    assert require_attestation(conn, aid) is False
    conn.execute("UPDATE attestations SET confirmed_at='2026-10-20T10:01:00' WHERE id=?", (aid,))
    assert require_attestation(conn, aid) is True


def test_wscdc_sandbox(conn):
    from backend.app.ingest.qr_arca import ArcaQr
    from backend.app.registries import arca_wscdc

    row = conn.execute("SELECT * FROM invoices WHERE resultado_wscdc='A' LIMIT 1").fetchone()
    qr = ArcaQr(
        ver=1,
        fecha=row["fecha"],
        cuit=int(row["cuit"]),
        ptoVta=row["pto_vta"],
        tipoCmp=row["tipo_cmp"],
        nroCmp=row["nro_cmp"],
        importe=row["importe"],
        moneda="PES",
        ctz=1,
        tipoCodAut="E",
        codAut=int(row["cae"]),
    )
    ok = arca_wscdc.constat(conn, qr)
    assert ok["Resultado"] == "A"
    ghost = ArcaQr(
        ver=1, fecha="2026-01-01", cuit=20999999999, ptoVta=9, tipoCmp=11, nroCmp=1,
        importe=1, moneda="PES", ctz=1, tipoCodAut="E", codAut=1,
    )
    bad = arca_wscdc.constat(conn, ghost)
    assert bad["Resultado"] == "R"


def test_route_enum_invariant():
    assert list(Route) == [Route.VIA_RAPIDA, Route.FALTA_DOCUMENTACION, Route.REVISION_HUMANA]
