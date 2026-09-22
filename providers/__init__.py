"""数据源注册与一键切换开关。

默认仍是 mock（行为与历史完全一致）；设置 `KESE_PRODUCT_SOURCE=pdd`
并配置 `KESE_PDD_CLIENT_ID/SECRET` 即切换到拼多多官方开放平台。
"""
from __future__ import annotations

import os

from providers.base import NormalizedProduct, ProductProvider
from providers.mock import MockProductProvider
from providers.pdd import PddProductProvider

_VALID_SOURCES = ("mock", "pdd")


def resolve_source() -> str:
    src = (os.environ.get("KESE_PRODUCT_SOURCE") or "mock").strip().lower()
    if src not in _VALID_SOURCES:
        raise ValueError(f"未知数据源 '{src}'，可选：{', '.join(_VALID_SOURCES)}")
    return src


def get_provider() -> ProductProvider:
    """按 KESE_PRODUCT_SOURCE 返回当前商品数据源。"""
    src = resolve_source()
    if src == "pdd":
        return PddProductProvider()
    return MockProductProvider()


def provider_status() -> dict:
    """给元数据接口用的状态描述。"""
    src = resolve_source()
    if src == "pdd":
        p = PddProductProvider()
        return {"source": src, "configured": p.configured}
    return {"source": src, "configured": True}
