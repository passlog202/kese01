"""文本相似度：TF-IDF + 余弦相似度。

把用户需求与商品「标签 + 名称 + 材质」向量化后计算余弦相似度，
度量用户偏好与商品特征的匹配程度。这是推荐算法中『智能』的第一步。
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _product_text(name: str, tags: list, material: str, category: str, brand: str) -> str:
    parts = [str(s).strip() for s in [name, category, brand, material] + list(tags or []) if str(s).strip()]
    return " ".join(parts)


def build_corpus_texts(products: list) -> list[str]:
    return [
        _product_text(p.name, p.tags, p.material, p.category, p.brand)
        for p in products
    ]


def user_query_text(preferences: list) -> str:
    return " ".join(preferences or [])


def compute_similarity(products: list, preferences: list) -> list[float]:
    """返回每个商品与用户需求偏好的相似度（0~1）。

    当用户未选择任何偏好标签时，返回中性值 0.5（不偏向任何商品）。
    """
    if not products:
        return []
    tags = list(preferences or [])
    if not tags:
        return [0.5] * len(products)

    corpus = build_corpus_texts(products)
    query = user_query_text(tags)

    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
    # 中文标签已在数据侧用空格分隔；在欧洲语言下按空白切分
    matrix = vectorizer.fit_transform(corpus + [query])
    sims = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    return sims.tolist()


def similarity_percent(sim: float) -> float:
    """把 0~1 相似度映射到 0~100 分。"""
    return round(float(sim) * 100.0, 2)
