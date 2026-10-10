"""
PDF text extraction using PyMuPDF, with optional OCR fallback (Tesseract)
for scanned pages that contain no extractable text layer.
"""
import logging
from dataclasses import dataclass

import fitz  # PyMuPDF

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str


def extract_pdf_pages(file_path: str) -> list[PageText]:
    """Extract raw text per page. Falls back to OCR per-page if enabled and
    the page has no extractable text (e.g. scanned image)."""
    pages: list[PageText] = []
    doc = fitz.open(file_path)
    try:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text and settings.enable_ocr:
                text = _ocr_page(page)
            pages.append(PageText(page_number=i, text=text))
    finally:
        doc.close()
    logger.info("Extracted %d pages from %s", len(pages), file_path)
    return pages


def _ocr_page(page: "fitz.Page") -> str:
    """OCR a single page image using Tesseract. Requires pytesseract + tesseract binary."""
    try:
        import pytesseract
        from PIL import Image
        import io

        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img)
    except Exception as exc:  # pragma: no cover - OCR is optional/best-effort
        logger.warning("OCR failed for a page: %s", exc)
        return ""
