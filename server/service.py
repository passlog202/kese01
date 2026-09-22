"""HTTP 服务：把业务层（services）包装为契约化的 HTTP 端点。

完全复用 algorithms / services / database 三层，不对业务逻辑做任何封装性修改，
仅做「HTTP 参数 ↔ 核心模型」的转换与响应组装。
"""
from __future__ import annotations

import json

from database import db
from core.models import RecommendQuery, RecommendationItem, StandardEvidence
from core.text_process import parse_requirement
from services import recommendation_service, standard_service, product_service
from api_contract import build_recommendation_response
from server import schemas


def query_from_request(req: schemas.RecommendationRequest) -> RecommendQuery:
    return RecommendQuery(
        category=req.category,
        budget_min=req.budget_min,
        budget_max=req.budget_max,
        preferences=req.preferences,
        brand=req.brand,
        require_standard=req.require_standard,
    )


def product_to_summary(p) -> schemas.ProductSummary:
    d = p.to_dict()
    d["standard_status"] = standard_service.verify_standard(p.standard_code).status
    return schemas.ProductSummary(**d)


def evidence_to_schema(ev: StandardEvidence) -> schemas.StandardEvidence:
    return schemas.StandardEvidence(
        raw=ev.raw,
        normalized=ev.normalized,
        matched=ev.matched,
        status=ev.status,
        record=schemas.StandardRecord(**ev.record.to_dict()) if ev.record else None,
    )


def to_schema_items(items: list[RecommendationItem]) -> list[schemas.RecommendationItem]:
    out = []
    for it in items:
        out.append(
            schemas.RecommendationItem(
                product=product_to_summary(it.product),
                score=it.score,
                breakdown=it.breakdown,
                reasons=it.reasons,
                standard_evidence=[evidence_to_schema(e) for e in it.standard_evidence],
            )
        )
    return out


def recommend(req: schemas.RecommendationRequest) -> schemas.RecommendationData:
    query = query_from_request(req)
    items = recommendation_service.recommend(
        db.get_all_products(), query,
        top_n=req.top_n, require_standard=req.require_standard,
    )
    # 复用 api_contract 的统一结构，保证与文档契约 / 进程内调用一致
    payload = build_recommendation_response(items, query.to_dict())
    # 持久化本次推荐到历史（HTTP 模式同样保留历史，前端「推荐历史」页依赖此数据）
    db.save_recommendation(
        json.dumps(query.to_dict(), ensure_ascii=False),
        json.dumps(payload["data"], ensure_ascii=False),
    )
    return schemas.RecommendationData(**payload["data"])


def list_products(category: str | None, keyword: str | None) -> schemas.ProductListData:
    products = product_service.list_products(category=category, keyword=keyword)
    return schemas.ProductListData(
        count=len(products),
        items=[product_to_summary(p) for p in products],
    )


def list_favorites() -> list[schemas.ProductSummary]:
    return [product_to_summary(p) for p in db.get_favorites()]


def verify_standard(text: str) -> schemas.StandardEvidence:
    evidence = standard_service.verify_standard(text)
    return evidence_to_schema(evidence)


def parse_requirement_text(text: str) -> schemas.ParseData:
    """自然语言需求 → 结构化查询字段（复用 core.text_process 规则解析）。"""
    parsed = parse_requirement(text)
    return schemas.ParseData(**parsed)
