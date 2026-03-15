#!/usr/bin/env python3
"""Descarga e indexa resoluciones de clasificación arancelaria de la DIAN.

Fase 1: Resoluciones 2025-2026 (tienen texto digital extraíble).
"""
from __future__ import annotations

import os
import re
import sys
import time

import fitz  # PyMuPDF
import requests
from openai import OpenAI

from database import get_client

BASE = "https://www.dian.gov.co"
SP_API = f"{BASE}/normatividad/_api/web/GetFolderByServerRelativeUrl('/normatividad/ClasificacionArancelaria')/Files"
HEADERS_API = {"Accept": "application/json;odata=verbose", "User-Agent": "Mozilla/5.0"}
HEADERS_DL = {"User-Agent": "Mozilla/5.0"}

EMBEDDING_MODEL = "text-embedding-3-small"


def get_embed_client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    base_url = None if os.environ.get("OPENAI_API_KEY") else "https://openrouter.ai/api/v1"
    return OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)


def list_files(year: str, batch_size: int = 100) -> list[dict]:
    """Lista todos los archivos de un año desde SharePoint."""
    all_files = []
    skip = 0

    while True:
        url = (
            f"{SP_API}?$top={batch_size}&$skip={skip}"
            f"&$select=Name,ServerRelativeUrl,Length,TimeCreated"
            f"&$filter=substringof('{year}',Name)"
            f"&$orderby=Name"
        )
        resp = requests.get(url, headers=HEADERS_API, timeout=15)
        if resp.status_code != 200:
            break
        files = resp.json().get("d", {}).get("results", [])
        if not files:
            break
        all_files.extend(files)
        skip += batch_size
        if len(files) < batch_size:
            break
        time.sleep(0.3)

    return all_files


def download_and_extract(file_info: dict) -> dict | None:
    """Descarga un PDF y extrae texto + metadata."""
    url = BASE + file_info["ServerRelativeUrl"]
    name = file_info["Name"]

    try:
        resp = requests.get(url, headers=HEADERS_DL, timeout=30)
        if resp.status_code != 200:
            return None

        doc = fitz.open(stream=resp.content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        if len(text.strip()) < 100:
            return None  # Escaneado, sin texto

        # Extraer metadata del nombre: "Resolución 600293 de 18-06-2025.pdf"
        match = re.match(r"Resolución\s+(\d+)\s+de\s+(\d{2}-\d{2}-\d{4})", name)
        numero = match.group(1) if match else ""
        fecha = match.group(2) if match else ""
        anio_match = re.search(r"(\d{4})", fecha or name)
        anio = int(anio_match.group(1)) if anio_match else 0

        # Extraer subpartidas mencionadas
        subpartidas = list(set(re.findall(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", text)))

        # Extraer producto (buscar después de "producto" o "mercancía")
        producto = ""
        prod_match = re.search(
            r"(?:producto|mercancía|descripción)[:\s]+([^\n]{10,200})",
            text, re.IGNORECASE,
        )
        if prod_match:
            producto = prod_match.group(1).strip()

        return {
            "numero": numero,
            "fecha": fecha,
            "anio": anio,
            "nombre_archivo": name,
            "url": url,
            "contenido": text[:8000],  # Limitar para embedding
            "subpartidas": subpartidas,
            "producto": producto[:500],
        }

    except Exception as e:
        print(f"    Error {name}: {e}")
        return None


def generate_resumen(contenido: str, client: OpenAI) -> str:
    """Genera resumen corto de la resolución para búsqueda."""
    try:
        resp = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    "Resume esta resolución DIAN en 1-2 líneas. "
                    "Incluye: producto, subpartida asignada, criterio principal. "
                    "Solo el resumen, nada más.\n\n"
                    + contenido[:3000]
                ),
            }],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return ""


def process_year(year: str):
    """Procesa todas las resoluciones de un año."""
    supabase = get_client()
    embed_client = get_embed_client()

    print(f"\n{'='*50}")
    print(f"  Procesando resoluciones {year}")
    print(f"{'='*50}")

    # Listar archivos
    print(f"  Listando archivos...")
    files = list_files(year)
    print(f"  Archivos encontrados: {len(files)}")

    # Verificar cuáles ya están en BD
    existing = supabase.table("resoluciones_dian").select("nombre_archivo").eq("anio", int(year)).execute()
    existing_names = {r["nombre_archivo"] for r in (existing.data or [])}
    new_files = [f for f in files if f["Name"] not in existing_names]
    print(f"  Ya procesados: {len(existing_names)} | Nuevos: {len(new_files)}")

    if not new_files:
        print("  Nada nuevo que procesar.")
        return

    processed = 0
    errors = 0
    skipped = 0

    for i, f in enumerate(new_files):
        print(f"  [{i+1}/{len(new_files)}] {f['Name'][:60]}...", end=" ")

        # Descargar y extraer
        data = download_and_extract(f)
        if not data:
            print("SKIP (escaneado/error)")
            skipped += 1
            continue

        # Generar resumen
        data["resumen"] = generate_resumen(data["contenido"], embed_client)

        # Generar embedding
        embed_text = f"Resolución DIAN {data['numero']} — {data['resumen']} — Producto: {data['producto']} — Subpartidas: {', '.join(data['subpartidas'])}"
        try:
            emb_resp = embed_client.embeddings.create(
                model=EMBEDDING_MODEL, input=embed_text[:4000],
            )
            data["embedding"] = emb_resp.data[0].embedding
        except Exception as e:
            print(f"EMB ERROR: {e}")
            errors += 1
            continue

        # Guardar en Supabase
        try:
            supabase.table("resoluciones_dian").insert(data).execute()
            processed += 1
            print(f"✓ {', '.join(data['subpartidas'][:3]) or 'sin subpartida'}")
        except Exception as e:
            print(f"DB ERROR: {e}")
            errors += 1

        time.sleep(0.5)  # Rate limiting

    print(f"\n  Resumen {year}:")
    print(f"    Procesados: {processed}")
    print(f"    Saltados (escaneados): {skipped}")
    print(f"    Errores: {errors}")


if __name__ == "__main__":
    years = sys.argv[1:] if len(sys.argv) > 1 else ["2026", "2025"]

    for year in years:
        process_year(year)

    # Stats finales
    supabase = get_client()
    total = supabase.table("resoluciones_dian").select("id", count="exact").execute()
    print(f"\n{'='*50}")
    print(f"  Total resoluciones en BD: {total.count}")
    print(f"{'='*50}")
