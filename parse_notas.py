#!/usr/bin/env python3
"""Parsea las notas de sección, capítulo y complementarias del Decreto 1881."""
from __future__ import annotations

import re
import sys

from pdf_loader import load_pdf, extract_chapters, extract_sections


def parse_notas(text: str) -> list[dict]:
    """Extrae notas de sección y capítulo del arancel."""
    notas: list[dict] = []

    # ── Notas de sección ──
    sections = extract_sections(text)
    for sec_name, sec_text in sections.items():
        if sec_name == "PREÁMBULO":
            continue
        # Extraer notas al inicio de cada sección (antes del primer CAPÍTULO)
        cap_pos = re.search(r"CAPÍTULO\s+\d+", sec_text, re.IGNORECASE)
        if cap_pos:
            notas_text = sec_text[: cap_pos.start()].strip()
        else:
            notas_text = sec_text[:3000].strip()

        if notas_text and len(notas_text) > 50:
            notas.append({
                "tipo": "seccion",
                "referencia": sec_name.strip(),
                "contenido": notas_text,
            })

    # ── Notas de capítulo ──
    chapters = extract_chapters(text)
    for chap_name, chap_text in chapters.items():
        if chap_name == "REGLAS_GENERALES":
            # Reglas generales de interpretación
            notas.append({
                "tipo": "reglas_generales",
                "referencia": "Reglas Generales de Interpretación",
                "contenido": chap_text[:5000],
            })
            continue

        # Extraer número de capítulo
        cap_num = re.search(r"\d+", chap_name)
        if not cap_num:
            continue
        cap_str = cap_num.group(0).zfill(2)

        # Las notas están ANTES de la primera partida (XX.XX)
        lines = chap_text.split("\n")
        notas_lines: list[str] = []
        titulo = ""

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Primera línea suele ser el título del capítulo
            if i == 0:
                titulo = stripped
                notas_lines.append(stripped)
                continue
            # Detectar inicio de partidas
            if re.match(r"^\d{2}\.\d{2}\b", stripped):
                break
            notas_lines.append(stripped)

        notas_text = "\n".join(notas_lines).strip()

        # Solo guardar si hay contenido sustancial
        if len(notas_text) > 30:
            notas.append({
                "tipo": "capitulo",
                "referencia": f"Capítulo {cap_str}",
                "contenido": notas_text,
            })

            # Buscar notas complementarias nacionales o Nandina
            comp_match = re.search(
                r"(Nota[s]?\s+complementaria[s]?\s+nacional[es]*[.:].+?)(?=\d{2}\.\d{2}\b|\Z)",
                chap_text,
                re.DOTALL | re.IGNORECASE,
            )
            if comp_match:
                notas.append({
                    "tipo": "complementaria_nacional",
                    "referencia": f"Capítulo {cap_str}",
                    "contenido": comp_match.group(1).strip()[:3000],
                })

            nandina_match = re.search(
                r"(Nota[s]?\s+complementaria[s]?\s+Nandina[.:].+?)(?=Nota[s]?\s+complementaria[s]?\s+nacional|(?:\d{2}\.\d{2}\b)|\Z)",
                chap_text,
                re.DOTALL | re.IGNORECASE,
            )
            if nandina_match:
                notas.append({
                    "tipo": "complementaria_nandina",
                    "referencia": f"Capítulo {cap_str}",
                    "contenido": nandina_match.group(1).strip()[:3000],
                })

    return notas


def cargar_notas_a_supabase(notas: list[dict]):
    """Carga las notas a Supabase."""
    from database import get_client

    client = get_client()

    # Limpiar tabla
    print("Limpiando tabla notas_arancel...")
    client.table("notas_arancel").delete().neq("id", 0).execute()

    # Insertar en batches
    batch_size = 50
    for i in range(0, len(notas), batch_size):
        batch = notas[i: i + batch_size]
        client.table("notas_arancel").insert(batch).execute()
        print(f"  Cargadas {min(i + batch_size, len(notas))}/{len(notas)}")

    print(f"✓ {len(notas)} notas cargadas a Supabase")


if __name__ == "__main__":
    print("Cargando PDF del Decreto 1881...")
    text = load_pdf()

    print("Parseando notas...")
    notas = parse_notas(text)

    # Stats
    tipos = {}
    for n in notas:
        tipos[n["tipo"]] = tipos.get(n["tipo"], 0) + 1
    print(f"Notas encontradas: {len(notas)}")
    for t, c in sorted(tipos.items()):
        print(f"  {t}: {c}")

    if "--upload" in sys.argv:
        cargar_notas_a_supabase(notas)
    else:
        print("\nUsa --upload para cargar a Supabase")
        for n in notas[:3]:
            print(f"\n[{n['tipo']}] {n['referencia']}:")
            print(f"  {n['contenido'][:150]}...")
