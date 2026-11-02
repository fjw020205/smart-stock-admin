"""用户管理：增删改查、启停、重置密码、用户级菜单。"""
from __future__ import annotations

import re

from flask import Blueprint, request
from sqlalchemy import or_

from ..db import session
from ..models import Menu, Role, User
from ..security import current_user, hash_password, require_perm, validate_password_strength
from ..services import build_tree
from .common import (
    ApiError,
    as_bool,
    as_int,
    clean_str,
    fmt_dt,
    ok,
    page_args,
    payload,
    require_fields,
)

bp = Blueprint("users", __name__)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def serialize_user(user: User, me: User | None = None) -> dict:
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
        "menu_mode": user.menu_mode,
        "last_login_at": fmt_dt(user.last_login_at),
        "created_at": fmt_dt(user.created_at),
        "is_self": bool(me and me.id == user.id),
        "protected": user.username == "admin",
    }


def _all_menus_tree() -> list[dict]:
    rows = session.query(Menu).order_by(Menu.sort_order, Menu.id).all()
    return build_tree(rows, prune_empty_groups=False)


def _get_user(user_id: int) -> User:
    user = session.get(User, user_id)
    if not user:
        raise ApiError("用户不存在", status=404)
    return user


def _active_admin_count() -> int:
    return (
        session.query(User)
        .join(Role)
        .filter(Role.code == "admin", User.status.is_(True))
        .count()
    )


@bp.get("")
@require_perm("user:view")
def list_users():
    keyword = clean_str(request.args.get("keyword"), 50)
    role_id = request.args.get("role_id")
    status = request.args.get("status")
    page, page_size = page_args()

    query = session.query(User)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(User.username.like(like), User.real_name.like(like), User.phone.like(like))
        )
    if role_id:
        query = query.filter(User.role_id == as_int(role_id, "role_id"))
    if status in {"0", "1"}:
        query = query.filter(User.status.is_(status == "1"))

    total = query.count()
    rows = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    me = current_user()
    return ok(
        {
            "items": [serialize_user(u, me) for u in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@bp.post("")
@require_perm("user:create")
def create_user():
    data = payload()
    require_fields(data, "username", "password", "real_name", "role_id")
    username = str(data["username"]).strip()
    if not USERNAME_PATTERN.match(username):
        raise ApiError("账号需为 3-20 位字母、数字或下划线")
    if session.query(User).filter(User.username == username).first():
        raise ApiError("该账号已存在", status=409)

    hint = validate_password_strength(str(data["password"]))
    if hint:
        raise ApiError(hint)

    role = session.get(Role, as_int(data["role_id"], "role_id"))
    if not role:
        raise ApiError("角色不存在", status=404)

    user = User(
        username=username,
        password_hash=hash_password(str(data["password"])),
        real_name=clean_str(data.get("real_name"), 32),
        phone=clean_str(data.get("phone"), 20),
        role_id=role.id,
        status=as_bool(data.get("status"), True),
        must_change_password=as_bool(data.get("must_change_password"), True),
        menu_mode="inherit",
    )
    session.add(user)
    session.commit()
    return ok(serialize_user(user), "用户已创建")


@bp.put("/<int:user_id>")
@require_perm("user:update")
def update_user(user_id: int):
    user = _get_user(user_id)
    me = current_user()
    data = payload()

    if "role_id" in data:
        role_id = as_int(data["role_id"], "role_id")
        if me.id == user.id and role_id != user.role_id:
            raise ApiError("不能修改自己的角色", status=409)
        role = session.get(Role, role_id)
        if not role:
            raise ApiError("角色不存在", status=404)
        user.role_id = role.id

    if "real_name" in data:
        real_name = clean_str(data.get("real_name"), 32)
        if not real_name:
            raise ApiError("姓名不能为空")
        user.real_name = real_name
    if "phone" in data:
        user.phone = clean_str(data.get("phone"), 20)

    session.commit()
    return ok(serialize_user(user, me), "用户已更新")


@bp.delete("/<int:user_id>")
@require_perm("user:delete")
def delete_user(user_id: int):
    user = _get_user(user_id)
    me = current_user()
    if user.id == me.id:
        raise ApiError("不能删除当前登录账号", status=409)
    if user.username == "admin":
        raise ApiError("内置管理员账号不可删除", status=409)
    if user.role and user.role.code == "admin" and _active_admin_count() <= 1:
        raise ApiError("系统至少需要保留一个可用的管理员", status=409)

    session.delete(user)
    session.commit()
    return ok(None, "用户已删除")


@bp.patch("/<int:user_id>/status")
@require_perm("user:update")
def toggle_status(user_id: int):
    user = _get_user(user_id)
    me = current_user()
    data = payload()
    if "status" not in data:
        raise ApiError("缺少参数：status")
    status = as_bool(data.get("status"), True)
    if user.id == me.id and not status:
        raise ApiError("不能停用当前登录账号", status=409)
    if user.username == "admin" and not status:
        raise ApiError("内置管理员账号不可停用", status=409)
    if user.role and user.role.code == "admin" and not status and _active_admin_count() <= 1:
        raise ApiError("系统至少需要保留一个可用的管理员", status=409)

    user.status = status
    if not status:
        user.token_version = int(user.token_version or 0) + 1
    session.commit()
    return ok(serialize_user(user, me), "已启用" if status else "已停用")


@bp.post("/<int:user_id>/reset-password")
@require_perm("user:reset")
def reset_password(user_id: int):
    user = _get_user(user_id)
    data = payload()
    require_fields(data, "new_password")
    new_password = str(data["new_password"])
    hint = validate_password_strength(new_password)
    if hint:
        raise ApiError(hint)

    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    user.token_version = int(user.token_version or 0) + 1
    user.failed_attempts = 0
    user.locked_until = None
    session.commit()
    return ok(None, "密码已重置，该用户下次登录需修改密码")


@bp.get("/<int:user_id>/menus")
@require_perm("user:grant")
def get_user_menus(user_id: int):
    user = _get_user(user_id)
    role_menu_ids = sorted(m.id for m in (user.role.menus if user.role else []))
    custom_ids = sorted(m.id for m in user.menus)
    return ok(
        {
            "mode": user.menu_mode or "inherit",
            "role_menu_ids": role_menu_ids,
            "menu_ids": custom_ids,
            "menus": _all_menus_tree(),
        }
    )


@bp.put("/<int:user_id>/menus")
@require_perm("user:grant")
def set_user_menus(user_id: int):
    user = _get_user(user_id)
    data = payload()
    mode = str(data.get("mode") or "inherit")
    if mode not in {"inherit", "custom"}:
        raise ApiError("mode 只能是 inherit 或 custom")
    if user.username == "admin":
        raise ApiError("超级管理员始终拥有全部菜单，无需单独配置", status=409)

    if mode == "custom":
        raw_ids = data.get("menu_ids") or []
        ids = {as_int(item, "menu_id") for item in raw_ids}
        if not ids:
            raise ApiError("自定义菜单至少选择一个页面，或改为跟随角色")
        menus = session.query(Menu).filter(Menu.id.in_(ids)).all() if ids else []
        if len(menus) != len(ids):
            raise ApiError("包含不存在的菜单", status=404)
        user.menus = menus
        user.menu_mode = "custom"
    else:
        user.menus = []
        user.menu_mode = "inherit"

    session.commit()
    return ok(
        {
            "mode": user.menu_mode,
            "menu_ids": sorted(m.id for m in user.menus),
            "role_menu_ids": sorted(m.id for m in (user.role.menus if user.role else [])),
        },
        "菜单权限已保存",
    )
