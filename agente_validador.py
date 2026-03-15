"""Agente Validador de Clasificación Arancelaria.

Revisa y valida las clasificaciones propuestas por el Agente Clasificador,
verificando que las subpartidas EXISTAN en el Decreto 1881 de 2021 y que
las reglas generales se hayan aplicado correctamente.
"""
from __future__ import annotations

import re

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


def _verificar_subpartida_en_arancel(subpartida: str, arancel_completo: str) -> dict:
    """Busca si una subpartida EXACTA existe en el texto completo del arancel.

    Retorna un dict con:
    - existe: bool
    - contexto: texto alrededor de la subpartida si existe
    - alternativas: subpartidas cercanas si no existe
    """
    # Limpiar formato
    sub_clean = subpartida.strip().replace(" ", "")

    # Buscar exacta
    if sub_clean in arancel_completo:
        pos = arancel_completo.find(sub_clean)
        start = max(0, pos - 200)
        end = min(len(arancel_completo), pos + 300)
        contexto = arancel_completo[start:end].strip()
        return {
            "existe": True,
            "subpartida": sub_clean,
            "contexto": contexto,
            "alternativas": [],
        }

    # No existe - buscar alternativas cercanas
    # Extraer los primeros 6-8 dígitos para buscar vecinas
    alternativas = []
    if len(sub_clean) >= 7:
        prefijo = sub_clean[:7]  # ej: 8424.89
        matches = re.findall(
            rf'{re.escape(prefijo)}[.\d]*\S*',
            arancel_completo,
        )
        alternativas = sorted(set(matches))[:10]

    # Si no encontró con 7, intentar con 4 (partida)
    if not alternativas and len(sub_clean) >= 5:
        prefijo = sub_clean[:5]  # ej: 8424.
        matches = re.findall(
            rf'{re.escape(prefijo)}\d{{2}}[.\d]*',
            arancel_completo,
        )
        alternativas = sorted(set(m for m in matches if len(m) >= 10))[:15]

    return {
        "existe": False,
        "subpartida": sub_clean,
        "contexto": "",
        "alternativas": alternativas,
    }


def validar_clasificacion(
    ficha_tecnica: str,
    clasificacion_propuesta: str,
    contexto_arancel: str,
    arancel_completo: str = "",
    model: str = "",
) -> dict:
    """Valida una clasificación arancelaria propuesta.

    Args:
        ficha_tecnica: Descripción/ficha técnica del producto.
        clasificacion_propuesta: Clasificación emitida por el agente clasificador.
        contexto_arancel: Texto relevante del arancel (capítulos).
        arancel_completo: Texto completo del decreto para verificación de códigos.
    """
    # Extraer subpartida propuesta
    sub_match = re.search(r'\d{4}\.\d{2}\.\d{2}\.\d{2}', clasificacion_propuesta)
    subpartida_propuesta = sub_match.group(0) if sub_match else ""

    # Verificar existencia en el arancel
    verificacion = {"existe": False, "subpartida": "", "contexto": "", "alternativas": []}
    if subpartida_propuesta and arancel_completo:
        verificacion = _verificar_subpartida_en_arancel(subpartida_propuesta, arancel_completo)

    # Construir sección de verificación de existencia
    if verificacion["existe"]:
        existencia_text = f"""
## VERIFICACIÓN DE EXISTENCIA DE LA SUBPARTIDA {subpartida_propuesta}:
✅ LA SUBPARTIDA EXISTE en el Decreto 1881 de 2021.
Contexto en el arancel: {verificacion['contexto']}
"""
    elif subpartida_propuesta:
        alts = ", ".join(verificacion["alternativas"][:10]) if verificacion["alternativas"] else "ninguna encontrada"
        existencia_text = f"""
## ⚠️ VERIFICACIÓN DE EXISTENCIA DE LA SUBPARTIDA {subpartida_propuesta}:
❌ LA SUBPARTIDA {subpartida_propuesta} NO EXISTE en el Decreto 1881 de 2021.
Subpartidas cercanas que SÍ existen: {alts}

IMPORTANTE: Si la subpartida no existe, la clasificación DEBE ser RECHAZADA y
debes sugerir la subpartida correcta de las alternativas que sí existen.
"""
    else:
        existencia_text = "\n## No se pudo extraer la subpartida propuesta para verificar.\n"

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    user_message = f"""\
{existencia_text}

## Contexto del Arancel de Aduanas (Decreto 1881 de 2021):

{contexto_arancel}

---

## Ficha Técnica del Producto:

{ficha_tecnica}

---

## Clasificación Propuesta por el Agente Clasificador:

{clasificacion_propuesta}

---

Valida la clasificación anterior. Revisa exhaustivamente:

1. ⚠️ PRIMERO: ¿La subpartida propuesta EXISTE en el arancel? (ver verificación arriba)
   Si NO existe → RECHAZAR inmediatamente y sugerir alternativa que SÍ exista.
2. Que las reglas generales se hayan aplicado correctamente
3. Que las notas de sección y capítulo no excluyan el producto
4. Que el código arancelario sea estructuralmente válido (10 dígitos)
5. Que el gravamen sea el correcto para esa subpartida
6. Que no exista una subpartida más específica o apropiada

Responde en formato estructurado:

### VERIFICACIÓN DE EXISTENCIA
**Subpartida {subpartida_propuesta}:** [EXISTE / NO EXISTE en el Decreto 1881]
**Acción:** [Si no existe, indicar la subpartida correcta]

### RESULTADO DE LA VALIDACIÓN
**VEREDICTO:** [APROBADO / RECHAZADO / REQUIERE REVISIÓN]

### VERIFICACIÓN DE REGLAS GENERALES
| Regla | ¿Correcta? | Observación |
|-------|-------------|-------------|
| Regla 1 | Sí/No/N/A | ... |
| Regla 2 | Sí/No/N/A | ... |
| Regla 3 | Sí/No/N/A | ... |
| Regla 4 | Sí/No/N/A | ... |
| Regla 5 | Sí/No/N/A | ... |
| Regla 6 | Sí/No/N/A | ... |

### VERIFICACIÓN DE NOTAS
- **Notas de sección:** [¿Coherentes?]
- **Notas de capítulo:** [¿Coherentes?]

### VERIFICACIÓN DEL CÓDIGO
- **Existe en el arancel:** [Sí/No]
- **Estructura válida (10 dígitos):** [Sí/No]
- **Gravamen correcto:** [Sí/No]

### ERRORES ENCONTRADOS
[Lista de errores, o "Ninguno"]

### CLASIFICACIÓN ALTERNATIVA (si aplica)
**Subpartida sugerida:** [código que SÍ existe]
**Razón del cambio:** [explicación]

### NIVEL DE CONFIANZA: [Alto/Medio/Bajo]
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

    return {
        "validacion_raw": result_text,
        "subpartida_existe": verificacion["existe"],
        "alternativas": verificacion.get("alternativas", []),
        "modelo": use_model,
        "tokens_input": usage.prompt_tokens if usage else 0,
        "tokens_output": usage.completion_tokens if usage else 0,
    }
