"""认证与鉴权：密码、JWT、登录守卫、权限装饰器。"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, request
from werkzeug.security import check_password_hash, generate_password_hash

from .config import SECRET_FILE, TOKEN_HOURS
from .db import session
from .models import User

ADMIN_ROLE = "admin"
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,20}$")
PASSWORD_HINT = "密码需 8-20 位，且同时包含字母和数字"

_ALLOWED_WHEN_MUST_CHANGE = {"auth.me", "auth.change_password", "auth.logout"}

_secret_cache: str | None = None


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code if code is not None else status


def secret_key() -> str:
    global _secret_cache
    if _secret_cache:
        return _secret_cache
    if SECRET_FILE.exists():
        _secret_cache = SECRET_FILE.read_text(encoding="utf-8").strip()
    else:
        _secret_cache = secrets.token_urlsafe(48)
        SECRET_FILE.write_text(_secret_cache, encoding="utf-8")
    return _secret_cache


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return check_password_hash(password_hash, password)
    except Exception:
        return False


def validate_password_strength(password: str) -> str | None:
    if not password or not PASSWORD_PATTERN.match(password):
        return PASSWORD_HINT
    return None


def issue_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "uid": user.id,
        "ver": int(user.token_version or 0),
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, secret_key(), algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, secret_key(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise AuthError("登录状态无效，请重新登录")


def authenticate() -> User:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise AuthError("请先登录")
    token = header[7:].strip()
    if not token:
        raise AuthError("请先登录")
    payload = decode_token(token)
    user = session.get(User, payload.get("uid"))
    if not user or not user.status:
        raise AuthError("账号不存在或已被停用")
    if int(user.token_version or 0) != int(payload.get("ver", -1)):
        raise AuthError("登录状态已失效，请重新登录")
    if user.must_change_password and request.endpoint not in _ALLOWED_WHEN_MUST_CHANGE:
        raise AuthError("请先修改初始密码", status=403, code=1002)
    g.current_user = user
    return user


def current_user() -> User:
    user = getattr(g, "current_user", None)
    if user is None:
        user = authenticate()
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        authenticate()
        return fn(*args, **kwargs)

    return wrapper


def require_perm(*codes: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from .services import permission_codes

            user = authenticate()
            granted = permission_codes(user)
            if not any(code in granted for code in codes):
                raise AuthError("没有该操作权限", status=403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
