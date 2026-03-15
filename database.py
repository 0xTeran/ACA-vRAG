"""Módulo de base de datos Supabase para ACA.

Gestiona clasificaciones, base de conocimiento, y métricas de costos.
"""
from __future__ import annotations

import re
from datetime import datetime

from supabase import create_client

from config import SUPABASE_KEY, SUPABASE_URL

# Precios por millón de tokens (USD) - OpenRouter
PRICING = {
    "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "perplexity/sonar-pro": {"input": 3.0, "output": 15.0},
    "google/gemini-2.0-flash-001": {"input": 0.1, "output": 0.4},
}
USD_TO_COP = 4200  # Tasa aproximada


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def calcular_costo(tokens_input: int, tokens_output: int, modelo: str) -> float:
    """Calcula el costo en USD basado en tokens y modelo."""
    prices = PRICING.get(modelo, {"input": 3.0, "output": 15.0})
    return (tokens_input * prices["input"] / 1_000_000) + (tokens_output * prices["output"] / 1_000_000)


def calcular_costo_total(resultados: list[dict]) -> dict:
    """Calcula costos totales de múltiples llamadas a agentes."""
    total_usd = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    for r in resultados:
        modelo = r.get("modelo", "anthropic/claude-sonnet-4")
        t_in = r.get("tokens_input", 0)
        t_out = r.get("tokens_output", 0)
        total_tokens_in += t_in
        total_tokens_out += t_out
        total_usd += calcular_costo(t_in, t_out, modelo)
    return {
        "tokens_input": total_tokens_in,
        "tokens_output": total_tokens_out,
        "tokens_total": total_tokens_in + total_tokens_out,
        "costo_usd": round(total_usd, 6),
        "costo_cop": round(total_usd * USD_TO_COP, 2),
    }


def extraer_subpartida(clasificacion_text: str) -> str:
    """Extrae la subpartida arancelaria del texto de clasificación."""
    match = re.search(r"\d{4}\.\d{2}\.\d{2}\.\d{2}", clasificacion_text)
    return match.group(0) if match else ""


def guardar_clasificacion(
    ficha_tecnica: str,
    fuente_tipo: str,
    fuente_nombre: str,
    investigacion: str,
    clasificacion: str,
    validacion: str,
    costos: dict,
    tiempo_segundos: float,
    fuentes: list[dict],
    anon_id: str = "",
) -> dict:
    """Guarda una clasificación completa en Supabase."""
    subpartida = extraer_subpartida(clasificacion)

    # Extraer sección, capítulo, gravamen del texto
    seccion_match = re.search(r"\*\*Sección:\*\*\s*([IVXLCDM]+)", clasificacion)
    capitulo_match = re.search(r"\*\*Capítulo:\*\*\s*(\d+)", clasificacion)
    gravamen_match = re.search(r"\*\*Gravamen[^:]*:\*\*\s*(\d+)", clasificacion)

    data = {
        "ficha_tecnica": ficha_tecnica,
        "fuente_tipo": fuente_tipo,
        "fuente_nombre": fuente_nombre or "",
        "subpartida": subpartida,
        "seccion": seccion_match.group(1) if seccion_match else "",
        "capitulo": capitulo_match.group(1) if capitulo_match else "",
        "gravamen_pct": int(gravamen_match.group(1)) if gravamen_match else None,
        "investigacion": investigacion,
        "clasificacion": clasificacion,
        "validacion": validacion,
        "estado": "pendiente",
        "tokens_total": costos["tokens_total"],
        "costo_usd": costos["costo_usd"],
        "costo_cop": costos["costo_cop"],
        "tiempo_segundos": tiempo_segundos,
        "fuentes": fuentes,
    }
    if anon_id:
        data["anon_id"] = anon_id

    client = get_client()
    result = client.table("clasificaciones").insert(data).execute()
    return result.data[0] if result.data else data


def actualizar_estado(clasificacion_id: str, estado: str, notas: str = "") -> dict:
    """Actualiza el estado de una clasificación (aprobar/rechazar/investigar)."""
    client = get_client()
    data = {
        "estado": estado,
        "notas_revision": notas,
        "updated_at": datetime.utcnow().isoformat(),
    }
    result = client.table("clasificaciones").update(data).eq("id", clasificacion_id).execute()

    # Si se aprueba, agregar a base de conocimiento
    if estado == "aprobada" and result.data:
        cls = result.data[0]
        _agregar_a_conocimiento(cls)

    return result.data[0] if result.data else {}


def _agregar_a_conocimiento(clasificacion: dict):
    """Agrega una clasificación aprobada a la base de conocimiento."""
    ficha = clasificacion.get("ficha_tecnica", "")
    # Generar keywords del producto
    words = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', ficha.lower()))
    keywords = " ".join(sorted(words)[:30])

    data = {
        "producto": ficha[:500],
        "descripcion": ficha,
        "subpartida": clasificacion.get("subpartida", ""),
        "seccion": clasificacion.get("seccion", ""),
        "capitulo": clasificacion.get("capitulo", ""),
        "gravamen_pct": clasificacion.get("gravamen_pct"),
        "justificacion": (clasificacion.get("clasificacion", ""))[:2000],
        "fuente": "aprobación usuario",
        "keywords": keywords,
        "clasificacion_id": clasificacion.get("id"),
    }
    client = get_client()
    client.table("conocimiento").insert(data).execute()


def buscar_conocimiento(ficha_tecnica: str, limit: int = 5) -> list[dict]:
    """Busca clasificaciones previas relevantes en la base de conocimiento."""
    words = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', ficha_tecnica.lower()))
    if not words:
        return []

    # Buscar por texto completo en español
    search_query = " | ".join(sorted(words)[:10])
    client = get_client()

    try:
        result = client.table("conocimiento").select(
            "producto, subpartida, seccion, capitulo, gravamen_pct, justificacion, fuente"
        ).text_search("keywords", search_query, config="spanish").limit(limit).execute()
        return result.data or []
    except Exception:
        # Fallback: buscar sin text search
        return []


