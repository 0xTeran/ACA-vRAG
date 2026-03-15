"""Módulo de base de datos Supabase para ACA.

Gestiona clasificaciones, base de conocimiento, y métricas de costos.
"""
from __future__ import annotations

import re
from datetime import datetime

from supabase import create_client

from config import SUPABASE_KEY, SUPABASE_URL

USD_TO_COP = 4200  # Tasa aproximada

# Cache de precios de modelos
_pricing_cache: dict | None = None


def _get_pricing() -> dict:
    """Obtiene precios de modelos desde BD (con cache)."""
    global _pricing_cache
    if _pricing_cache:
        return _pricing_cache
    try:
        client = get_client()
        result = client.table("modelos").select("id, precio_input, precio_output").execute()
        _pricing_cache = {
            m["id"]: {"input": float(m["precio_input"]), "output": float(m["precio_output"])}
            for m in (result.data or [])
        }
        # Siempre incluir perplexity
        _pricing_cache.setdefault("perplexity/sonar-pro", {"input": 3.0, "output": 15.0})
        return _pricing_cache
    except Exception:
        return {
            "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
            "perplexity/sonar-pro": {"input": 3.0, "output": 15.0},
        }


def listar_modelos() -> list[dict]:
    """Lista modelos disponibles."""
    client = get_client()
    result = client.table("modelos").select("*").eq("activo", True).order("es_default", desc=True).order("nombre").execute()
    return result.data or []


def get_modelo_default() -> str:
    """Retorna el ID del modelo default."""
    client = get_client()
    result = client.table("modelos").select("id").eq("es_default", True).limit(1).execute()
    return result.data[0]["id"] if result.data else "anthropic/claude-sonnet-4"


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def calcular_costo(tokens_input: int, tokens_output: int, modelo: str) -> float:
    """Calcula el costo en USD basado en tokens y modelo."""
    pricing = _get_pricing()
    prices = pricing.get(modelo, {"input": 3.0, "output": 15.0})
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

    # Si se aprueba, agregar a base de conocimiento + extraer lecciones del chat
    if estado == "aprobada" and result.data:
        cls = result.data[0]
        _agregar_a_conocimiento(cls)
        try:
            extraer_lecciones_de_chat(clasificacion_id)
        except Exception:
            pass  # No bloquear la aprobación si falla

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


# ── Arancel estructurado ──


def verificar_codigo_arancel(codigo: str) -> dict | None:
    """Verifica si un código arancelario existe en la BD. Retorna el registro o None."""
    client = get_client()
    result = client.table("arancel").select("*").eq("codigo", codigo).execute()
    return result.data[0] if result.data else None


def buscar_arancel_por_partida(partida: str) -> list[dict]:
    """Retorna todas las subpartidas de una partida (ej: '84.24' o '8424')."""
    client = get_client()
    # Normalizar: '84.24' → '84.24', '8424' → '84.24'
    if len(partida) == 4 and "." not in partida:
        partida = partida[:2] + "." + partida[2:]
    result = client.table("arancel").select("codigo, descripcion, gravamen").eq("partida", partida).order("codigo").execute()
    return result.data or []


def buscar_arancel_por_descripcion(query: str, limit: int = 20) -> list[dict]:
    """Busca subpartidas por descripción usando full-text search."""
    client = get_client()
    words = re.findall(r'\b[a-záéíóúñ]{4,}\b', query.lower())
    if not words:
        return []
    search = " & ".join(words[:8])
    try:
        result = client.table("arancel").select(
            "codigo, descripcion, gravamen, capitulo, partida"
        ).text_search("descripcion", search, config="spanish").limit(limit).execute()
        return result.data or []
    except Exception:
        return []


def _get_embed_client():
    """Retorna cliente de embeddings (singleton-like)."""
    import os as _os
    from openai import OpenAI as _OpenAI

    api_key = _os.environ.get("OPENAI_API_KEY") or _os.environ.get("OPENROUTER_API_KEY", "")
    base_url = None if _os.environ.get("OPENAI_API_KEY") else "https://openrouter.ai/api/v1"
    return _OpenAI(api_key=api_key, base_url=base_url) if base_url else _OpenAI(api_key=api_key)


