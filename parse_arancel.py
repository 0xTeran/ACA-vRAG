#!/usr/bin/env python3
"""Parsea el Decreto 1881 de 2021 (PDF) y carga las subpartidas a Supabase."""
from __future__ import annotations

import re
import sys

from pdf_loader import load_pdf


def parse_arancel(text: str) -> list[dict]:
    """Extrae todas las subpartidas del texto del arancel.

    Busca el patrón: código 10 dígitos + descripción + gravamen.
    Maneja múltiples formatos del PDF.
    """
    lines = text.split("\n")
    entries: list[dict] = []
    seen: set[str] = set()

    current_section = ""
    current_chapter = ""
    current_partida_desc = ""

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detectar sección
        sec_match = re.match(r"^SECCIÓN\s+([IVXLCDM]+)", stripped, re.IGNORECASE)
        if sec_match:
            current_section = sec_match.group(1)
            continue

        # Detectar capítulo
        cap_match = re.match(r"^CAPÍTULO\s+(\d+)", stripped, re.IGNORECASE)
        if cap_match:
            current_chapter = cap_match.group(1).zfill(2)
            continue

        # Detectar partida (XX.XX + descripción)
        partida_match = re.match(r"^(\d{2}\.\d{2})\s*$", stripped)
        if partida_match:
            # Buscar descripción en las líneas siguientes
            desc_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                next_l = lines[j].strip()
                if not next_l or re.match(r"^\d{4}", next_l) or re.match(r"^-", next_l):
                    break
                if not next_l.startswith("<") and not next_l.startswith(">"):
                    desc_lines.append(next_l)
            current_partida_desc = " ".join(desc_lines)
            continue

        # Detectar subpartida de 10 dígitos
        code_match = re.match(r"^(\d{4}\.\d{2}\.\d{2}\.\d{2})", stripped)
        if not code_match:
            continue

        code = code_match.group(1)
        if code in seen:
            continue
        seen.add(code)

        # Extraer descripción: buscar en la misma línea (después del código) o líneas cercanas
        desc = ""
        rest = stripped[len(code):].strip()
        if rest and not re.match(r"^\d+$", rest):
            desc = rest.strip("- ")

        if not desc:
            # Buscar descripción ANTES del código (patrón común en el PDF)
            for j in range(i - 1, max(i - 5, -1), -1):
                prev = lines[j].strip()
                if not prev or re.match(r"^\d{4}\.\d{2}", prev) or re.match(r"^\d+$", prev):
                    break
                if prev.startswith("<") or prev.startswith(">"):
                    continue
                desc = prev.strip("- ") + (" " + desc if desc else "")

        # Buscar gravamen DESPUÉS del código
        gravamen = None
        for j in range(i + 1, min(i + 4, len(lines))):
            next_l = lines[j].strip()
            grv_match = re.match(r"^(\d{1,3})\s*$", next_l)
            if grv_match:
                g = int(grv_match.group(1))
                if g <= 100:  # Gravámenes válidos
                    gravamen = g
                break
            if re.match(r"^\d{4}", next_l):
                break

        # También buscar gravamen en la misma línea
        if gravamen is None:
            inline_grv = re.search(r"\s(\d{1,3})\s*$", stripped)
            if inline_grv:
                g = int(inline_grv.group(1))
                if g <= 100:
                    gravamen = g

        capitulo = code[:2]
        partida = code[:5]

        # Limpiar descripción
        desc = re.sub(r"\s+", " ", desc).strip()
        if not desc:
            desc = current_partida_desc[:200] if current_partida_desc else "Sin descripción"

        entries.append({
            "codigo": code,
            "descripcion": desc[:500],
            "gravamen": gravamen,
            "capitulo": capitulo,
            "partida": partida,
            "seccion": current_section or None,
        })

    return entries


def cargar_a_supabase(entries: list[dict], batch_size: int = 200):
    """Carga las subpartidas a Supabase en batches."""
    from database import get_client

    client = get_client()

    # Limpiar tabla existente
    print("Limpiando tabla arancel...")
    client.table("arancel").delete().neq("codigo", "").execute()

    total = len(entries)
    for i in range(0, total, batch_size):
        batch = entries[i : i + batch_size]
        client.table("arancel").upsert(batch).execute()
        print(f"  Cargados {min(i + batch_size, total)}/{total}")

    print(f"✓ {total} subpartidas cargadas a Supabase")


if __name__ == "__main__":
    print("Cargando PDF del Decreto 1881...")
    text = load_pdf()
    print(f"PDF: {len(text):,} caracteres")

    print("Parseando subpartidas...")
    entries = parse_arancel(text)
    print(f"Subpartidas encontradas: {len(entries)}")

    # Stats
    with_gravamen = sum(1 for e in entries if e["gravamen"] is not None)
    chapters = len(set(e["capitulo"] for e in entries))
    print(f"Con gravamen: {with_gravamen} ({100*with_gravamen//len(entries)}%)")
    print(f"Capítulos: {chapters}")

    if "--upload" in sys.argv:
        cargar_a_supabase(entries)
    else:
        print("\nUsa --upload para cargar a Supabase")
        # Mostrar muestra
        for e in entries[:3]:
            print(f"  {e['codigo']} | {e['gravamen']}% | {e['descripcion'][:60]}")
        print("  ...")
        for e in entries[-3:]:
            print(f"  {e['codigo']} | {e['gravamen']}% | {e['descripcion'][:60]}")
