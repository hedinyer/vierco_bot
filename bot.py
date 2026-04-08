#!/usr/bin/env python3

import asyncio
import json
import logging
import mimetypes
import os
import re
import time
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from agent import TelegramBusinessAgent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class PendingAction:
    original_message: str
    expires_at: datetime


@dataclass
class PendingImageFlow:
    mode: str  # "add" | "replace"
    product_ref: str | None = None
    image_id: str | None = None
    expires_at: datetime | None = None


PENDING_BY_CHAT: dict[int, PendingAction] = {}
PENDING_IMAGE_FLOW_BY_CHAT: dict[int, PendingImageFlow] = {}
ACTIVE_PRODUCT_REF_BY_CHAT: dict[int, str] = {}
CHAT_CONTEXT_BY_CHAT: dict[int, list[tuple[str, str]]] = {}
CUSTOM_RULES_BY_CHAT: dict[int, str] = {}
SKILLS_BY_CHAT: dict[int, list[dict[str, str]]] = {}
ACTIVE_SKILL_DIRS_BY_CHAT: dict[int, list[str]] = {}
CONFIRM_TTL_MINUTES = 10
WRITE_KEYWORDS = {
    "agrega",
    "agregar",
    "añade",
    "anade",
    "crea",
    "crear",
    "modifica",
    "modificar",
    "actualiza",
    "actualizar",
    "edita",
    "editar",
    "cambia",
    "cambiar",
    "elimina",
    "eliminar",
    "borra",
    "borrar",
    "setea",
    "set",
    "incrementa",
    "decrementa",
    "resta",
    "suma",
    "add",
    "create",
    "update",
    "delete",
    "remove",
}
READ_KEYWORDS = {
    "ver",
    "mostrar",
    "muestrame",
    "muéstrame",
    "dejame",
    "déjame",
    "dame",
    "consultar",
    "consulta",
    "info",
    "informacion",
    "detalles",
    "listar",
    "lista",
    "buscar",
    "busca",
    "inventario",
    "stock",
    "existencias",
    "tallas",
    "ficha",
}

agent: TelegramBusinessAgent | None = None
MAX_CONTEXT_TURNS = 12

# Throttle log when no subscriber chats exist yet
_NO_SALE_SUBSCRIBERS_LAST_LOG: float = 0.0

_DEFAULT_PAID_NOTIFY_STATUSES = ("PAID", "COMPLETED", "DELIVERED")


def _sale_notify_subscribers_path() -> Path:
    return Path(
        os.getenv("SALE_NOTIFY_SUBSCRIBER_CHATS_STATE", ".sale_notify_subscriber_chats.json")
    ).resolve()


def _load_sale_notify_chat_ids() -> set[int]:
    path = _sale_notify_subscribers_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data.get("chat_ids", [])
        if not isinstance(raw, list):
            return set()
        return {int(x) for x in raw}
    except Exception:
        logger.exception("No se pudo leer %s; avisos de venta sin destinatarios persistidos", path)
        return set()


def register_sale_notify_subscriber_chat(chat_id: int) -> None:
    """Persiste un chat para recibir avisos de nuevas ventas (llamar al interactuar con el bot)."""
    path = _sale_notify_subscribers_path()
    ids = _load_sale_notify_chat_ids()
    if chat_id in ids:
        return
    ids.add(chat_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"chat_ids": sorted(ids)}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Chat %s registrado para avisos de ventas.", chat_id)
    except Exception:
        logger.exception("No se pudo guardar suscriptor de avisos en %s", path)


def _paid_notify_statuses_from_env() -> list[str]:
    raw = os.getenv("PAID_ORDER_NOTIFY_STATUSES", "").strip()
    if not raw:
        return list(_DEFAULT_PAID_NOTIFY_STATUSES)
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def _embed_one(row: dict[str, Any], key: str) -> dict[str, Any] | None:
    val = row.get(key)
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, list) and val:
        first = val[0]
        return first if isinstance(first, dict) else None
    return None


def _money_cop(cents: int | None) -> str:
    v = int(cents) if cents is not None else 0
    return f"${v:,} COP"


def _agent_memory_path() -> Path:
    return Path("agent_history/agent_memory.md").resolve()


def _chat_customization_path() -> Path:
    return Path("agent_history/chat_customization.json").resolve()


def _load_chat_customizations() -> None:
    path = _chat_customization_path()
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rules = payload.get("custom_rules", {})
        skills = payload.get("skills", {})
        active_skill_dirs = payload.get("active_skill_dirs", {})
        if isinstance(rules, dict):
            for k, v in rules.items():
                if isinstance(v, str) and v.strip():
                    CUSTOM_RULES_BY_CHAT[int(k)] = v.strip()
        if isinstance(skills, dict):
            for k, rows in skills.items():
                if isinstance(rows, list):
                    normalized: list[dict[str, str]] = []
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        name = str(row.get("name", "")).strip()
                        source = str(row.get("source", "")).strip()
                        content = str(row.get("content", "")).strip()
                        if name and source and content:
                            normalized.append({"name": name, "source": source, "content": content})
                    if normalized:
                        SKILLS_BY_CHAT[int(k)] = normalized
        if isinstance(active_skill_dirs, dict):
            for k, rows in active_skill_dirs.items():
                if not isinstance(rows, list):
                    continue
                cleaned = [str(x).strip() for x in rows if str(x).strip()]
                if cleaned:
                    ACTIVE_SKILL_DIRS_BY_CHAT[int(k)] = cleaned
    except Exception:
        logger.exception("No se pudieron cargar personalizaciones de chat")


