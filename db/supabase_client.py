import os
import re
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client, create_client


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value and name == "SUPABASE_URL":
        value = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    if not value and name == "SUPABASE_SERVICE_ROLE_KEY":
        value = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class SupabaseBusinessDB:
    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        supabase_url = url or _require_env("SUPABASE_URL")
        service_key = key or _require_env("SUPABASE_SERVICE_ROLE_KEY")
        self.client: Client = create_client(supabase_url, service_key)
        self.bucket_name = os.getenv("SUPABASE_STORAGE_BUCKET", "images").strip() or "images"
        self.products_folder = os.getenv("SUPABASE_PRODUCTS_FOLDER", "products").strip() or "products"

    def upload_product_image_to_storage(
        self,
        product_id: str,
        image_bytes: bytes,
        extension: str = "jpg",
        content_type: str = "image/jpeg",
    ) -> str:
        safe_ext = (extension or "jpg").strip(".").lower()
        object_path = f"{self.products_folder}/{product_id}/{uuid4().hex}.{safe_ext}"
        self.client.storage.from_(self.bucket_name).upload(
            object_path,
            image_bytes,
            {"content-type": content_type, "upsert": "false"},
        )
        return self.client.storage.from_(self.bucket_name).get_public_url(object_path)

    # ---------- Products ----------
    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("products").insert(payload).execute()
        return result.data[0]

    def list_products(
        self,
        search: str | None = None,
        categoria: str | None = None,
        tipo: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query = self.client.table("products").select("*").limit(limit).order("created_at", desc=True)
        if search:
            cleaned = search.strip()
            # Buscar por nombre, referencia o slug (para soportar "VRC-CHS-005", "bota-chelsea-negra", etc.)
            query = query.or_(
                f"name.ilike.%{cleaned}%,ref.ilike.%{cleaned}%,slug.ilike.%{cleaned}%"
            )
        if categoria:
            query = query.eq("categoria", categoria.strip())
        if tipo:
            query = query.eq("tipo", tipo.strip())
        result = query.execute()
        return result.data or []

    def get_product(self, slug_or_id: str) -> dict[str, Any] | None:
        value = (slug_or_id or "").strip()
        if not value:
            return None

        # UUID -> id
        if len(value) == 36 and "-" in value:
            field = "id"
            result = self.client.table("products").select("*").eq(field, value).limit(1).execute()
            return result.data[0] if result.data else None

        # Ref tipo "VRC-CHS-005" -> ref
        if re.fullmatch(r"[A-Z]{2,10}-[A-Z]{2,10}-\d{2,6}", value.upper()):
            result = self.client.table("products").select("*").eq("ref", value.upper()).limit(1).execute()
            return result.data[0] if result.data else None

        # Default: slug
        result = self.client.table("products").select("*").eq("slug", value).limit(1).execute()
        return result.data[0] if result.data else None

    def update_product(self, slug_or_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        field = "id" if len(slug_or_id) == 36 and "-" in slug_or_id else "slug"
        self.client.table("products").update(changes).eq(field, slug_or_id).execute()
        return self.get_product(slug_or_id)

    def add_product_image(
        self, product_id: str, image_url: str, alt_text: str | None = None, position: int = 0
    ) -> dict[str, Any]:
        payload = {
            "product_id": product_id,
            "image_url": image_url,
            "alt_text": alt_text,
            "position": position,
        }
        result = self.client.table("product_images").insert(payload).execute()
        return result.data[0]

    def list_product_images(self, product_id: str) -> list[dict[str, Any]]:
        result = (
            self.client.table("product_images")
            .select("*")
            .eq("product_id", product_id)
            .order("position")
            .execute()
        )
        return result.data or []

    def update_product_image(self, image_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        self.client.table("product_images").update(changes).eq("id", image_id).execute()
        result = self.client.table("product_images").select("*").eq("id", image_id).limit(1).execute()
        return result.data[0] if result.data else None

    def delete_product_image(self, image_id: str) -> bool:
        result = self.client.table("product_images").delete().eq("id", image_id).execute()
        return bool(result.data)

    def reorder_product_images(self, product_id: str, image_ids_in_order: list[str]) -> list[dict[str, Any]]:
        for idx, image_id in enumerate(image_ids_in_order):
            self.client.table("product_images").update({"position": idx}).eq("id", image_id).eq(
                "product_id", product_id
            ).execute()
        return self.list_product_images(product_id)

    def add_product_feature(
        self, product_id: str, title: str, description: str, position: int = 0
    ) -> dict[str, Any]:
        payload = {
            "product_id": product_id,
            "title": title,
            "description": description,
            "position": position,
        }
        result = self.client.table("product_features").insert(payload).execute()
        return result.data[0]

    # ---------- Customers ----------
    def create_customer(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("customers").insert(payload).execute()
        return result.data[0]

    def find_customers(self, query_text: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        query = self.client.table("customers").select("*").limit(limit).order("created_at", desc=True)
        if query_text:
            cleaned = query_text.strip()
            query = query.or_(
                f"email.ilike.%{cleaned}%,full_name.ilike.%{cleaned}%,phone_number.ilike.%{cleaned}%,legal_id.ilike.%{cleaned}%"
            )
        result = query.execute()
        return result.data or []

    def update_customer(self, customer_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        self.client.table("customers").update(changes).eq("id", customer_id).execute()
        result = self.client.table("customers").select("*").eq("id", customer_id).limit(1).execute()
        return result.data[0] if result.data else None

    def create_shipping_address(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("shipping_addresses").insert(payload).execute()
        return result.data[0]

    # ---------- Orders ----------
    def create_order(self, order_payload: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
        order_result = self.client.table("orders").insert(order_payload).execute()
        created_order = order_result.data[0]
        order_id = created_order["id"]

        items_payload: list[dict[str, Any]] = []
        for item in items:
            row = dict(item)
            row["order_id"] = order_id
            items_payload.append(row)
        if items_payload:
            self.client.table("order_items").insert(items_payload).execute()

        return created_order

    def update_order_status(self, order_id: str, status: str) -> dict[str, Any] | None:
        self.client.table("orders").update({"status": status}).eq("id", order_id).execute()
        result = self.client.table("orders").select("*").eq("id", order_id).limit(1).execute()
        return result.data[0] if result.data else None

    def list_recent_orders(self, limit: int = 20) -> list[dict[str, Any]]:
        result = (
            self.client.table("orders")
            .select("*, customers(full_name, email)")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def list_notifyable_paid_orders_with_details(
        self, canonical_statuses: list[str], *, limit: int = 200
    ) -> list[dict[str, Any]]:
        """
        Recent orders whose status matches any of the given labels (case variants included).
        Includes nested customer, shipping address and line items.
        """
        variants: list[str] = []
        for s in canonical_statuses:
            t = (s or "").strip()
            if not t:
                continue
            for v in (t, t.upper(), t.lower(), t.capitalize()):
                if v not in variants:
                    variants.append(v)
        if not variants:
            return []
        result = (
            self.client.table("orders")
            .select(
                "*, "
                "customers!customer_id(*), "
                "shipping_addresses!shipping_address_id(*), "
                "order_items(*)"
            )
            .in_("status", variants)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def sales_summary(self, days: int = 7) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = (
            self.client.table("orders")
            .select("total_cents,status,created_at")
            .gte("created_at", since.isoformat())
            .execute()
        )
        rows = result.data or []
        completed_rows = [r for r in rows if str(r.get("status", "")).upper() in {"PAID", "COMPLETED", "DELIVERED"}]
        total_cents = sum(int(r.get("total_cents") or 0) for r in rows)
        completed_cents = sum(int(r.get("total_cents") or 0) for r in completed_rows)
        return {
            "window_days": days,
            "orders_count": len(rows),
            "completed_orders_count": len(completed_rows),
            "gross_total_cents": total_cents,
            "completed_total_cents": completed_cents,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
