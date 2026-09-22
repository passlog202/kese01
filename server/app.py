"""FastAPI 应用：docs/前后端契约.md 的 HTTP 实现。

运行：
    python -m server.main
    或
    .venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000

文档：http://127.0.0.1:8000/docs（Swagger UI）
认证：JWT Bearer Token（/api/v1/auth/register、/api/v1/auth/login）
"""
from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import BRANDS, CATEGORIES, TAGS_VOCAB
from database import db
from services import standard_service
from server import schemas, security
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
    return {"id": user["id"], "username": user["username"]}


# ---------------------------------------------------------------------------
# 统一错误响应：让所有 4xx/5xx 都符合契约中的统一错误结构
# ---------------------------------------------------------------------------
def _error_body(code: str, message: str, field: str | None = None, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
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
def auth_register(req: schemas.RegisterRequest) -> schemas.AuthResponse:
    if db.get_user_by_username(req.username) is not None:
        raise HTTPException(status_code=409, detail={"code": "USER_EXISTS", "message": "用户名已存在", "field": "username"})
    uid = db.create_user(req.username, security.hash_password(req.password))
    token = security.create_access_token(uid, req.username)
    return schemas.AuthResponse(
        ok=True,
        data=schemas.AuthData(token=token, user=schemas.AuthUser(id=uid, username=req.username)),
        error=None,
    )


@app.post(
    "/api/v1/auth/login",
    response_model=schemas.AuthResponse,
    tags=["auth"],
    summary="登录",
)
def auth_login(req: schemas.LoginRequest) -> schemas.AuthResponse:
    user = db.get_user_by_username(req.username)
    if user is None or not security.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"})
    token = security.create_access_token(user["id"], user["username"])
    return schemas.AuthResponse(
        ok=True,
        data=schemas.AuthData(token=token, user=schemas.AuthUser(id=user["id"], username=user["username"])),
        error=None,
    )


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
    return schemas.MeResponse(ok=True, data=schemas.AuthUser(id=user["id"], username=user["username"]), error=None)


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
