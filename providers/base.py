"""数据源抽象层（ProductSource / Adapter）。

核心思想：推荐、评分、展示层只依赖统一模型 `core.models.Product`，
不关心商品来自 Mock 种子数据还是真实电商。所有数据源都实现
`ProductProvider` 协议，通过 `get_provider()` 一键切换。

真实数据源的『执行标准号』等字段可能拿不到（例如拼多多搜索接口
不返回标准号）。**严禁为了填充字段而编造数据**——拿不到的字段
保持为空/占位，由系统如实标记（见 `real_data_missing`），
这是与 Mock 数据本质不同的地方，也是「执行标准辅助导购」在真实
数据上必须诚实面对的问题（后续用 OCR 增量补齐）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from core.models import Product


@dataclass
class FetchStats:
    """一次抓取的统计信息。"""

    fetched: int = 0          # 本次实际抓取入库的条数
    skipped: int = 0          # 因缺字段被跳过的条数
    requested: int = 0        # 请求的条数（分页上限）
    elapsed_ms: int = 0       # 耗时（毫秒）
    messages: list[str] = field(default_factory=list)


@dataclass
class NormalizedProduct:
    """适配层的中间产物：尚未分配本地数据库 id 的商品。

    与 `core.models.Product` 的区别在于没有本地自增 id（真实源用外部
    goods_id 标识），字段缺失用 None/空表示，由落库层补齐默认值。
    """

    external_id: str                       # 源平台商品 ID（唯一）
    name: str
    category: str = ""
    brand: str = ""
    price: float = 0.0                     # 单位：元
    rating: float = 0.0
    sales: int = 0
    stock: int = 0
    shop: str = ""
    shop_type: str = ""
    material: str = ""
    standard_code: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    source: str = "unknown"
    url: str = ""
    image: str = ""
    real_data_missing: list[str] = field(default_factory=list)  # 真实数据已知缺失的字段


class ProductProvider(Protocol):
    """商品数据源协议：任何数据源只需实现 fetch_products。"""

    source: str

    def fetch_products(self, keyword: str, limit: int = 50) -> tuple[list[NormalizedProduct], FetchStats]:
        """按关键词抓取商品，返回 (商品列表, 统计)。

        实现约定：
        - 抓取失败应抛异常，由调用方捕获并透出可读错误；
        - 拿不到真实值的字段保持空/占位，严禁编造；
        - `limit` 为需求条数上限，实现可因接口限制减少。
        """
        ...
