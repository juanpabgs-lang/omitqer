"""Production-shaped WSCDC adapter over a local sandbox.

Never calls the real ARCA. The SOAP envelope matches ComprobanteConstatar
so the same adapter can later point at homologación.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.app.ingest.qr_arca import ArcaQr


def soap_envelope(token: str, sign: str, cuit_repr: int, cmp: dict[str, Any]) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ComprobanteConstatar xmlns="http://servicios1.afip.gob.ar/wscdc/">
      <Auth>
        <Token>{token}</Token>
        <Sign>{sign}</Sign>
        <Cuit>{cuit_repr}</Cuit>
      </Auth>
      <CmpReq>
        <CbteModo>{cmp.get("CbteModo", "CAE")}</CbteModo>
        <CuitEmisor>{cmp["CuitEmisor"]}</CuitEmisor>
        <PtoVta>{cmp["PtoVta"]}</PtoVta>
        <CbteTipo>{cmp["CbteTipo"]}</CbteTipo>
        <NroCbte>{cmp["NroCbte"]}</NroCbte>
        <CbteFch>{cmp["CbteFch"]}</CbteFch>
        <ImpTotal>{cmp["ImpTotal"]}</ImpTotal>
        <CodAutorizacion>{cmp["CodAutorizacion"]}</CodAutorizacion>
        <DocTipoReceptor>{cmp.get("DocTipoReceptor", "")}</DocTipoReceptor>
        <DocNroReceptor>{cmp.get("DocNroReceptor", "")}</DocNroReceptor>
      </CmpReq>
    </ComprobanteConstatar>
  </soap:Body>
</soap:Envelope>"""


def constat(conn, qr: ArcaQr, cuit_repr: int = 30685243130) -> dict[str, Any]:
    request = {
        "CuitEmisor": qr.cuit,
        "PtoVta": qr.ptoVta,
        "CbteTipo": qr.tipoCmp,
        "NroCbte": qr.nroCmp,
        "CbteFch": qr.fecha.replace("-", ""),
        "ImpTotal": qr.importe,
        "CodAutorizacion": qr.codAut,
        "DocTipoReceptor": qr.tipoDocRec,
        "DocNroReceptor": qr.nroDocRec,
    }
    envelope = soap_envelope("SANDBOX-TOKEN", "SANDBOX-SIGN", cuit_repr, request)
    row = conn.execute(
        """
        SELECT * FROM invoices
        WHERE cuit=? AND pto_vta=? AND tipo_cmp=? AND nro_cmp=?
        """,
        (str(qr.cuit), qr.ptoVta, qr.tipoCmp, qr.nroCmp),
    ).fetchone()
    if row is None:
        resultado = "R"
        obs = [{"Code": 107, "Msg": "Comprobante inexistente"}]
    else:
        resultado = row["resultado_wscdc"]
        obs = [] if resultado == "A" else [{"Code": 102, "Msg": "CAE inexistente o no vigente"}]
        if abs(float(row["importe"]) - float(qr.importe)) > 0.05:
            resultado = "R"
            obs.append({"Code": 111, "Msg": "Importe informado distinto al autorizado"})
    response = {
        "Resultado": resultado,
        "Observaciones": obs,
        "FchProceso": datetime.now().strftime("%Y%m%d%H%M%S"),
        "sandbox": True,
    }
    return {
        "Resultado": resultado,
        "request": request,
        "response": response,
        "soap": envelope,
        "sandbox": True,
    }
