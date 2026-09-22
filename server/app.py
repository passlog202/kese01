"""FastAPI 应用：docs/前后端契约.md 的 HTTP 实现。

运行：
    python -m server.main
    或
    .venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000

文档：http://127.0.0.1:8000/docs（Swagger UI）
"""
from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import BRANDS, CATEGORIES, TAGS_VOCAB
from database import db
from services import standard_service
from server import schemas
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
    # 兼容我们在业务中抛出的 detail={"code","message","field"} 结构
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

# 启动时保证数据库与种子数据已就绪
db.init_db()
if db.product_count() == 0:
    db.seed_from_csv()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_body(code="INTERNAL_ERROR", message="服务器内部错误", status=500)


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
    "/api/v1/parse",
    response_model=schemas.ParseResponse,
    tags=["recommendation"],
    summary="自然语言需求解析",
)
def parse_endpoint(req: schemas.ParseRequest) -> schemas.ParseResponse:
    data = parse_requirement_text(req.text)
    return schemas.ParseResponse(ok=True, data=data, error=None)


@app.get(
    "/api/v1/meta",
    response_model=schemas.MetaResponse,
    tags=["meta"],
    summary="元数据（类别/品牌/标签词表）",
)
def meta() -> schemas.MetaResponse:
    return schemas.MetaResponse(
        ok=True,
        data=schemas.MetaData(categories=CATEGORIES, brands=BRANDS, tags=TAGS_VOCAB),
        error=None,
    )


@app.get(
    "/api/v1/products",
    response_model=schemas.ProductListResponse,
    tags=["products"],
    summary="商品列表",
)
def products_list(
    category: str | None = Query(default=None, description="商品类别"),
    keyword: str | None = Query(default=None, description="名称/品牌/标签关键词"),
) -> schemas.ProductListResponse:
    data = list_products(category, keyword)
    return schemas.ProductListResponse(ok=True, data=data, error=None)


@app.post(
    "/api/v1/recommend",
    response_model=schemas.RecommendationResponse,
    tags=["recommendation"],
    summary="智能推荐",
)
def recommend_endpoint(req: schemas.RecommendationRequest) -> schemas.RecommendationResponse:
    data = recommend(req)
    return schemas.RecommendationResponse(ok=True, data=data, error=None)


@app.post(
    "/api/v1/standards/verify",
    response_model=schemas.StandardEvidenceResponse,
    tags=["standards"],
    summary="执行标准核验",
)
def standards_verify(req: schemas.VerifyStandardRequest) -> schemas.StandardEvidenceResponse:
    data = verify_standard(req.text)
    return schemas.StandardEvidenceResponse(ok=True, data=data, error=None)


@app.get(
    "/api/v1/favorites",
    response_model=schemas.ProductListResponse,
    tags=["favorites"],
    summary="收藏列表",
)
def favorites_list() -> schemas.ProductListResponse:
    items = list_favorites()
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
def favorites_add(req: schemas.FavoriteAddRequest) -> schemas.FavoriteAddResponse:
    if db.get_product(req.product_id) is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"商品 {req.product_id} 不存在", "field": "product_id"},
        )
    db.add_favorite(req.product_id)
    return schemas.FavoriteAddResponse(ok=True, data={"added": True, "product_id": req.product_id}, error=None)


@app.delete(
    "/api/v1/favorites/{product_id}",
    response_model=schemas.FavoriteAddResponse,
    tags=["favorites"],
    summary="取消收藏",
)
def favorites_remove(product_id: int) -> schemas.FavoriteAddResponse:
    db.remove_favorite(product_id)
    return schemas.FavoriteAddResponse(ok=True, data={"added": False, "product_id": product_id}, error=None)


@app.get(
    "/api/v1/history/recommendations",
    response_model=schemas.HistoryResponse,
    tags=["history"],
    summary="历史推荐列表",
)
def history_recommendations(limit: int = Query(default=50, ge=1, le=500)) -> schemas.HistoryResponse:
    rows = db.list_recommendations(limit=limit)
    items = [schemas.HistoryRecord(**r) for r in rows]
    return schemas.HistoryResponse(ok=True, data=schemas.HistoryData(count=len(items), items=items), error=None)
