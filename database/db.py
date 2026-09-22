"""SQLite 数据访问层。

只使用 Python 标准库 sqlite3（不引入 SQLAlchemy），
提供建表、种子导入、产品查询、用户、推荐历史、收藏等基础操作。
数据按用户隔离：favorites / recommendation_history 均挂 user_id。
"""
from __future__ import annotations

import csv as _csv
import sqlite3
from datetime import datetime, timezone
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

CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    query_json  TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS browse_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, product_id)
);
"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表（若不存在）+ 执行必要的迁移（老库无损升级）。"""
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """老库升级：为 fav/history 表补充 user_id 列（幂等）。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(favorites)").fetchall()}
    if "user_id" not in cols:
        # 简单场景下直接重建结构（旧收藏数据量小，且旧表无用户信息，无法归属）
        conn.execute("DROP TABLE IF EXISTS favorites")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, product_id)
            );
            """
        )
    hcols = {r[1] for r in conn.execute("PRAGMA table_info(recommendation_history)").fetchall()}
    if "user_id" not in hcols:
        conn.execute("ALTER TABLE recommendation_history ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
    bcols = {r[1] for r in conn.execute("PRAGMA table_info(browse_history)").fetchall()}
    if "user_id" not in bcols:
        conn.execute("ALTER TABLE browse_history ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")


def seed_from_csv(csv_path: Optional[Path] = None) -> int:
    """用 data/products.csv 重建商品表（全新灌入，保证可重复）。返回导入条数。"""
    csv_path = csv_path or (DATA_DIR / "products.csv")
    conn = _connect()
    try:
        conn.execute("DELETE FROM products")
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            count = 0
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
                        (row.get("image") or "").strip(), row.get("created_at") or _now(),
                    ),
                )
                count += 1
        conn.commit()
        return count
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 商品
# ---------------------------------------------------------------------------
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


def _product_cols(conn: sqlite3.Connection) -> list[str]:
    return [c[0] for c in conn.execute("SELECT * FROM products LIMIT 0").description]


def get_all_products() -> list[Product]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
        cols = _product_cols(conn)
        return [_row_to_product(r, cols) for r in rows]
    finally:
        conn.close()


def get_product(pid: int) -> Optional[Product]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if row is None:
            return None
        return _row_to_product(row, _product_cols(conn))
    finally:
        conn.close()


def product_count() -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------
def create_user(username: str, password_hash: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)",
            (username, password_hash, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    conn = _connect()
    try:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()


def get_user(uid: int) -> Optional[sqlite3.Row]:
    conn = _connect()
    try:
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 推荐历史（按用户隔离）
# ---------------------------------------------------------------------------
def save_recommendation(user_id: int, query_json: str, result_json: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO recommendation_history (user_id, query_json, result_json, created_at) VALUES (?,?,?,?)",
            (user_id, query_json, result_json, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_recommendations(user_id: int, limit: int = 50) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, query_json, result_json, created_at "
            "FROM recommendation_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_last_recommendation(user_id: int) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, query_json, result_json, created_at "
            "FROM recommendation_history WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 浏览（按用户隔离）
# ---------------------------------------------------------------------------
def add_browse(user_id: int, product_id: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO browse_history (user_id, product_id, created_at) VALUES (?,?,?)",
            (user_id, product_id, _now()),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 收藏（按用户隔离）
# ---------------------------------------------------------------------------
def add_favorite(user_id: int, product_id: int) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (user_id, product_id, created_at) VALUES (?,?,?)",
            (user_id, product_id, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def remove_favorite(user_id: int, product_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM favorites WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        conn.commit()
    finally:
        conn.close()


def get_favorites(user_id: int) -> list[Product]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM products WHERE id IN "
            "(SELECT product_id FROM favorites WHERE user_id = ?) ORDER BY id",
            (user_id,),
        ).fetchall()
        cols = _product_cols(conn)
        return [_row_to_product(r, cols) for r in rows]
    finally:
        conn.close()


def get_favorite_ids(user_id: int) -> set[int]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT product_id FROM favorites WHERE user_id = ?", (user_id,)).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()