def _embed_text(text: str) -> list[float]:
    """Genera embedding para un texto."""
    client = _get_embed_client()
    response = client.embeddings.create(model="text-embedding-3-small", input=text[:4000])
    return response.data[0].embedding


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Genera embeddings para múltiples textos en una sola llamada."""
    client = _get_embed_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[t[:4000] for t in texts],
    )
    return [item.embedding for item in response.data]


def _buscar_chunks_por_embedding(embedding: list[float], top_k: int = 8, threshold: float = 0.25) -> list[dict]:
    """Busca chunks similares dado un embedding."""
    client = get_client()
    result = client.rpc("buscar_decreto", {
        "query_embedding": embedding,
        "match_count": top_k,
        "match_threshold": threshold,
    }).execute()
    return result.data or []


def extraer_caracteristicas(ficha_tecnica: str) -> list[dict]:
    """Extrae características clave de una ficha técnica usando IA.

    Retorna lista de dicts con {tipo, valor, query} para búsqueda RAG.
    """
    from config import MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
    from openai import OpenAI

    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",  # Modelo rápido y barato para extracción
        max_tokens=800,
        messages=[
            {
                "role": "system",
                "content": (
                    "Extrae las características clave de esta ficha técnica para clasificación arancelaria. "
                    "Responde SOLO en JSON array. Cada elemento: "
                    '{\"tipo\": \"material|estructura|funcion|uso|acabado|composicion|forma|peso|origen\", '
                    '\"valor\": \"descripción corta\", '
                    '\"query\": \"texto optimizado para buscar en el arancel de aduanas\"}. '
                    "Máximo 6 características. La query debe usar vocabulario arancelario."
                ),
            },
            {"role": "user", "content": ficha_tecnica[:3000]},
        ],
    )

    import json as _json
    try:
        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        # Limpiar posibles caracteres extra
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        return _json.loads(raw)
    except Exception:
        return []


def buscar_decreto_multicaracteristica(ficha_tecnica: str, top_k: int = 15) -> str:
    """Búsqueda RAG multi-característica.

    1. Extrae características de la ficha técnica (material, uso, forma, etc.)
    2. Hace búsqueda semántica por cada característica
    3. Cruza resultados: partidas que aparecen en múltiples búsquedas = más relevantes
    4. Retorna contexto ordenado por frecuencia de aparición
    """
    # Extraer características
    caracteristicas = extraer_caracteristicas(ficha_tecnica)

    if not caracteristicas:
        # Fallback a búsqueda simple
        return buscar_decreto_semantico(ficha_tecnica, top_k)

    # Generar embeddings en batch (1 sola llamada API)
    queries = [c.get("query", c.get("valor", "")) for c in caracteristicas]
    # Agregar la ficha completa como query adicional
    queries.append(ficha_tecnica[:2000])

    try:
        embeddings = _embed_batch(queries)
    except Exception:
        return buscar_decreto_semantico(ficha_tecnica, top_k)

    # Buscar chunks por cada característica
    all_chunks: dict[str, dict] = {}  # key = chunk_id → {chunk, score, matches}

    for idx, embedding in enumerate(embeddings):
        label = caracteristicas[idx]["tipo"] if idx < len(caracteristicas) else "ficha_completa"
        chunks = _buscar_chunks_por_embedding(embedding, top_k=8, threshold=0.25)

        for chunk in chunks:
            chunk_id = str(chunk.get("id", ""))
            sim = chunk.get("similarity", 0)

            if chunk_id in all_chunks:
                all_chunks[chunk_id]["matches"].append(label)
                all_chunks[chunk_id]["total_score"] += sim
                all_chunks[chunk_id]["max_score"] = max(all_chunks[chunk_id]["max_score"], sim)
            else:
                all_chunks[chunk_id] = {
                    "chunk": chunk,
                    "matches": [label],
                    "total_score": sim,
                    "max_score": sim,
                }

    if not all_chunks:
        return buscar_decreto_semantico(ficha_tecnica, top_k)

    # Ordenar por: número de matches (intersección) > score total
    ranked = sorted(
        all_chunks.values(),
        key=lambda x: (len(x["matches"]), x["total_score"]),
        reverse=True,
    )[:top_k]

    # Formatear contexto
    parts = [
        "## CONTEXTO DEL DECRETO 1881/2021 (búsqueda multi-característica):\n",
        "### Características extraídas de la ficha técnica:",
    ]
    for c in caracteristicas:
        parts.append(f"  - **{c.get('tipo', '?')}**: {c.get('valor', '?')}")
    parts.append("")

    for i, item in enumerate(ranked, 1):
        chunk = item["chunk"]
        n_matches = len(item["matches"])
        max_sim = round(item["max_score"] * 100, 1)
        match_labels = ", ".join(sorted(set(item["matches"])))

        tipo = chunk.get("tipo", "")
        cap = chunk.get("capitulo", "")
        meta = chunk.get("metadata", {}) or {}
        partida = meta.get("partida", "") if isinstance(meta, dict) else ""

        if tipo == "notas_capitulo":
            header = f"Notas Cap.{cap}"
        elif tipo == "partida":
            header = f"Partida {partida} Cap.{cap}"
        else:
            header = tipo

        parts.append(f"### [{i}] {header} — coincide con {n_matches} características ({match_labels}) — sim: {max_sim}%")
        parts.append(chunk.get("contenido", ""))
        parts.append("")

    return "\n".join(parts)


def buscar_decreto_semantico(ficha_tecnica: str, top_k: int = 12) -> str:
    """Búsqueda semántica sobre el Decreto 1881 usando embeddings.

    Convierte la ficha técnica a embedding y busca los chunks más similares.
    Retorna el contexto formateado listo para inyectar a los agentes.
    """
    import os as _os
    from openai import OpenAI as _OpenAI

    api_key = _os.environ.get("OPENAI_API_KEY") or _os.environ.get("OPENROUTER_API_KEY", "")
    base_url = None if _os.environ.get("OPENAI_API_KEY") else "https://openrouter.ai/api/v1"

    embed_client = _OpenAI(api_key=api_key, base_url=base_url) if base_url else _OpenAI(api_key=api_key)

    response = embed_client.embeddings.create(
        model="text-embedding-3-small",
        input=ficha_tecnica[:4000],
    )
    query_embedding = response.data[0].embedding

    client = get_client()
    result = client.rpc("buscar_decreto", {
        "query_embedding": query_embedding,
        "match_count": top_k,
        "match_threshold": 0.25,
    }).execute()

    chunks = result.data or []
    if not chunks:
        return ""

    parts = ["## CONTEXTO DEL DECRETO 1881/2021 (búsqueda semántica):\n"]

    for i, chunk in enumerate(chunks, 1):
        sim = round(chunk.get("similarity", 0) * 100, 1)
        tipo = chunk.get("tipo", "")
        cap = chunk.get("capitulo", "")
        meta = chunk.get("metadata", {}) or {}
        partida = meta.get("partida", "") if isinstance(meta, dict) else ""

        if tipo == "notas_capitulo":
            parts.append(f"### [{i}] Notas Cap.{cap} (relevancia: {sim}%)")
        elif tipo == "partida":
            parts.append(f"### [{i}] Partida {partida} Cap.{cap} (relevancia: {sim}%)")
        else:
            parts.append(f"### [{i}] {tipo} (relevancia: {sim}%)")

        parts.append(chunk.get("contenido", ""))
        parts.append("")

    return "\n".join(parts)


def obtener_notas_capitulo(capitulo: str) -> list[dict]:
    """Obtiene notas de un capítulo específico."""
    client = get_client()
    cap_ref = f"Capítulo {capitulo.zfill(2)}"
    result = client.table("notas_arancel").select("tipo, contenido").or_(
        f"referencia.eq.{cap_ref},tipo.eq.reglas_generales"
    ).execute()
    return result.data or []


def obtener_notas_seccion(seccion: str) -> list[dict]:
    """Obtiene notas de una sección."""
    client = get_client()
    result = client.table("notas_arancel").select("tipo, referencia, contenido").ilike(
        "referencia", f"%{seccion}%"
    ).execute()
    return result.data or []


def obtener_notas_para_clasificacion(capitulos: list[str]) -> str:
    """Obtiene las notas relevantes para una lista de capítulos y las formatea."""
    client = get_client()
    parts: list[str] = []
    seen: set[str] = set()

    # Reglas generales (siempre)
    reglas = client.table("notas_arancel").select("contenido").eq("tipo", "reglas_generales").execute()
    if reglas.data:
        parts.append("## Reglas Generales de Interpretación:\n" + reglas.data[0]["contenido"][:2000])

    for cap in capitulos:
        cap_str = cap.zfill(2)
        if cap_str in seen:
            continue
        seen.add(cap_str)

        cap_ref = f"Capítulo {cap_str}"
        result = client.table("notas_arancel").select("tipo, contenido").eq("referencia", cap_ref).execute()
        for nota in (result.data or []):
            label = {
                "capitulo": f"Notas del Capítulo {cap_str}",
                "complementaria_nacional": f"Notas complementarias nacionales - Cap. {cap_str}",
                "complementaria_nandina": f"Notas complementarias Nandina - Cap. {cap_str}",
            }.get(nota["tipo"], f"Nota Cap. {cap_str}")
            parts.append(f"\n### {label}:\n{nota['contenido']}")

    # Doctrina concordante (siempre incluir)
    doctrina = client.table("notas_arancel").select("referencia, contenido").eq("tipo", "doctrina_concordante").execute()
    for d in (doctrina.data or []):
        parts.append(f"\n### Doctrina Concordante — {d['referencia']}:\n{d['contenido']}")

    # Abreviaturas y símbolos (siempre incluir)
    abrev = client.table("notas_arancel").select("contenido").eq("tipo", "abreviaturas").execute()
    if abrev.data:
        parts.append(f"\n### Abreviaturas y Símbolos del Arancel:\n{abrev.data[0]['contenido']}")

    return "\n\n".join(parts)


def obtener_contexto_arancel_estructurado(ficha_tecnica: str, subpartidas_investigacion: list[str] = None) -> str:
    """Construye contexto del arancel desde la BD estructurada.

    Mucho más eficiente que enviar texto crudo del PDF.
    """
    parts: list[str] = []

    # 1. Si hay subpartidas del investigador, traer esas partidas completas
    partidas_vistas: set[str] = set()
    if subpartidas_investigacion:
        for sub in subpartidas_investigacion:
            partida = sub[:5] if len(sub) >= 5 else sub[:4]
            if partida in partidas_vistas:
                continue
            partidas_vistas.add(partida)
            entries = buscar_arancel_por_partida(partida)
            if entries:
                lines = [f"\n### Partida {partida} (del arancel vigente):"]
                for e in entries:
                    grv = f" | Gravamen: {e['gravamen']}%" if e.get('gravamen') is not None else ""
                    lines.append(f"  {e['codigo']} — {e['descripcion']}{grv}")
                parts.append("\n".join(lines))

    # 2. Buscar por descripción del producto
    resultados = buscar_arancel_por_descripcion(ficha_tecnica, limit=15)
    if resultados:
        # Traer partidas completas de los resultados
        for r in resultados:
            partida = r.get("partida", "")
            if partida and partida not in partidas_vistas:
                partidas_vistas.add(partida)
                entries = buscar_arancel_por_partida(partida)
                if entries:
                    lines = [f"\n### Partida {partida} (relevante por descripción):"]
                    for e in entries:
                        grv = f" | Gravamen: {e['gravamen']}%" if e.get('gravamen') is not None else ""
                        lines.append(f"  {e['codigo']} — {e['descripcion']}{grv}")
                    parts.append("\n".join(lines))

    if parts:
        header = "## SUBPARTIDAS DEL ARANCEL VIGENTE (Decreto 1881/2021 - datos exactos de la BD):\n"
        header += "⚠️ Estos datos son EXACTOS de la base de datos. Si un código aparece aquí, EXISTE.\n"
        return header + "\n".join(parts)

    return ""


# ── Lecciones aprendidas ──


def _generate_embedding(text: str) -> list[float] | None:
    """Genera embedding para un texto. Retorna None si falla."""
    import os as _os
    from openai import OpenAI as _OpenAI

    api_key = _os.environ.get("OPENAI_API_KEY") or _os.environ.get("OPENROUTER_API_KEY", "")
    base_url = None if _os.environ.get("OPENAI_API_KEY") else "https://openrouter.ai/api/v1"

    try:
        client = _OpenAI(api_key=api_key, base_url=base_url) if base_url else _OpenAI(api_key=api_key)
        response = client.embeddings.create(model="text-embedding-3-small", input=text[:4000])
        return response.data[0].embedding
    except Exception:
        return None


def guardar_leccion(
    regla: str,
    keywords: str,
    agente: str = "clasificador",
    subpartida: str = "",
    producto: str = "",
    fuente: str = "manual",
    clasificacion_id: str = "",
) -> dict:
    """Guarda una lección con embedding para búsqueda semántica."""
    client = get_client()

    # Texto para embedding: regla + producto + subpartida
    embed_text = f"{regla} {producto[:200]} {subpartida}"
    embedding = _generate_embedding(embed_text)

    data = {
        "regla": regla,
        "keywords": keywords,
        "agente": agente,
        "subpartida": subpartida,
        "producto": producto[:500] if producto else "",
        "fuente": fuente,
    }
    if clasificacion_id:
        data["clasificacion_id"] = clasificacion_id
    if embedding:
        data["embedding"] = embedding

    result = client.table("lecciones").insert(data).execute()
    return result.data[0] if result.data else data


def buscar_lecciones(ficha_tecnica: str, agente: str = "", limit: int = 8) -> list[dict]:
    """Busca lecciones relevantes usando búsqueda semántica + transversales."""
    client = get_client()
    results: list[dict] = []
    seen: set[str] = set()

    # 1. Búsqueda semántica con embedding
    embedding = _generate_embedding(ficha_tecnica)
    if embedding:
        try:
            semantic = client.rpc("buscar_lecciones_similares", {
                "query_embedding": embedding,
                "agente_filter": agente,
                "match_count": limit,
                "match_threshold": 0.30,
            }).execute()

            for l in (semantic.data or []):
                key = l["regla"][:50]
                if key not in seen:
                    seen.add(key)
                    results.append(l)
        except Exception:
            pass

    # 2. Lecciones transversales (protocolos, sin producto) como fallback
    if len(results) < limit:
        try:
            q = client.table("lecciones").select(
                "regla, subpartida, agente, producto, fuente"
            ).eq("producto", "").limit(limit - len(results))
            if agente:
                q = q.eq("agente", agente)
            transversales = q.execute()
            for l in (transversales.data or []):
                key = l["regla"][:50]
                if key not in seen:
                    seen.add(key)
                    results.append(l)
        except Exception:
            pass

    return results[:limit]


def extraer_lecciones_de_chat(clasificacion_id: str) -> list[dict]:
    """Extrae lecciones de correcciones hechas en el chat de una clasificación.

    Usa IA para analizar el historial de chat y extraer reglas aprendidas.
    """
    from openai import OpenAI
    from config import MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

    # Obtener clasificación y chat
    cls = obtener_clasificacion(clasificacion_id)
    if not cls:
        return []
    mensajes = obtener_chat_mensajes(clasificacion_id)
    if not mensajes:
        return []

    # Solo procesar si hay correcciones del usuario
    chat_text = "\n".join(f"{m['role']}: {m['content']}" for m in mensajes)

    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": (
                    "Analiza esta conversación de chat sobre una clasificación arancelaria. "
                    "Extrae SOLO las correcciones o reglas nuevas que el usuario enseñó. "
                    "Responde SOLO en formato JSON array. Si no hay correcciones, responde []. "
                    "Cada elemento: {\"regla\": \"texto corto de la regla\", \"agente\": \"clasificador|investigador|validador\", \"subpartida\": \"si aplica\"}"
                ),
            },
            {
                "role": "user",
                "content": f"Producto: {cls.get('ficha_tecnica', '')[:300]}\n\n"
                f"Clasificación original: {cls.get('subpartida', '')}\n\n"
                f"Chat:\n{chat_text}",
            },
        ],
    )

    import json as _json
    try:
        raw = response.choices[0].message.content.strip()
        # Extraer JSON del response
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        lecciones_data = _json.loads(raw)
        if not isinstance(lecciones_data, list):
            return []

        # Generar keywords del producto
        producto = cls.get("ficha_tecnica", "")
        words = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', producto.lower()))
        keywords = " ".join(sorted(words)[:20])

        saved = []
        for l in lecciones_data:
            if not l.get("regla"):
                continue
            s = guardar_leccion(
                regla=l["regla"],
                keywords=keywords,
                agente=l.get("agente", "clasificador"),
                subpartida=l.get("subpartida", cls.get("subpartida", "")),
                producto=producto[:300],
                fuente=f"chat sesión {clasificacion_id[:8]}",
                clasificacion_id=clasificacion_id,
            )
            saved.append(s)
        return saved
    except Exception:
        return []


def listar_lecciones(limit: int = 50) -> list[dict]:
    """Lista todas las lecciones."""
    client = get_client()
    result = client.table("lecciones").select("*").order("created_at", desc=True).limit(limit).execute()
    return result.data or []


def eliminar_leccion(leccion_id: str) -> bool:
    client = get_client()
    client.table("lecciones").delete().eq("id", leccion_id).execute()
    return True


# ── Agent Prompts ──


def get_agent_prompt(agent_key: str) -> str:
    """Obtiene el system prompt de un agente desde Supabase."""
    client = get_client()
    result = client.table("agent_prompts").select("system_prompt").eq("agent_key", agent_key).execute()
    if result.data:
        return result.data[0]["system_prompt"]
    return ""


def get_all_agent_prompts() -> list[dict]:
    """Obtiene todos los prompts de agentes."""
    client = get_client()
    result = client.table("agent_prompts").select("agent_key, label, system_prompt, updated_at").order("agent_key").execute()
    return result.data or []


def update_agent_prompt(agent_key: str, system_prompt: str) -> dict:
    """Actualiza el system prompt de un agente."""
    client = get_client()
    result = client.table("agent_prompts").update({
        "system_prompt": system_prompt,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("agent_key", agent_key).execute()
    return result.data[0] if result.data else {}


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
