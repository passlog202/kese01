"""限流与登录安全辅助：阈值常量、IP 提取、限流判定、429/413 响应构造。"""
from __future__ import annotations

import os

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# 阈值（均可通过环境变量覆盖）
# ---------------------------------------------------------------------------
EMAIL_COOLDOWN_SECONDS = int(os.environ.get("KESE_EMAIL_COOLDOWN", 60))       # 同邮箱发码冷却
EMAIL_PER_HOUR = int(os.environ.get("KESE_EMAIL_PER_HOUR", 5))                # 同邮箱每小时上限
IP_SEND_PER_HOUR = int(os.environ.get("KESE_IP_SEND_PER_HOUR", 30))           # 每 IP 每小时发码上限
IP_REGISTER_PER_HOUR = int(os.environ.get("KESE_IP_REGISTER_PER_HOUR", 20))   # 每 IP 每小时注册上限
IP_LOGIN_PER_10MIN = int(os.environ.get("KESE_IP_LOGIN_PER_10MIN", 20))       # 每 IP 每 10 分钟登录尝试
IP_VERIFY_PER_10MIN = int(os.environ.get("KESE_IP_VERIFY_PER_10MIN", 30))     # 每 IP 每 10 分钟验证码校验

LOGIN_MAX_FAILURES = int(os.environ.get("KESE_LOGIN_MAX_FAILURES", 5))        # 连续失败锁定阈值
LOGIN_LOCK_SECONDS = int(os.environ.get("KESE_LOGIN_LOCK_SECONDS", 900))      # 锁定时长（秒）15 分钟

MAX_BODY_BYTES = int(os.environ.get("KESE_MAX_BODY_BYTES", 1024 * 256))       # 请求体上限 256KB


def client_ip(request: Request) -> str:
    """提取客户端 IP：优先 X-Forwarded-For（nginx 反代场景），回退直连地址。"""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def limit_or_raise(bucket: str, limit: int, window: float, db, message: str, request: Request) -> None:
    """命中限流则抛出 429，附 Retry-After 头 + 统一错误结构。"""
    hit, wait = db.rate_limit_hit(bucket, limit, window)
    if hit:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMITED",
                "message": message,
                "retry_after": int(wait) + 1,
            },
        )


def make_rate_limited(detail: dict) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(int(detail.get("retry_after", 60)))},
        content={
            "api_version": "1.0",
            "ok": False,
            "data": None,
            "error": detail,
        },
    )
