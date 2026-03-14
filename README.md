# ACA - Agente de Clasificación Arancelaria

Sistema de clasificación arancelaria basado en el Decreto 1881 de 2021 (DIAN Colombia).

## Arquitectura

El sistema usa dos agentes especializados:

1. **Agente Clasificador**: Analiza fichas técnicas de productos y determina la subpartida arancelaria correcta aplicando las 6 Reglas Generales de Interpretación.
2. **Agente Validador**: Verifica que la clasificación propuesta sea correcta revisando notas de sección, capítulo y subpartida.

## Uso

```bash
pip install -r requirements.txt
python main.py
```
