"""Render synthetic ARCA Factura C images with a real RG 4892 QR."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from backend.app.ingest.qr_arca import ArcaQr, render_qr_png


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def render_factura(
    qr: ArcaQr,
    *,
    profesional: str,
    matricula: str,
    especialidad: str,
    paciente: str,
    socio_nro: str,
    detalle: str,
    diagnostico: str | None,
    sesiones: str | None = None,
    domicilio: str = "Av. Santa Fe 2145, CABA",
    iva: str = "IVA Responsable Monotributo",
    warped: bool = False,
    missing_stamp: bool = False,
) -> Image.Image:
    w, h = 1240, 1754
    img = Image.new("RGB", (w, h), "#F7F4EE")
    d = ImageDraw.Draw(img)
    ink = "#1A1A1A"
    navy = "#002583"
    d.rectangle((0, 0, w, 90), fill=navy)
    d.text((48, 28), "FACTURA C", font=_font(36, True), fill="#F7F4EE")
    d.text((780, 36), "COMPROBANTE ELECTRÓNICO", font=_font(16), fill="#F7F4EE")

    y = 120
    d.text((48, y), profesional, font=_font(28, True), fill=ink)
    d.text((48, y + 40), f"CUIT {qr.cuit}   {iva}", font=_font(16), fill=ink)
    d.text((48, y + 68), domicilio, font=_font(16), fill="#444")
    d.text((48, y + 96), f"Inicio de actividades: 12/03/2014    IIBB: {str(qr.cuit)[-8:]}", font=_font(14), fill="#555")

    box = (48, 230, w - 48, 360)
    d.rectangle(box, outline=navy, width=2)
    d.text((64, 244), f"Punto de venta: {qr.ptoVta:05d}", font=_font(16), fill=ink)
    d.text((64, 274), f"Comp. N°: {qr.nroCmp:08d}", font=_font(16), fill=ink)
    d.text((64, 304), f"Fecha: {qr.fecha}", font=_font(16), fill=ink)
    d.text((520, 244), f"CAE: {qr.codAut}", font=_font(16), fill=ink)
    d.text((520, 274), f"Tipo: {qr.tipoCmp}  (Factura C)", font=_font(16), fill=ink)
    d.text((520, 304), f"Moneda: {qr.moneda}  Ctz {qr.ctz}", font=_font(16), fill=ink)

    d.text((48, 390), "Datos del socio / paciente", font=_font(18, True), fill=navy)
    d.text((48, 424), f"Paciente: {paciente}", font=_font(16), fill=ink)
    d.text((48, 454), f"N° socio: {socio_nro}    OMINT S.A. de Servicios", font=_font(16), fill=ink)
    if qr.nroDocRec:
        d.text((48, 484), f"Doc. receptor: {qr.nroDocRec}", font=_font(16), fill=ink)

    d.text((48, 540), "Detalle de la prestación", font=_font(18, True), fill=navy)
    d.line((48, 572, w - 48, 572), fill="#C9C4B8", width=1)
    d.text((48, 590), detalle, font=_font(16), fill=ink)
    if sesiones:
        d.text((48, 624), f"Sesiones: {sesiones}", font=_font(16), fill=ink)
    if diagnostico:
        d.text((48, 658), f"Diagnóstico: {diagnostico}", font=_font(16), fill=ink)
    else:
        d.text((48, 658), "Diagnóstico: —", font=_font(16), fill="#888")

    d.text((48, 740), f"Importe total: $ {qr.importe:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), font=_font(28, True), fill=ink)

    if not missing_stamp:
        d.ellipse((80, 860, 280, 1060), outline=navy, width=3)
        d.text((110, 920), "SELLO", font=_font(18, True), fill=navy)
        d.text((96, 952), profesional.split()[0][:12], font=_font(14), fill=navy)
        d.text((100, 978), f"MN {matricula}", font=_font(14), fill=navy)
        d.text((96, 1004), especialidad[:16], font=_font(12), fill=navy)
        d.text((320, 940), f"Firma y sello — {especialidad}", font=_font(16), fill=ink)
        d.text((320, 972), f"Matrícula {matricula}", font=_font(16), fill=ink)

    qr_img = render_qr_png(qr, scale=7)
    qr_img = qr_img.resize((280, 280), Image.Resampling.NEAREST)
    img.paste(qr_img, (880, 1380))
    d.text((880, 1670), "ARCA RG 4892", font=_font(12), fill="#555")
    d.text((48, 1680), "Original. Documento no válido como factura sin CAE.", font=_font(12), fill="#666")

    if warped:
        img = _phone_photo(img)
    return img


def _phone_photo(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    canvas = Image.new("RGB", (int(w * 1.08), int(h * 1.08)), "#2A2A28")
    canvas.paste(img, (40, 30))
    canvas = ImageOps.autocontrast(canvas, cutoff=1)
    canvas = ImageEnhance.Brightness(canvas).enhance(0.92)
    canvas = ImageEnhance.Color(canvas).enhance(0.85)
    canvas = canvas.filter(ImageFilter.GaussianBlur(radius=0.4))
    # slight perspective via transform
    nw, nh = canvas.size
    coeffs = _find_coeffs(
        [(0, 0), (nw, 0), (nw, nh), (0, nh)],
        [(18, 8), (nw - 6, 22), (nw - 28, nh - 10), (32, nh - 4)],
    )
    warped = canvas.transform((nw, nh), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC, fillcolor="#2A2A28")
    return warped


def _find_coeffs(src: list[tuple[int, int]], dst: list[tuple[int, int]]):
    import numpy as np

    matrix = []
    for s, d in zip(src, dst):
        matrix.append([d[0], d[1], 1, 0, 0, 0, -s[0] * d[0], -s[0] * d[1]])
        matrix.append([0, 0, 0, d[0], d[1], 1, -s[1] * d[0], -s[1] * d[1]])
    A = np.array(matrix, dtype=float)
    B = np.array(src, dtype=float).reshape(8)
    res = np.linalg.lstsq(A, B, rcond=None)[0]
    return res.tolist()


def save_png(img: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    return path


def png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
