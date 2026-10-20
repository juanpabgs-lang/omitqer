"""ARCA invoice QR (RG 4892/2020) encode and decode."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import segno
from PIL import Image

QR_PREFIX = "https://www.arca.gob.ar/fe/qr/?p="
# Historic AFIP host still seen on older invoices
QR_PREFIX_AFIP = "https://www.afip.gob.ar/fe/qr/?p="


@dataclass
class ArcaQr:
    ver: int
    fecha: str
    cuit: int
    ptoVta: int
    tipoCmp: int
    nroCmp: int
    importe: float
    moneda: str
    ctz: float
    tipoCodAut: str
    codAut: int
    tipoDocRec: int | None = None
    nroDocRec: str | int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ver": self.ver,
            "fecha": self.fecha,
            "cuit": int(self.cuit),
            "ptoVta": int(self.ptoVta),
            "tipoCmp": int(self.tipoCmp),
            "nroCmp": int(self.nroCmp),
            "importe": float(self.importe),
            "moneda": self.moneda,
            "ctz": float(self.ctz),
            "tipoCodAut": self.tipoCodAut,
            "codAut": int(self.codAut),
        }
        if self.tipoDocRec is not None:
            d["tipoDocRec"] = int(self.tipoDocRec)
        if self.nroDocRec is not None:
            d["nroDocRec"] = self.nroDocRec
        return d

    def url(self) -> str:
        payload = json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)
        token = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        return QR_PREFIX + token


def encode_url(data: dict[str, Any] | ArcaQr) -> str:
    if isinstance(data, ArcaQr):
        return data.url()
    return ArcaQr(**data).url()  # type: ignore[arg-type]


def parse_url(url: str) -> ArcaQr:
    url = url.strip()
    token = None
    for prefix in (QR_PREFIX, QR_PREFIX_AFIP):
        if url.startswith(prefix):
            token = url[len(prefix) :]
            break
    if token is None:
        m = re.search(r"[?&]p=([^&\s]+)", url)
        if not m:
            raise ValueError("QR no es un comprobante ARCA RG 4892")
        token = m.group(1)
    pad = "=" * (-len(token) % 4)
    raw = base64.b64decode(token + pad)
    data = json.loads(raw.decode("utf-8"))
    return ArcaQr(
        ver=int(data.get("ver", 1)),
        fecha=str(data["fecha"]),
        cuit=int(data["cuit"]),
        ptoVta=int(data["ptoVta"]),
        tipoCmp=int(data["tipoCmp"]),
        nroCmp=int(data["nroCmp"]),
        importe=float(data["importe"]),
        moneda=str(data.get("moneda", "PES")),
        ctz=float(data.get("ctz", 1)),
        tipoCodAut=str(data.get("tipoCodAut", "E")),
        codAut=int(data["codAut"]),
        tipoDocRec=int(data["tipoDocRec"]) if data.get("tipoDocRec") is not None else None,
        nroDocRec=data.get("nroDocRec"),
    )


def render_qr_png(data: dict[str, Any] | ArcaQr, scale: int = 6) -> Image.Image:
    url = encode_url(data)
    buf = BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=scale, border=2)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def decode_image(image: Image.Image) -> ArcaQr | None:
    import zxingcpp

    if image.mode != "RGB":
        image = image.convert("RGB")
    results = zxingcpp.read_barcodes(image)
    for r in results:
        text = getattr(r, "text", None) or str(r)
        if "fe/qr" in text or "p=" in text:
            try:
                return parse_url(text)
            except Exception:
                continue
        try:
            return parse_url(text)
        except Exception:
            continue
    return None
