"""前后端契约（Python 参考实现）。

文档定义见 docs/前后端契约.md。这里提供 `build_recommendation_response`，
把 RecommendationItem 列表转换为统一的 JSON 结构，方便未来迁移到
FastAPI 时直接复用该函数作为 response_model。

契约版本：v1
"""
from __future__ import annotations

from typing import Optional

from core.models import RecommendationItem

API_VERSION = "1.0"


def build_recommendation_response(
    items: list[RecommendationItem],
    query: dict,
    ok: bool = True,
    error: Optional[dict] = None,
) -> dict:
    """组装统一响应结构（对应 RecommendationResponse）。"""
    payload = {
        "api_version": API_VERSION,
        "ok": ok,
        "data": {
            "query": query,
            "count": len(items),
            "items": [it.to_dict() for it in items],
        },
        "error": error,
    }
    return payload
