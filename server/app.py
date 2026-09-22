"""FastAPI 应用：docs/前后端契约.md 的 HTTP 实现。

运行：
    python -m server.main
    或
    .venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000

文档：http://127.0.0.1:8000/docs（Swagger UI）
认证：JWT Bearer Token（/api/v1/auth/register、/api/v1/auth/login）
"""
from __future__ import annotations

import time
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import BRANDS, CATEGORIES, TAGS_VOCAB
from database import db
from services import standard_service
from server import captcha, limits, mailer, schemas, security
from server.service import (
    list_favorites,
    list_products,
    parse_requirement_text,
    recommend,
    verify_standard,
)

app = FastAPI(
    title="智能导购系统 API",
    description="基于 docs/前后端契约.md v1 的 HTTP 接口，业务逻辑完全复用 services/algorithms 层。",
    version=schemas.API_VERSION,
)

# 跨域：允许本地 Vue 前端（开发服务器）调用；生产环境由 nginx 反向代理同源访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_and_body_limit(request: Request, call_next):
    """安全响应头 + 请求体大小上限拦截。"""
    # 1) 请求体大小限制（在路由前拦下超大请求）
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > limits.MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "api_version": schemas.API_VERSION,
                    "ok": False,
                    "data": None,
                    "error": {"code": "PAYLOAD_TOO_LARGE", "message": "请求体过大"},
                },
            )
    response = await call_next(request)
    # 2) 统一安全响应头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# 启动时保证数据库与种子数据已就绪
db.init_db()
if db.product_count() == 0:
    db.seed_from_csv()


# ---------------------------------------------------------------------------
# 认证依赖
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """解析 Bearer Token 并返回当前用户，未认证/无效/过期则 401。"""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "未登录或缺少凭证"})
    payload = security.decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "登录凭证无效或已过期，请重新登录"})
    uid = int(payload.get("sub", 0))
    user = db.get_user(uid)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "用户不存在"})
    return {"id": user["id"], "username": user["username"], "email": user["email"]}


def _auth_payload(user) -> schemas.AuthData:
    """统一构造登录/注册的令牌与用户信息响应。"""
    uid = user["id"]
    token = security.create_access_token(uid, user["username"])
    return schemas.AuthData(
        token=token,
        user=schemas.AuthUser(id=uid, username=user["username"], email=user["email"]),
    )


