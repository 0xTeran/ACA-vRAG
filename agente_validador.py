"""Agente Validador de Clasificación Arancelaria.

Revisa y valida las clasificaciones propuestas por el Agente Clasificador,
verificando coherencia con las reglas generales, notas de sección/capítulo
y la nomenclatura del Decreto 1881 de 2021.
"""
from __future__ import annotations

from openai import OpenAI

from config import MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from database import get_agent_prompt

_DEFAULT_PROMPT = "Eres un validador de clasificación arancelaria de la DIAN Colombia. Responde en español."


def _get_prompt() -> str:
    try:
        p = get_agent_prompt("validador")
        return p if p else _DEFAULT_PROMPT
    except Exception:
        return _DEFAULT_PROMPT


def validar_clasificacion(
    ficha_tecnica: str,
    clasificacion_propuesta: str,
    contexto_arancel: str,
) -> dict:
    """Valida una clasificación arancelaria propuesta.

    Args:
        ficha_tecnica: Descripción/ficha técnica del producto.
        clasificacion_propuesta: Clasificación emitida por el agente clasificador.
        contexto_arancel: Texto relevante del arancel.

    Returns:
        Diccionario con el resultado de la validación.
    """
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    user_message = f"""\
## Contexto del Arancel de Aduanas (Decreto 1881 de 2021):

{contexto_arancel[:80000]}

---

## Ficha Técnica del Producto:

{ficha_tecnica}

---

## Clasificación Propuesta por el Agente Clasificador:

{clasificacion_propuesta}

---

Valida la clasificación anterior. Revisa exhaustivamente:

1. Que las reglas generales se hayan aplicado correctamente
2. Que las notas de sección y capítulo no excluyan el producto
3. Que el código arancelario sea estructuralmente válido (10 dígitos)
4. Que el gravamen sea el correcto para esa subpartida
5. Que no exista una subpartida más específica o apropiada

Responde en formato estructurado:

### RESULTADO DE LA VALIDACIÓN

**VEREDICTO:** [APROBADO / RECHAZADO / REQUIERE REVISIÓN]

### VERIFICACIÓN DE REGLAS GENERALES
| Regla | ¿Aplicada correctamente? | Observación |
|-------|--------------------------|-------------|
| Regla 1 | Sí/No/N/A | ... |
| Regla 2 | Sí/No/N/A | ... |
| Regla 3 | Sí/No/N/A | ... |
| Regla 4 | Sí/No/N/A | ... |
| Regla 5 | Sí/No/N/A | ... |
| Regla 6 | Sí/No/N/A | ... |

### VERIFICACIÓN DE NOTAS
- **Notas de sección:** [¿Coherentes? ¿Alguna exclusión?]
- **Notas de capítulo:** [¿Coherentes? ¿Alguna exclusión?]
- **Notas complementarias:** [¿Se consideraron?]

### VERIFICACIÓN DEL CÓDIGO
- **Estructura válida:** [Sí/No]
- **Jerarquía coherente:** [Sí/No]
- **Gravamen correcto:** [Sí/No/No verificable]

### ERRORES ENCONTRADOS
[Lista de errores, o "Ninguno"]

### CLASIFICACIÓN ALTERNATIVA (si aplica)
**Subpartida sugerida:** [código]
**Razón del cambio:** [explicación]

### OBSERVACIONES GENERALES
[Comentarios sobre la calidad y completitud del análisis]

### NIVEL DE CONFIANZA EN LA VALIDACIÓN: [Alto/Medio/Bajo]
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
        "validacion_raw": result_text,
        "modelo": MODEL,
        "tokens_input": usage.prompt_tokens if usage else 0,
        "tokens_output": usage.completion_tokens if usage else 0,
    }