def importar_conocimiento(registros: list[dict]) -> int:
    """Importa registros a la base de conocimiento desde CSV/JSON."""
    client = get_client()
    inserted = 0
    for reg in registros:
        producto = reg.get("producto", reg.get("descripcion", ""))
        subpartida = reg.get("subpartida", reg.get("codigo", ""))
        if not producto or not subpartida:
            continue

        words = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', producto.lower()))
        data = {
            "producto": producto[:500],
            "descripcion": producto,
            "subpartida": subpartida,
            "seccion": reg.get("seccion", ""),
            "capitulo": reg.get("capitulo", ""),
            "gravamen_pct": reg.get("gravamen", reg.get("gravamen_pct")),
            "justificacion": reg.get("justificacion", ""),
            "fuente": reg.get("fuente", "importado"),
            "keywords": " ".join(sorted(words)[:30]),
        }
        client.table("conocimiento").insert(data).execute()
        inserted += 1
    return inserted


def listar_clasificaciones(estado: str = None, limit: int = 50) -> list[dict]:
    """Lista clasificaciones, opcionalmente filtradas por estado."""
    client = get_client()
    query = client.table("clasificaciones").select(
        "id, created_at, ficha_tecnica, subpartida, gravamen_pct, estado, "
        "costo_cop, tiempo_segundos, notas_revision"
    ).order("created_at", desc=True).limit(limit)

    if estado:
        query = query.eq("estado", estado)

    result = query.execute()
    return result.data or []


def obtener_clasificacion(clasificacion_id: str) -> dict:
    """Obtiene una clasificación completa por ID."""
    client = get_client()
    result = client.table("clasificaciones").select("*").eq("id", clasificacion_id).single().execute()
    return result.data or {}


def stats_conocimiento() -> dict:
    """Estadísticas de la base de conocimiento."""
    client = get_client()
    total = client.table("conocimiento").select("id", count="exact").execute()
    return {"total_registros": total.count or 0}


# ── Chat persistente ──


def guardar_mensaje_chat(clasificacion_id: str, role: str, content: str) -> dict:
    """Guarda un mensaje de chat vinculado a una clasificación."""
    client = get_client()
    data = {
        "clasificacion_id": clasificacion_id,
        "role": role,
        "content": content,
    }
    result = client.table("chat_mensajes").insert(data).execute()
    return result.data[0] if result.data else data


def obtener_chat_mensajes(clasificacion_id: str) -> list[dict]:
    """Obtiene todos los mensajes de chat de una clasificación."""
    client = get_client()
    result = (
        client.table("chat_mensajes")
        .select("role, content, created_at")
        .eq("clasificacion_id", clasificacion_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


# ── Auth / usuarios ──

def get_anon_count(anon_id: str) -> int:
    """Devuelve cuántas clasificaciones ha hecho este usuario anónimo."""
    client = get_client()
    result = client.table("anon_usos").select("count").eq("anon_id", anon_id).execute()
    return result.data[0]["count"] if result.data else 0


def increment_anon_count(anon_id: str) -> int:
    """Incrementa y devuelve el contador de usos anónimos."""
    client = get_client()
    result = client.table("anon_usos").select("count").eq("anon_id", anon_id).execute()
    if result.data:
        new_count = result.data[0]["count"] + 1
        client.table("anon_usos").update(
            {"count": new_count, "updated_at": datetime.utcnow().isoformat()}
        ).eq("anon_id", anon_id).execute()
    else:
        new_count = 1
        client.table("anon_usos").insert({"anon_id": anon_id, "count": 1}).execute()
    return new_count


def crear_verificacion(email: str, codigo: str, minutes: int = 15) -> None:
    """Crea un código de verificación; invalida los anteriores del mismo email."""
    from datetime import timedelta
    client = get_client()
    client.table("verificaciones").update({"usado": True}).eq("email", email).execute()
    expires_at = (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()
    client.table("verificaciones").insert({
        "email": email, "codigo": codigo,
        "expires_at": expires_at, "usado": False,
    }).execute()


def verificar_codigo(email: str, codigo: str) -> bool:
    """Valida el código. True si es correcto y no expiró; lo marca como usado."""
    from datetime import timezone
    client = get_client()
    result = (
        client.table("verificaciones")
        .select("*")
        .eq("email", email)
        .eq("codigo", codigo.upper())
        .eq("usado", False)
        .execute()
    )
    if not result.data:
        return False
    record = result.data[0]
    expires_str = record["expires_at"].replace("Z", "+00:00")
    expires_at = datetime.fromisoformat(expires_str)
    if datetime.now(timezone.utc) > expires_at:
        return False
    client.table("verificaciones").update({"usado": True}).eq("id", record["id"]).execute()
    return True


def get_or_create_usuario(email: str) -> dict:
    """Obtiene o crea un usuario verificado."""
    client = get_client()
    result = client.table("usuarios").select("*").eq("email", email).execute()
    if result.data:
        u = result.data[0]
        if not u.get("verificado"):
            client.table("usuarios").update({"verificado": True}).eq("email", email).execute()
            u["verificado"] = True
        return u
    new = client.table("usuarios").insert({"email": email, "verificado": True}).execute()
    return new.data[0]


def get_usuario(user_id: str) -> dict | None:
    """Obtiene un usuario por su UUID."""
    client = get_client()
    result = client.table("usuarios").select("id,email,nombre,created_at").eq("id", user_id).execute()
    return result.data[0] if result.data else None
