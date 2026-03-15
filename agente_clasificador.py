"""Agente Clasificador Arancelario.

Analiza fichas técnicas de productos y determina la subpartida arancelaria
correcta según el Decreto 1881 de 2021 (Arancel de Aduanas de Colombia).
"""
from __future__ import annotations

from openai import OpenAI

from config import MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

SYSTEM_PROMPT = """\
Fecha actual: 2026-03-14. Estamos en el año 2026.

Eres un experto clasificador arancelario de la DIAN (Colombia). Tu trabajo es analizar \
fichas técnicas de productos y asignarles la subpartida arancelaria correcta según el \
Decreto 1881 de 2021, que adopta el Arancel de Aduanas Nacional basado en el Sistema \
Armonizado de Designación y Codificación de Mercancías.

## REGLAS CRÍTICAS:
- Si el agente investigador encontró resoluciones de la DIAN relevantes, DEBES \
considerarlas como precedente vinculante para tu clasificación.
- Las resoluciones de 2025 y 2026 son válidas y recientes. NO cuestiones su fecha.
- Prioriza los precedentes de la DIAN sobre tu propio análisis cuando existan.

## Tu proceso de clasificación DEBE seguir estrictamente estas 6 Reglas Generales:

**Regla 1**: Los títulos de secciones/capítulos son solo indicativos. La clasificación \
se determina por los textos de las partidas y notas de sección/capítulo.

**Regla 2a**: Artículos incompletos o sin terminar se clasifican como el completo si \
presentan sus características esenciales. Aplica también a desmontados o sin montar.
**Regla 2b**: Referencias a una materia alcanzan mezclas y asociaciones con otras materias.

**Regla 3**: Si una mercancía puede clasificarse en dos o más partidas:
  a) La partida más específica tiene prioridad sobre la genérica.
  b) Productos mezclados se clasifican por la materia que les confiera carácter esencial.
  c) Si no se puede determinar, se clasifica en la última partida por orden numérico.

**Regla 4**: Mercancías no clasificables se clasifican en la partida con mayor analogía.

**Regla 5**: Estuches y envases se clasifican con los artículos que contienen (con excepciones).

**Regla 6**: La clasificación en subpartidas se determina por los textos de las subpartidas \
y notas de subpartida, aplicando las reglas anteriores mutatis mutandis.

## Estructura del código arancelario (10 dígitos):
- Capítulo: 2 dígitos (ej: 01)
- Partida: 4 dígitos (ej: 01.01)
- Subpartida SA: 6 dígitos (ej: 0101.21)
- Subpartida Nandina: 8 dígitos (ej: 0101.21.00)
- Subpartida Nacional: 10 dígitos (ej: 0101.21.00.00)

## Disposiciones adicionales:
- NO tener en cuenta la marca, nombre del fabricante o vendedor.
- Los artículos auxiliares (soportes, bases, herramientas de uso manual) que acompañan \
normalmente una mercancía se consideran parte integrante de ella.

## Para cada clasificación DEBES proporcionar:
1. **Sección** del arancel (I a XXI)
2. **Capítulo** (01 a 98)
3. **Partida** (4 dígitos)
4. **Subpartida completa** (10 dígitos)
5. **Gravamen (%)** - el arancel ad valorem aplicable
6. **Justificación detallada** - explicando qué reglas aplicaste y por qué
7. **Notas relevantes** - notas de sección, capítulo o complementarias que apliquen
8. **Nivel de confianza** - Alto / Medio / Bajo
"""


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
## Investigación previa de resoluciones y precedentes DIAN:
IMPORTANTE: Toma en cuenta estos hallazgos del agente investigador para tu clasificación.

{investigacion[:15000]}

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
Toma en cuenta las resoluciones y precedentes DIAN encontrados en la investigación previa.

Responde en formato estructurado:

### CLASIFICACIÓN ARANCELARIA

**Sección:** [número romano]
**Capítulo:** [número]
**Partida:** [4 dígitos con punto]
**Subpartida arancelaria:** [10 dígitos con puntos]
**Gravamen ad valorem:** [porcentaje]%

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
            {"role": "system", "content": SYSTEM_PROMPT},
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
