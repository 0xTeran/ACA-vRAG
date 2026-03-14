"""Utilidad para extraer texto del PDF del Decreto 1881 de 2021."""
from __future__ import annotations

import re
from pathlib import Path

from PyPDF2 import PdfReader

from config import DECRETO_PDF_PATH


def load_pdf(path: str | None = None) -> str:
    """Carga todo el texto del PDF."""
    path = path or DECRETO_PDF_PATH
    reader = PdfReader(Path(path))
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    return "\n".join(pages_text)


def extract_sections(full_text: str) -> dict[str, str]:
    """Divide el texto en secciones (SECCIÓN I, II, ...) con su contenido."""
    pattern = r"(SECCIÓN\s+[IVXLCDM]+\.?\s*\n)"
    parts = re.split(pattern, full_text, flags=re.IGNORECASE)
    sections: dict[str, str] = {}
    if parts[0].strip():
        sections["PREÁMBULO"] = parts[0].strip()
    for i in range(1, len(parts) - 1, 2):
        header = parts[i].strip().rstrip(".")
        body = parts[i + 1] if i + 1 < len(parts) else ""
        sections[header] = body.strip()
    return sections


def extract_chapters(full_text: str) -> dict[str, str]:
    """Divide el texto en capítulos (CAPÍTULO 1, 2, ...) con su contenido."""
    pattern = r"(CAPÍTULO\s+\d+\.?\s*\n)"
    parts = re.split(pattern, full_text, flags=re.IGNORECASE)
    chapters: dict[str, str] = {}
    if parts[0].strip():
        chapters["REGLAS_GENERALES"] = parts[0].strip()
    for i in range(1, len(parts) - 1, 2):
        header = parts[i].strip().rstrip(".")
        body = parts[i + 1] if i + 1 < len(parts) else ""
        chapters[header] = body.strip()
    return chapters


def find_relevant_chapters(product_description: str, full_text: str) -> str:
    """Busca los capítulos más relevantes para un producto dado.

    Retorna el texto de los capítulos que contengan palabras clave del producto.
    """
    chapters = extract_chapters(full_text)
    keywords = set(product_description.lower().split())
    # Siempre incluir reglas generales
    relevant = [chapters.get("REGLAS_GENERALES", "")]

    for chapter_name, chapter_text in chapters.items():
        if chapter_name == "REGLAS_GENERALES":
            continue
        chapter_lower = chapter_text[:2000].lower()
        matches = sum(1 for kw in keywords if kw in chapter_lower and len(kw) > 3)
        if matches >= 1:
            relevant.append(f"\n--- {chapter_name} ---\n{chapter_text}")

    return "\n".join(relevant)
