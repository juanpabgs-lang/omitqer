"""Local Tesseract OCR for invoice fields. Spanish language pack."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from PIL import Image

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore


@dataclass
class FieldHit:
    name: str
    value: str
    confidence: float
    source: str


@dataclass
class OcrResult:
    text: str
    fields: list[FieldHit] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "fields": [f.__dict__ for f in self.fields],
        }


FIELD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("cuit", re.compile(r"CUIT[:\s]*(\d{2}[-.]?\d{8}[-.]?\d)", re.I)),
    ("cae", re.compile(r"CAE[:\s]*(\d{10,14})", re.I)),
    ("importe", re.compile(r"(?:TOTAL|IMPORTE)[:\s]*\$?\s*([\d\.]+,\d{2}|\d+)", re.I)),
    ("fecha", re.compile(r"Fecha[:\s]*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})", re.I)),
    ("matricula", re.compile(r"(?:Matr[ií]cula|MN|MP)[:\s]*(\d{3,7})", re.I)),
    ("socio", re.compile(r"(?:Socio|N[°º]\s*socio)[:\s]*(\d{5,10})", re.I)),
    ("diagnostico", re.compile(r"Diagn[oó]stico[:\s]*(.+)", re.I)),
    ("paciente", re.compile(r"(?:Paciente|Socio/a)[:\s]*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ ]{3,40})", re.I)),
]


def run_ocr(image: Image.Image) -> OcrResult:
    if pytesseract is None:
        return OcrResult(text="", fields=[])
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    try:
        data = pytesseract.image_to_data(image, lang="spa+eng", output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(image, lang="spa+eng")
    except Exception:
        text = ""
        data = {"conf": [], "text": []}
    fields: list[FieldHit] = []
    for name, pat in FIELD_PATTERNS:
        m = pat.search(text)
        if m:
            confs = [int(c) for c in data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) > 0]
            avg = (sum(confs) / len(confs) / 100) if confs else 0.7
            fields.append(FieldHit(name=name, value=m.group(1).strip(), confidence=round(avg, 2), source="ocr"))
    return OcrResult(text=text, fields=fields)


def parse_importe(raw: str) -> float | None:
    raw = raw.replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None
