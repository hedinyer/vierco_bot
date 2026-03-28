#!/usr/bin/env python3

import asyncio
import json
import logging
import mimetypes
import os
import re
import time
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
    v = (int(cents) if cents is not None else 0) / 100.0
    if abs(v - round(v)) < 1e-9:
        return f"${int(round(v)):,} COP"
    return f"${v:,.2f} COP"


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
    await update.message.reply_text(
        "Bot conectado.\n"
        "- Preguntas/consultas: se responden directo.\n"
        "- Cambios en base de datos: te pido confirmacion con 'confirmar'."
    )


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if update.effective_chat:
        register_sale_notify_subscriber_chat(update.effective_chat.id)
    name = update.effective_user.first_name if update.effective_user else "there"
    await update.message.reply_text(f"Hello {name}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    if update.effective_chat:
        register_sale_notify_subscriber_chat(update.effective_chat.id)

    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    now = datetime.now(timezone.utc)
    current_agent = get_agent()

    pending_flow = PENDING_IMAGE_FLOW_BY_CHAT.get(chat_id)
    if pending_flow:
        if pending_flow.expires_at and pending_flow.expires_at < now:
            PENDING_IMAGE_FLOW_BY_CHAT.pop(chat_id, None)
            await update.message.reply_text("El flujo de imagen expiró. Vuelve a intentarlo.")
            return

        if pending_flow.product_ref is None:
            product_ref = _extract_product_ref(text)
            try:
                product, err = _resolve_product_any(current_agent, text, chat_id=chat_id)
                if err:
                    await update.message.reply_text(err)
                    return
            except Exception as exc:
                await update.message.reply_text(f"No pude validar el producto: {exc}")
                return
            if not product:
                await update.message.reply_text("No encontré ese producto. Dime el nombre exacto del producto.")
                return
            pending_flow.product_ref = product["id"]
            ACTIVE_PRODUCT_REF_BY_CHAT[chat_id] = product["id"]

            if pending_flow.mode == "replace":
                images = current_agent.tools.db.list_product_images(product["id"])
                if not images:
                    await update.message.reply_text(
                        "Ese producto no tiene imágenes registradas. Envía una foto ahora y la agrego."
                    )
                    pending_flow.mode = "add"
                    return
                lines = ["Estas son las imágenes actuales. Envíame el ID de la imagen que quieres reemplazar:"]
                for img in images[:10]:
                    lines.append(f"- ID: {img.get('id')} | pos: {img.get('position')} | url: {img.get('image_url')}")
                await update.message.reply_text("\n".join(lines))
                return

            await update.message.reply_text(
                "Perfecto. Ahora sube la foto desde Telegram (álbum o cámara) y la agrego al producto."
            )
            return

        if pending_flow.mode == "replace" and pending_flow.image_id is None:
            image_id = _extract_image_id(text)
            if not image_id:
                await update.message.reply_text("Envíame un ID de imagen válido (UUID) para reemplazar.")
                return
            pending_flow.image_id = image_id
            await update.message.reply_text("Listo. Ahora sube la nueva foto y reemplazo esa imagen.")
            return

    if text.lower() == "confirmar":
        pending = PENDING_BY_CHAT.get(chat_id)
        if not pending:
            await update.message.reply_text("No hay ninguna accion pendiente para confirmar.")
            return
        if pending.expires_at < now:
            PENDING_BY_CHAT.pop(chat_id, None)
            await update.message.reply_text("La accion pendiente expiro. Vuelve a enviar tu solicitud.")
            return

        await update.message.reply_text("Confirmado. Ejecutando accion...")
        try:
            response = await asyncio.to_thread(
                current_agent.run,
                str(chat_id),
                pending.original_message,
                True,
            )
        except Exception as exc:
            logger.exception("Error executing confirmed action")
            await update.message.reply_text(f"Error ejecutando la accion: {exc}")
            return
        finally:
            PENDING_BY_CHAT.pop(chat_id, None)

        await update.message.reply_text(_clean_output(response))
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
                    await update.message.reply_text(f"No pude validar el producto: {exc}")
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
                await update.message.reply_text(f"No pude validar el producto: {exc}")
                return
            if not product:
                await update.message.reply_text("No encontré ese producto. Dime el nombre exacto del producto.")
                return
            ACTIVE_PRODUCT_REF_BY_CHAT[chat_id] = product_ref
            if mode == "replace":
                images = current_agent.tools.db.list_product_images(product["id"])
                if not images:
                    await update.message.reply_text(
                        "Ese producto no tiene imágenes registradas. Envía una foto ahora y la agrego."
                    )
                    PENDING_IMAGE_FLOW_BY_CHAT[chat_id].mode = "add"
                    return
                lines = ["Estas son las imágenes actuales. Envíame el ID de la imagen que quieres reemplazar:"]
                for img in images[:10]:
                    lines.append(f"- ID: {img.get('id')} | pos: {img.get('position')} | url: {img.get('image_url')}")
                await update.message.reply_text("\n".join(lines))
            else:
                await update.message.reply_text(
                    "Perfecto. Ahora sube la foto desde Telegram (álbum o cámara) y la agrego al producto."
                )
            return

        if mode == "replace":
            await update.message.reply_text(
                "No tengo un producto activo en este chat.\n"
                "Primero indícame una vez el nombre del producto, y luego ya podrás subir/cambiar fotos sin repetirlo."
            )
        else:
            await update.message.reply_text(
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

    if _is_probable_write_intent(text):
        PENDING_BY_CHAT[chat_id] = PendingAction(
            original_message=text,
            expires_at=now + timedelta(minutes=CONFIRM_TTL_MINUTES),
        )
        await update.message.reply_text(
            "Detecte una accion de escritura (crear/actualizar/eliminar datos).\n"
            "Responde con 'confirmar' para ejecutarla, o envia un nuevo mensaje para reemplazarla."
        )
        return

    try:
        # Si el usuario pide inventario/stock/tallas sin especificar, usamos el producto activo.
        low = text.lower()
        if any(k in low for k in ("inventario", "stock", "existencias", "tallas")) and not _extract_product_ref(text):
            active_id = ACTIVE_PRODUCT_REF_BY_CHAT.get(chat_id)
            if active_id:
                try:
                    product = current_agent.tools.db.get_product(active_id)
                except Exception:
                    product = None
                if product and product.get("name"):
                    text = f"{text} del producto {product.get('name')}"

        response = await asyncio.to_thread(current_agent.run, str(chat_id), text, False)
    except Exception as exc:
        logger.exception("Error in read-only agent run")
        await update.message.reply_text(
            "Error procesando tu solicitud. Revisa variables de entorno:\n"
            "- SUPABASE_URL\n"
            "- SUPABASE_SERVICE_ROLE_KEY\n"
            "- DASHSCOPE_API_KEY\n"
            f"Detalle: {exc}"
        )
        return
    await update.message.reply_text(_clean_output(response))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return

    if update.effective_chat:
        register_sale_notify_subscriber_chat(update.effective_chat.id)

    chat_id = update.effective_chat.id
    pending_flow = PENDING_IMAGE_FLOW_BY_CHAT.get(chat_id)
    if not pending_flow:
        await update.message.reply_text(
            "Recibí la foto. Si quieres gestionarla, primero escribe algo como:\n"
            "- 'quiero agregar foto al producto <slug>'\n"
            "- 'quiero cambiar foto del producto <slug>'"
        )
        return

    if not pending_flow.product_ref:
        await update.message.reply_text("Primero necesito el slug o ID del producto.")
        return

    current_agent = get_agent()
    try:
        product = current_agent.tools.db.get_product(pending_flow.product_ref)
    except Exception as exc:
        await update.message.reply_text(f"No pude consultar el producto: {exc}")
        return
    if not product:
        await update.message.reply_text("No encontré ese producto. Reenvía el nombre del producto.")
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
                await update.message.reply_text("Primero dime qué imagen quieres reemplazar (ID).")
                return
            updated = current_agent.tools.db.update_product_image(
                pending_flow.image_id, {"image_url": storage_url}
            )
            if not updated:
                await update.message.reply_text("No pude actualizar: no encontré esa imagen ID.")
                return
            await update.message.reply_text(
                f"Imagen reemplazada correctamente.\nImagen ID: {pending_flow.image_id}\nProducto: {product.get('name')}"
            )
        else:
            created = current_agent.tools.db.add_product_image(
                product_id=product["id"],
                image_url=storage_url,
                alt_text=product.get("name"),
                position=0,
            )
            await update.message.reply_text(
                f"Imagen agregada correctamente.\nImagen ID: {created.get('id')}\nProducto: {product.get('name')}"
            )
    except Exception as exc:
        await update.message.reply_text(f"No pude guardar la imagen: {exc}")
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
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Starting Telegram business agent bot...")
    app.run_polling()


if __name__ == "__main__":
    main()