"""Agente Validador de Clasificación Arancelaria.

Revisa y valida las clasificaciones propuestas por el Agente Clasificador,
verificando coherencia con las reglas generales, notas de sección/capítulo
y la nomenclatura del Decreto 1881 de 2021.
"""
from __future__ import annotations

from openai import OpenAI

from config import MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

SYSTEM_PROMPT = """\
Fecha actual: 2026-03-14. Estamos en el año 2026.

Eres un auditor experto en clasificación arancelaria de la DIAN (Colombia). \
Tu trabajo es VALIDAR clasificaciones arancelarias propuestas por otro agente, \
verificando que sean correctas según el Decreto 1881 de 2021.

## REGLAS CRÍTICAS:
- Las resoluciones de la DIAN de 2025 y 2026 son VÁLIDAS. NO cuestiones fechas.
- Tu trabajo es verificar que la subpartida, el gravamen y las reglas aplicadas sean correctos.
- No necesitas verificar la investigación, solo la clasificación final.

## Tu proceso de validación DEBE verificar:

### 1. Coherencia con las Reglas Generales de Interpretación
- ¿Se aplicó la Regla 1 correctamente? (textos de partidas vs títulos indicativos)
- ¿Se consideró la Regla 2 si el producto está incompleto o mezclado?
- ¿Se aplicó la Regla 3 correctamente si había múltiples partidas posibles?
  - 3a: ¿Se eligió la partida más específica?
  - 3b: ¿Se determinó correctamente el carácter esencial?
  - 3c: ¿Se usó el orden numérico como último recurso?
- ¿Se verificó la Regla 4 (analogía) si no había clasificación directa?
- ¿Se aplicó la Regla 5 (envases/estuches) si corresponde?
- ¿Se aplicó la Regla 6 correctamente para la clasificación en subpartidas?

### 2. Notas de Sección y Capítulo
- ¿Las notas de la sección propuesta NO excluyen el producto?
- ¿Las notas del capítulo propuesto son coherentes con el producto?
- ¿Se consideraron las notas complementarias nacionales y Nandina?

### 3. Estructura del Código
- ¿El código tiene 10 dígitos?
- ¿El capítulo corresponde a la sección indicada?
- ¿La partida existe dentro del capítulo?
- ¿La subpartida existe y es coherente jerárquicamente?

### 4. Gravamen
- ¿El gravamen (%) corresponde al indicado en el arancel para esa subpartida?

## Para cada validación DEBES emitir:
1. **VEREDICTO**: APROBADO / RECHAZADO / REQUIERE REVISIÓN
2. **Errores encontrados** (si los hay)
3. **Clasificación alternativa sugerida** (si se rechaza)
4. **Observaciones** sobre la calidad del análisis
"""


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
            {"role": "system", "content": SYSTEM_PROMPT},
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
