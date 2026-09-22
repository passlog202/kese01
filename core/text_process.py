"""自然语言需求解析（轻量规则版）。

不依赖 jieba 等重库：用正则 + 词表匹配，从类似
"300 以内 防漏耐高温的保鲜盒，最好是乐扣乐扣" 的自由文本中，
抽取【预算 / 类别 / 品牌 / 需求标签】四类结构化信息。
后续接入真正的爬虫数据或换 NLP 模型时，只需替换本模块。
"""
from __future__ import annotations

import re
from typing import Optional

from core.config import CATEGORIES, BRANDS, TAGS_VOCAB

# 价格抽取：支持 "300以内"、"100-300元"、"预算200"、"大概250左右" 等
_PRICE_PAIR = re.compile(r"(\d{2,5})\s*[-~到～]\s*(\d{2,5})")
_PRICE_UNDER = re.compile(r"(?:预算|价格)?\s*(\d{2,5})\s*(?:元|块|以内|以下|之内|内)")
_PRICE_ABOUT = re.compile(r"(?:预算|大概|大约|左右)?\s*(\d{2,5})\s*(?:左右|上下)")

_CJK_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9}


def extract_budget(text: str) -> Optional[tuple[float, Optional[float]]]:
    """从文本抽取预算区间 (min, max)，max 为 None 表示不限上限。"""
    if not text:
        return None
    m = _PRICE_PAIR.search(text)
    if m:
        low, high = sorted((int(m.group(1)), int(m.group(2))))
        return float(low), float(high)
    m = _PRICE_UNDER.search(text)
    if m:
        return 0.0, float(m.group(1))
    m = _PRICE_ABOUT.search(text)
    if m:
        mid = float(m.group(1))
        return mid * 0.85, mid * 1.15
    return None


def extract_category(text: str) -> Optional[str]:
    """从文本抽取商品类别（命中词表第一个）。"""
    if not text:
        return None
    for cat in CATEGORIES:
        if cat in text:
            return cat
    return None


def extract_brand(text: str) -> Optional[str]:
    """从文本抽取品牌偏好。"""
    if not text:
        return None
    for b in BRANDS:
        if b in text:
            return b
    return None


def extract_tags(text: str) -> list[str]:
    """从文本抽取需求标签（词表匹配，多个标签去重返回）。"""
    if not text:
        return []
    return [t for t in TAGS_VOCAB if t in text]


def parse_requirement(text: str) -> dict:
    """把一句自然语言需求解析为结构化字段（供智能导购一键填充）。"""
    text = (text or "").strip()
    if not text:
        return {}
    result: dict = {"preferences": extract_tags(text)}
    b = extract_budget(text)
    if b:
        result["budget_min"], result["budget_max"] = b
    c = extract_category(text)
    if c:
        result["category"] = c
    br = extract_brand(text)
    if br:
        result["brand"] = br
    return result
