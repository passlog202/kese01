"""HTTP 契约 Schema（Pydantic v2）。

字段与 docs/前后端契约.md 严格一致，作为 FastAPI 的请求/响应模型。
这部分即文档中「前后端契约」的可执行版本。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

API_VERSION = "1.0"


# ---------------------------------------------------------------------------
# 产品模型
# ---------------------------------------------------------------------------
class ProductSummary(BaseModel):
    id: int
    name: str
    category: str
    brand: str
    price: float
    rating: float
    sales: int
    stock: int
    shop: str
    shop_type: str
    material: str
    standard_code: str = ""
    standard_status: str = ""  # 核验结论：现行/废止/未收录/未标注/无法识别
    tags: list[str] = []
    description: str = ""
    source: str = "mock"
    url: str = ""
    image: str = ""
    created_at: str = ""


# ---------------------------------------------------------------------------
# 标准核验
# ---------------------------------------------------------------------------
class StandardRecord(BaseModel):
    code: str
    name: str
    category: str = ""
    material: str = ""
    status: str = "现行"
    publish_year: int = 0
    implement_year: int = 0
    note: str = ""


class StandardEvidence(BaseModel):
    raw: str = ""
    normalized: str = ""
    matched: bool = False
    status: str = "未标注"
    record: Optional[StandardRecord] = None


# ---------------------------------------------------------------------------
# 推荐
# ---------------------------------------------------------------------------
class RecommendationRequest(BaseModel):
    category: Optional[str] = Field(default=None, description="null 表示全部类别")
    budget_min: float = Field(default=0.0, ge=0, description="预算下限")
    budget_max: Optional[float] = Field(default=None, description="null 表示不设上限")
    preferences: list[str] = Field(default_factory=list, description="偏好标签")
    brand: Optional[str] = Field(default=None, description="null 表示品牌不限")
    require_standard: bool = Field(default=False, description="true 仅返回现行标准商品")
    top_n: int = Field(default=10, ge=1, le=100)


class RecommendationItem(BaseModel):
    product: ProductSummary
    score: float
    breakdown: dict[str, float]
    reasons: list[str] = []
    standard_evidence: list[StandardEvidence] = []


class RecommendationData(BaseModel):
    query: dict
    count: int
    items: list[RecommendationItem]


class RecommendationResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: RecommendationData
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 商品列表
# ---------------------------------------------------------------------------
class ProductListData(BaseModel):
    count: int
    items: list[ProductSummary]


class ProductListResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: ProductListData
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 标准核验接口
# ---------------------------------------------------------------------------
class VerifyStandardRequest(BaseModel):
    text: str = Field(description="待核验的文本或标准编号")


class StandardEvidenceResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: StandardEvidence
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 收藏接口
# ---------------------------------------------------------------------------
class FavoriteAddRequest(BaseModel):
    product_id: int


class FavoriteAddResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: dict = {"added": True}
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 历史记录
# ---------------------------------------------------------------------------
class HistoryRecord(BaseModel):
    id: int
    query_json: str
    result_json: str
    created_at: str


class HistoryData(BaseModel):
    count: int
    items: list[HistoryRecord]


class HistoryResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: HistoryData
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 自然语言解析接口
# ---------------------------------------------------------------------------
class ParseRequest(BaseModel):
    text: str = Field(description="一句话需求，如『150 以内 防漏耐高温的保鲜盒』")


class ParseData(BaseModel):
    category: Optional[str] = None
    budget_min: float = 0.0
    budget_max: Optional[float] = None
    preferences: list[str] = Field(default_factory=list)
    brand: Optional[str] = None


class ParseResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: ParseData
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------
class HealthData(BaseModel):
    name: str
    api_version: str
    products: int
    standards: int
    categories: list[str] = []
    time: str = ""


# ---------------------------------------------------------------------------
# 元数据（供前端表单选项使用：类别/品牌/标签词表）
# ---------------------------------------------------------------------------
class MetaData(BaseModel):
    categories: list[str]
    brands: list[str]
    tags: list[str]


class MetaResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: MetaData
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_\u4e00-\u9fa5]{3,32}$")
    password: str = Field(min_length=6, max_length=64)
    email: Optional[str] = Field(default=None, description="邮箱（可选，提供则走邮箱验证/可直接绑定）")
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None


class SendCodeRequest(BaseModel):
    email: str
    purpose: Optional[str] = Field(default="register", description="register / reset")


class VerifyCodeRequest(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)
    purpose: Optional[str] = "register"


class ResetPasswordRequest(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=6, max_length=64)


class AuthUser(BaseModel):
    id: int
    username: str
    email: Optional[str] = None


class AuthData(BaseModel):
    token: str
    user: AuthUser
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: AuthData
    error: Optional[dict] = None


class SendCodeData(BaseModel):
    message: str = "验证码已发送"
    # 仅调试模式（未配置 SMTP）会回显验证码，便于演示；生产环境为 None
    code: Optional[str] = None
    debug: bool = False


class SendCodeResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: SendCodeData
    error: Optional[dict] = None


class VerifyCodeResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: dict = {"verified": True}
    error: Optional[dict] = None


class MeResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: AuthUser
    error: Optional[dict] = None


class CaptchaData(BaseModel):
    id: str
    image: str = ""  # base64 data-uri
    ttl: int = 180


class CaptchaResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = True
    data: Optional[CaptchaData] = None
    error: Optional[dict] = None


# ---------------------------------------------------------------------------
# 统一错误
# ---------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    api_version: str = API_VERSION
    ok: bool = False
    data: None = None
    error: ErrorDetail
