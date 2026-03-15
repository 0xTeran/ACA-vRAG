#!/usr/bin/env python3
"""Genera embeddings directamente del PDF del Decreto 1881 de 2021.

Divide el decreto en chunks inteligentes (por partida/notas) y genera
embeddings con OpenAI text-embedding-3-small.

Costo estimado: ~$0.03-0.05 (todo el decreto).
"""
from __future__ import annotations

import os
import re
import sys
import time

from openai import OpenAI

from config import DECRETO_PDF_PATH, OPENROUTER_API_KEY
from database import get_client
from pdf_loader import load_pdf, extract_chapters

EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_MAX_CHARS = 2000  # Tamaño máximo por chunk


def get_embedding_client() -> OpenAI:
    """Cliente para embeddings. Prefiere OpenAI directo si hay key."""
    direct_key = os.environ.get("OPENAI_API_KEY", "")
    if direct_key:
        print("  Usando OpenAI directo")
        return OpenAI(api_key=direct_key)
    print("  Usando OpenRouter")
    return OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")


def chunk_chapter(chapter_name: str, chapter_text: str) -> list[dict]:
    """Divide un capítulo en chunks inteligentes.

    Estrategia:
    1. Las notas del capítulo = 1 chunk (o varios si son largas)
    2. Cada partida (XX.XX) con sus subpartidas = 1 chunk
    3. Si una partida es muy larga, se divide en sub-chunks
    """
    chunks = []
    lines = chapter_text.split("\n")

    # Extraer número de capítulo
    cap_match = re.search(r"\d+", chapter_name)
    cap_num = cap_match.group(0).zfill(2) if cap_match else ""

    # Detectar sección actual (se hereda del contexto)
    seccion = ""

    # Encontrar dónde empiezan las partidas
    first_partida_idx = len(lines)
    for i, line in enumerate(lines):
        if re.match(r"^\d{2}\.\d{2}\b", line.strip()):
            first_partida_idx = i
            break

    # Chunk 1: Notas del capítulo (todo antes de la primera partida)
    notas_text = "\n".join(lines[:first_partida_idx]).strip()
    if notas_text and len(notas_text) > 50:
        # Dividir notas largas en sub-chunks
        for sub_chunk in _split_text(notas_text, CHUNK_MAX_CHARS):
            chunks.append({
                "seccion": seccion,
                "capitulo": cap_num,
                "contenido": sub_chunk,
                "tipo": "notas_capitulo",
                "metadata": {"capitulo_nombre": chapter_name},
            })

    # Chunks de partidas: agrupar por partida XX.XX
    partida_starts = []
    for i in range(first_partida_idx, len(lines)):
        if re.match(r"^\d{2}\.\d{2}\b", lines[i].strip()):
            partida_starts.append(i)

    for idx, start in enumerate(partida_starts):
        end = partida_starts[idx + 1] if idx + 1 < len(partida_starts) else len(lines)
        partida_text = "\n".join(lines[start:end]).strip()
        partida_code = lines[start].strip().split()[0] if lines[start].strip() else ""

        # Extraer códigos de subpartidas contenidas
        subpartidas = re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", partida_text)

        if len(partida_text) <= CHUNK_MAX_CHARS:
            chunks.append({
                "seccion": seccion,
                "capitulo": cap_num,
                "contenido": partida_text,
                "tipo": "partida",
                "metadata": {
                    "partida": partida_code,
                    "subpartidas": subpartidas,
                },
            })
        else:
            # Partida muy grande: dividir pero mantener contexto
            header = "\n".join(lines[start:start + 3])  # Primeras líneas como contexto
            for sub_chunk in _split_text(partida_text, CHUNK_MAX_CHARS):
                chunks.append({
                    "seccion": seccion,
                    "capitulo": cap_num,
                    "contenido": sub_chunk,
                    "tipo": "partida",
                    "metadata": {
                        "partida": partida_code,
                        "subpartidas": re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", sub_chunk),
                    },
                })

    return chunks


def _split_text(text: str, max_chars: int) -> list[str]:
    """Divide texto largo en chunks respetando saltos de línea."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1

    if current:
        chunks.append("\n".join(current))

    return chunks


def chunk_reglas_generales(text: str) -> list[dict]:
    """Chunks para las reglas generales de interpretación."""
    chunks = []
    for sub in _split_text(text[:5000], CHUNK_MAX_CHARS):
        chunks.append({
            "seccion": "",
            "capitulo": "00",
            "contenido": sub,
            "tipo": "reglas_generales",
            "metadata": {},
        })
    return chunks


def generate_all_chunks() -> list[dict]:
    """Genera todos los chunks del decreto."""
    print("Cargando PDF...")
    text = load_pdf()
    print(f"  PDF: {len(text):,} chars")

    print("Extrayendo capítulos...")
    chapters = extract_chapters(text)
    print(f"  Capítulos: {len(chapters)}")

    all_chunks = []

    for chapter_name, chapter_text in chapters.items():
        if chapter_name == "REGLAS_GENERALES":
            chunks = chunk_reglas_generales(chapter_text)
        else:
            chunks = chunk_chapter(chapter_name, chapter_text)
        all_chunks.extend(chunks)

    print(f"  Total chunks: {len(all_chunks)}")
    return all_chunks


def upload_chunks_and_embed():
    """Sube chunks a Supabase y genera embeddings."""
    supabase = get_client()
    client = get_embedding_client()

    # Generar chunks
    all_chunks = generate_all_chunks()

    # Limpiar tabla
    print("\nLimpiando tabla decreto_chunks...")
    supabase.table("decreto_chunks").delete().neq("id", 0).execute()

    # Subir chunks en batches con embeddings
    batch_size = 50
    total = len(all_chunks)
    processed = 0

    for i in range(0, total, batch_size):
        batch = all_chunks[i:i + batch_size]

        # Generar embeddings para el batch
        texts = [c["contenido"] for c in batch]
        try:
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            embeddings = [item.embedding for item in response.data]
        except Exception as e:
            print(f"  Error generando embeddings batch {i}: {e}")
            time.sleep(5)
            # Reintentar
            try:
                response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
                embeddings = [item.embedding for item in response.data]
            except Exception as e2:
                print(f"  Error persistente, saltando batch: {e2}")
                continue

        # Insertar en Supabase
        rows = []
        for j, chunk in enumerate(batch):
            rows.append({
                "seccion": chunk["seccion"],
                "capitulo": chunk["capitulo"],
                "contenido": chunk["contenido"],
                "tipo": chunk["tipo"],
                "metadata": chunk["metadata"],
                "embedding": embeddings[j],
            })

        try:
            supabase.table("decreto_chunks").insert(rows).execute()
        except Exception as e:
            print(f"  Error insertando batch {i}: {e}")
            # Insertar uno por uno como fallback
            for row in rows:
                try:
                    supabase.table("decreto_chunks").insert(row).execute()
                except Exception:
                    pass

        processed += len(batch)
        print(f"  {processed}/{total} chunks procesados")
        time.sleep(0.3)

    # Stats finales
    result = supabase.table("decreto_chunks").select("id", count="exact").execute()
    print(f"\n✓ {result.count} chunks en Supabase con embeddings")

    # Stats por tipo
    for tipo in ["reglas_generales", "notas_capitulo", "partida"]:
        r = supabase.table("decreto_chunks").select("id", count="exact").eq("tipo", tipo).execute()
        print(f"  {tipo}: {r.count}")


if __name__ == "__main__":
    print("=" * 50)
    print("  RAG: Embeddings del Decreto 1881 de 2021")
    print("=" * 50)
    upload_chunks_and_embed()
