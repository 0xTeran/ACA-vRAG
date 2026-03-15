"""Utilidad para extraer texto del PDF del Decreto 1881 de 2021."""
from __future__ import annotations

import re
from pathlib import Path

from PyPDF2 import PdfReader

from config import DECRETO_PDF_PATH

# Límite de contexto para el modelo (dejar margen para prompt + investigación)
MAX_CONTEXT_CHARS = 60000


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

    Usa un sistema de scoring para priorizar capítulos:
    - Busca keywords en todo el texto del capítulo (no solo los primeros 2000 chars)
    - Puntúa más alto si la keyword aparece en el título/notas del capítulo
    - Ordena por relevancia y ajusta al límite de tokens
    """
    chapters = extract_chapters(full_text)

    # Extraer keywords significativas (>3 chars, sin stopwords)
    stopwords = {
        "para", "como", "está", "este", "esta", "estos", "estas", "sido",
        "tiene", "tienen", "puede", "pueden", "será", "sean", "donde",
        "entre", "desde", "hasta", "sobre", "bajo", "cada", "todo",
        "todos", "otras", "otros", "otro", "otra", "también", "pero",
        "cuando", "porque", "aunque", "sino", "según", "cual", "cuyo",
        "tipo", "nombre", "producto", "ficha", "técnica", "descripción",
        "presentación", "origen", "proceso", "consumo", "humano",
        "general", "especial", "forma", "modo", "manera", "parte",
        "peso", "alto", "bajo", "mayor", "menor", "gran", "grande",
    }
    words = product_description.lower().split()
    keywords = {w for w in words if len(w) > 3 and w not in stopwords}

    # Buscar subpartidas mencionadas en la descripción (ej: 8424.89)
    partidas_mencionadas = set(re.findall(r'\d{4}\.\d{2}', product_description))

    # Score cada capítulo
    scored: list[tuple[int, str, str]] = []

    for chapter_name, chapter_text in chapters.items():
        if chapter_name == "REGLAS_GENERALES":
            continue

        score = 0
        chapter_lower = chapter_text.lower()

        # Score por keywords en título/notas (primeros 500 chars = alta relevancia)
        header_text = chapter_lower[:500]
        for kw in keywords:
            if kw in header_text:
                score += 10  # Keywords en título pesan más

        # Score por keywords en el cuerpo completo
        for kw in keywords:
            count = chapter_lower.count(kw)
            if count > 0:
                score += min(count, 5)  # Máximo 5 puntos por keyword

        # Score alto si contiene una partida mencionada explícitamente
        for partida in partidas_mencionadas:
            if partida in chapter_text:
                score += 50  # Prioridad máxima

        # Extraer número de capítulo para buscar por código arancelario
        cap_num_match = re.search(r'CAPÍTULO\s+(\d+)', chapter_name, re.IGNORECASE)
        if cap_num_match:
            cap_num = cap_num_match.group(1).zfill(2)
            # Si alguna keyword parece un código arancelario del capítulo
            for kw in keywords:
                if kw.startswith(cap_num):
                    score += 30

        if score > 0:
            scored.append((score, chapter_name, chapter_text))

    # Ordenar por score descendente
    scored.sort(key=lambda x: -x[0])

    # Construir contexto respetando el límite
    parts: list[str] = []
    total_chars = 0

    # Siempre incluir reglas generales (compactas)
    reglas = chapters.get("REGLAS_GENERALES", "")
    if reglas:
        # Solo las reglas generales de interpretación, no todo el preámbulo
        reglas_cortas = reglas[:3000]
        parts.append(reglas_cortas)
        total_chars += len(reglas_cortas)

    # Agregar capítulos por relevancia hasta llenar el límite
    for score, chapter_name, chapter_text in scored:
        chunk = f"\n--- {chapter_name} (relevancia: {score}) ---\n{chapter_text}"
        if total_chars + len(chunk) > MAX_CONTEXT_CHARS:
            # Capítulo muy grande - incluir notas + partidas relevantes
            remaining = MAX_CONTEXT_CHARS - total_chars - 200
            if remaining > 2000 and score >= 5:
                excerpt = _extract_relevant_section(chapter_text, keywords | partidas_mencionadas, max_chars=remaining)
                if excerpt:
                    chunk = f"\n--- {chapter_name} (extracto, relevancia: {score}) ---\n{excerpt}"
                    parts.append(chunk)
                    total_chars += len(chunk)
            continue  # Intentar con el siguiente capítulo también
        parts.append(chunk)
        total_chars += len(chunk)

    return "\n".join(parts)


def _extract_relevant_section(chapter_text: str, keywords: set[str], max_chars: int = 15000) -> str:
    """Extrae las partes relevantes de un capítulo grande.

    Estrategia:
    1. Notas del capítulo (siempre)
    2. Partidas de 4 dígitos que matcheen keywords → incluir completas con subpartidas
    3. Índice de todas las partidas del capítulo (para referencia)
    """
    lines = chapter_text.split("\n")

    # Identificar bloques de partidas: partida XX.XX → todo hasta la siguiente XX.XX
    partida_blocks: list[tuple[int, int, str]] = []  # (start, end, partida_code)
    partida_starts: list[int] = []

    for i, line in enumerate(lines):
        if re.match(r'^\d{2}\.\d{2}\b', line.strip()):
            partida_starts.append(i)

    for idx, start in enumerate(partida_starts):
        end = partida_starts[idx + 1] if idx + 1 < len(partida_starts) else len(lines)
        code = lines[start].strip().split()[0] if lines[start].strip() else ""
        partida_blocks.append((start, end, code))

    # 1. Notas del capítulo (antes de primera partida)
    notes_end = partida_starts[0] if partida_starts else min(50, len(lines))
    result_parts: list[str] = ["\n".join(lines[:notes_end])]
    total = len(result_parts[0])

    # 2. Encontrar partidas relevantes (keywords en su bloque de texto)
    relevant_blocks: list[tuple[int, int, str, int]] = []  # + score
    for start, end, code in partida_blocks:
        block_text = "\n".join(lines[start:end]).lower()
        score = 0
        for kw in keywords:
            if kw in block_text:
                score += block_text.count(kw)
        # También matchear por código de partida
        for kw in keywords:
            if kw in code:
                score += 20
        if score > 0:
            relevant_blocks.append((start, end, code, score))

    relevant_blocks.sort(key=lambda x: -x[3])

    # 3. Incluir partidas relevantes completas (con todas sus subpartidas)
    for start, end, code, score in relevant_blocks:
        block = f"\n[Partida {code}]\n" + "\n".join(lines[start:end])
        if total + len(block) > max_chars - 2000:
            break
        result_parts.append(block)
        total += len(block)

    # 4. Índice de partidas no incluidas (para que el modelo sepa qué más existe)
    included_codes = {b[2] for b in relevant_blocks if any(b[2] in p for p in result_parts)}
    index_lines = ["\n[Otras partidas en este capítulo:]"]
    for start, end, code in partida_blocks:
        if code not in included_codes and start < len(lines):
            desc = ""
            for j in range(start, min(start + 3, end)):
                desc += " " + lines[j].strip()
            index_lines.append(f"  {desc.strip()[:120]}")

    index_text = "\n".join(index_lines)
    if total + len(index_text) <= max_chars:
        result_parts.append(index_text)

    return "\n".join(result_parts)
