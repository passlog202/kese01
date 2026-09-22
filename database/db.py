"""SQLite 数据访问层。

只使用 Python 标准库 sqlite3（不引入 SQLAlchemy），
提供建表、种子导入、产品查询、推荐/浏览历史、收藏等基础操作。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import DB_PATH, DATA_DIR
from core.models import Product

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    category      TEXT NOT NULL,
    brand         TEXT NOT NULL,
    price         REAL NOT NULL,
    rating        REAL NOT NULL,
    sales         INTEGER NOT NULL,
    stock         INTEGER NOT NULL,
    shop          TEXT NOT NULL,
    shop_type     TEXT NOT NULL,
    material      TEXT NOT NULL,
    standard_code TEXT NOT NULL DEFAULT '',
    tags          TEXT NOT NULL DEFAULT '',
    description   TEXT NOT NULL DEFAULT '',
    source        TEXT NOT NULL DEFAULT 'mock',
    url           TEXT NOT NULL DEFAULT '',
    image         TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query_json  TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS browse_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """建表（若不存在）。"""
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_from_csv(csv_path: Optional[Path] = None) -> int:
    """用 data/products.csv 重建商品表（全新灌入，保证可重复）。返回导入条数。"""
    import csv as _csv

    csv_path = csv_path or (DATA_DIR / "products.csv")
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.execute("DELETE FROM products")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        count = 0
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            for row in _csv.DictReader(f):
                conn.execute(
                    """INSERT INTO products
                       (id, name, category, brand, price, rating, sales, stock,
                        shop, shop_type, material, standard_code, tags,
                        description, source, url, image, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        int(row["id"]), row["name"], row["category"], row["brand"],
                        float(row["price"]), float(row["rating"]), int(row["sales"]),
                        int(row["stock"]), row["shop"], row["shop_type"],
                        row["material"], (row.get("standard_code") or "").strip(),
                        (row.get("tags") or "").strip(), (row.get("description") or "").strip(),
                        (row.get("source") or "mock").strip(), (row.get("url") or "").strip(),
                        (row.get("image") or "").strip(), row.get("created_at") or now,
                    ),
                )
                count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def get_all_products() -> list[Product]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
        # Product.from_row 依赖列顺序，这里显式构造列序以保持稳定
        cols = [c[0] for c in conn.execute("SELECT * FROM products LIMIT 0").description]
        return [_row_to_product(r, cols) for r in rows]
    finally:
        conn.close()


def _row_to_product(row: sqlite3.Row, cols: list[str]) -> Product:
    vals = [row[c] for c in cols]
    return Product(
        id=vals[0], name=vals[1], category=vals[2], brand=vals[3],
        price=vals[4], rating=vals[5], sales=vals[6], stock=vals[7],
        shop=vals[8], shop_type=vals[9], material=vals[10],
        standard_code=vals[11] or "",
        tags=[t for t in str(vals[12]).split() if t],
        description=vals[13] or "", source=vals[14] or "",
        url=vals[15] or "", image=vals[16] or "", created_at=vals[17],
    )


def get_product(pid: int) -> Optional[Product]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if row is None:
            return None
        cols = [c[0] for c in conn.execute("SELECT * FROM products LIMIT 0").description]
        return _row_to_product(row, cols)
    finally:
        conn.close()


def product_count() -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    finally:
        conn.close()


def save_recommendation(query_json: str, result_json: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO recommendation_history (query_json, result_json, created_at) VALUES (?,?,?)",
            (query_json, result_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_recommendations(limit: int = 50) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, query_json, result_json, created_at FROM recommendation_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_last_recommendation() -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, query_json, result_json, created_at FROM recommendation_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_browse(product_id: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO browse_history (product_id, created_at) VALUES (?,?)",
            (product_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()


def add_favorite(product_id: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (product_id, created_at) VALUES (?,?)",
            (product_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()


def remove_favorite(product_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM favorites WHERE product_id = ?", (product_id,))
        conn.commit()
    finally:
        conn.close()


def get_favorites() -> list[Product]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM products WHERE id IN (SELECT product_id FROM favorites) ORDER BY id"
        ).fetchall()
        cols = [c[0] for c in conn.execute("SELECT * FROM products LIMIT 0").description]
        return [_row_to_product(r, cols) for r in rows]
    finally:
        conn.close()


def get_favorite_ids() -> set[int]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT product_id FROM favorites").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()
