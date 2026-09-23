"""数据源注册与一键切换开关。

默认仍是 mock（行为与历史完全一致）；设置 `KESE_PRODUCT_SOURCE=jd`
即切换到京东商品搜索（纯 HTTP，匿名可尝试）。
"""
from __future__ import annotations

import os

from providers.base import NormalizedProduct, ProductProvider
from providers.jd import JdProductProvider
from providers.mock import MockProductProvider

_VALID_SOURCES = ("mock", "jd")


def resolve_source() -> str:
    src = (os.environ.get("KESE_PRODUCT_SOURCE") or "mock").strip().lower()
    if src not in _VALID_SOURCES:
        raise ValueError(f"未知数据源 '{src}'，可选：{', '.join(_VALID_SOURCES)}")
    return src


def get_provider() -> ProductProvider:
    """按 KESE_PRODUCT_SOURCE 返回当前商品数据源。"""
    src = resolve_source()
    if src == "jd":
        return JdProductProvider()
    return MockProductProvider()


def provider_status() -> dict:
    """给元数据接口用的状态描述。"""
    src = resolve_source()
    if src == "jd":
        p = JdProductProvider()
        return {"source": src, "configured": p.configured, "cookie_loaded": bool(p.cookie)}
    return {"source": src, "configured": True}