# ---------------------------------------------------------------------------
# 统一错误响应：让所有 4xx/5xx 都符合契约中的统一错误结构
# ---------------------------------------------------------------------------
def _error_body(code: str, message: str, field: str | None = None, status: int = 400, retry_after: int | None = None) -> JSONResponse:
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(
        status_code=status,
        headers=headers,
        content={
            "api_version": schemas.API_VERSION,
            "ok": False,
            "data": None,
            "error": {"code": code, "message": message, "field": field},
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return _error_body(
            code=exc.detail.get("code", "INTERNAL_ERROR"),
            message=exc.detail.get("message", str(exc.detail)),
            field=exc.detail.get("field"),
            status=exc.status_code,
            retry_after=exc.detail.get("retry_after"),
        )
    code = "NOT_FOUND" if exc.status_code == 404 else (
        "INVALID_REQUEST" if exc.status_code in (400, 422) else "INTERNAL_ERROR"
    )
    return _error_body(code=code, message=str(exc.detail), status=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query", "path"))
    return _error_body(
        code="INVALID_REQUEST",
        message=f"参数校验失败：{first.get('msg', '')}",
        field=loc or None,
        status=422,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_body(code="INTERNAL_ERROR", message="服务器内部错误", status=500)


# ---------------------------------------------------------------------------
# 公开端点（无需认证）
# ---------------------------------------------------------------------------
@app.get("/", tags=["meta"], summary="服务健康/说明")
def root() -> dict:
    return {
        "name": "智能导购系统 API",
        "api_version": schemas.API_VERSION,
        "products": db.product_count(),
        "standards": len(standard_service.get_registry().all_records()),
        "docs": "/docs",
    }


@app.get(
    "/api/v1/auth/captcha",
    response_model=schemas.CaptchaResponse,
    tags=["auth"],
    summary="获取图片验证码",
)
def auth_captcha() -> schemas.CaptchaResponse:
    """生成一次性图形验证码，返回 id 与 base64 图片。客户端刷新可再次调用。"""
    captcha_id, code, image = captcha.new_captcha()
    db.save_captcha(captcha_id, security.hash_verify_code(code), time.time() + captcha.CAPTCHA_TTL_SECONDS)
    return schemas.CaptchaResponse(
        ok=True,
        data=schemas.CaptchaData(id=captcha_id, image=image, ttl=captcha.CAPTCHA_TTL_SECONDS),
        error=None,
    )


def _require_captcha(captcha_id: str | None, captcha_code: str | None) -> None:
    """登录/注册前校验图形验证码（对应 send-code 未要求时仅在登录接口强制使用）。"""
    if not captcha_id or not captcha_code:
        raise HTTPException(status_code=400, detail={"code": "CAPTCHA_REQUIRED", "message": "请完成图形验证码"})
    if not db.verify_captcha(captcha_id, captcha_code):
        raise HTTPException(status_code=400, detail={"code": "CAPTCHA_INVALID", "message": "图形验证码错误或已过期，请刷新重试", "field": "captcha_code"})


@app.get(
    "/api/v1/health",
    response_model=schemas.HealthData,
    tags=["meta"],
    summary="健康检查",
)
def health() -> schemas.HealthData:
    return schemas.HealthData(
        name="智能导购系统 API",
        api_version=schemas.API_VERSION,
        products=db.product_count(),
        standards=len(standard_service.get_registry().all_records()),
        categories=CATEGORIES,
        time=datetime.now().isoformat(timespec="seconds"),
    )


@app.post(
    "/api/v1/auth/register",
    response_model=schemas.AuthResponse,
    tags=["auth"],
    summary="注册",
)
def auth_register(req: schemas.RegisterRequest, request: Request) -> schemas.AuthResponse:
    ip = limits.client_ip(request)
    # 限流：每 IP 每小时注册次数
    limits.limit_or_raise(
        f"register:ip:{ip}", limits.IP_REGISTER_PER_HOUR, 3600, db,
        "注册过于频繁，请稍后再试", request,
    )
    # 图形验证码
    _require_captcha(req.captcha_id, req.captcha_code)
    if db.get_user_by_username(req.username) is not None:
        raise HTTPException(status_code=409, detail={"code": "USER_EXISTS", "message": "用户名已存在", "field": "username"})
    email = (req.email or "").strip().lower() or None
    if email and db.get_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail={"code": "EMAIL_EXISTS", "message": "该邮箱已被使用", "field": "email"})
    uid = db.create_user(req.username, security.hash_password(req.password), email=email, email_verified=0)
    user = db.get_user(uid)
    return schemas.AuthResponse(ok=True, data=_auth_payload(user), error=None)


@app.post(
    "/api/v1/auth/login",
    response_model=schemas.AuthResponse,
    tags=["auth"],
    summary="登录（用户名或邮箱）",
)
def auth_login(req: schemas.LoginRequest, request: Request) -> schemas.AuthResponse:
    ident = (req.username or "").strip()
    password = req.password or ""
    ip = limits.client_ip(request)

    # 限流：每 IP 每 10 分钟登录尝试
    limits.limit_or_raise(
        f"login:ip:{ip}", limits.IP_LOGIN_PER_10MIN, 600, db,
        "登录尝试过于频繁，请 10 分钟后再试", request,
    )
    # 图形验证码
    _require_captcha(req.captcha_id, req.captcha_code)

    # 账号锁定检查（连续失败）
    lock = db.get_login_lock(ident)
    if lock["locked"]:
        raise HTTPException(
            status_code=423,
            detail={"code": "ACCOUNT_LOCKED", "message": f"账号已锁定，请 {int(lock['wait']) // 60 + 1} 分钟后重试", "retry_after": int(lock["wait"]) + 1},
        )

    user = None
    if "@" in ident:
        user = db.get_user_by_email(ident.lower())
    elif ident:
        user = db.get_user_by_username(ident)
    if user is None or not security.verify_password(password, user["password_hash"]):
        res = db.login_failure(ident, limits.LOGIN_MAX_FAILURES, limits.LOGIN_LOCK_SECONDS)
        if res["locked"]:
            raise HTTPException(
                status_code=423,
                detail={"code": "ACCOUNT_LOCKED", "message": f"连续失败 {limits.LOGIN_MAX_FAILURES} 次，账号已锁定 15 分钟", "retry_after": int(res["wait"]) + 1},
            )
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "用户名/邮箱或密码错误"})
    db.clear_login_failures(ident)
    return schemas.AuthResponse(ok=True, data=_auth_payload(user), error=None)


@app.post(
    "/api/v1/auth/send-code",
    response_model=schemas.SendCodeResponse,
    tags=["auth"],
    summary="发送邮箱验证码",
)
def auth_send_code(req: schemas.SendCodeRequest, request: Request) -> schemas.SendCodeResponse:
    email = req.email.strip().lower()
    purpose = req.purpose or "register"
    ip = limits.client_ip(request)

    if purpose == "register" and db.get_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail={"code": "EMAIL_EXISTS", "message": "该邮箱已被注册", "field": "email"})

    # 限流：同邮箱发码冷却（60s）
    limits.limit_or_raise(
        f"send:cooldown:{email}", 1, limits.EMAIL_COOLDOWN_SECONDS, db,
        f"发送过于频繁，请 {limits.EMAIL_COOLDOWN_SECONDS} 秒后再试", request,
    )
    # 限流：同邮箱每小时上限
    limits.limit_or_raise(
        f"send:hour:{email}", limits.EMAIL_PER_HOUR, 3600, db,
        f"该邮箱每小时最多发送 {limits.EMAIL_PER_HOUR} 封验证码", request,
    )
    # 限流：每 IP 每小时发码上限
    limits.limit_or_raise(
        f"send:ip:{ip}", limits.IP_SEND_PER_HOUR, 3600, db,
        "当前网络发送验证码过于频繁，请稍后再试", request,
    )

    if purpose == "reset" and db.get_user_by_email(email) is None:
        # 不暴露邮箱是否注册，统一提示已发送（防枚举）
        return schemas.SendCodeResponse(ok=True, data=schemas.SendCodeData(message="验证码已发送，请查收"), error=None)

    code = security.generate_verify_code()
    db.save_email_code(email, purpose, security.hash_verify_code(code), security.code_expiry().strftime("%Y-%m-%d %H:%M:%S"))

    label = "注册" if purpose == "register" else "找回密码"
    mailer.send_code_email(email, code, label)

    # 调试模式回显验证码，便于课设演示
    debug_code = code if mailer.debug_mode() else None
    return schemas.SendCodeResponse(
        ok=True,
        data=schemas.SendCodeData(message="验证码已发送，请查收", code=debug_code, debug=mailer.debug_mode()),
        error=None,
    )


