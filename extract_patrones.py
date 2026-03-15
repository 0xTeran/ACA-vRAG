#!/usr/bin/env python3
"""Extrae patrones interpretativos de las resoluciones DIAN.

Analiza cada resolución y extrae:
- El tipo de desafío interpretativo que resolvió
- El patrón de razonamiento que usó la DIAN
- Un ejemplo concreto del caso

Estos patrones se buscan por similitud semántica según el DESAFÍO
de clasificación (no el producto), para entrenar a los agentes.
"""
from __future__ import annotations

import os
import json
import sys
import time

from openai import OpenAI

from database import get_client

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_clients():
    api_key = os.environ.get("OPENAI_API_KEY") or OPENROUTER_API_KEY
    base_url = None if os.environ.get("OPENAI_API_KEY") else OPENROUTER_BASE_URL
    embed = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    llm = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    return embed, llm


def extract_patterns_from_resolution(contenido: str, numero: str, llm: OpenAI) -> list[dict]:
    """Usa IA para extraer patrones interpretativos de una resolución."""
    try:
        response = llm.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": (
                    "Analiza esta resolución de clasificación arancelaria de la DIAN Colombia. "
                    "Extrae los PATRONES INTERPRETATIVOS — cómo razona la DIAN, no qué producto clasifica.\n\n"
                    "Responde SOLO en JSON array. Cada elemento:\n"
                    '{"tipo_desafio": "uno de: composicion_vs_forma | capitulos_competidores | '
                    'material_ambiguo | producto_compuesto | proceso_manufactura | '
                    'funcion_vs_material | exclusion_por_nota | especificidad_subpartida | '
                    'aplicacion_RGI | precedente_vinculante | otro",\n'
                    '"patron": "regla interpretativa que usó la DIAN (máx 150 chars)",\n'
                    '"ejemplo": "cómo la aplicó en este caso concreto (máx 200 chars)"}\n\n'
                    "Máximo 3 patrones por resolución. Si no hay patrón claro, responde [].\n\n"
                    f"RESOLUCIÓN {numero}:\n{contenido[:4000]}"
                ),
            }],
        )

        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        patterns = json.loads(raw)
        return patterns if isinstance(patterns, list) else []
    except Exception as e:
        print(f"    Error extrayendo patrones: {e}")
        return []


def process_resolutions(limit: int = 0):
    """Procesa resoluciones y extrae patrones interpretativos."""
    supabase = get_client()
    embed_client, llm_client = get_clients()

    # Obtener resoluciones no procesadas
    existing = supabase.table("patrones_interpretativos").select("resolucion_numero").execute()
    processed_nums = {r["resolucion_numero"] for r in (existing.data or [])}

    query = supabase.table("resoluciones_dian").select(
        "id, numero, contenido"
    ).order("anio", desc=True).order("numero")

    if limit > 0:
        query = query.limit(limit)

    result = query.execute()
    resoluciones = [r for r in (result.data or []) if r["numero"] not in processed_nums]

    print(f"Resoluciones pendientes: {len(resoluciones)}")
    if not resoluciones:
        return

    total_patterns = 0

    for i, res in enumerate(resoluciones):
        print(f"  [{i+1}/{len(resoluciones)}] Res. {res['numero']}...", end=" ")

        # Extraer patrones con IA
        patterns = extract_patterns_from_resolution(
            res["contenido"], res["numero"], llm_client
        )

        if not patterns:
            print("sin patrones")
            continue

        # Generar embeddings y guardar
        for p in patterns:
            embed_text = f"{p.get('tipo_desafio', '')}: {p.get('patron', '')} — {p.get('ejemplo', '')}"
            try:
                emb = embed_client.embeddings.create(
                    model="text-embedding-3-small", input=embed_text[:4000]
                )
                supabase.table("patrones_interpretativos").insert({
                    "tipo_desafio": p.get("tipo_desafio", "otro"),
                    "patron": p.get("patron", "")[:500],
                    "ejemplo": p.get("ejemplo", "")[:500],
                    "resolucion_numero": res["numero"],
                    "resolucion_id": res["id"],
                    "embedding": emb.data[0].embedding,
                }).execute()
                total_patterns += 1
            except Exception as e:
                print(f"error: {e}", end=" ")

        print(f"✓ {len(patterns)} patrones")
        time.sleep(0.3)

    # Stats
    stats = supabase.table("patrones_interpretativos").select("tipo_desafio").execute()
    from collections import Counter
    tipos = Counter(r["tipo_desafio"] for r in (stats.data or []))
    print(f"\nTotal patrones: {sum(tipos.values())}")
    for t, c in tipos.most_common():
        print(f"  {t}: {c}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print("=" * 50)
    print("  Extracción de Patrones Interpretativos DIAN")
    print("=" * 50)
    process_resolutions(limit)
