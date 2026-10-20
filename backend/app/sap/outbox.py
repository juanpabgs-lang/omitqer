"""Clean-core SAP S/4HANA Public Cloud payloads. Never invent Z-APIs."""

from __future__ import annotations

import json
from datetime import datetime


def supplier_invoice_payload(claim: dict, member: dict) -> dict:
    return {
        "CommunicationScenario": "SAP_COM_0057",
        "API": "API_SUPPLIERINVOICE_PROCESS_SRV",
        "SupplierInvoice": {
            "CompanyCode": "AR01",
            "DocumentDate": claim.get("fecha_prestacion"),
            "PostingDate": claim.get("paid_at") or datetime.now().date().isoformat(),
            "InvoiceGrossAmount": f"{claim['estimado']:.2f}",
            "DocumentCurrency": "ARS",
            "InvoicingParty": "ONETIME",
            "SupplierInvoiceIDByInvoicingParty": claim.get("public_id"),
            "PaymentTerms": "0001",
            "TaxIsCalculatedAutomatically": True,
            "to_SuplrInvcItemPurOrdRef": [
                {
                    "SupplierInvoiceItem": "1",
                    "DocumentCurrency": "ARS",
                    "SupplierInvoiceItemAmount": f"{claim['estimado']:.2f}",
                    "GLAccount": "65010000",
                    "CostCenter": "REINTEGROS",
                    "TaxCode": "V0",
                    "Text": f"Reintegro {member.get('socio_nro')} {claim.get('tipo')}",
                }
            ],
        },
        "note": "One-time supplier invoice for member reimbursement. Clean-core, released API only.",
    }


def journal_entry_payload(claim: dict, member: dict) -> dict:
    return {
        "CommunicationScenario": "SAP_COM_0002",
        "API": "Journal Entry - Post (SOAP)",
        "JournalEntry": {
            "OriginalReferenceDocumentType": "BKPFF",
            "BusinessTransactionType": "RFBU",
            "AccountingDocumentType": "SA",
            "CompanyCode": "AR01",
            "DocumentDate": claim.get("paid_at") or datetime.now().date().isoformat(),
            "PostingDate": claim.get("paid_at") or datetime.now().date().isoformat(),
            "Item": [
                {
                    "GLAccount": {"Debit": "65010000", "Amount": claim["estimado"], "Text": f"Reintegro {claim.get('public_id')}"},
                },
                {
                    "GLAccount": {"Credit": "21080000", "Amount": claim["estimado"], "Text": f"CBU {member.get('cbu','')[:8]}…"},
                },
            ],
        },
    }


def enqueue(conn, claim: dict, member: dict, kind: str = "supplier_invoice") -> dict:
    payload = supplier_invoice_payload(claim, member) if kind == "supplier_invoice" else journal_entry_payload(claim, member)
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO sap_outbox (claim_id, api, comm_scenario, payload, posted_at, status)
        VALUES (?, ?, ?, ?, ?, 'posted_sandbox')
        """,
        (
            claim["id"],
            payload["API"],
            payload["CommunicationScenario"],
            json.dumps(payload, ensure_ascii=False),
            now,
        ),
    )
    return payload


def list_outbox(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM sap_outbox ORDER BY id DESC LIMIT 50").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d["payload"])
        out.append(d)
    return out
