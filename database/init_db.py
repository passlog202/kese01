"""数据库初始化脚本：建表 + 从 CSV 灌入种子商品数据。

用法：
    python -m database.init_db
"""
from __future__ import annotations

from database import db


def main() -> None:
    db.init_db()
    n = db.seed_from_csv()
    print(f"[init_db] 已建表并灌入 {n} 条商品数据 -> {db.DB_PATH if hasattr(db, 'DB_PATH') else 'smart_shop.db'}")


if __name__ == "__main__":
    main()
