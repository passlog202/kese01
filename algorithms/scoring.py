"""评分引擎：多因素加权综合评分。

综合匹配度计算公式：

    score = Σ 维度得分(0~100) × 权重

    需求相似度  similarity  30%
    标准核验    standard    20%
    价格匹配    price       15%
    用户评分    rating      12%
    销量        sales        8%
    品牌偏好    brand        8%
    店铺信誉    shop         7%

各维度得分都归一化到 0~100，加权求和后即得到最终匹配度。
"""
from __future__ import annotations

from core.config import SCORING_WEIGHTS, SALES_CAP, SHOP_TRUST, DEFAULT_SHOP_TRUST
from core.models import Product, RecommendQuery, StandardEvidence
from services import standard_service


def score_similarity(sim: float) -> float:
    """需求相似度→分数。sim 为 0~1。"""
    return float(sim) * 100.0


def score_standard(evidence: StandardEvidence) -> float:
    return standard_service.standard_score(evidence)


def score_price(price: float, budget_min: float, budget_max: float | None) -> float:
    """价格匹配度：越接近预算中间值得分越高，超预算越靠近边界则扣分更多。"""
    if budget_max is None:
        # 只有下限：不低于下限且越低越好
        if price < budget_min:
            return max(0.0, 100.0 - (budget_min - price)) 
        return max(0.0, 100.0 - (price - budget_min) * 2.0)
    if price < budget_min:
        return max(0.0, 100.0 - (budget_min - price) * 2.0)
    if price > budget_max:
        over = price - budget_max
        # 超出预算上限按比例快速衰减
        return max(0.0, 100.0 - over * 3.0)
    mid = (budget_min + budget_max) / 2.0
    span = max(budget_max - budget_min, 1.0)
    return 100.0 - abs(price - mid) / span * 40.0


def score_rating(rating: float) -> float:
    return max(0.0, min(100.0, rating * 20.0))  # 5 分制 -> 0~100


def score_sales(sales: int) -> float:
    return min(100.0, sales / SALES_CAP * 100.0)


def score_brand(brand: str, preferred: str | None) -> float:
    if not preferred:
        return 60.0  # 品牌不限 → 中性分
    return 100.0 if brand == preferred else 40.0


def score_shop(shop_type: str) -> float:
    return float(SHOP_TRUST.get(shop_type, DEFAULT_SHOP_TRUST))


def compute_score(
    product: Product,
    query: RecommendQuery,
    sim: float,
    evidence: StandardEvidence,
) -> tuple[float, dict]:
    """计算单个商品的综合匹配度，返回 (总分, 维度明细)。"""
    breakdown = {
        "相似度": round(score_similarity(sim), 2),
        "标准核验": round(score_standard(evidence), 2),
        "价格匹配": round(score_price(product.price, query.budget_min, query.budget_max), 2),
        "用户评分": round(score_rating(product.rating), 2),
        "销量": round(score_sales(product.sales), 2),
        "品牌匹配": round(score_brand(product.brand, query.brand), 2),
        "店铺信誉": round(score_shop(product.shop_type), 2),
    }
    total = sum(breakdown[k] * SCORING_WEIGHTS[k] for k in breakdown)
    return round(total, 2), breakdown
