#!/usr/bin/env python3
"""ACA - Agente de Clasificación Arancelaria.

Sistema de clasificación arancelaria basado en el Decreto 1881 de 2021.
Orquesta dos agentes: Clasificador y Validador.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

from agente_clasificador import clasificar_producto
from agente_validador import validar_clasificacion
from pdf_loader import find_relevant_chapters, load_pdf


def print_header():
    print("=" * 70)
    print("  ACA - Agente de Clasificación Arancelaria")
    print("  Decreto 1881 de 2021 - DIAN Colombia")
    print("=" * 70)
    print()


def print_step(step: int, title: str):
    print(f"\n{'─' * 60}")
    print(f"  Paso {step}: {title}")
    print(f"{'─' * 60}\n")


def run_classification(ficha_tecnica: str) -> dict:
    """Ejecuta el flujo completo de clasificación y validación."""

    # ── Paso 1: Cargar el arancel ──
    print_step(1, "Cargando Arancel de Aduanas (Decreto 1881/2021)")
    print("  Extrayendo texto del PDF...")
    full_text = load_pdf()
    print(f"  PDF cargado: {len(full_text):,} caracteres")

    # ── Paso 2: Buscar capítulos relevantes ──
    print_step(2, "Identificando capítulos relevantes")
    contexto = find_relevant_chapters(ficha_tecnica, full_text)
    print(f"  Contexto relevante: {len(contexto):,} caracteres")

    # ── Paso 3: Agente Clasificador ──
    print_step(3, "AGENTE CLASIFICADOR analizando ficha técnica")
    print("  Enviando al modelo de IA...")
    resultado_clasificacion = clasificar_producto(ficha_tecnica, contexto)
    clasificacion_text = resultado_clasificacion["clasificacion_raw"]
    print(f"  Tokens usados: {resultado_clasificacion['tokens_input']} in / "
          f"{resultado_clasificacion['tokens_output']} out")
    print("\n" + clasificacion_text)

    # ── Paso 4: Agente Validador ──
    print_step(4, "AGENTE VALIDADOR verificando clasificación")
    print("  Enviando al modelo de IA...")
    resultado_validacion = validar_clasificacion(
        ficha_tecnica, clasificacion_text, contexto,
    )
    validacion_text = resultado_validacion["validacion_raw"]
    print(f"  Tokens usados: {resultado_validacion['tokens_input']} in / "
          f"{resultado_validacion['tokens_output']} out")
    print("\n" + validacion_text)

    # ── Resumen ──
    total_tokens_in = (
        resultado_clasificacion["tokens_input"]
        + resultado_validacion["tokens_input"]
    )
    total_tokens_out = (
        resultado_clasificacion["tokens_output"]
        + resultado_validacion["tokens_output"]
    )

    return {
        "ficha_tecnica": ficha_tecnica,
        "clasificacion": clasificacion_text,
        "validacion": validacion_text,
        "tokens_totales": {
            "input": total_tokens_in,
            "output": total_tokens_out,
        },
        "timestamp": datetime.now().isoformat(),
    }


def interactive_mode():
    """Modo interactivo: pide fichas técnicas en un loop."""
    print_header()
    print("Ingrese la ficha técnica del producto (o 'salir' para terminar).")
    print("Para fichas multilinea, termine con una línea vacía.\n")

    while True:
        print("─" * 60)
        print("FICHA TÉCNICA DEL PRODUCTO:")
        lines: list[str] = []
        while True:
            try:
                line = input("> " if not lines else "  ")
            except (EOFError, KeyboardInterrupt):
                print("\nSaliendo...")
                return

            if line.strip().lower() == "salir":
                print("\nHasta luego.")
                return
            if not line.strip() and lines:
                break
            lines.append(line)

        ficha = "\n".join(lines).strip()
        if not ficha:
            print("Ficha vacía, intente de nuevo.")
            continue

        try:
            resultado = run_classification(ficha)
            # Guardar resultado
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"resultado_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
            print(f"\nResultado guardado en: {filename}")
        except Exception as e:
            print(f"\nError durante la clasificación: {e}")
            print("Verifique que ANTHROPIC_API_KEY esté configurada y el PDF exista.")


ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json"}


def _read_ficha_file(raw_path: str) -> str:
    """Lee un archivo de ficha técnica con validación de ruta.

    Mitiga Path Traversal (CWE-23):
    - Rechaza componentes de ruta como ".." y rutas absolutas.
    - Restringe a extensiones permitidas.
    - Solo permite archivos dentro del directorio de trabajo.
    """
    import re
    from pathlib import Path

    # Sanitizar: rechazar traversal patterns antes de construir el Path
    sanitized = raw_path.strip()
    if ".." in sanitized or sanitized.startswith("/") or sanitized.startswith("\\"):
        print("Error: ruta no permitida. Use una ruta relativa sin '..'.")
        sys.exit(1)
    if not re.match(r"^[\w\-./\\]+$", sanitized):
        print("Error: la ruta contiene caracteres no permitidos.")
        sys.exit(1)

    cwd = Path.cwd().resolve()
    resolved = (cwd / sanitized).resolve()
    if not str(resolved).startswith(str(cwd) + os.sep):
        print("Error: solo se permiten archivos dentro del directorio de trabajo.")
        sys.exit(1)
    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        print(f"Error: extensión '{resolved.suffix}' no permitida. "
              f"Use: {ALLOWED_EXTENSIONS}")
        sys.exit(1)
    if not resolved.is_file():
        print(f"Error: el archivo '{resolved}' no existe.")
        sys.exit(1)
    return resolved.read_text(encoding="utf-8")


def main():
    if len(sys.argv) > 1:
        # Modo archivo: leer ficha técnica de un archivo
        ficha = _read_ficha_file(sys.argv[1])
        print_header()
        resultado = run_classification(ficha)
        output = json.dumps(resultado, ensure_ascii=False, indent=2)
        print(f"\n{'=' * 60}")
        print("RESULTADO COMPLETO (JSON):")
        print(output)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
