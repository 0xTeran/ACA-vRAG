#!/usr/bin/env python3
"""ACA Web - Agente de Clasificación Arancelaria (versión web).

3 agentes + base de conocimiento Supabase + sistema de aprobación.
"""
from __future__ import annotations

import base64
import csv
import io
import ipaddress
import json
import os
import re
import socket
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

import bleach
import markdown
import requests as http_requests
from flask import Flask, jsonify, render_template, request
from markupsafe import escape as html_escape
from openai import OpenAI
from PyPDF2 import PdfReader

from agente_clasificador import clasificar_producto
from agente_investigador import investigar_producto
from agente_validador import validar_clasificacion
from config import (
    ALLOWED_FILE_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    UPLOAD_FOLDER,
    VISION_MODEL,
)
from database import (
    actualizar_estado,
    buscar_conocimiento,
    calcular_costo_total,
    guardar_clasificacion,
    importar_conocimiento,
    listar_clasificaciones,
    obtener_clasificacion,
    stats_conocimiento,
)
from pdf_loader import find_relevant_chapters, load_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

print("Cargando Arancel de Aduanas (Decreto 1881/2021)...")
ARANCEL_TEXT = load_pdf()
print(f"Arancel cargado: {len(ARANCEL_TEXT):,} caracteres")

ALLOWED_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr",
    "strong", "em", "code", "pre", "blockquote",
    "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "a", "span", "div",
]
ALLOWED_ATTRS = {"a": ["href", "target"], "th": ["align"], "td": ["align"]}
ALLOWED_URL_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = frozenset({
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "metadata.google.internal", "169.254.169.254",
})


def _render_markdown_safe(text: str) -> str:
    raw_html = markdown.markdown(text, extensions=["tables", "fenced_code"])
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_FILE_EXTENSIONS


