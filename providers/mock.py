"""Mock 数据源：把 data/products.csv 里的种子商品当作『数据源』暴露出去。

保持既有 Mock 演示能力不变：本地开发默认仍是 mock，行为与之前完全一致
（唯一区别是种子数据现在经过统一适配层，为接入真实数据做铺垫）。
"""
from __future__ import annotations

from pathlib import Path

from core.config import DATA_DIR
from providers.base import FetchStats, NormalizedProduct, ProductProvider

_CSV_PATH = DATA_DIR / "products.csv"


class MockProductProvider:
    source = "mock"

    def __init__(self, csv_path: Path | str | None = None) -> None:
        self.csv_path = Path(csv_path or _CSV_PATH)

    # ------------------------------------------------------------------
    # 读取（与 database.db.seed_from_csv 一致，但输出稳定元数据）
    # ------------------------------------------------------------------
    def _rows(self) -> list[dict]:
        import csv

        with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def fetch_products(self, keyword: str = "", limit: int = 50) -> tuple[list[NormalizedProduct], FetchStats]:
        rows = self._rows()
        matched: list[NormalizedProduct] = []
        kw = (keyword or "").strip()
        for r in rows:
            if kw and not self._hit(r, kw):
                continue
            matched.append(self._to_normalized(r))
            if len(matched) >= limit:
                break
        stats = FetchStats(
            fetched=len(matched),
            requested=limit,
            messages=[f"mock 种子数据命中 {len(matched)} 条" + (f"（关键词「{kw}」）" if kw else "（全量）")],
        )
        # mock 数据字段齐全，不做真实性标记
        return matched, stats

    @staticmethod
    def _hit(r: dict, kw: str) -> bool:
        haystack = " ".join(
            str(r.get(k, "")) for k in ("name", "brand", "category", "tags", "description", "standard_code")
        )
        return kw in haystack

    @staticmethod
    def _to_normalized(r: dict) -> NormalizedProduct:
        return NormalizedProduct(
            external_id=str(r["id"]),
            name=r["name"],
            category=r.get("category", ""),
            brand=r.get("brand", ""),
            price=float(r.get("price", 0)),
            rating=float(r.get("rating", 0)),
            sales=int(r.get("sales", 0)),
            stock=int(r.get("stock", 0)),
            shop=r.get("shop", ""),
            shop_type=r.get("shop_type", ""),
            material=r.get("material", ""),
            standard_code=(r.get("standard_code") or "").strip(),
            tags=[t for t in str(r.get("tags", "")).split() if t],
            description=r.get("description", ""),
            source="mock",
            url=r.get("url", ""),
            image=r.get("image", ""),
        )