def _verify_code_or_raise(email: str, code: str, purpose: str) -> None:
    """校验验证码：存在 / 未过期 / 尝试次数未超限 / 取值一致。"""
    rec = db.get_latest_email_code(email, purpose)
    if rec is None:
        raise HTTPException(status_code=400, detail={"code": "CODE_INVALID", "message": "验证码无效，请重新发送", "field": "code"})
    if rec["expires_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        raise HTTPException(status_code=400, detail={"code": "CODE_EXPIRED", "message": "验证码已过期，请重新发送", "field": "code"})
    if rec["attempts"] >= security.VERIFY_CODE_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail={"code": "CODE_LOCKED", "message": "尝试次数过多，请重新发送验证码", "field": "code"})
    if not security.verify_code_hash(code, rec["code_hash"]):
        db.bump_email_code_attempts(rec["id"])
        remaining = security.VERIFY_CODE_MAX_ATTEMPTS - rec["attempts"] - 1
        raise HTTPException(status_code=400, detail={"code": "CODE_INVALID", "message": f"验证码错误，剩余 {max(remaining, 0)} 次", "field": "code"})


@app.post(
    "/api/v1/auth/verify-code",
    response_model=schemas.VerifyCodeResponse,
    tags=["auth"],
    summary="校验邮箱验证码",
)
def auth_verify_code(req: schemas.VerifyCodeRequest, request: Request) -> schemas.VerifyCodeResponse:
    email = req.email.strip().lower()
    purpose = req.purpose or "register"
    ip = limits.client_ip(request)
    # 限流：每 IP 每 10 分钟验证码校验次数（防暴力枚举）
    limits.limit_or_raise(
        f"verify:ip:{ip}", limits.IP_VERIFY_PER_10MIN, 600, db,
        "验证码校验过于频繁，请稍后再试", request,
    )
    _verify_code_or_raise(email, req.code, purpose)
    return schemas.VerifyCodeResponse(ok=True, data={"verified": True}, error=None)


@app.post(
    "/api/v1/auth/reset-password",
    response_model=schemas.AuthResponse,
    tags=["auth"],
    summary="邮箱验证码重置密码",
)
def auth_reset_password(req: schemas.ResetPasswordRequest, request: Request) -> schemas.AuthResponse:
    email = req.email.strip().lower()
    ip = limits.client_ip(request)
    # 限流：每 IP 每 10 分钟重置密码尝试
    limits.limit_or_raise(
        f"reset:ip:{ip}", limits.IP_VERIFY_PER_10MIN, 600, db,
        "重置操作过于频繁，请稍后再试", request,
    )
    user = db.get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "该邮箱未注册"})
    _verify_code_or_raise(email, req.code, "reset")
    db.update_password(user["id"], security.hash_password(req.new_password))
    fresh = db.get_user(user["id"])
    return schemas.AuthResponse(ok=True, data=_auth_payload(fresh), error=None)


@app.get("/api/v1/meta", tags=["meta"], summary="元数据（类别/品牌/标签词表）")
def meta() -> schemas.MetaResponse:
    return schemas.MetaResponse(
        ok=True,
        data=schemas.MetaData(categories=CATEGORIES, brands=BRANDS, tags=TAGS_VOCAB),
        error=None,
    )


