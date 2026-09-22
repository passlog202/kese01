"""认证安全模块：密码哈希（PBKDF2-HMAC-SHA256）+ JWT 签发/校验。

- 密码哈希使用标准库 hashlib.pbkdf2_hmac，无需额外编译依赖。
- JWT 使用 PyJWT（HS256），密钥来自环境变量 KESE_JWT_SECRET；
  未设置时自动生成临时密钥（进程内有效，重启后旧 token 失效）。
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

# 令牌有效期
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("KESE_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))

_SECRET_FILE = os.environ.get("KESE_JWT_SECRET_FILE")
_JWT_SECRET = os.environ.get("KESE_JWT_SECRET") or (
    open(_SECRET_FILE, encoding="utf-8").read().strip() if _SECRET_FILE and os.path.exists(_SECRET_FILE) else None
)

if _JWT_SECRET:
    _JWT_SECRET = _JWT_SECRET.strip()
else:
    # 开发环境自动生成的会话级密钥（不持久化）
    _JWT_SECRET = secrets.token_hex(32)

JWT_ALGORITHM = "HS256"
_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 密码哈希，返回 `salt$iterations$hexdigest`。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${_PBKDF2_ITERATIONS}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, iters, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return secrets.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, username: str) -> str:
    """签发带过期的 JWT。payload 含 sub(用户id) 与 username。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """校验 JWT，成功返回 payload，失败/过期返回 None。"""
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