def _is_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _is_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "pdf"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrae texto de un PDF. Si PyPDF2 no extrae texto de alguna página
    (PDF escaneado/imagen), usa el modelo de visión como fallback."""
    import fitz  # PyMuPDF - mejor extracción que PyPDF2

    try:
        doc = fitz.open(pdf_path)
        pages_text = []
        empty_pages = []
        for i, page in enumerate(doc):
            text = page.get_text()
            if text and text.strip():
                pages_text.append(f"--- Página {i + 1} ---\n{text.strip()}")
            else:
                empty_pages.append(i)
        doc.close()

        # Si hay páginas vacías (escaneadas), intentar con visión
        if empty_pages and len(empty_pages) <= 5:
            doc = fitz.open(pdf_path)
            for page_idx in empty_pages:
                page = doc[page_idx]
                pix = page.get_pixmap(dpi=200)
                img_path = os.path.join(UPLOAD_FOLDER, f"pdf_page_{page_idx}.png")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                pix.save(img_path)
                try:
                    ocr_text = extract_text_from_image(img_path)
                    if ocr_text:
                        pages_text.insert(page_idx, f"--- Página {page_idx + 1} (OCR) ---\n{ocr_text}")
                except Exception:
                    pass
            doc.close()

        return "\n\n".join(pages_text)

    except Exception:
        # Fallback a PyPDF2
        reader = PdfReader(pdf_path)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- Página {i + 1} ---\n{text}")
        return "\n\n".join(pages_text)


def extract_text_from_image(image_path: str) -> str:
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    ext = Path(image_path).suffix.lower().lstrip(".")
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif", "bmp": "bmp"}
    mime_type = f"image/{mime_map.get(ext, 'png')}"
    response = client.chat.completions.create(
        model=VISION_MODEL, max_tokens=2048,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Extrae toda la información de esta ficha técnica de producto. Incluye: nombre, descripción, materiales, composición, dimensiones, peso, uso, origen. Responde solo con la información extraída."},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
        ]}],
    )
    return response.choices[0].message.content


def _fetch_url_safe(user_url: str) -> http_requests.Response:
    parsed = urlparse(user_url)
    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        raise ValueError("Solo se permiten URLs http/https.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL inválida.")
    if hostname in BLOCKED_HOSTS:
        raise ValueError("URL no permitida: host local o reservado.")
    resolved_ip = socket.gethostbyname(hostname)
    ip_obj = ipaddress.ip_address(resolved_ip)
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
        raise ValueError("URL no permitida: IP privada o reservada.")
    safe_url = f"{parsed.scheme}://{hostname}"
    if parsed.port:
        safe_url += f":{parsed.port}"
    safe_url += parsed.path
    if parsed.query:
        safe_url += f"?{parsed.query}"
    return http_requests.get(safe_url, headers={"User-Agent": "ACA-Bot/1.0"}, timeout=30, allow_redirects=True)


def extract_text_from_url(user_url: str) -> str:
    resp = _fetch_url_safe(user_url)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    # Detectar PDF por content-type O por extensión de URL
    url_path = urlparse(user_url).path.lower()
    is_pdf = "application/pdf" in content_type or url_path.endswith(".pdf")
    if is_pdf:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        tmp = os.path.join(UPLOAD_FOLDER, "url_temp.pdf")
        with open(tmp, "wb") as f:
            f.write(resp.content)
        return extract_text_from_pdf(tmp)
    if any(t in content_type for t in ["image/png", "image/jpeg", "image/webp", "image/gif"]):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        tmp = os.path.join(UPLOAD_FOLDER, "url_temp.png")
        with open(tmp, "wb") as f:
            f.write(resp.content)
        return extract_text_from_image(tmp)
    html = resp.text
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:5000]


def _build_knowledge_context(ficha_tecnica: str) -> str:
    """Busca clasificaciones previas relevantes y las formatea como contexto."""
    precedentes = buscar_conocimiento(ficha_tecnica, limit=5)
    if not precedentes:
        return ""
    lines = ["## Precedentes de clasificación en la base de conocimiento:\n"]
    for i, p in enumerate(precedentes, 1):
        lines.append(f"**{i}. Producto:** {p['producto'][:200]}")
        lines.append(f"   **Subpartida:** {p['subpartida']} | Gravamen: {p.get('gravamen_pct', '?')}%")
        if p.get("justificacion"):
            lines.append(f"   **Justificación:** {p['justificacion'][:300]}")
        lines.append(f"   **Fuente:** {p.get('fuente', 'N/A')}\n")
    return "\n".join(lines)


# ── Rutas ──

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/clasificar", methods=["POST"])
def clasificar():
    try:
        start_time = time.time()
        input_type = request.form.get("input_type", "texto")
        fuente_nombre = ""
        ficha_tecnica = ""

        if input_type == "texto":
            ficha_tecnica = request.form.get("ficha_texto", "").strip()
            if not ficha_tecnica:
                return jsonify({"error": "La ficha técnica está vacía."}), 400
        elif input_type == "url":
            url = request.form.get("ficha_url", "").strip()
            if not url or not url.startswith(("http://", "https://")):
                return jsonify({"error": "URL inválida."}), 400
            fuente_nombre = url
            ficha_tecnica = extract_text_from_url(url)
        elif input_type == "archivo":
            if "ficha_archivo" not in request.files:
                return jsonify({"error": "No se seleccionó ningún archivo."}), 400
            file = request.files["ficha_archivo"]
            if file.filename == "" or not _allowed_file(file.filename):
                return jsonify({"error": f"Formato no permitido. Use: {ALLOWED_FILE_EXTENSIONS}"}), 400
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            safe_name = re.sub(r"[^\w.\-]", "_", file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, safe_name)
            file.save(filepath)
            fuente_nombre = file.filename
            if _is_pdf(file.filename):
                ficha_tecnica = extract_text_from_pdf(filepath)
            elif _is_image(file.filename):
                ficha_tecnica = extract_text_from_image(filepath)
            else:
                return jsonify({"error": "Tipo no soportado."}), 400
        else:
            return jsonify({"error": "Tipo de entrada no válido."}), 400

        if not ficha_tecnica.strip():
            return jsonify({"error": "No se pudo extraer texto del archivo."}), 400

        # Buscar precedentes en base de conocimiento
        knowledge_ctx = _build_knowledge_context(ficha_tecnica)
        contexto = find_relevant_chapters(ficha_tecnica, ARANCEL_TEXT)

        # Paso 1: Investigador
        res_inv = investigar_producto(ficha_tecnica)
        investigacion = res_inv["investigacion_raw"]

        # Paso 2: Clasificador (con conocimiento previo + investigación)
        clasificador_contexto = contexto
        if knowledge_ctx:
            clasificador_contexto = knowledge_ctx + "\n\n" + contexto
        res_cls = clasificar_producto(ficha_tecnica, clasificador_contexto, investigacion)
        clasificacion = res_cls["clasificacion_raw"]

        # Paso 3: Validador
        res_val = validar_clasificacion(ficha_tecnica, clasificacion, contexto)
        validacion = res_val["validacion_raw"]

        elapsed = round(time.time() - start_time, 2)

        # Calcular costos
        costos = calcular_costo_total([res_inv, res_cls, res_val])

        # Guardar en Supabase
        registro = guardar_clasificacion(
            ficha_tecnica=ficha_tecnica,
            fuente_tipo=input_type,
            fuente_nombre=fuente_nombre,
            investigacion=investigacion,
            clasificacion=clasificacion,
            validacion=validacion,
            costos=costos,
            tiempo_segundos=elapsed,
            fuentes=res_inv.get("fuentes", []),
        )

        return jsonify({
            "id": registro.get("id", ""),
            "ficha_tecnica": str(html_escape(ficha_tecnica)),
            "investigacion_html": _render_markdown_safe(investigacion),
            "clasificacion_html": _render_markdown_safe(clasificacion),
            "validacion_html": _render_markdown_safe(validacion),
            "clasificacion_raw": clasificacion,
            "validacion_raw": validacion,
            "investigacion_raw": investigacion,
            "fuentes": res_inv.get("fuentes", []),
            "tokens": costos["tokens_total"],
            "costo_usd": costos["costo_usd"],
            "costo_cop": costos["costo_cop"],
            "tiempo_segundos": elapsed,
            "precedentes_usados": len(buscar_conocimiento(ficha_tecnica, limit=5)),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/estado", methods=["POST"])
def cambiar_estado():
    """Aprobar, rechazar o marcar para investigación profunda."""
    try:
        data = request.get_json()
        clasificacion_id = data.get("id", "").strip()
        estado = data.get("estado", "").strip()
        notas = data.get("notas", "").strip()

        if not clasificacion_id or estado not in ("aprobada", "rechazada", "investigar"):
            return jsonify({"error": "ID o estado inválido."}), 400

        result = actualizar_estado(clasificacion_id, estado, notas)
        return jsonify({"ok": True, "registro": result})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/historial")
def historial():
    """Lista clasificaciones con filtro opcional por estado."""
    estado = request.args.get("estado")
    registros = listar_clasificaciones(estado=estado, limit=100)
    return jsonify({"registros": registros})


@app.route("/clasificacion/<clasificacion_id>")
def ver_clasificacion(clasificacion_id):
    """Obtiene una clasificación completa."""
    registro = obtener_clasificacion(clasificacion_id)
    if not registro:
        return jsonify({"error": "No encontrada."}), 404
    return jsonify(registro)


@app.route("/importar", methods=["POST"])
def importar():
    """Importa base de conocimiento desde CSV o JSON."""
    try:
        if "archivo" not in request.files:
            return jsonify({"error": "No se seleccionó archivo."}), 400

        file = request.files["archivo"]
        filename = file.filename.lower()
        content = file.read().decode("utf-8")

        registros = []
        if filename.endswith(".json"):
            registros = json.loads(content)
            if isinstance(registros, dict):
                registros = registros.get("data", registros.get("registros", [registros]))
        elif filename.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(content))
            registros = list(reader)
        else:
            return jsonify({"error": "Use archivo .json o .csv"}), 400

        inserted = importar_conocimiento(registros)
        return jsonify({"ok": True, "importados": inserted, "total_enviados": len(registros)})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/conocimiento/stats")
def conocimiento_stats():
    return jsonify(stats_conocimiento())


# ── Chat ──

CHAT_SYSTEM_PROMPT = """\
Eres un experto en clasificación arancelaria de la DIAN (Colombia), especializado en el \
Decreto 1881 de 2021. Un usuario recibió una clasificación, validación e investigación de \
fuentes DIAN sobre un producto. Responde preguntas de seguimiento con precisión, citando \
reglas, notas y resoluciones relevantes.

