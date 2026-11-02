"""角色与功能权限。"""
from __future__ import annotations

import re

from flask import Blueprint

from ..db import session
from ..models import Menu, Permission, Role, User
from ..registry import MODULE_ORDER
from ..security import current_user, require_perm
from .common import ApiError, as_int, clean_str, fmt_dt, ok, payload, require_fields

bp = Blueprint("roles", __name__)

ROLE_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,19}$")
ADMIN_ROLE_CODE = "admin"


def _get_role(role_id: int) -> Role:
    role = session.get(Role, role_id)
    if not role:
        raise ApiError("角色不存在", status=404)
    return role


def serialize_role(role: Role, with_relations: bool = False) -> dict:
    data = {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description or "",
        "is_builtin": bool(role.is_builtin),
        "is_admin": role.code == ADMIN_ROLE_CODE,
        "user_count": session.query(User).filter(User.role_id == role.id).count(),
        "created_at": fmt_dt(role.created_at),
    }
    if with_relations:
        data["permissions"] = sorted(p.code for p in role.permissions)
        data["menu_ids"] = sorted(m.id for m in role.menus)
    return data


def _guard_editable(role: Role) -> None:
    me = current_user()
    if role.code == ADMIN_ROLE_CODE:
        raise ApiError("超级管理员拥有全部权限，不可修改", status=409)
    if me.role_id == role.id:
        raise ApiError("不能修改当前登录账号所属的角色", status=409)


@bp.get("")
@require_perm("role:view")
def list_roles():
    roles = session.query(Role).order_by(Role.id).all()
    return ok({"items": [serialize_role(role, with_relations=True) for role in roles]})


@bp.get("/permissions")
@require_perm("role:view")
def list_permissions():
    rows = session.query(Permission).order_by(Permission.sort_order, Permission.id).all()
    modules: list[str] = []
    for module in MODULE_ORDER:
        if any(p.module == module for p in rows):
            modules.append(module)
    for permission in rows:
        if permission.module not in modules:
            modules.append(permission.module)
    return ok(
        {
            "modules": modules,
            "items": [
                {"code": p.code, "name": p.name, "module": p.module}
                for p in rows
            ],
        }
    )


@bp.get("/<int:role_id>")
@require_perm("role:view")
def get_role(role_id: int):
    return ok(serialize_role(_get_role(role_id), with_relations=True))


@bp.post("")
@require_perm("role:manage")
def create_role():
    data = payload()
    require_fields(data, "code", "name")
    code = str(data["code"]).strip().lower()
    if not ROLE_CODE_PATTERN.match(code):
        raise ApiError("角色标识需为 2-20 位小写字母、数字或下划线，且以字母开头")
    if session.query(Role).filter(Role.code == code).first():
        raise ApiError("角色标识已存在", status=409)

    role = Role(
        code=code,
        name=clean_str(data.get("name"), 32),
        description=clean_str(data.get("description"), 200),
        is_builtin=False,
    )
    session.add(role)
    session.flush()

    codes = data.get("permissions") or []
    if codes:
        role.permissions = _resolve_permissions(codes)
    menu_ids = data.get("menu_ids") or []
    if menu_ids:
        menus = _resolve_menus(menu_ids)
        role.menus = menus
        _auto_grant_menu_permissions(role, menus)

    session.commit()
    return ok(serialize_role(role, with_relations=True), "角色已创建")


@bp.put("/<int:role_id>")
@require_perm("role:manage")
def update_role(role_id: int):
    role = _get_role(role_id)
    data = payload()
    if "name" in data:
        name = clean_str(data.get("name"), 32)
        if not name:
            raise ApiError("角色名称不能为空")
        role.name = name
    if "description" in data:
        role.description = clean_str(data.get("description"), 200)
    session.commit()
    return ok(serialize_role(role, with_relations=True), "角色已更新")


@bp.delete("/<int:role_id>")
@require_perm("role:manage")
def delete_role(role_id: int):
    role = _get_role(role_id)
    if role.is_builtin:
        raise ApiError("内置角色不可删除", status=409)
    if session.query(User).filter(User.role_id == role.id).count() > 0:
        raise ApiError("该角色下仍有用户，请先调整用户角色", status=409)
    session.delete(role)
    session.commit()
    return ok(None, "角色已删除")


@bp.put("/<int:role_id>/permissions")
@require_perm("role:manage")
def set_permissions(role_id: int):
    role = _get_role(role_id)
    _guard_editable(role)
    data = payload()
    codes = data.get("permissions")
    if not isinstance(codes, list):
        raise ApiError("permissions 必须为数组")
    role.permissions = _resolve_permissions(codes)
    session.commit()
    return ok(serialize_role(role, with_relations=True), "功能权限已保存")


@bp.put("/<int:role_id>/menus")
@require_perm("role:manage")
def set_menus(role_id: int):
    role = _get_role(role_id)
    _guard_editable(role)
    data = payload()
    menu_ids = data.get("menu_ids")
    if not isinstance(menu_ids, list):
        raise ApiError("menu_ids 必须为数组")
    menus = _resolve_menus(menu_ids)
    role.menus = menus
    _auto_grant_menu_permissions(role, menus)
    session.commit()
    return ok(serialize_role(role, with_relations=True), "菜单权限已保存")


def _resolve_permissions(codes: list) -> list[Permission]:
    unique = {str(code) for code in codes}
    if not unique:
        return []
    rows = session.query(Permission).filter(Permission.code.in_(unique)).all()
    if len(rows) != len(unique):
        raise ApiError("包含不存在的权限码", status=404)
    return rows


def _resolve_menus(menu_ids: list) -> list[Menu]:
    unique = {as_int(item, "menu_id") for item in menu_ids}
    if not unique:
        return []
    rows = session.query(Menu).filter(Menu.id.in_(unique)).all()
    if len(rows) != len(unique):
        raise ApiError("包含不存在的菜单", status=404)
    return rows


def _auto_grant_menu_permissions(role: Role, menus: list[Menu]) -> None:
    """授予菜单时自动补齐页面权限，避免出现能看见却打不开的菜单。"""
    existing = {p.code for p in role.permissions}
    for menu in menus:
        code = menu.permission_code
        if not code or code in existing:
            continue
        permission = session.query(Permission).filter(Permission.code == code).first()
        if permission:
            role.permissions.append(permission)
            existing.add(code)
