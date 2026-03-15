"""Agente Investigador de Resoluciones y Fuentes DIAN.

Busca en la página oficial de la DIAN y en internet (via Perplexity)
resoluciones, conceptos y doctrina de clasificación arancelaria
relacionadas con un producto, ANTES de clasificarlo.
"""
from __future__ import annotations

import re

import requests as http_requests
from openai import OpenAI

from config import (
    DIAN_RESOLUCIONES_URL,
    MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    PERPLEXITY_MODEL,
)
from database import get_agent_prompt

# Fallback si no hay prompt en BD
_DEFAULT_PROMPT = "Eres un investigador de resoluciones DIAN Colombia. Responde en español."


def _get_prompt() -> str:
    try:
        p = get_agent_prompt("investigador")
        return p if p else _DEFAULT_PROMPT
    except Exception:
        return _DEFAULT_PROMPT


def _scrape_dian_resoluciones() -> str:
    """Descarga y extrae texto de la página de resoluciones DIAN."""
    try:
        resp = http_requests.get(
            DIAN_RESOLUCIONES_URL,
            headers={"User-Agent": "ACA-Bot/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        html = resp.text
        # Limpiar HTML
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Preservar enlaces
        html = re.sub(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.DOTALL)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"\s+", " ", html).strip()
        return html[:8000]
    except Exception as e:
        print(f"Error scraping DIAN: {e}")
        return f"[No se pudo acceder a {DIAN_RESOLUCIONES_URL}: {e}]"


def _search_perplexity(query: str) -> str:
    """Usa Perplexity (via OpenRouter) para buscar información actualizada en internet."""
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

    try:
        response = client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            max_tokens=3000,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Fecha actual: marzo 2026. Estamos en 2026. "
                        "Eres un asistente de investigación especializado en normativa "
                        "aduanera colombiana. Busca información actualizada sobre "
                        "resoluciones de clasificación arancelaria de la DIAN Colombia. "
                        "Las resoluciones de 2025 y 2026 son válidas y recientes. "
                        "Incluye URLs de las fuentes cuando sea posible. "
                        "Responde en español."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error Perplexity: {e}")
        return f"[Error en búsqueda Perplexity: {e}]"


def investigar_producto(ficha_tecnica: str, model: str = "") -> dict:
    """Investiga resoluciones y fuentes DIAN para un producto ANTES de clasificarlo.

    Args:
        ficha_tecnica: Descripción/ficha técnica del producto a investigar.

    Returns:
        Diccionario con la investigación, fuentes encontradas y contexto.
    """
    producto_resumen = ficha_tecnica[:500]

    # ── Paso 1: Scraping de la página oficial de resoluciones DIAN ──
    print("  [Investigador] Consultando página de resoluciones DIAN...")
    dian_content = _scrape_dian_resoluciones()

    # ── Paso 2: Búsquedas con Perplexity (internet en tiempo real) ──
    print("  [Investigador] Buscando con Perplexity (internet)...")

    perplexity_query_1 = (
        f"Busca resoluciones de clasificación arancelaria de la DIAN Colombia "
        f"para el siguiente tipo de producto: {producto_resumen[:300]}. "
        f"Incluye el número de resolución, la subpartida arancelaria asignada, "
        f"y la fecha. Busca en dian.gov.co y otras fuentes oficiales colombianas."
    )
    perplexity_result_1 = _search_perplexity(perplexity_query_1)

    perplexity_query_2 = (
        f"¿Cuál es la clasificación arancelaria correcta en Colombia (arancel DIAN, "
        f"Decreto 1881 de 2021) para este producto: {producto_resumen[:200]}? "
        f"Busca conceptos de la DIAN, sentencias del Consejo de Estado y "
        f"resoluciones de clasificación arancelaria relacionadas. "
        f"Incluye las subpartidas arancelarias a 10 dígitos si las encuentras."
    )
    perplexity_result_2 = _search_perplexity(perplexity_query_2)

    # ── Paso 3: Síntesis con Claude Sonnet ──
    print("  [Investigador] Sintetizando hallazgos...")
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

    # Buscar lecciones para el investigador
    from database import buscar_lecciones as _buscar
    lecciones_inv = _buscar(ficha_tecnica, agente="investigador", limit=5)
    lecciones_ctx = ""
    if lecciones_inv:
        lines = ["## Lecciones aprendidas para investigación:\n"]
        for l in lecciones_inv:
            lines.append(f"- {l['regla']}")
        lecciones_ctx = "\n".join(lines) + "\n\n---\n"

    user_message = f"""\
{lecciones_ctx}## Ficha técnica del producto a investigar:
{ficha_tecnica}

## Información de la página oficial de Resoluciones de Clasificación Arancelaria DIAN:
URL: {DIAN_RESOLUCIONES_URL}
{dian_content}

## Búsqueda en internet #1 - Resoluciones específicas:
{perplexity_result_1}

## Búsqueda en internet #2 - Clasificación y conceptos:
{perplexity_result_2}

---

Con base en toda la información recopilada:

1. **Resoluciones DIAN encontradas** que se relacionen con este tipo de producto
2. **Conceptos y doctrina DIAN** aplicables
3. **Precedentes de clasificación** para productos iguales o similares
4. **Subpartidas arancelarias identificadas** en los precedentes
5. **GUÍA DE CLASIFICACIÓN**: Lista ordenada de las subpartidas más probables \
según los precedentes encontrados, con justificación de cada una

Esta investigación será usada por el agente clasificador como insumo para tomar \
la mejor decisión de clasificación arancelaria.
"""

    use_model = model or MODEL
    response = client.chat.completions.create(
        model=use_model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _get_prompt()},
            {"role": "user", "content": user_message},
        ],
    )

    result_text = response.choices[0].message.content
    usage = response.usage

    # Extraer fuentes/URLs mencionadas en los resultados de Perplexity
    all_text = perplexity_result_1 + "\n" + perplexity_result_2
    urls_found = re.findall(r'https?://[^\s<>"\')\]]+', all_text)
    fuentes = []
    seen = set()
    for url in urls_found:
        url = url.rstrip(".,;:")
        if url not in seen:
            seen.add(url)
            fuentes.append({"title": url.split("/")[-1] or url, "url": url, "snippet": ""})

    return {
        "investigacion_raw": result_text,
        "fuentes": fuentes[:20],
        "modelo": use_model,
        "tokens_input": usage.prompt_tokens if usage else 0,
        "tokens_output": usage.completion_tokens if usage else 0,
    }
