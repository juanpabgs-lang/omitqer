"""Hash-chained evidence log sealed with Ed25519."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.app.db import KEYS_DIR

GENESIS = "0" * 64


def _key_paths() -> tuple[Path, Path]:
    return KEYS_DIR / "ed25519.pem", KEYS_DIR / "ed25519.pub"


def load_or_create_key() -> Ed25519PrivateKey:
    priv_path, pub_path = _key_paths()
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if priv_path.exists():
        data = priv_path.read_bytes()
        return serialization.load_pem_private_key(data, password=None)  # type: ignore[return-value]
    key = Ed25519PrivateKey.generate()
    priv_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return key


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def event_hash(prev_hash: str, payload: dict) -> str:
    material = (prev_hash + canonical_json(payload)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def last_hash(conn) -> tuple[int, str]:
    row = conn.execute("SELECT seq, hash FROM ledger_events ORDER BY seq DESC LIMIT 1").fetchone()
    if not row:
        return 0, GENESIS
    return int(row["seq"]), row["hash"]


def append(conn, payload: dict, created_at: str | None = None) -> dict:
    key = load_or_create_key()
    seq, prev = last_hash(conn)
    created_at = created_at or datetime.now().isoformat(timespec="seconds")
    body = {**payload, "created_at": created_at}
    digest = event_hash(prev, body)
    sig = key.sign(digest.encode("ascii")).hex()
    conn.execute(
        """
        INSERT INTO ledger_events (seq, prev_hash, hash, payload, signature, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (seq + 1, prev, digest, canonical_json(body), sig, created_at),
    )
    return {"seq": seq + 1, "prev_hash": prev, "hash": digest, "signature": sig, "payload": body}


def verify_chain(conn) -> dict:
    key = load_or_create_key().public_key()
    rows = conn.execute("SELECT * FROM ledger_events ORDER BY seq").fetchall()
    prev = GENESIS
    for i, row in enumerate(rows):
        try:
            payload = json.loads(row["payload"])
        except json.JSONDecodeError:
            return {"ok": False, "broken_at": row["seq"], "reason": "payload corrupto"}
        expected = event_hash(prev, payload)
        if expected != row["hash"] or row["prev_hash"] != prev:
            return {"ok": False, "broken_at": row["seq"], "reason": "hash mismatch"}
        try:
            key.verify(bytes.fromhex(row["signature"]), row["hash"].encode("ascii"))
        except Exception:
            return {"ok": False, "broken_at": row["seq"], "reason": "bad signature"}
        prev = row["hash"]
    return {"ok": True, "events": len(rows), "tip": prev}


def public_key_pem() -> str:
    _, pub = _key_paths()
    if pub.exists():
        return pub.read_text()
    load_or_create_key()
    return pub.read_text()