# ---------------------------------------------------------------------------
# 认证端点（需登录）
# ---------------------------------------------------------------------------
@app.get(
    "/api/v1/auth/me",
    response_model=schemas.MeResponse,
    tags=["auth"],
    summary="当前登录用户",
)
def auth_me(user: dict = Depends(get_current_user)) -> schemas.MeResponse:
    return schemas.MeResponse(
        ok=True,
        data=schemas.AuthUser(id=user["id"], username=user["username"], email=user.get("email")),
        error=None,
    )


# ---------------------------------------------------------------------------
# 受保护端点（需登录）
# ---------------------------------------------------------------------------
@app.get(
    "/api/v1/products",
    response_model=schemas.ProductListResponse,
    tags=["products"],
    summary="商品列表",
)
def products_list(
    category: str | None = Query(default=None, description="商品类别"),
    keyword: str | None = Query(default=None, description="名称/品牌/标签关键词"),
    _user: dict = Depends(get_current_user),
) -> schemas.ProductListResponse:
    data = list_products(category, keyword)
    return schemas.ProductListResponse(ok=True, data=data, error=None)


@app.post(
    "/api/v1/recommend",
    response_model=schemas.RecommendationResponse,
    tags=["recommendation"],
    summary="智能推荐",
)
def recommend_endpoint(
    req: schemas.RecommendationRequest,
    user: dict = Depends(get_current_user),
) -> schemas.RecommendationResponse:
    data = recommend(req, user["id"])
    return schemas.RecommendationResponse(ok=True, data=data, error=None)


@app.post(
    "/api/v1/standards/verify",
    response_model=schemas.StandardEvidenceResponse,
    tags=["standards"],
    summary="执行标准核验",
)
def standards_verify(
    req: schemas.VerifyStandardRequest,
    _user: dict = Depends(get_current_user),
) -> schemas.StandardEvidenceResponse:
    data = verify_standard(req.text)
    return schemas.StandardEvidenceResponse(ok=True, data=data, error=None)


@app.post(
    "/api/v1/parse",
    response_model=schemas.ParseResponse,
    tags=["recommendation"],
    summary="自然语言需求解析",
)
def parse_endpoint(
    req: schemas.ParseRequest,
    _user: dict = Depends(get_current_user),
) -> schemas.ParseResponse:
    data = parse_requirement_text(req.text)
    return schemas.ParseResponse(ok=True, data=data, error=None)


# ---------------------------------------------------------------------------
# 收藏（需登录，按用户隔离）
# ---------------------------------------------------------------------------
@app.get(
    "/api/v1/favorites",
    response_model=schemas.ProductListResponse,
    tags=["favorites"],
    summary="收藏列表",
)
def favorites_list(user: dict = Depends(get_current_user)) -> schemas.ProductListResponse:
    items = list_favorites(user["id"])
    return schemas.ProductListResponse(
        ok=True,
        data=schemas.ProductListData(count=len(items), items=items),
        error=None,
    )


@app.post(
    "/api/v1/favorites",
    response_model=schemas.FavoriteAddResponse,
    tags=["favorites"],
    summary="添加收藏",
)
def favorites_add(
    req: schemas.FavoriteAddRequest,
    user: dict = Depends(get_current_user),
) -> schemas.FavoriteAddResponse:
    if db.get_product(req.product_id) is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"商品 {req.product_id} 不存在", "field": "product_id"},
        )
    db.add_favorite(user["id"], req.product_id)
    return schemas.FavoriteAddResponse(ok=True, data={"added": True, "product_id": req.product_id}, error=None)


@app.delete(
    "/api/v1/favorites/{product_id}",
    response_model=schemas.FavoriteAddResponse,
    tags=["favorites"],
    summary="取消收藏",
)
def favorites_remove(
    product_id: int,
    user: dict = Depends(get_current_user),
) -> schemas.FavoriteAddResponse:
    db.remove_favorite(user["id"], product_id)
    return schemas.FavoriteAddResponse(ok=True, data={"added": False, "product_id": product_id}, error=None)


# ---------------------------------------------------------------------------
# 历史（需登录，按用户隔离）
# ---------------------------------------------------------------------------
@app.get(
    "/api/v1/history/recommendations",
    response_model=schemas.HistoryResponse,
    tags=["history"],
    summary="历史推荐列表",
)
def history_recommendations(
    limit: int = Query(default=50, ge=1, le=500),
    user: dict = Depends(get_current_user),
) -> schemas.HistoryResponse:
    rows = db.list_recommendations(user["id"], limit=limit)
    items = [schemas.HistoryRecord(**r) for r in rows]
    return schemas.HistoryResponse(ok=True, data=schemas.HistoryData(count=len(items), items=items), error=None)
