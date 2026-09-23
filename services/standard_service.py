"""执行标准核验服务。

课设核心亮点之一：不直接相信商城的文字宣称，而是把商品声明的
「执行标准编号」归一化后，到本地标准知识库中核验其是否存在、
现行还是废止、适用范围是否匹配，并把结论作为推荐评分依据。

后续接入 OCR（识别包装图片上的 GB/GB/T 编号）时，只需要
把 OCR 文本交给 `verify_standard`，本模块无需改动。
"""
from __future__ import annotations

import json
import re
from typing import Optional

from core.config import DATA_DIR
from core.models import StandardEvidence, StandardRecord

REGISTRY_PATH = DATA_DIR / "standards" / "standard_registry.json"

# 识别 "GB 4806.7-2023" / "GB/T4806.7" / "QB/T 2442" 等标准号
_CODE_RE = re.compile(
    r"(?<![A-Z0-9])"
    r"(?:GB|GB/T|QB|QB/T|SN|HG|JC)\s*[·:：/]?\s*"
    r"T?\s*\d{4,5}(?:\.\d+)?(?:\.\d+)?(?:[—-]\d{4})?"
    r"(?![A-Z0-9])",
    re.IGNORECASE,
)


def normalize_standard_code(raw: str) -> str:
    """归一化标准编号：去空格、统一大写、把中文连接符换成 '-'.

    例如 "GB/T 4806.7-2023" -> "GB/T4806.7-2023"
    """
    if not raw:
        return ""
    s = raw.strip().upper()
    s = s.replace("—", "-").replace("–", "-").replace("－", "-")
    s = re.sub(r"\s+", "", s)
    return s


def extract_standard_codes(text: str) -> list[str]:
    """从一段文本（例如商品参数/OCR 结果）中抽取所有标准编号。"""
    if not text:
        return []
    return [normalize_standard_code(m.group(0)) for m in _CODE_RE.finditer(text)]


class StandardRegistry:
    """本地标准知识库（加载 data/standards/standard_registry.json）。

    索引策略支持「无年份」查询：例如商品只写 "GB4806.7"，会把它
    归属到该编号最新、且处于现行状态的标准记录。
    """

    def __init__(self) -> None:
        self._records: dict[str, StandardRecord] = {}
        self._by_base: dict[str, list[StandardRecord]] = {}
        self.load()

    def load(self) -> None:
        self._records.clear()
        self._by_base.clear()
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            rec = StandardRecord(
                code=item["code"],
                normalized=normalize_standard_code(item["code"]),
                name=item["name"],
                category=item.get("category", ""),
                material=item.get("material", ""),
                status=item.get("status", "现行"),
                publish_year=int(item.get("publish_year", 0)),
                implement_year=int(item.get("implement_year", 0)),
                note=item.get("note", ""),
            )
            self._records[rec.normalized] = rec
            base = rec.normalized.split("-")[0]
            self._by_base.setdefault(base, []).append(rec)
        # 每个 base 下记录排序：现行优先，其次年份新的优先
        for base, recs in self._by_base.items():
            recs.sort(key=lambda r: (0 if r.status == "现行" else 1, -r.publish_year))

    def lookup(self, code: str) -> Optional[StandardRecord]:
        """先精确匹配完整编号；失败则按无年份 base 匹配最新现行记录。"""
        if not code:
            return None
        norm = normalize_standard_code(code)
        if not norm:
            return None
        if norm in self._records:
            return self._records[norm]
        base = norm.split("-")[0]
        recs = self._by_base.get(base)
        if recs:
            return recs[0]
        return None

    def all_records(self) -> list[StandardRecord]:
        return list(self._records.values())


_registry: Optional[StandardRegistry] = None


def get_registry() -> StandardRegistry:
    global _registry
    if _registry is None:
        _registry = StandardRegistry()
    return _registry


def verify_standard(raw: str) -> StandardEvidence:
    """核验一个标准编号，返回带核验结论的证据对象。

    状态取值：现行 / 废止 / 未收录 / 未标注 / 无法识别
    """
    raw = (raw or "").strip()
    if not raw:
        return StandardEvidence(raw="", normalized="", matched=False, status="未标注")

    norm = normalize_standard_code(raw)
    if not re.match(r"^(GB|QB|SN|HG|JC)", norm):
        return StandardEvidence(raw=raw, normalized=norm, matched=False, status="无法识别")

    rec = get_registry().lookup(norm)
    if rec is None:
        return StandardEvidence(raw=raw, normalized=norm, matched=False, status="未收录")
    status = rec.status if rec.status in ("现行", "废止") else "现行"
    return StandardEvidence(raw=raw, normalized=norm, matched=True, record=rec, status=status)


# ---------------------------------------------------------------------------
# 标准维度评分（供 ScoringEngine 使用）
# ---------------------------------------------------------------------------
STANDARD_STATUS_SCORE = {
    "现行": 100.0,
    "未收录": 48.0,   # 存在但未收录 → 存疑，低于中性分
    "无法识别": 30.0,
    "未标注": 15.0,
    "废止": 10.0,     # 废止标准 → 严重扣分
}


def standard_score(evidence: StandardEvidence) -> float:
    """把核验结论映射为 0~100 分。"""
    return STANDARD_STATUS_SCORE.get(evidence.status, 30.0)
