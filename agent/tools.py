import json
from typing import Any

from db import SupabaseBusinessDB


def _to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _loads_json(value: str, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


class BusinessTools:
    def __init__(self, db: SupabaseBusinessDB | None = None) -> None:
        self.db = db or SupabaseBusinessDB()

    # ---------- Products ----------
    def list_products(
        self, search: str = "", categoria: str = "", tipo: str = "", limit: int = 20
    ) -> str:
        rows = self.db.list_products(
            search=search or None,
            categoria=categoria or None,
            tipo=tipo or None,
            limit=limit,
        )
        return _to_json(rows)

    def get_product(self, slug_or_id: str) -> str:
        row = self.db.get_product(slug_or_id)
        return _to_json(row or {"error": "Product not found"})

    def create_product(
        self,
        slug: str,
        name: str,
        price_cents: int,
        image_url: str,
        ref: str = "",
        description: str = "",
        availability: str = "available",
        categoria: str = "",
        tipo: str = "",
        sizes_json: str = "[]",
    ) -> str:
        payload = {
            "slug": slug,
            "name": name,
            "price_cents": int(price_cents),
            "image_url": image_url,
            "ref": ref or None,
            "description": description or None,
            "availability": availability or None,
            "categoria": categoria or None,
            "tipo": tipo or None,
            "sizes": _loads_json(sizes_json, []),
        }
        created = self.db.create_product(payload)
        return _to_json(created)

    def update_product(self, slug_or_id: str, changes_json: str) -> str:
        changes = _loads_json(changes_json, {})
        updated = self.db.update_product(slug_or_id, changes)
        return _to_json(updated or {"error": "Product not found or no changes applied"})

    def set_product_sizes(self, slug_or_id: str, sizes_json: str) -> str:
        sizes = _loads_json(sizes_json, [])
        updated = self.db.update_product(slug_or_id, {"sizes": sizes})
        return _to_json(updated or {"error": "Product not found"})

    def add_product_image(
        self, product_id: str, image_url: str, alt_text: str = "", position: int = 0
    ) -> str:
        created = self.db.add_product_image(
            product_id=product_id,
            image_url=image_url,
            alt_text=alt_text or None,
            position=position,
        )
        return _to_json(created)

    def list_product_images(self, product_id: str) -> str:
        rows = self.db.list_product_images(product_id)
        return _to_json(rows)

    def update_product_image(self, image_id: str, changes_json: str) -> str:
        changes = _loads_json(changes_json, {})
        updated = self.db.update_product_image(image_id, changes)
        return _to_json(updated or {"error": "Image not found or no changes applied"})

    def delete_product_image(self, image_id: str) -> str:
        deleted = self.db.delete_product_image(image_id)
        return _to_json({"deleted": deleted, "image_id": image_id})

    def reorder_product_images(self, product_id: str, image_ids_json: str) -> str:
        image_ids = _loads_json(image_ids_json, [])
        rows = self.db.reorder_product_images(product_id, image_ids)
        return _to_json(rows)

    def add_product_feature(
        self, product_id: str, title: str, description: str, position: int = 0
    ) -> str:
        created = self.db.add_product_feature(
            product_id=product_id,
            title=title,
            description=description,
            position=position,
        )
        return _to_json(created)

    # ---------- Customers ----------
    def create_customer(
        self,
        email: str,
        full_name: str,
        phone_number: str,
        legal_id: str,
        legal_id_type: str,
        phone_prefix: str = "+57",
    ) -> str:
        payload = {
            "email": email,
            "full_name": full_name,
            "phone_number": phone_number,
            "phone_prefix": phone_prefix,
            "legal_id": legal_id,
            "legal_id_type": legal_id_type,
        }
        created = self.db.create_customer(payload)
        return _to_json(created)

    def find_customers(self, query_text: str = "", limit: int = 20) -> str:
        rows = self.db.find_customers(query_text or None, limit=limit)
        return _to_json(rows)

    def update_customer(self, customer_id: str, changes_json: str) -> str:
        changes = _loads_json(changes_json, {})
        updated = self.db.update_customer(customer_id, changes)
        return _to_json(updated or {"error": "Customer not found or no changes applied"})

    def create_shipping_address(
        self,
        customer_id: str,
        address_line_1: str,
        city: str,
        region: str,
        phone_number: str,
        country: str = "CO",
    ) -> str:
        payload = {
            "customer_id": customer_id,
            "address_line_1": address_line_1,
            "city": city,
            "region": region,
            "country": country,
            "phone_number": phone_number,
        }
        created = self.db.create_shipping_address(payload)
        return _to_json(created)

    # ---------- Orders ----------
    def create_order(
        self,
        customer_id: str,
        shipping_address_id: str,
        payment_method: str,
        items_json: str,
        shipping_cents: int = 0,
        status: str = "PENDING",
    ) -> str:
        items = _loads_json(items_json, [])
        subtotal = sum(int(item.get("line_total_cents") or 0) for item in items)
        payload = {
            "customer_id": customer_id,
            "shipping_address_id": shipping_address_id,
            "payment_method": payment_method,
            "subtotal_cents": subtotal,
            "shipping_cents": int(shipping_cents),
            "total_cents": subtotal + int(shipping_cents),
            "status": status,
        }
        created = self.db.create_order(payload, items=items)
        return _to_json(created)

    def update_order_status(self, order_id: str, status: str) -> str:
        updated = self.db.update_order_status(order_id, status)
        return _to_json(updated or {"error": "Order not found"})

    def list_recent_orders(self, limit: int = 20) -> str:
        rows = self.db.list_recent_orders(limit=limit)
        return _to_json(rows)

    def sales_summary(self, days: int = 7) -> str:
        summary = self.db.sales_summary(days=days)
        return _to_json(summary)

    def available_actions(self) -> str:
        return _to_json(
            {
                "products": [
                    "list_products",
                    "get_product",
                    "create_product",
                    "update_product",
                    "set_product_sizes",
                    "add_product_image",
                    "list_product_images",
                    "update_product_image",
                    "delete_product_image",
                    "reorder_product_images",
                    "add_product_feature",
                ],
                "customers": [
                    "create_customer",
                    "find_customers",
                    "update_customer",
                    "create_shipping_address",
                ],
                "orders_sales": [
                    "create_order",
                    "update_order_status",
                    "list_recent_orders",
                    "sales_summary",
                ],
            }
        )
