"""SQLite connection and schema for the OMINT demo."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "omint.db"
SAMPLES_DIR = DATA_DIR / "samples"
KEYS_DIR = DATA_DIR / "keys"


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY,
    socio_nro TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL,
    dni TEXT NOT NULL,
    plan TEXT NOT NULL,
    zona TEXT NOT NULL,
    familia_id INTEGER,
    tenure_months INTEGER NOT NULL,
    cbu TEXT NOT NULL,
    email TEXT,
    churn_risk REAL NOT NULL DEFAULT 0,
    churned INTEGER NOT NULL DEFAULT 0,
    churn_reason TEXT,
    holdout INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id),
    version TEXT NOT NULL,
    plan TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    body TEXT NOT NULL,
    signed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS professionals (
    id INTEGER PRIMARY KEY,
    cuit TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    matricula TEXT NOT NULL,
    especialidad TEXT NOT NULL,
    jurisdiccion TEXT NOT NULL,
    zona TEXT NOT NULL,
    precio_base INTEGER NOT NULL,
    refeps_estado TEXT NOT NULL,
    en_directo INTEGER NOT NULL DEFAULT 0,
    cbu TEXT,
    riesgo TEXT NOT NULL DEFAULT 'bajo',
    onboarded_at TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    cuit TEXT NOT NULL,
    pto_vta INTEGER NOT NULL,
    tipo_cmp INTEGER NOT NULL,
    nro_cmp INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    importe REAL NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'PES',
    cae TEXT NOT NULL,
    tipo_doc_rec INTEGER,
    nro_doc_rec TEXT,
    raw_json TEXT NOT NULL,
    resultado_wscdc TEXT NOT NULL DEFAULT 'A',
    UNIQUE(cuit, pto_vta, tipo_cmp, nro_cmp)
);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY,
    public_id TEXT UNIQUE NOT NULL,
    member_id INTEGER NOT NULL REFERENCES members(id),
    professional_id INTEGER REFERENCES professionals(id),
    invoice_id INTEGER REFERENCES invoices(id),
    tipo TEXT NOT NULL,
    route TEXT NOT NULL,
    status TEXT NOT NULL,
    importe REAL NOT NULL,
    estimado REAL NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'ARS',
    fecha_prestacion TEXT NOT NULL,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    sample_key TEXT,
    attestation_id INTEGER,
    notes TEXT,
    diagnosis_hidden TEXT,
    days_to_pay INTEGER,
    bounced INTEGER NOT NULL DEFAULT 0,
    bounce_reason TEXT,
    stall_stage TEXT,
    historical INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS claim_checks (
    id INTEGER PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id),
    name TEXT NOT NULL,
    ok INTEGER NOT NULL,
    result TEXT NOT NULL,
    source TEXT NOT NULL,
    citation TEXT,
    raw_request TEXT,
    raw_response TEXT
);

CREATE TABLE IF NOT EXISTS claim_docs (
    id INTEGER PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id),
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_events (
    id INTEGER PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES claims(id),
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_events (
    id INTEGER PRIMARY KEY,
    seq INTEGER UNIQUE NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    payload TEXT NOT NULL,
    signature TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS value_events (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    ars REAL NOT NULL,
    status TEXT NOT NULL,
    evidence_hash TEXT NOT NULL,
    claim_id INTEGER,
    liquidacion_id INTEGER,
    created_at TEXT NOT NULL,
    confirmed_by TEXT,
    confirmed_at TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS attestations (
    id INTEGER PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id),
    professional_id INTEGER NOT NULL REFERENCES professionals(id),
    confirmed_at TEXT,
    created_at TEXT NOT NULL,
    claim_id INTEGER
);

CREATE TABLE IF NOT EXISTS liquidaciones (
    id INTEGER PRIMARY KEY,
    provider_name TEXT NOT NULL,
    period TEXT NOT NULL,
    convenio TEXT NOT NULL,
    total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS liquidacion_lines (
    id INTEGER PRIMARY KEY,
    liquidacion_id INTEGER NOT NULL REFERENCES liquidaciones(id),
    member_id INTEGER REFERENCES members(id),
    codigo TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    importe REAL NOT NULL,
    convenio_importe REAL NOT NULL,
    auth TEXT,
    planted_anomaly TEXT,
    member_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS debitos (
    id INTEGER PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES liquidacion_lines(id),
    reason TEXT NOT NULL,
    ars REAL NOT NULL,
    status TEXT NOT NULL,
    proposed_at TEXT NOT NULL,
    confirmed_by TEXT,
    confirmed_at TEXT,
    evidence_hash TEXT
);

CREATE TABLE IF NOT EXISTS denuncias (
    id INTEGER PRIMARY KEY,
    public_id TEXT UNIQUE NOT NULL,
    member_id INTEGER NOT NULL REFERENCES members(id),
    claim_id INTEGER,
    tipo TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    deadline TEXT NOT NULL,
    status TEXT NOT NULL,
    asunto TEXT NOT NULL,
    descargo TEXT
);

CREATE TABLE IF NOT EXISTS sap_outbox (
    id INTEGER PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id),
    api TEXT NOT NULL,
    comm_scenario TEXT NOT NULL,
    payload TEXT NOT NULL,
    posted_at TEXT,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS samples (
    key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    path TEXT NOT NULL,
    member_id INTEGER,
    expected_route TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id),
    professional_id INTEGER,
    member_id INTEGER,
    amount REAL NOT NULL,
    rail TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tx_ref TEXT
);

CREATE TABLE IF NOT EXISTS clawbacks (
    id INTEGER PRIMARY KEY,
    claim_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT,
    approved_by TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_member ON claims(member_id);
CREATE INDEX IF NOT EXISTS idx_value_status ON value_events(status);
CREATE INDEX IF NOT EXISTS idx_invoices_cae ON invoices(cae);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path or DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    own = conn is None
    conn = conn or connect()
    conn.executescript(SCHEMA)
    conn.commit()
    if own:
        return conn
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def rows(cur: sqlite3.Cursor | list) -> list[dict]:
    if isinstance(cur, list):
        return [dict(r) for r in cur]
    return [dict(r) for r in cur.fetchall()]


def one(cur: sqlite3.Cursor) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None
