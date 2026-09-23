"""京东商品搜索数据源（纯 HTTP/requests，零浏览器依赖）。

方案参考开源项目 hairconker/Product-Crawling 的 `run_cpu_crawl.py`（仅供思路）
——本文件为独立重写，未复制其代码：

  1. GET https://search.jd.com/Search?keyword=...（SSR 搜索页）
     正则提取 `data-sku="..."` 商品块，解析标题/店铺/图片；
  2. GET https://p.3.cn/prices/mgets?skuIds=J_xxx,J_yyy（价格接口）
     补商品现价(origin p)/原价(m)，`p=-1` 视为无价；
  3. 兜底走 s_new.php 异步接口（需 cookie）。

凭据：
  可选环境变量 KESE_JD_COOKIE（京东登录 cookie 串），匿名可尝试；
  匿名被风控时，`state/jd_cookie.txt` 与 KESE_JD_COOKIE 均可提供 cookie。

诚实性契约：京东搜索接口不含执行标准号/材质/评分/库存，适配层如实留空、
由核验标记「未标注」，绝不编造。
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from providers.base import FetchStats, NormalizedProduct, ProductProvider

_SEARCH_URL = "https://search.jd.com/Search"
_SNEW_URL = "https://search.jd.com/s_new.php"
_PRICE_URL = "https://p.3.cn/prices/mgets"
_ITEM_URL = "https://item.jd.com/{sku}.html"
_TIMEOUT = float(os.environ.get("KESE_JD_TIMEOUT_SECONDS", "12"))

_COOKIE_FILE = os.path.join(os.path.dirname(__file__), "state", "jd_cookie.txt")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 风控/登录特征：命中即提示（避免把登录页误当商品页解析）
_RISK_FLAGS = ("rgv587_flag", "deny_h5", "verify", "登录", "安全验证", "verifycode")


def _load_cookie() -> str:
    """cookie 优先级：环境变量 > state/jd_cookie.txt。"""
    env = (os.environ.get("KESE_JD_COOKIE") or "").strip()
    if env:
        return env
    if os.path.exists(_COOKIE_FILE):
        content = open(_COOKIE_FILE, encoding="utf-8").read().strip()
        if content and not content.startswith("#"):
            return content.replace("\r", "").replace("\n", "")
    return ""


def _http_get(url: str, params: dict | None = None, headers: dict | None = None, cookie: str = "") -> str:
    qs = urllib.parse.urlencode(params) if params else ""
    full = f"{url}?{qs}" if qs else url
    hdrs = {"User-Agent": _UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    if headers:
        hdrs.update(headers)
    if cookie:
        hdrs["Cookie"] = cookie
    req = urllib.request.Request(full, headers=hdrs)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read().decode("utf-8", "ignore")


def _strip(s: str) -> str:
    # 用 requests 同款语义：去掉标签与首尾空白
    return re.sub(r"<[^>]+>", "", s or "").strip().replace("&nbsp;", " ")


def _parse_search_html(html: str) -> list[dict]:
    """从京东搜索页 SSR HTML 解析商品块（data-sku 定位）。"""
    skus = list(dict.fromkeys(re.findall(r'data-sku="(\d+)"', html)))
    products: dict[str, dict] = {}
    for sku in skus:
        m = re.search(r'<(li|div)[^>]+data-sku="' + sku + r'"[^>]*>(.*?)</\1>', html, re.DOTALL)
        if not m:
            continue
        block = m.group(2)
        title_m = re.search(r'<div class="p-name[^"]*">.*?<em>(.*?)</em>', block, re.DOTALL)
        shop_m = re.search(r'<div class="p-shop[^"]*">.*?<a[^>]*>(.*?)</a>', block, re.DOTALL)
        img_m = re.search(r'<img[^>]+data-lazy-img="([^"]+)"', block) or re.search(r'<img[^>]+src="([^"]+)"', block)
        img = img_m.group(1) if img_m else ""
        if img.startswith("//"):
            img = "https:" + img
        products[sku] = {
            "item_id": sku,
            "title": _strip(title_m.group(1)) if title_m else "",
            "shop": _strip(shop_m.group(1)) if shop_m else "",
            "image": img,
        }
    return [products[k] for k in skus if k in products]


def _fetch_prices(skus: list[str], cookie: str) -> dict[str, dict]:
    """价格接口：p.3.cn/prices/mgets，返回 {sku: {p, m}}。"""
    if not skus:
        return {}
    params = {"skuIds": ",".join(f"J_{s}" for s in skus), "type": 1}
    try:
        payload = json.loads(_http_get(_PRICE_URL, params,
                                       headers={"Referer": "https://search.jd.com/"}, cookie=cookie))
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for item in payload if isinstance(payload, list) else []:
        sku = str(item.get("id", "")).lstrip("J_")
        if not sku:
            continue
        out[sku] = {"p": item.get("p"), "m": item.get("m")}
    return out


# ---------------------------------------------------------------------------
# 项目词表映射（与 core.config 对齐，把标题归到本系统维度）
# ---------------------------------------------------------------------------
_KNOWN_BRANDS = (
    "乐扣乐扣", "特百惠", "富光", "哈尔斯", "希乐", "九阳", "美的", "苏泊尔",
    "双立人", "虎牌", "象印", "膳魔师", "贝亲", "爱得利", "康宁", "乐美雅",
    "茶花", "北鼎", "小熊", "摩飞",
)

_CATEGORY_RULES = (
    ("保鲜盒", ("保鲜盒", "密封盒", "收纳盒", "饭盒", "餐盒")),
    ("保温杯", ("保温杯", "保温壶", "焖烧杯", "焖烧罐")),
    ("水杯", ("水杯", "杯子", "杯", "随行杯", "摇摇杯")),
    ("电热水壶", ("电热水壶", "热水壶", "烧水壶", "养生壶", "电水壶")),
    ("餐具", ("餐具", "筷子", "碗", "勺子", "刀叉", "餐盘")),
    ("奶瓶", ("奶瓶", "奶嘴", "吸奶器")),
    ("玻璃杯", ("玻璃杯", "高硼硅", "玻璃")),
    ("陶瓷餐具", ("陶瓷", "骨瓷", "瓷碗", "瓷盘")),
)

_MATERIAL_RULES = (
    ("不锈钢", ("不锈钢", "316", "304")),
    ("高硼硅玻璃", ("高硼硅", "耐热玻璃", "硼硅")),
    ("玻璃", ("玻璃",)),
    ("PP 塑料", ("pp", "塑料", "食品级pp")),
    ("陶瓷", ("陶瓷", "骨瓷", "瓷")),
)

_TAG_RULES = (
    ("食品级", ("食品级",)), ("耐高温", ("耐高温", "耐热")),
    ("防漏", ("防漏", "密封", "防洒")), ("大容量", ("大容量", "大号")),
    ("便携", ("便携", "随行", "户外")), ("保温", ("保温",)),
    ("儿童", ("儿童", "宝宝", "婴幼儿")), ("硅胶", ("硅胶",)),
)


def _guess_category(name: str) -> str:
    for cat, kws in _CATEGORY_RULES:
        if any(kw in name for kw in kws):
            return cat
    return ""


def _guess_material(name: str) -> str:
    low = name.lower()
    for mat, kws in _MATERIAL_RULES:
        if any(kw.lower() in low for kw in kws):
            return mat
    return ""


def _guess_brand(name: str) -> str:
    for b in _KNOWN_BRANDS:
        if b in name:
            return b
    return ""


def _guess_tags(name: str, material: str) -> list[str]:
    low = name.lower()
    tags = [tag for tag, kws in _TAG_RULES if any(k in low for k in kws)]
    if material and material not in tags:
        tags.insert(0, material)
    return tags[:6]


def _to_yuan(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 2) if f > 0 else None


class JdProductProvider:
    source = "jd"

    def __init__(self, cookie: str | None = None) -> None:
        self.cookie = (cookie if cookie is not None else _load_cookie()).strip()

    @property
    def configured(self) -> bool:
        return True  # 京东匿名可尝试，无需强制凭据

    def fetch_products(self, keyword: str, limit: int = 50) -> tuple[list[NormalizedProduct], FetchStats]:
        start = time.time()
        kw = (keyword or "").strip()
        if not kw:
            raise ValueError("京东搜索接口必须提供关键词（keyword）")

        cookie = self.cookie
        try:
            html = _http_get(_SEARCH_URL, {"keyword": kw, "enc": "utf-8", "wq": kw, "page": 1},
                             headers={"Referer": "https://www.jd.com/"}, cookie=cookie)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"京东搜索页请求失败（HTTP {e.code}）") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"京东搜索页网络错误：{e.reason}（请确认网络可达 search.jd.com）") from e

        if any(flag in html for flag in _RISK_FLAGS):
            raise RuntimeError("京东触发风控/登录验证：请提供 KESE_JD_COOKIE 后重试")

        items = _parse_search_html(html)

        # 兜底：无 SSR 商品时改走 s_new.php 异步接口（需 cookie）
        if not items:
            if not cookie:
                raise RuntimeError("匿名未解析到商品且未配置 cookie：请提供 KESE_JD_COOKIE 后重试")
            try:
                html2 = _http_get(_SNEW_URL,
                                  {"keyword": kw, "enc": "utf-8", "qrst": 1, "stock": 1,
                                   "page": 1, "s": 1, "scrolling": "y"},
                                  headers={"Referer": f"https://search.jd.com/Search?keyword=" + urllib.parse.quote(kw),
                                           "X-Requested-With": "XMLHttpRequest"},
                                  cookie=cookie)
                items = _parse_search_html(html2)
            except Exception as e:
                raise RuntimeError(f"京东 s_new.php 兜底请求失败：{e}") from e

        items = items[: max(1, min(limit, 60))]

        # 价格接口补价
        price_map = _fetch_prices([it["item_id"] for it in items], cookie)
        normalized: list[NormalizedProduct] = []
        for it in items:
            price = price_map.get(it["item_id"], {})
            normalized.append(self._to_normalized(it, price))
        stats = FetchStats(
            fetched=len(normalized),
            requested=limit,
            elapsed_ms=int((time.time() - start) * 1000),
            messages=[f"jd搜索 keyword={kw!r} 解析 {len(items)} 条"],
        )
        return normalized, stats

    def _to_normalized(self, raw: dict, price: dict) -> NormalizedProduct:
        name = raw["title"]
        material = _guess_material(name)
        missing = ["standard_code"]
        if not material:
            missing.append("material")
        return NormalizedProduct(
            external_id=raw["item_id"],
            name=name,
            category=_guess_category(name),
            brand=_guess_brand(name),
            price=_to_yuan(price.get("p")) or 0.0,
            rating=0.0,
            sales=0,
            stock=0,
            shop=(raw.get("shop") or "").strip(),
            shop_type="第三方店铺",
            material=material,
            standard_code="",
            tags=_guess_tags(name, material),
            description="",
            source="jd",
            url=_ITEM_URL.format(sku=raw["item_id"]),
            image=raw.get("image", ""),
            real_data_missing=missing,
        )
