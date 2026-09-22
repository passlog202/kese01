"""核心数据模型。

统一使用 Python dataclass 定义数据结构，避免引入额外依赖。
`Product` 是贯穿全系统的统一商品数据模型：无论商品来自
Mock 数据源、京东、淘宝还是官方 API，最终都归一化为 Product。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Product:
    """统一商品数据模型（从数据库 products 表映射）。"""

    id: int
    name: str
    category: str
    brand: str
    price: float
    rating: float
    sales: int
    stock: int
    shop: str
    shop_type: str
    material: str
    standard_code: str
    tags: list          # 标签列表，例如 ["食品级", "耐高温"]
    description: str
    source: str
    url: str
    image: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_row(row: tuple) -> "Product":
        return Product(
            id=row[0], name=row[1], category=row[2], brand=row[3],
            price=row[4], rating=row[5], sales=row[6], stock=row[7],
            shop=row[8], shop_type=row[9], material=row[10],
            standard_code=row[11],
            tags=[t for t in str(row[12]).split() if t],
            description=row[13] or "", source=row[14] or "",
            url=row[15] or "", image=row[16] or "", created_at=row[17],
        )


@dataclass
class StandardRecord:
    """标准知识库中的一条标准记录。"""

    code: str            # 展示用完整编号，如 "GB 4806.7-2023"
    normalized: str      # 归一化编号（无空格），如 "GB/T4806.7" 或 "GB4806.7"
    name: str
    category: str
    material: str
    status: str          # 现行 / 即将实施 / 废止 / 已废止
    publish_year: int
    implement_year: int
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StandardEvidence:
    """对商品所声明执行标准的核验证据。"""

    raw: str             # 商品原始声明文本
    normalized: str      # 归一化编号
    matched: bool        # 是否在知识库中命中
    record: Optional[StandardRecord] = None
    status: str = "未收录"  # 现实中的核验结论：现行 / 废止 / 未收录 / 无法识别

    def to_dict(self) -> dict:
        d = {
            "raw": self.raw,
            "normalized": self.normalized,
            "matched": self.matched,
            "status": self.status,
        }
        if self.record is not None:
            d["record"] = self.record.to_dict()
        return d


@dataclass
class RecommendQuery:
    """推荐请求（对应前后端契约中的 RecommendationRequest 核心字段）。"""

    category: Optional[str] = None      # None 表示全部类别
    budget_min: float = 0.0
    budget_max: Optional[float] = None  # None 表示不设上限
    preferences: list = field(default_factory=list)
    brand: Optional[str] = None         # None 表示品牌不限
    require_standard: bool = False      # 仅推荐通过标准核验（现行标准）的商品

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RecommendationItem:
    """单条推荐结果（对应 RecommendationResponse.items 中的一个元素）。"""

    product: Product
    score: float                       # 综合匹配度 0~100
    breakdown: dict                    # 各维度得分明细（ScoreBreakdown）
    reasons: list = field(default_factory=list)      # 可解释推荐理由
    standard_evidence: list = field(default_factory=list)  # 执行标准核验证据

    def to_dict(self) -> dict:
        return {
            "product": self.product.to_dict(),
            "score": round(self.score, 2),
            "breakdown": self.breakdown,
            "reasons": self.reasons,
            "standard_evidence": [e.to_dict() if isinstance(e, StandardEvidence) else e
                                  for e in self.standard_evidence],
        }
