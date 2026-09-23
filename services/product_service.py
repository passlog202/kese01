"""商品服务：商品检索、统计与收藏行为封装。"""
from __future__ import annotations

from database import db
from core.models import Product, RecommendQuery


def list_products(category: str | None = None, keyword: str | None = None) -> list[Product]:
    products = db.get_all_products()
    if category:
        products = [p for p in products if p.category == category]
    if keyword:
        kw = keyword.strip()
        products = [
            p for p in products
            if kw in p.name or kw in p.brand or kw in p.description
            or any(kw in t for t in p.tags)
        ]
    return products


def product_categories(products: list[Product]) -> list[str]:
    seen: list[str] = []
    for p in products:
        if p.category not in seen:
            seen.append(p.category)
    return seen


def get_product(pid: int):
    return db.get_product(pid)
