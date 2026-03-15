"""Agente Clasificador Arancelario.

Analiza fichas técnicas de productos y determina la subpartida arancelaria
correcta según el Decreto 1881 de 2021 (Arancel de Aduanas de Colombia).
"""
from __future__ import annotations

from openai import OpenAI

from config import MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from database import get_agent_prompt

_DEFAULT_PROMPT = "Eres un clasificador arancelario de la DIAN Colombia. Responde en español."


def _get_prompt() -> str:
    try:
        p = get_agent_prompt("clasificador")
        return p if p else _DEFAULT_PROMPT
    except Exception:
        return _DEFAULT_PROMPT


def clasificar_producto(
    ficha_tecnica: str,
    contexto_arancel: str,
    investigacion: str = "",
) -> dict:
    """Clasifica un producto según su ficha técnica.

    Args:
        ficha_tecnica: Descripción/ficha técnica del producto.
        contexto_arancel: Texto relevante del arancel (capítulos, notas).
        investigacion: Resultado de la investigación previa de resoluciones DIAN.

    Returns:
        Diccionario con la clasificación propuesta.
    """
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    investigacion_section = ""
    if investigacion:
        investigacion_section = f"""
## INVESTIGACIÓN PREVIA — Resoluciones y precedentes DIAN encontrados:
⚠️ OBLIGATORIO: Debes leer esta sección COMPLETA antes de clasificar.
- Si hay resoluciones de la DIAN que clasifican este producto o uno similar, DEBES \
usar esa subpartida como base de tu clasificación.
- Cita explícitamente las resoluciones relevantes en tu justificación.
- Si tu análisis difiere de una resolución DIAN, explica por qué.

{investigacion}

---
"""

    user_message = f"""\
## Contexto del Arancel de Aduanas (Decreto 1881 de 2021):

{contexto_arancel[:80000]}

---
{investigacion_section}
## Ficha Técnica del Producto a Clasificar:

{ficha_tecnica}

---

Analiza la ficha técnica anterior y clasifícala según el arancel colombiano.

IMPORTANTE: Si la investigación previa encontró resoluciones de la DIAN que clasifican \
este producto o uno similar, DEBES usar esa subpartida. Las resoluciones DIAN son \
vinculantes y tienen prioridad sobre tu análisis propio.

Responde en formato estructurado:

### CLASIFICACIÓN ARANCELARIA

**Sección:** [número romano]
**Capítulo:** [número]
**Partida:** [4 dígitos con punto]
**Subpartida arancelaria:** [10 dígitos con puntos]
**Gravamen ad valorem:** [porcentaje]%

### PRECEDENTES DIAN CONSIDERADOS
[Lista las resoluciones/conceptos de la DIAN que encontró el investigador y que usaste]

### JUSTIFICACIÓN

**Reglas aplicadas:** [lista de reglas generales utilizadas]

**Análisis:**
[Explicación paso a paso de por qué esta es la clasificación correcta]

**Notas de sección/capítulo aplicables:**
[Notas relevantes que sustentan la clasificación]

**Subpartidas descartadas y por qué:**
[Alternativas consideradas y razón de descarte]

### NIVEL DE CONFIANZA: [Alto/Medio/Bajo]
**Razón:** [Por qué este nivel de confianza]
"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _get_prompt()},
            {"role": "user", "content": user_message},
        ],
    )

    result_text = response.choices[0].message.content
    usage = response.usage

    return {
        "clasificacion_raw": result_text,
        "modelo": MODEL,
        "tokens_input": usage.prompt_tokens if usage else 0,
        "tokens_output": usage.completion_tokens if usage else 0,
    }