def _save_chat_customizations() -> None:
    path = _chat_customization_path()
    payload = {
        "custom_rules": {str(k): v for k, v in CUSTOM_RULES_BY_CHAT.items()},
        "skills": {str(k): v for k, v in SKILLS_BY_CHAT.items()},
        "active_skill_dirs": {str(k): v for k, v in ACTIVE_SKILL_DIRS_BY_CHAT.items()},
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("No se pudieron guardar personalizaciones de chat")


PROACTIVE_SKILL_DIR = "skills/proactive-agent-3.1.0"
PDF_GENERATOR_SKILL_DIR = "skills/pdf-generator-1.0.1"
UI_DESIGNER_SKILL_DIR = "skills/ui-designer-1.0.0"

_PDF_INTENT_KEYWORDS = (
    "pdf",
    "inventario",
    "factura",
    "cotiz",
    "presupuesto",
    "exportar a pdf",
    "generar pdf",
    "imprimir",
    "reporte",
    "documento",
    "catalogo",
    "catálogo",
    "boleta",
    "recibo",
    "remision",
    "remisión",
)


def _strip_yaml_frontmatter(md: str) -> str:
    text = (md or "").strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def _read_skill_snippet(rel_dir: str, max_chars: int) -> str:
    skill_path = (Path(rel_dir) / "SKILL.md").resolve()
    if not skill_path.exists():
        return ""
    try:
        raw = skill_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    body = _strip_yaml_frontmatter(raw)
    return body[:max_chars] if body else ""


def _is_pdf_generation_intent(text: str) -> bool:
    low = (text or "").lower()
    return any(k in low for k in _PDF_INTENT_KEYWORDS)


def _ordered_skill_dirs_for_runtime(chat_id: int, *, include_pdf_skills: bool) -> list[str]:
    """Proactive siempre primero; PDF/UI cuando aplique; luego el resto sin duplicar."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(rel: str) -> None:
        if rel in seen:
            return
        if not (Path(rel) / "SKILL.md").resolve().exists():
            return
        seen.add(rel)
        ordered.append(rel)

    add(PROACTIVE_SKILL_DIR)
    if include_pdf_skills:
        add(PDF_GENERATOR_SKILL_DIR)
        add(UI_DESIGNER_SKILL_DIR)
    for rel in ACTIVE_SKILL_DIRS_BY_CHAT.get(chat_id, []):
        add(rel)
    return ordered


def _build_runtime_personalization(chat_id: int, *, include_pdf_skills: bool = False) -> str:
    parts: list[str] = []
    custom_rule = CUSTOM_RULES_BY_CHAT.get(chat_id, "").strip()
    if custom_rule:
        parts.append(f"Operator custom behavior:\n{custom_rule}")
    skills = SKILLS_BY_CHAT.get(chat_id, [])
    if skills:
        skill_lines = ["Loaded skills (apply these patterns when useful):"]
        for idx, skill in enumerate(skills, start=1):
            skill_lines.append(f"{idx}. {skill.get('name', '')} ({skill.get('source', '')})")
            content = (skill.get("content", "") or "").strip()
            if content:
                skill_lines.append(content[:1200])
        parts.append("\n".join(skill_lines))

    for rel_dir in _ordered_skill_dirs_for_runtime(chat_id, include_pdf_skills=include_pdf_skills):
        if rel_dir == PROACTIVE_SKILL_DIR:
            max_chars = 12000
        elif rel_dir in (PDF_GENERATOR_SKILL_DIR, UI_DESIGNER_SKILL_DIR):
            max_chars = 4500
        else:
            max_chars = 2200
        snippet = _read_skill_snippet(rel_dir, max_chars)
        if snippet:
            label = (
                "BASE SKILL (obligatorio: patrones proactive-agent, mejora continua)"
                if rel_dir == PROACTIVE_SKILL_DIR
                else f"Local skill ({rel_dir})"
            )
            parts.append(f"{label}:\n{snippet}")
    return "\n\n".join(parts).strip()


def _download_skill_markdown(url: str) -> str:
    req = urllib.request.Request(url=url, headers={"User-Agent": "vierco-bot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    text = raw.decode("utf-8", errors="replace")
    return text.strip()


def _safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip().lower()).strip("-")
    return slug or "skill"


def _extract_skill_download_url_from_html(html: str) -> str | None:
    patterns = (
        r'https?://[^\s"\'<>]+SKILL\.md',
        r'https?://[^\s"\'<>]+\.md',
        r'https?://[^\s"\'<>]+\.zip',
    )
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _download_and_save_skill_to_folder(url: str, desired_name: str = "") -> dict[str, str]:
    skills_root = Path("skills").resolve()
    skills_root.mkdir(parents=True, exist_ok=True)
    source_url = url
    content = _download_skill_markdown(url)
    if "<html" in content.lower():
        extracted = _extract_skill_download_url_from_html(content)
        if extracted:
            source_url = extracted
            content = _download_skill_markdown(extracted)

    if desired_name.strip():
        folder_name = _safe_slug(desired_name)
    else:
        parsed = urlparse(source_url)
        folder_name = _safe_slug(Path(parsed.path).stem)
    target_dir = skills_root / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    skill_file = target_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return {"dir": str(target_dir), "source": source_url, "name": folder_name}


def _ensure_default_proactive_skill(chat_id: int) -> None:
    """Mantiene proactive-agent siempre en la lista persistida (orden: primero)."""
    rows = ACTIVE_SKILL_DIRS_BY_CHAT.setdefault(chat_id, [])
    if PROACTIVE_SKILL_DIR in rows:
        rows.remove(PROACTIVE_SKILL_DIR)
    rows.insert(0, PROACTIVE_SKILL_DIR)


def _append_agent_memory(role: str, text: str, *, chat_id: int | None = None, user_id: int | None = None) -> None:
    path = _agent_memory_path()
    ts = datetime.now(timezone.utc).isoformat()
    cid = str(chat_id) if chat_id is not None else "-"
    uid = str(user_id) if user_id is not None else "-"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(f"\n[{ts}] chat={cid} user={uid} role={role}\n")
            f.write(f"{text.strip()}\n")
    except Exception:
        logger.exception("No se pudo escribir memoria de agente en %s", path)


def _build_contextual_prompt(chat_id: int, text: str) -> str:
    history = CHAT_CONTEXT_BY_CHAT.get(chat_id, [])
    if not history:
        return text
    recent = history[-MAX_CONTEXT_TURNS:]
    lines: list[str] = ["Contexto reciente de esta conversacion:"]
    for role, msg in recent:
        lines.append(f"{role}: {msg}")
    lines.append("Mensaje actual del usuario:")
    lines.append(text)
    return "\n".join(lines)


def _remember_turn(chat_id: int, user_text: str, assistant_text: str) -> None:
    history = CHAT_CONTEXT_BY_CHAT.setdefault(chat_id, [])
    history.append(("usuario", user_text.strip()))
    history.append(("asistente", assistant_text.strip()))
    CHAT_CONTEXT_BY_CHAT[chat_id] = history[-MAX_CONTEXT_TURNS:]


async def _reply_and_log(update: Update, text: str) -> None:
    if not update.message:
        return
    await update.message.reply_text(text)
    _append_agent_memory(
        "assistant",
        text,
        chat_id=update.effective_chat.id if update.effective_chat else None,
        user_id=update.effective_user.id if update.effective_user else None,
    )


def _format_new_sale_message(order: dict[str, Any]) -> str:
    customer = _embed_one(order, "customers") or {}
    ship = _embed_one(order, "shipping_addresses") or {}
    items = order.get("order_items") or []
    if isinstance(items, dict):
        items = [items]

    lines: list[str] = [
        "Nueva compra (pago aprobado)",
        f"Pedido: {order.get('id', '')}",
        f"Estado: {order.get('status', '')}",
        f"Método de pago: {order.get('payment_method', '')}",
        "",
        "Cliente:",
        f"- {customer.get('full_name', '—')}",
        f"- {customer.get('email', '—')}",
        f"- {customer.get('phone_prefix', '')} {customer.get('phone_number', '')}".strip(),
        "",
        "Envío:",
        f"- Dirección: {ship.get('address_line_1', '—')}",
        f"- Ciudad: {ship.get('city', '—')}",
        f"- Departamento / región: {ship.get('region', '—')}",
        f"- País: {ship.get('country', '—')}",
        "",
        "Ítems:",
    ]
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("product_name", "—")
        size = it.get("size", "—")
        qty = it.get("quantity", 1)
        line_total = _money_cop(it.get("line_total_cents"))
        unit = _money_cop(it.get("unit_price_cents"))
        lines.append(f"- {name} | Talla: {size} | Cant: {qty} | P.u. {unit} | Subtotal línea: {line_total}")

    lines.extend(
        [
            "",
            f"Subtotal pedido: {_money_cop(order.get('subtotal_cents'))}",
            f"Envío: {_money_cop(order.get('shipping_cents'))}",
            f"TOTAL: {_money_cop(order.get('total_cents'))}",
        ]
    )
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n…(mensaje recortado)"
    return text


def _load_fallback_keys_from_apikey_md() -> None:
    """
    Carga valores de respaldo desde apikeys/apikey.md si faltan en entorno.
    """
    apikey_file = Path("apikeys/apikey.md")
    if not apikey_file.exists():
        return

    text = apikey_file.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("NEXT_PUBLIC_SUPABASE_URL=") and not os.getenv("SUPABASE_URL"):
            os.environ["SUPABASE_URL"] = line.split("=", 1)[1].strip()

        if (
            line.startswith("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=")
            and not os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        ):
            # Solo para entorno local/simple; en producción usa SERVICE_ROLE real.
            os.environ["SUPABASE_SERVICE_ROLE_KEY"] = line.split("=", 1)[1].strip()

        if "alibaba cloud studio api key" in line.lower() and not os.getenv("DASHSCOPE_API_KEY"):
            maybe_key = line.split()[-1].strip()
            if maybe_key.startswith("sk-"):
                os.environ["DASHSCOPE_API_KEY"] = maybe_key


def get_agent() -> TelegramBusinessAgent:
    global agent
    if agent is not None:
        return agent
    _load_fallback_keys_from_apikey_md()
    agent = TelegramBusinessAgent()
    return agent


def _is_probable_write_intent(text: str) -> bool:
    words = {w.strip(".,:;!?()[]{}").lower() for w in text.split()}
    low = text.lower()
    # Si el usuario explícitamente pide ver/consultar, priorizamos lectura.
    if words.intersection(READ_KEYWORDS) or any(p in low for p in ("quiero ver", "solo ver", "mostrar", "consulta")):
        return False
    if words.intersection(WRITE_KEYWORDS):
        return True
    # Heurísticas extra de escritura (evitar "inventario" porque suele ser lectura).
    patterns = (
        "nuevo producto",
        "new product",
        "change stock",
        "actualiza el inventario",
        "actualizar inventario",
        "ajusta el inventario",
        "modifica el inventario",
        "set stock",
        "pon el stock",
        "pon el inventario",
    )
    return any(p in low for p in patterns)


def _is_image_management_intent(text: str) -> bool:
    low = text.lower()
    has_image_word = any(w in low for w in ("imagen", "foto", "fotos"))
    has_add_or_change = any(
        w in low for w in ("agregar", "agrega", "añadir", "anadir", "subir", "cambiar", "reemplazar", "actualizar")
    )
    return has_image_word and has_add_or_change


def _extract_product_ref(text: str) -> str | None:
    # UUID
    uuid_match = re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", text, re.IGNORECASE
    )
    if uuid_match:
        return uuid_match.group(0)
    # Ref (ej: VRC-CHS-005)
    ref_match = re.search(r"\b[A-Z]{2,10}-[A-Z]{2,10}-\d{2,6}\b", text, re.IGNORECASE)
    if ref_match:
        return ref_match.group(0).upper()
    # slug after "producto"
    slug_match = re.search(r"(?:producto|product)\s+([a-z0-9][a-z0-9\-]{2,})", text.lower())
    if slug_match:
        return slug_match.group(1)
    return None


def _extract_product_name_hint(text: str) -> str | None:
    low = text.lower().strip()
    patterns = [
        r"(?:producto|product)\s+(.+)$",
        r"(?:de|del|para)\s+(.+)$",
    ]
    for pat in patterns:
        match = re.search(pat, low)
        if match:
            candidate = match.group(1).strip(" .,:;!?")
            if candidate:
                return candidate
    cleaned = re.sub(
        r"\b(quiero|agregar|agrega|añadir|anadir|subir|cambiar|reemplazar|actualizar|foto|fotos|imagen|imagenes|del|de|al|la|el)\b",
        " ",
        low,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;!?")
    return cleaned or None


def _extract_image_id(text: str) -> str | None:
    id_match = re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", text, re.IGNORECASE
    )
    return id_match.group(0) if id_match else None


def _clean_output(text: str) -> str:
    cleaned = text.replace("*", "").replace("`", "")
    # Limpieza ligera de encabezados markdown
    cleaned = cleaned.replace("### ", "").replace("## ", "").replace("# ", "")
    return cleaned.strip()


def _extract_generated_paths(text: str) -> list[Path]:
    """
    Detecta rutas de archivo en texto del agente y las normaliza al workspace.
    """
    workspace = Path.cwd().resolve()
    candidates = re.findall(r"(?:/[\w\-. /]+?\.\w{2,5}|\b[\w\-. /]+?\.\w{2,5}\b)", text or "")
    out: list[Path] = []
    for raw in candidates:
        token = raw.strip().strip(".,;:!?)(").strip("'\"")
        if not token:
            continue
        path = Path(token)
        if not path.is_absolute():
            path = (workspace / token).resolve()
        if path.exists() and path.is_file():
            # Solo permitimos enviar archivos dentro del workspace del bot.
            try:
                path.relative_to(workspace)
            except Exception:
                continue
            out.append(path)
    unique: list[Path] = []
    seen: set[str] = set()
    for p in out:
        key = str(p)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


async def _send_detected_files(update: Update, paths: list[Path]) -> None:
    if not update.message:
        return
    for path in paths[:5]:
        suffix = path.suffix.lower()
        with path.open("rb") as f:
            if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                await update.message.reply_photo(photo=f, caption=f"Archivo generado: {path.name}")
            elif suffix in {".mp4", ".mov", ".webm", ".mkv"}:
                await update.message.reply_video(video=f, caption=f"Archivo generado: {path.name}")
            else:
                await update.message.reply_document(document=f, filename=path.name, caption=f"Archivo generado: {path.name}")


def _resolve_product_by_name(current_agent: TelegramBusinessAgent, name_hint: str) -> tuple[dict | None, str | None]:
    hint = (name_hint or "").strip()
    if not hint:
        return None, "Necesito el nombre del producto."
    rows = current_agent.tools.db.list_products(search=hint, limit=10)
    if not rows:
        return None, f"No encontré productos que coincidan con '{hint}'."

    hint_low = hint.lower()
    exact = [p for p in rows if str(p.get("name", "")).lower() == hint_low]
    if len(exact) == 1:
        return exact[0], None
    if len(rows) == 1:
        return rows[0], None

    options = "\n".join(f"- {p.get('name')}" for p in rows[:5])
    return None, "Encontré varios productos con ese nombre. Dime cuál de estos quieres usar:\n" + options


def _resolve_product_any(
    current_agent: TelegramBusinessAgent, raw_hint: str | None, *, chat_id: int | None = None
) -> tuple[dict | None, str | None]:
    """
    Resuelve un producto usando (en orden):
    - producto activo del chat (si el usuario dice "ese producto"/"el producto")
    - id/slug/ref explícito en el texto
    - búsqueda por nombre/ref/slug vía list_products(search=...)
    """
    hint = (raw_hint or "").strip()
    low = hint.lower()

    if chat_id is not None and any(p in low for p in ("ese producto", "este producto", "el producto", "ese", "este")):
        active = ACTIVE_PRODUCT_REF_BY_CHAT.get(chat_id)
        if active:
            try:
                product = current_agent.tools.db.get_product(active)
            except Exception:
                product = None
            if product:
                return product, None

    ref = _extract_product_ref(hint) or (ACTIVE_PRODUCT_REF_BY_CHAT.get(chat_id) if chat_id is not None else None)
    if ref:
        try:
            product = current_agent.tools.db.get_product(ref)
        except Exception:
            product = None
        if product:
            return product, None

    if not hint:
        return None, "Necesito el nombre o referencia del producto."
    return _resolve_product_by_name(current_agent, hint)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if update.effective_chat:
        register_sale_notify_subscriber_chat(update.effective_chat.id)
        _ensure_default_proactive_skill(update.effective_chat.id)
        _save_chat_customizations()
    _append_agent_memory(
        "user",
        "/start",
        chat_id=update.effective_chat.id if update.effective_chat else None,
        user_id=update.effective_user.id if update.effective_user else None,
    )
    reply_text = (
        "Bot conectado.\n"
        "- Responde consultas y ejecuta cambios solicitados directamente.\n"
        "- Mantiene memoria de contexto de la conversacion.\n"
        "- Entrega archivos generados por chat (txt/pdf/imagen/video) si detecta rutas válidas.\n"
        "- Personalización por chat: /setrule, /rules, /clearrule.\n"
        "- Skills remotas: /skill_add <nombre> <url>, /skills, /skill_remove <n>.\n"
        "- Skills locales/descarga: /skill_enable_local <carpeta>, /skills_local, /skill_download <url> [nombre].\n"
        "- Skill base siempre activa: skills/proactive-agent-3.1.0 (mejora continua).\n"
        "- PDFs (inventario/factura/cotización/etc.): se cargan skills/pdf-generator-1.0.1 y skills/ui-designer-1.0.0 automáticamente."
    )
    await _reply_and_log(update, reply_text)


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if update.effective_chat:
        register_sale_notify_subscriber_chat(update.effective_chat.id)
    name = update.effective_user.first_name if update.effective_user else "there"
    user_text = "/hello"
    reply_text = f"Hello {name}"
    _append_agent_memory(
        "user",
        user_text,
        chat_id=update.effective_chat.id if update.effective_chat else None,
        user_id=update.effective_user.id if update.effective_user else None,
    )
    await _reply_and_log(update, reply_text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    if update.effective_chat:
        register_sale_notify_subscriber_chat(update.effective_chat.id)

    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    now = datetime.now(timezone.utc)
    current_agent = get_agent()
    _ensure_default_proactive_skill(chat_id)

    low = text.lower()
    if low.startswith("/setrule "):
        rule = text.split(" ", 1)[1].strip()
        CUSTOM_RULES_BY_CHAT[chat_id] = rule
        _save_chat_customizations()
        await _reply_and_log(update, "Regla personalizada guardada para este chat.")
        return
    if low == "/clearrule":
        CUSTOM_RULES_BY_CHAT.pop(chat_id, None)
        _save_chat_customizations()
        await _reply_and_log(update, "Regla personalizada eliminada para este chat.")
        return
    if low == "/rules":
        rule = CUSTOM_RULES_BY_CHAT.get(chat_id, "").strip()
        await _reply_and_log(update, f"Regla actual:\n{rule}" if rule else "No hay regla personalizada activa.")
        return
    if low.startswith("/skill_add "):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            await _reply_and_log(update, "Uso: /skill_add <nombre> <url_markdown>")
            return
        skill_name = parts[1].strip()
        url = parts[2].strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            await _reply_and_log(update, "La URL debe iniciar con http:// o https://")
            return
        try:
            content = await asyncio.to_thread(_download_skill_markdown, url)
        except Exception as exc:
            await _reply_and_log(update, f"No pude descargar la skill: {exc}")
            return
        if not content:
            await _reply_and_log(update, "La skill descargada está vacía.")
            return
        skills = SKILLS_BY_CHAT.setdefault(chat_id, [])
        skills.append({"name": skill_name, "source": url, "content": content[:4000]})
        _save_chat_customizations()
        await _reply_and_log(update, f"Skill '{skill_name}' agregada correctamente.")
        return
    if low == "/skills":
        skills = SKILLS_BY_CHAT.get(chat_id, [])
        if not skills:
            await _reply_and_log(update, "No tienes skills cargadas en este chat.")
            return
        lines = ["Skills activas:"]
        for idx, sk in enumerate(skills, start=1):
            lines.append(f"{idx}. {sk.get('name')} - {sk.get('source')}")
        await _reply_and_log(update, "\n".join(lines))
        return
    if low.startswith("/skill_remove "):
        idx_raw = text.split(" ", 1)[1].strip()
        if not idx_raw.isdigit():
            await _reply_and_log(update, "Uso: /skill_remove <numero>")
            return
        idx = int(idx_raw)
        skills = SKILLS_BY_CHAT.get(chat_id, [])
        if idx < 1 or idx > len(skills):
            await _reply_and_log(update, "Índice fuera de rango.")
            return
        removed = skills.pop(idx - 1)
        if not skills:
            SKILLS_BY_CHAT.pop(chat_id, None)
        _save_chat_customizations()
        await _reply_and_log(update, f"Skill eliminada: {removed.get('name')}")
        return
    if low.startswith("/skill_enable_local "):
        rel_dir = text.split(" ", 1)[1].strip().strip("/")
        skill_md = (Path(rel_dir) / "SKILL.md").resolve()
        if not skill_md.exists():
            await _reply_and_log(update, "No encontré SKILL.md en esa carpeta.")
            return
        rows = ACTIVE_SKILL_DIRS_BY_CHAT.setdefault(chat_id, [])
        if rel_dir not in rows:
            rows.append(rel_dir)
            _save_chat_customizations()
        await _reply_and_log(update, f"Skill local habilitada: {rel_dir}")
        return
    if low == "/skills_local":
        rows = ACTIVE_SKILL_DIRS_BY_CHAT.get(chat_id, [])
        if not rows:
            await _reply_and_log(update, "No hay skills locales activas en este chat.")
            return
        await _reply_and_log(update, "Skills locales activas:\n" + "\n".join(f"- {x}" for x in rows))
        return
    if low.startswith("/skill_download "):
        parts = text.split(" ", 2)
        if len(parts) < 2:
            await _reply_and_log(update, "Uso: /skill_download <url> [nombre]")
            return
        url = parts[1].strip()
        desired_name = parts[2].strip() if len(parts) >= 3 else ""
        if not (url.startswith("http://") or url.startswith("https://")):
            await _reply_and_log(update, "La URL debe iniciar con http:// o https://")
            return
        try:
            saved = await asyncio.to_thread(_download_and_save_skill_to_folder, url, desired_name)
        except Exception as exc:
            await _reply_and_log(update, f"No pude descargar/guardar la skill: {exc}")
            return
        rel_dir = str(Path(saved["dir"]).relative_to(Path.cwd()))
        rows = ACTIVE_SKILL_DIRS_BY_CHAT.setdefault(chat_id, [])
        if rel_dir not in rows:
            rows.append(rel_dir)
        _save_chat_customizations()
        await _reply_and_log(
            update,
            f"Skill descargada y habilitada.\n- Carpeta: {rel_dir}\n- Fuente: {saved['source']}",
        )
        return

    _append_agent_memory(
        "user",
        text,
        chat_id=chat_id,
        user_id=update.effective_user.id if update.effective_user else None,
    )

    pending_flow = PENDING_IMAGE_FLOW_BY_CHAT.get(chat_id)
    if pending_flow:
        if pending_flow.expires_at and pending_flow.expires_at < now:
            PENDING_IMAGE_FLOW_BY_CHAT.pop(chat_id, None)
            await _reply_and_log(update, "El flujo de imagen expiró. Vuelve a intentarlo.")
            return

        if pending_flow.product_ref is None:
            product_ref = _extract_product_ref(text)
            try:
                product, err = _resolve_product_any(current_agent, text, chat_id=chat_id)
                if err:
                    await _reply_and_log(update, err)
                    return
            except Exception as exc:
                await _reply_and_log(update, f"No pude validar el producto: {exc}")
                return
            if not product:
                await _reply_and_log(update, "No encontré ese producto. Dime el nombre exacto del producto.")
                return
            pending_flow.product_ref = product["id"]
            ACTIVE_PRODUCT_REF_BY_CHAT[chat_id] = product["id"]

            if pending_flow.mode == "replace":
                images = current_agent.tools.db.list_product_images(product["id"])
                if not images:
                    await _reply_and_log(update,
                        "Ese producto no tiene imágenes registradas. Envía una foto ahora y la agrego."
                    )
                    pending_flow.mode = "add"
                    return
                lines = ["Estas son las imágenes actuales. Envíame el ID de la imagen que quieres reemplazar:"]
                for img in images[:10]:
                    lines.append(f"- ID: {img.get('id')} | pos: {img.get('position')} | url: {img.get('image_url')}")
                await _reply_and_log(update, "\n".join(lines))
                return

            await _reply_and_log(update,
                "Perfecto. Ahora sube la foto desde Telegram (álbum o cámara) y la agrego al producto."
            )
            return

        if pending_flow.mode == "replace" and pending_flow.image_id is None:
            image_id = _extract_image_id(text)
            if not image_id:
                await _reply_and_log(update, "Envíame un ID de imagen válido (UUID) para reemplazar.")
                return
            pending_flow.image_id = image_id
            await _reply_and_log(update, "Listo. Ahora sube la nueva foto y reemplazo esa imagen.")
            return

    if _is_image_management_intent(text):
        mode = "replace" if any(k in text.lower() for k in ("cambiar", "reemplazar", "actualizar")) else "add"
        product_ref = _extract_product_ref(text) or ACTIVE_PRODUCT_REF_BY_CHAT.get(chat_id)
        if not product_ref:
            name_hint = _extract_product_name_hint(text)
            if name_hint:
                try:
                    by_name, err = _resolve_product_by_name(current_agent, name_hint)
                    if not err and by_name:
                        product_ref = by_name["id"]
                except Exception as exc:
                    await _reply_and_log(update, f"No pude validar el producto: {exc}")
                    return
        PENDING_IMAGE_FLOW_BY_CHAT[chat_id] = PendingImageFlow(
            mode=mode,
            product_ref=product_ref,
            expires_at=now + timedelta(minutes=CONFIRM_TTL_MINUTES),
        )

        if product_ref:
            try:
                product = current_agent.tools.db.get_product(product_ref)
            except Exception as exc:
                await _reply_and_log(update, f"No pude validar el producto: {exc}")
                return
            if not product:
                await _reply_and_log(update, "No encontré ese producto. Dime el nombre exacto del producto.")
                return
            ACTIVE_PRODUCT_REF_BY_CHAT[chat_id] = product_ref
            if mode == "replace":
                images = current_agent.tools.db.list_product_images(product["id"])
                if not images:
                    await _reply_and_log(update,
                        "Ese producto no tiene imágenes registradas. Envía una foto ahora y la agrego."
                    )
                    PENDING_IMAGE_FLOW_BY_CHAT[chat_id].mode = "add"
                    return
                lines = ["Estas son las imágenes actuales. Envíame el ID de la imagen que quieres reemplazar:"]
                for img in images[:10]:
                    lines.append(f"- ID: {img.get('id')} | pos: {img.get('position')} | url: {img.get('image_url')}")
                await _reply_and_log(update, "\n".join(lines))
            else:
                await _reply_and_log(update,
                    "Perfecto. Ahora sube la foto desde Telegram (álbum o cámara) y la agrego al producto."
                )
            return

        if mode == "replace":
            await _reply_and_log(update,
                "No tengo un producto activo en este chat.\n"
                "Primero indícame una vez el nombre del producto, y luego ya podrás subir/cambiar fotos sin repetirlo."
            )
        else:
            await _reply_and_log(update,
                "No tengo un producto activo en este chat.\n"
                "Primero indícame una vez el nombre del producto, y luego ya podrás agregar fotos sin repetirlo."
            )
        return

    # Si el mensaje parece estar nombrando un producto, lo dejamos activo para próximas referencias ("ese producto").
    referenced_product = _extract_product_ref(text)
    if referenced_product:
        try:
            resolved = current_agent.tools.db.get_product(referenced_product)
        except Exception:
            resolved = None
        if resolved:
            ACTIVE_PRODUCT_REF_BY_CHAT[chat_id] = resolved["id"]

    try:
        # Si el usuario pide inventario/stock/tallas sin especificar, usamos el producto activo.
        if any(k in low for k in ("inventario", "stock", "existencias", "tallas")) and not _extract_product_ref(text):
            active_id = ACTIVE_PRODUCT_REF_BY_CHAT.get(chat_id)
            if active_id:
                try:
                    product = current_agent.tools.db.get_product(active_id)
                except Exception:
                    product = None
                if product and product.get("name"):
                    text = f"{text} del producto {product.get('name')}"
        contextual_prompt = _build_contextual_prompt(chat_id, text)
        runtime_instructions = _build_runtime_personalization(
            chat_id, include_pdf_skills=_is_pdf_generation_intent(text)
        )
        response = await asyncio.to_thread(
            current_agent.run,
            str(chat_id),
            contextual_prompt,
            True,
            runtime_instructions,
        )
    except Exception as exc:
        logger.exception("Error in agent run")
        await _reply_and_log(update,
            "Error procesando tu solicitud. Revisa variables de entorno:\n"
            "- SUPABASE_URL\n"
            "- SUPABASE_SERVICE_ROLE_KEY\n"
            "- DASHSCOPE_API_KEY\n"
            f"Detalle: {exc}"
        )
        return
    cleaned = _clean_output(response)
    _remember_turn(chat_id, text, cleaned)
    await _reply_and_log(update, cleaned)
    generated = _extract_generated_paths(f"{response}\n{cleaned}")
    if generated:
        await _send_detected_files(update, generated)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return

    if update.effective_chat:
        register_sale_notify_subscriber_chat(update.effective_chat.id)
    _append_agent_memory(
        "user",
        "[photo_uploaded]",
        chat_id=update.effective_chat.id if update.effective_chat else None,
        user_id=update.effective_user.id if update.effective_user else None,
    )

    chat_id = update.effective_chat.id
    pending_flow = PENDING_IMAGE_FLOW_BY_CHAT.get(chat_id)
    if not pending_flow:
        await _reply_and_log(update,
            "Recibí la foto. Si quieres gestionarla, primero escribe algo como:\n"
            "- 'quiero agregar foto al producto <slug>'\n"
            "- 'quiero cambiar foto del producto <slug>'"
        )
        return

    if not pending_flow.product_ref:
        await _reply_and_log(update, "Primero necesito el slug o ID del producto.")
        return

    current_agent = get_agent()
    try:
        product = current_agent.tools.db.get_product(pending_flow.product_ref)
    except Exception as exc:
        await _reply_and_log(update, f"No pude consultar el producto: {exc}")
        return
    if not product:
        await _reply_and_log(update, "No encontré ese producto. Reenvía el nombre del producto.")
        return
    ACTIVE_PRODUCT_REF_BY_CHAT[chat_id] = pending_flow.product_ref

    # Tomamos la mejor resolución enviada por Telegram.
    photo = update.message.photo[-1]
    tg_file = await photo.get_file()
    file_path = tg_file.file_path or ""
    guessed_type = mimetypes.guess_type(file_path)[0] or "image/jpeg"
    ext = (file_path.rsplit(".", 1)[-1] if "." in file_path else "jpg").lower()
    file_bytes = bytes(await tg_file.download_as_bytearray())

    try:
        storage_url = current_agent.tools.db.upload_product_image_to_storage(
            product_id=product["id"],
            image_bytes=file_bytes,
            extension=ext,
            content_type=guessed_type,
        )

        if pending_flow.mode == "replace":
            if not pending_flow.image_id:
                await _reply_and_log(update, "Primero dime qué imagen quieres reemplazar (ID).")
                return
            updated = current_agent.tools.db.update_product_image(
                pending_flow.image_id, {"image_url": storage_url}
            )
            if not updated:
                await _reply_and_log(update, "No pude actualizar: no encontré esa imagen ID.")
                return
            await _reply_and_log(update,
                f"Imagen reemplazada correctamente.\nImagen ID: {pending_flow.image_id}\nProducto: {product.get('name')}"
            )
        else:
            created = current_agent.tools.db.add_product_image(
                product_id=product["id"],
                image_url=storage_url,
                alt_text=product.get("name"),
                position=0,
            )
            await _reply_and_log(update,
                f"Imagen agregada correctamente.\nImagen ID: {created.get('id')}\nProducto: {product.get('name')}"
            )
    except Exception as exc:
        await _reply_and_log(update, f"No pude guardar la imagen: {exc}")
        return
    finally:
        PENDING_IMAGE_FLOW_BY_CHAT.pop(chat_id, None)


async def _paid_orders_watcher(application: Application) -> None:
    global _NO_SALE_SUBSCRIBERS_LAST_LOG
    state_path = Path(os.getenv("NOTIFIED_PAID_ORDERS_STATE", ".notified_paid_order_ids.json")).resolve()
    poll_s = max(5, int(os.getenv("PAID_ORDERS_POLL_SECONDS", "20")))
    fetch_limit = max(20, int(os.getenv("PAID_ORDERS_FETCH_LIMIT", "200")))
    statuses = _paid_notify_statuses_from_env()

    def load_ids() -> set[str]:
        if not state_path.exists():
            return set()
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            raw = data.get("ids", [])
            return {str(x) for x in raw} if isinstance(raw, list) else set()
        except Exception:
            logger.exception("Could not read %s; starting with empty notified set", state_path)
            return set()

    def save_ids(ids: set[str]) -> None:
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"ids": sorted(ids)}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Could not write notified order state to %s", state_path)

    notified = load_ids()
    seed_existing = len(notified) == 0
    _load_fallback_keys_from_apikey_md()

    logger.info(
        "Paid-order watcher active (poll every %ss, statuses=%s, state=%s)",
        poll_s,
        ",".join(statuses),
        state_path,
    )

    while True:
        try:
            db = get_agent().tools.db
            orders = await asyncio.to_thread(
                db.list_notifyable_paid_orders_with_details,
                statuses,
                limit=fetch_limit,
            )
            paid_set = {s.upper() for s in statuses}
            paid_rows = [
                o
                for o in orders
                if o.get("id") and str(o.get("status", "")).strip().upper() in paid_set
            ]

            if seed_existing:
                for o in paid_rows:
                    oid = str(o.get("id", ""))
                    if oid:
                        notified.add(oid)
                save_ids(notified)
                seed_existing = False
                logger.info(
                    "Primera ejecución: %d pedidos ya pagados registrados sin enviar aviso.",
                    len(notified),
                )
            else:
                targets = _load_sale_notify_chat_ids()
                pending_sales = [
                    o for o in paid_rows if str(o.get("id", "")) and str(o["id"]) not in notified
                ]
                if not targets:
                    if pending_sales:
                        now = time.monotonic()
                        if now - _NO_SALE_SUBSCRIBERS_LAST_LOG > 300:
                            logger.warning(
                                "Hay %d venta(s) sin notificar pero ningún chat registrado. "
                                "Escribe /start o cualquier mensaje al bot para registrar tu chat.",
                                len(pending_sales),
                            )
                            _NO_SALE_SUBSCRIBERS_LAST_LOG = now
                else:
                    for o in pending_sales:
                        oid = str(o.get("id", ""))
                        text = _format_new_sale_message(o)
                        any_ok = False
                        for cid in targets:
                            try:
                                await application.bot.send_message(chat_id=cid, text=text)
                                any_ok = True
                            except Exception:
                                logger.exception(
                                    "No se pudo enviar aviso de venta del pedido %s al chat %s", oid, cid
                                )
                        if any_ok:
                            notified.add(oid)
                            save_ids(notified)
        except Exception:
            logger.exception("Fallo al consultar pedidos pagados para avisos")

        await asyncio.sleep(poll_s)


async def _post_init(application: Application) -> None:
    asyncio.create_task(_paid_orders_watcher(application))


def main() -> None:
    os.environ.setdefault("VIERCO_WORKSPACE_ROOT", str(Path.cwd().resolve()))
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        token = "8560443034:AAGaDYgab47RbD8REFiQnncajFC8Ocpt7q8"
        logger.warning("Using fallback TELEGRAM_BOT_TOKEN hardcoded in bot.py")

    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(_post_init)
        .build()
    )
    _load_chat_customizations()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(MessageHandler(filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Starting Telegram business agent bot...")
    app.run_polling()


if __name__ == "__main__":
    main()