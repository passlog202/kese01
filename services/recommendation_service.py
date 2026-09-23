"""推荐服务：协调『筛选 → 相似度 → 标准核验 → 评分 → 排序 → Top-N』的全流程。

这是系统的核心纵向链路：把 RecommendQuery 转换为 RecommendationItem 列表，
并附带可解释的推荐理由与标准核验证据。
"""
from __future__ import annotations

from typing import Optional

from algorithms.similarity import compute_similarity
from algorithms.scoring import compute_score
from core.config import TOP_N
from core.models import Product, RecommendationItem, RecommendQuery, StandardEvidence
from services import standard_service


def filter_products(products: list[Product], query: RecommendQuery) -> list[Product]:
    """硬条件筛选：类别 / 预算区间 / 有货。"""
    result = []
    for p in products:
        if query.category and p.category != query.category:
            continue
        if p.price < query.budget_min:
            continue
        if query.budget_max is not None and p.price > query.budget_max:
            continue
        if p.stock <= 0:
            continue
        result.append(p)
    return result


def _build_reasons(
    product: Product,
    query: RecommendQuery,
    breakdown: dict,
    evidence: StandardEvidence,
) -> list[str]:
    reasons: list[str] = []
    if evidence.status == "现行":
        reasons.append(f"✓ 执行标准 {evidence.normalized} 为现行标准，安全核验通过")
    elif evidence.status == "废止":
        reasons.append(f"⚠ 执行标准 {evidence.normalized} 已废止，请谨慎")
    elif evidence.status == "未收录":
        reasons.append(f"⚠ 执行标准 {evidence.normalized} 未收录，需进一步核验")
    elif evidence.status == "无法识别":
        reasons.append("⚠ 标准编号无法识别，建议人工核对包装")

    if query.budget_max is not None:
        if product.price <= query.budget_max:
            save = (query.budget_max - product.price) / query.budget_max * 100
            reasons.append(f"✓ 价格 {product.price:.1f} 元，低于预算上限 {save:.0f}%")
    if product.rating >= 4.8:
        reasons.append(f"✓ 用户评分 {product.rating}，口碑较高")
    if breakdown["销量"] >= 60:
        reasons.append(f"✓ 销量 {product.sales}，市场认可度较高")
    if query.brand and product.brand == query.brand:
        reasons.append(f"✓ 匹配品牌偏好：{product.brand}")
    reasons.append(f"✓ 店铺为{product.shop_type}，信誉等级较高" if breakdown["店铺信誉"] >= 80
                   else f"⚠ 店铺为{product.shop_type}，建议关注售后")
    return reasons


def recommend(
    products: list[Product],
    query: RecommendQuery,
    top_n: int = TOP_N,
    require_standard: bool = False,
) -> list[RecommendationItem]:
    """执行完整推荐流程，返回按综合得分降序的 Top-N 推荐结果。"""
    candidates = filter_products(products, query)
    if not candidates:
        return []

    sims = compute_similarity(candidates, query.preferences)

    items: list[RecommendationItem] = []
    for p, sim in zip(candidates, sims):
        evidence = standard_service.verify_standard(p.standard_code)
        if require_standard and evidence.status != "现行":
            continue  # 用户勾选“仅看通过标准核验”时过滤
        total, breakdown = compute_score(p, query, sim, evidence)
        reasons = _build_reasons(p, query, breakdown, evidence)
        items.append(
            RecommendationItem(
                product=p, score=total, breakdown=breakdown,
                reasons=reasons, standard_evidence=[evidence],
            )
        )

    items.sort(key=lambda it: it.score, reverse=True)
    return items[:top_n]


def recommend_from_records(products: list[Product], query: dict) -> list[RecommendationItem]:
    """从字典形式的查询条件构造 RecommendQuery 后执行推荐（供接口/页面复用）。"""
    q = RecommendQuery(
        category=query.get("category"),
        budget_min=float(query.get("budget_min", 0.0)),
        budget_max=query.get("budget_max"),
        preferences=list(query.get("preferences") or []),
        brand=query.get("brand"),
        require_standard=bool(query.get("require_standard", False)),
    )
    return recommend(products, q, top_n=query.get("top_n", TOP_N))
