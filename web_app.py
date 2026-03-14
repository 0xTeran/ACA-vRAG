#!/usr/bin/env python3
"""ACA Web - Agente de Clasificación Arancelaria (versión web).

Interfaz web con 3 agentes: Clasificador, Validador e Investigador.
Soporta texto, URL, imagen y PDF como entrada.
"""
from __future__ import annotations

import base64
import ipaddress
import os
import re
import socket
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
from pdf_loader import find_relevant_chapters, load_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

print("Cargando Arancel de Aduanas (Decreto 1881/2021)...")
ARANCEL_TEXT = load_pdf()
print(f"Arancel cargado: {len(ARANCEL_TEXT):,} caracteres")

ALLOWED_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr",
    "strong", "em", "code", "pre", "blockquote",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
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
    reader = PdfReader(pdf_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    return "\n".join(pages_text)[:15000]


def extract_text_from_image(image_path: str) -> str:
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    ext = Path(image_path).suffix.lower().lstrip(".")
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif", "bmp": "bmp"}
    mime_type = f"image/{mime_map.get(ext, 'png')}"
    response = client.chat.completions.create(
        model=VISION_MODEL,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Extrae toda la información de esta ficha técnica de producto. "
                    "Incluye: nombre, descripción, materiales, composición, dimensiones, "
                    "peso, uso, origen, y cualquier otro dato relevante. "
                    "Responde solo con la información extraída."
                )},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
            ],
        }],
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
    return http_requests.get(safe_url, headers={"User-Agent": "ACA-Bot/1.0"}, timeout=15, allow_redirects=False)


def extract_text_from_url(user_url: str) -> str:
    resp = _fetch_url_safe(user_url)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "application/pdf" in content_type:
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/clasificar", methods=["POST"])
def clasificar():
    try:
        input_type = request.form.get("input_type", "texto")
        ficha_tecnica = ""

        if input_type == "texto":
            ficha_tecnica = request.form.get("ficha_texto", "").strip()
            if not ficha_tecnica:
                return jsonify({"error": "La ficha técnica está vacía."}), 400

        elif input_type == "url":
            url = request.form.get("ficha_url", "").strip()
            if not url:
                return jsonify({"error": "La URL está vacía."}), 400
            if not url.startswith(("http://", "https://")):
                return jsonify({"error": "URL inválida."}), 400
            ficha_tecnica = extract_text_from_url(url)

        elif input_type == "archivo":
            if "ficha_archivo" not in request.files:
                return jsonify({"error": "No se seleccionó ningún archivo."}), 400
            file = request.files["ficha_archivo"]
            if file.filename == "":
                return jsonify({"error": "No se seleccionó ningún archivo."}), 400
            if not _allowed_file(file.filename):
                return jsonify({"error": f"Formato no permitido. Use: {ALLOWED_FILE_EXTENSIONS}"}), 400
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            safe_name = re.sub(r"[^\w.\-]", "_", file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, safe_name)
            file.save(filepath)
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

        contexto = find_relevant_chapters(ficha_tecnica, ARANCEL_TEXT)

        # Paso 1: Investigador (busca resoluciones DIAN + Perplexity)
        res_inv = investigar_producto(ficha_tecnica)
        investigacion = res_inv["investigacion_raw"]

        # Paso 2: Clasificador (usa la investigación como insumo)
        res_cls = clasificar_producto(ficha_tecnica, contexto, investigacion)
        clasificacion = res_cls["clasificacion_raw"]

        # Paso 3: Validador (verifica la clasificación)
        res_val = validar_clasificacion(ficha_tecnica, clasificacion, contexto)
        validacion = res_val["validacion_raw"]

        tokens_total = (
            res_cls["tokens_input"] + res_cls["tokens_output"]
            + res_val["tokens_input"] + res_val["tokens_output"]
            + res_inv["tokens_input"] + res_inv["tokens_output"]
        )

        return jsonify({
            "ficha_tecnica": str(html_escape(ficha_tecnica)),
            "clasificacion_html": _render_markdown_safe(clasificacion),
            "validacion_html": _render_markdown_safe(validacion),
            "investigacion_html": _render_markdown_safe(investigacion),
            "fuentes": res_inv.get("fuentes", []),
            "clasificacion_raw": clasificacion,
            "validacion_raw": validacion,
            "investigacion_raw": investigacion,
            "tokens": tokens_total,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


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
    """Detecta URLs en el texto, descarga su contenido y retorna el contexto extraído."""
    urls = _URL_PATTERN.findall(text)
    if not urls:
        return ""

    extracted_parts: list[str] = []
    for url in urls[:3]:  # Máximo 3 URLs por mensaje
        try:
            content = extract_text_from_url(url)
            if content:
                extracted_parts.append(
                    f"\n---\n**Contenido extraído de:** {url}\n\n{content[:5000]}\n---"
                )
        except Exception as e:
            extracted_parts.append(f"\n[No se pudo acceder a {url}: {e}]")

    return "\n".join(extracted_parts)


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos."}), 400
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "El mensaje está vacío."}), 400

        # Detectar y descargar URLs en el mensaje
        url_content = _extract_urls_content(user_message)
        enriched_message = user_message
        if url_content:
            enriched_message += (
                "\n\n[El sistema descargó el contenido de los enlaces proporcionados:]\n"
                + url_content
            )

        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        context_msg = (
            f"## Contexto:\n\n### Ficha técnica:\n{data.get('ficha_tecnica', '')}\n\n"
            f"### Clasificación:\n{data.get('clasificacion', '')}\n\n"
            f"### Validación:\n{data.get('validacion', '')}\n\n"
            f"### Investigación de fuentes DIAN:\n{data.get('investigacion', '')}"
        )
        messages.append({"role": "user", "content": context_msg})
        messages.append({"role": "assistant", "content": "Entendido. Tengo el contexto completo. ¿En qué puedo ayudarte?"})

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