Cuando el usuario comparta un enlace, el sistema descargará automáticamente el contenido \
y te lo proporcionará como contexto adicional. Analiza ese contenido en tu respuesta.

Responde en español.
"""

_URL_PATTERN = re.compile(r'https?://[^\s<>"\']+')


def _extract_urls_content(text: str) -> str:
    urls = _URL_PATTERN.findall(text)
    if not urls:
        return ""
    parts: list[str] = []
    for url in urls[:3]:
        try:
            content = extract_text_from_url(url)
            if content:
                parts.append(f"\n---\n**Contenido de:** {url}\n\n{content[:5000]}\n---")
        except Exception as e:
            parts.append(f"\n[No se pudo acceder a {url}: {e}]")
    return "\n".join(parts)


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos."}), 400
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "El mensaje está vacío."}), 400

        url_content = _extract_urls_content(user_message)
        enriched_message = user_message
        if url_content:
            enriched_message += "\n\n[Contenido descargado:]\n" + url_content

        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        context_msg = (
            f"## Contexto:\n\n### Ficha técnica:\n{data.get('ficha_tecnica', '')}\n\n"
            f"### Clasificación:\n{data.get('clasificacion', '')}\n\n"
            f"### Validación:\n{data.get('validacion', '')}\n\n"
            f"### Investigación:\n{data.get('investigacion', '')}"
        )
        messages.append({"role": "user", "content": context_msg})
        messages.append({"role": "assistant", "content": "Entendido. ¿En qué puedo ayudarte?"})

        for entry in data.get("history", []):
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": enriched_message})

        client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
        response = client.chat.completions.create(model=MODEL, max_tokens=2048, messages=messages)

        reply = response.choices[0].message.content
        return jsonify({"reply": reply, "reply_html": _render_markdown_safe(reply)})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=5050)
