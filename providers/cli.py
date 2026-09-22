"""CLI：从当前数据源抓取关键词，写入数据目录（供 analyze/sync/演示）。

用法：
    .venv/bin/python -m providers.cli fetch [--keyword 保鲜盒] [--limit 40] [--page-size 20] [--no-flush]
    # 未配置 API 或需要看实现效果时，可显式指定数据源：
    KESE_PRODUCT_SOURCE=mock .venv/bin/python -m providers.cli fetch --keyword 水杯 --limit 10

说明：
    为保证系统内数据一致，抓取结果默认同时同步到 SQLite `products` 表
    （`--no-flush` 只落盘镜像、不动库）。这样即使后台未运行，也可以
    通过数据迁移脚本把最新快照灌入前端使用的数据库。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from core.config import DATA_DIR
from providers import get_provider, provider_status
from providers.base import ProductProvider


def fetch_to_snapshot(
    provider: ProductProvider,
    keyword: str,
    limit: int,
    mirror_path: Path,
) -> dict:
    items, stats = provider.fetch_products(keyword, limit)
    snapshot = {
        "source": provider.source,
        "keyword": keyword,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "stats": stats.__dict__,
        "items": [vars(it) for it in items],
    }
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    mirror_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def run(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kese-sync", description="按数据源抓取商品到数据目录与 SQLite")
    p.add_argument("--keyword", default="保鲜盒", help="pdd 搜索关键词；mock 可留空")
    p.add_argument("--limit", type=int, default=40, help="总条数（pdd 每页最多 50）")
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--mirror", default=None, help="镜像 JSON 输出路径（默认 data/snapshots/<source>_<ts>.json）")
    p.add_argument("--no-flush", action="store_true", help="只落盘镜像，不写入 SQLite")
    args = p.parse_args(argv)
    if args.page_size != 20:
        print("INFO: pdd.ddk.goods.search 单页上限 50，已按 --page-size 传递", file=sys.stderr)
    provider = get_provider()
    mirror_path = Path(args.mirror) if args.mirror else (DATA_DIR / "snapshots" /
                                  f"{provider.source}_{time.strftime('%Y%m%d_%H%M%S')}.json")
    snapshot = fetch_to_snapshot(provider, args.keyword, args.limit, mirror_path)
    print(f"[sync] 数据源={snapshot['source']} keyword={snapshot['keyword']!r} "
          f"入库 {snapshot['count']} 条 (跳过 {snapshot['stats']['skipped']})")
    print(f"[sync] 镜像已写：{mirror_path}")
    if not args.no_flush:
        from database import db
        db.init_db()  # 幂等建表，独立跑 CLI 也能正确落库（不丢已有数据）
        db.sync_products(snapshot["items"])
        print(f"[sync] SQLite 商品表已同步（当前共 {db.product_count()} 条）")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
