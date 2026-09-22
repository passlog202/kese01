"""拼多多开放平台数据源（多多进宝 pdd.ddk.goods.search，免商家 access_token）。

签名算法（平台 POP 规范）：
  1) 剔除 sign、client_secret 之外的业务参数，按参数名 ASCII 升序排列
  2) 依次拼接「参数名 + 参数值」（各参数直接相连，无分隔符）
  3) 首尾各拼一次 client_secret，MD5 后转大写

接口事实（来自开放平台公开文档）：
  - 网关：https://gw-api.pinduoduo.com/api/router
  - 返回：goods_search_response.goods_list[]，字段含
    goods_id / goods_name / min_group_price(单位:分) / sales_tip /
    mall_name / goods_image_url / goods_desc 等
  - 个人开发者 2000 次/日，生产建议缓存 + 本地库降频
  - 搜索接口不返回「执行标准号 / 材质」等字段：本适配层如实置空，
    由展示层标记为「未标注」，后续用 OCR 增量补齐，绝不编造。

鉴权凭据全部走环境变量（绝不放代码/git 里）：
  KESE_PDD_CLIENT_ID / KESE_PDD_CLIENT_SECRET
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from providers.base import FetchStats, NormalizedProduct, ProductProvider

_GW = os.environ.get("KESE_PDD_GATEWAY", "https://gw-api.pinduoduo.com/api/router")
_SEARCH_TYPE = "pdd.ddk.goods.search"
_REQUEST_TIMEOUT = float(os.environ.get("KESE_PDD_TIMEOUT_SECONDS", "10"))


def _sign(params: dict, client_secret: str) -> str:
    """拼多多 POP 签名：参数字典序 → key+value 直接相连 → 首尾拼 secret → MD5 大写。"""
    keys = sorted(k for k in params if k not in ("sign", "client_secret"))
    raw = "".join(f"{k}{params[k]}" for k in keys)
    return hashlib.md5(f"{client_secret}{raw}{client_secret}".encode("utf-8")).hexdigest().upper()


def _guess_category(name: str) -> str:
    """按标题关键词把真实商品归到本项目词表类别（没命中则保持空，不硬塞）。"""
    rules = (
        ("保鲜盒", ("保鲜盒", "密封盒", "收纳盒", "饭盒", "餐盒")),
        ("保温杯", ("保温杯", "保温壶", "焖烧杯", "焖烧罐")),
        ("水杯", ("水杯", "杯子", "杯", "随行杯", "摇摇杯")),
        ("电热水壶", ("电热水壶", "热水壶", "烧水壶", "养生壶", "电水壶")),
        ("餐具", ("餐具", "筷子", "碗", "勺子", "刀叉", "餐盘")),
        ("奶瓶", ("奶瓶", "奶嘴", "吸奶器")),
        ("玻璃杯", ("玻璃杯", "高硼硅", "玻璃")),
        ("陶瓷餐具", ("陶瓷", "骨瓷", "瓷碗", "瓷盘")),
    )
    for cat, kws in rules:
        for kw in kws:
            if kw in name:
                return cat
    return ""


def _guess_material(name: str) -> str:
    """按标题推断材质（仅当标题自证材质时才填，否则留空）。"""
    rules = (
        ("不锈钢", ("不锈钢", "316", "304")),
        ("高硼硅玻璃", ("高硼硅", "耐热玻璃", "硼硅")),
        ("玻璃", ("玻璃",)),
        ("PP 塑料", ("pp", "塑料", "食品级pp")),
        ("陶瓷", ("陶瓷", "骨瓷", "瓷")),
    )
    low = name.lower()
    for mat, kws in rules:
        if any(kw.lower() in low for kw in kws):
            return mat
    return ""


class PddProductProvider:
    source = "pdd"

    def __init__(self, client_id: str | None = None, client_secret: str | None = None) -> None:
        self.client_id = (client_id or os.environ.get("KESE_PDD_CLIENT_ID") or "").strip()
        self.client_secret = (client_secret or os.environ.get("KESE_PDD_CLIENT_SECRET") or "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _search(self, keyword: str, limit: int) -> list[dict]:
        params = {
            "type": _SEARCH_TYPE,
            "client_id": self.client_id,
            "timestamp": int(time.time()),
            "data_type": "JSON",
            "keyword": keyword,
            "page_size": max(1, min(limit, 50)),
        }
        # 签名用原始 keyword，build_query 会做 URL 编码
        params["sign"] = _sign(params, self.client_secret)
        url = f"{_GW}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "kese-smart-shopper/1.0"})
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return self._extract_list(payload)

    @staticmethod
    def _extract_list(payload: dict) -> list[dict]:
        """兼容几种常见的响应包裹形式，尽量鲁棒。"""
        if not isinstance(payload, dict):
            return []
        search = payload.get("goods_search_response") or {}
        if isinstance(search, list):
            return search
        if isinstance(search, dict) and isinstance(search.get("goods_list"), list):
            return search["goods_list"]
        # 部分网关封装：{error_response:{error_msg}} 走异常路径由调用方处理
        return []

    def fetch_products(self, keyword: str, limit: int = 50) -> tuple[list[NormalizedProduct], FetchStats]:
        start = time.time()
        if not self.configured:
            raise RuntimeError(
                "拼多多数据源未配置：请设置环境变量 KESE_PDD_CLIENT_ID / KESE_PDD_CLIENT_SECRET"
            )
        if not (keyword or "").strip():
            raise ValueError("拼多多搜索接口必须提供关键词（keyword）")
        try:
            raw_list = self._search(keyword.strip(), limit)
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", "ignore")
            except Exception:
                detail = ""
            raise RuntimeError(f"拼多多接口请求失败（HTTP {e.code}）：{detail[:300]}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"拼多多接口网络错误：{e.reason}") from e

        items: list[NormalizedProduct] = []
        skipped = 0
        for raw in raw_list:
            np = self._to_normalized(raw)
            if not np.name:
                skipped += 1
                continue
            items.append(np)

        stats = FetchStats(
            fetched=len(items),
            skipped=skipped,
            requested=limit,
            elapsed_ms=int((time.time() - start) * 1000),
            messages=[f"pdd.ddk.goods.search keyword={keyword!r} 返回 {len(raw_list)} 条，入库 {len(items)} 条"],
        )
        return items, stats

    # ------------------------------------------------------------------
    # 字段映射
    # ------------------------------------------------------------------
    @staticmethod
    def _to_normalized(raw: dict) -> NormalizedProduct:
        name = (raw.get("goods_name") or "").strip()
        missing: list[str] = []
        if not (raw.get("standard_code") or "").strip():
            missing.append("standard_code")   # 搜索接口无标准号，如实标记
        material = _guess_material(name)
        if not material:
            missing.append("material")

        return NormalizedProduct(
            external_id=str(raw.get("goods_id") or ""),
            name=name,
            category=_guess_category(name),
            brand=_brand_of(raw),
            price=_fen_to_yuan(raw.get("min_group_price")),
            rating=0.0,                       # 搜索接口无评分
            sales=_parse_sales(raw.get("sales_tip")),
            stock=0,                          # 接口不返回库存
            shop=(raw.get("mall_name") or "").strip(),
            shop_type="第三方店铺",
            material=material,
            standard_code=(raw.get("standard_code") or "").strip(),
            tags=_tags_of(name, material),
            description=(raw.get("goods_desc") or "").strip()[:200],
            source="pdd",
            url=f"https://mobile.yangkeduo.com/goods.html?goods_id={raw.get('goods_id', '')}",
            image=(raw.get("goods_image_url") or "").strip(),
            real_data_missing=missing,
        )


def _fen_to_yuan(v) -> float:
    """拼多多价格单位是分，转元并保留 2 位。"""
    try:
        return round(float(v) / 100.0, 2)
    except (TypeError, ValueError):
        return 0.0


_CN_UNIT = {"万": 10_000, "亿": 100_000_000}


def _parse_sales(v) -> int:
    """把「已拼2.3万件 / 已拼500件 / 销量10万+」解析成整数销量近似值。"""
    import re

    if v is None:
        return 0
    s = str(v)
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([万亿])?", s)
    if not m:
        return 0
    num = float(m.group(1))
    unit = m.group(2) or ""
    return int(num * _CN_UNIT.get(unit, 1))


# 已知品牌词表（与 core.config.BRANDS 对齐，仅用于把真实标题归到本系统品牌维度；
# 命中不到则留空，不臆造品牌，避免把标题里无关的词错当成品牌）
_KNOWN_BRANDS = (
    "乐扣乐扣", "特百惠", "富光", "哈尔斯", "希乐", "九阳", "美的", "苏泊尔",
    "双立人", "虎牌", "象印", "膳魔师", "贝亲", "爱得利", "康宁", "乐美雅",
    "茶花", "北鼎", "小熊", "摩飞",
)


def _brand_of(raw: dict) -> str:
    """从标题命中已知品牌词表，没命中就空（诚实，不硬编）。"""
    name = (raw.get("goods_name") or "").strip()
    for b in _KNOWN_BRANDS:
        if b in name:
            return b
    return ""


def _tags_of(name: str, material: str) -> list[str]:
    tags: list[str] = []
    low = name.lower()
    for tag, kws in (("食品级", ("食品级",)), ("耐高温", ("耐高温", "耐热")),
                     ("防漏", ("防漏", "密封", "防洒")), ("大容量", ("大容量", "大号")),
                     ("便携", ("便携", "随行", "户外")), ("保温", ("保温",)),
                     ("儿童", ("儿童", "宝宝", "婴幼儿")), ("硅胶", ("硅胶",))):
        if any(k in low for k in kws):
            tags.append(tag)
    if material and material not in tags:
        tags.insert(0, material)
    return tags[:6]
