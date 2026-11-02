"""登录、登出、当前用户、修改密码。"""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint

from ..config import LOCK_MINUTES, MAX_LOGIN_FAILURES
from ..db import session
from ..models import User
from ..security import (
    current_user,
    hash_password,
    issue_token,
    login_required,
    validate_password_strength,
    verify_password,
)
from ..services import menu_tree_for, permission_codes
from .common import ApiError, fmt_dt, ok, payload, require_fields

bp = Blueprint("auth", __name__)


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone or "",
        "status": bool(user.status),
        "role": (
            {"id": user.role.id, "code": user.role.code, "name": user.role.name}
            if user.role
            else None
        ),
        "must_change_password": bool(user.must_change_password),
        "menu_mode": user.menu_mode,
        "last_login_at": fmt_dt(user.last_login_at),
        "created_at": fmt_dt(user.created_at),
    }


def session_payload(user: User, token: str | None = None) -> dict:
    menus = menu_tree_for(user)
    data = {
        "user": serialize_user(user),
        "menus": menus,
        "permissions": sorted(permission_codes(user)),
    }
    if token:
        data["token"] = token
    return data


@bp.post("/login")
def login():
    data = payload()
    require_fields(data, "username", "password")
    username = str(data["username"]).strip()
    password = str(data["password"])

    user = session.query(User).filter(User.username == username).first()
    if user and user.locked_until and user.locked_until > datetime.now():
        remain = int((user.locked_until - datetime.now()).total_seconds() // 60) + 1
        raise ApiError(f"连续输错次数过多，账号已锁定，请 {remain} 分钟后再试", status=403)

    if not user or not verify_password(user.password_hash, password):
        if user:
            user.failed_attempts = int(user.failed_attempts or 0) + 1
            if user.failed_attempts >= MAX_LOGIN_FAILURES:
                user.locked_until = datetime.now() + timedelta(minutes=LOCK_MINUTES)
                user.failed_attempts = 0
            session.commit()
        raise ApiError("账号或密码错误", status=401)

    if not user.status:
        raise ApiError("账号已被停用，请联系管理员", status=403)

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now()
    session.commit()

    token = issue_token(user)
    return ok(session_payload(user, token), "登录成功")


@bp.post("/logout")
@login_required
def logout():
    return ok(None, "已退出登录")


@bp.get("/me")
@login_required
def me():
    return ok(session_payload(current_user()))


@bp.put("/password")
@login_required
def change_password():
    user = current_user()
    data = payload()
    require_fields(data, "old_password", "new_password")
    if not verify_password(user.password_hash, str(data["old_password"])):
        raise ApiError("原密码不正确")
    new_password = str(data["new_password"])
    hint = validate_password_strength(new_password)
    if hint:
        raise ApiError(hint)
    if new_password == str(data["old_password"]):
        raise ApiError("新密码不能与原密码相同")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.token_version = int(user.token_version or 0) + 1
    session.commit()

    token = issue_token(user)
    data = session_payload(user)
    data["token"] = token
    return ok(data, "密码修改成功")
