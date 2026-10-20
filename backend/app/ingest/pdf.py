"""PDF text extraction and first-page render via pypdfium2."""

from __future__ import annotations

from io import BytesIO

from PIL import Image


def render_first_page(data: bytes, scale: float = 2.0) -> Image.Image:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    page = pdf[0]
    bitmap = page.render(scale=scale)
    image = bitmap.to_pil()
    return image.convert("RGB")


def extract_text(data: bytes) -> str:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    parts = []
    for page in pdf:
        parts.append(page.get_textpage().get_text_bounded())
    return "\n".join(parts)


def load_image_or_pdf(data: bytes, filename: str = "") -> tuple[Image.Image | None, str]:
    name = filename.lower()
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        image = render_first_page(data)
        text = extract_text(data)
        return image, text
    try:
        image = Image.open(BytesIO(data)).convert("RGB")
        return image, ""
    except Exception:
        return None, ""
