"""菜单管理：菜单树、增删改、角色可见范围。"""
from __future__ import annotations

from uuid import uuid4

from flask import Blueprint

from ..db import session
from ..models import Menu, Permission, Role
from ..registry import PAGE_BY_PATH, PAGES
from ..security import current_user, require_perm
from .common import ApiError, as_bool, as_int, clean_str, ok, payload, require_fields

bp = Blueprint("menus", __name__)


def _get_menu(menu_id: int) -> Menu:
    menu = session.get(Menu, menu_id)
    if not menu:
        raise ApiError("菜单不存在", status=404)
    return menu


def _menu_rows() -> list[Menu]:
    return session.query(Menu).order_by(Menu.sort_order, Menu.id).all()


def _node(menu: Menu) -> dict:
    return {
        "id": menu.id,
        "parent_id": menu.parent_id,
        "name": menu.name,
        "path": menu.path,
        "icon": menu.icon or "Menu",
        "sort": menu.sort_order,
        "visible": bool(menu.visible),
        "permission": menu.permission_code,
        "is_builtin": bool(menu.is_builtin),
        "role_ids": sorted(r.id for r in menu.roles),
        "role_names": [r.name for r in sorted(menu.roles, key=lambda r: r.id)],
        "created_at": menu.created_at.strftime("%Y-%m-%d %H:%M:%S") if menu.created_at else None,
    }


def _tree() -> list[dict]:
    nodes = {menu.id: {**_node(menu), "children": []} for menu in _menu_rows()}
    roots: list[dict] = []
    for menu in _menu_rows():
        item = nodes[menu.id]
        parent = nodes.get(menu.parent_id) if menu.parent_id else None
        if parent:
            parent["children"].append(item)
        else:
            roots.append(item)

    def sort_children(items: list[dict]) -> list[dict]:
        for item in items:
            item["children"] = sort_children(item["children"])
        items.sort(key=lambda n: (n["sort"], n["id"]))
        return items

    return sort_children(roots)


@bp.get("")
@require_perm("menu:view")
def list_menus():
    return ok({"items": _tree(), "roles": [{"id": r.id, "code": r.code, "name": r.name} for r in session.query(Role).order_by(Role.id).all()]})


@bp.get("/registry")
@require_perm("menu:view")
def page_registry():
    used = {m.path for m in _menu_rows()}
    return ok(
        {
            "pages": PAGES,
            "used_paths": sorted(used),
            "available": [page for page in PAGES if page["path"] not in used],
        }
    )


@bp.post("")
@require_perm("menu:manage")
def create_menu():
    data = payload()
    menu_type = str(data.get("type") or "page")
    name = clean_str(data.get("name"), 32)
    parent_id = data.get("parent_id")
    parent = None
    if parent_id not in (None, "", 0, "0"):
        parent = _get_menu(as_int(parent_id, "parent_id"))
        if parent.permission_code:
            raise ApiError("页面菜单下不能再挂子菜单")

    if menu_type == "group":
        if not name:
            raise ApiError("请填写分组名称")
        path = f"/group/{uuid4().hex[:10]}"
        menu = Menu(
            parent_id=parent.id if parent else None,
            name=name,
            path=path,
            icon=clean_str(data.get("icon"), 32, "Folder"),
            sort_order=as_int(data.get("sort", 99), "sort", 0, 999),
            visible=as_bool(data.get("visible"), True),
            permission_code=None,
            is_builtin=False,
        )
    else:
        path = clean_str(data.get("path"), 128)
        page = PAGE_BY_PATH.get(path)
        if not page:
            raise ApiError("请选择已注册的页面")
        if session.query(Menu).filter(Menu.path == path).first():
            raise ApiError("该页面已在菜单中", status=409)
        menu = Menu(
            parent_id=parent.id if parent else None,
            name=name or page["name"],
            path=path,
            icon=clean_str(data.get("icon"), 32, page["icon"]),
            sort_order=as_int(data.get("sort", 99), "sort", 0, 999),
            visible=as_bool(data.get("visible"), True),
            permission_code=page["permission"],
            is_builtin=False,
        )

    session.add(menu)
    session.commit()
    return ok(_node(menu), "菜单已创建")


@bp.put("/<int:menu_id>")
@require_perm("menu:manage")
def update_menu(menu_id: int):
    menu = _get_menu(menu_id)
    data = payload()

    if "name" in data:
        name = clean_str(data.get("name"), 32)
        if not name:
            raise ApiError("菜单名称不能为空")
        menu.name = name
    if "icon" in data:
        menu.icon = clean_str(data.get("icon"), 32, "Menu")
    if "sort" in data:
        menu.sort_order = as_int(data.get("sort"), "sort", 0, 999)
    if "visible" in data:
        visible = as_bool(data.get("visible"), True)
        if not visible and menu.path == "/system/menus":
            raise ApiError("「菜单管理」是系统配置入口，不能隐藏", status=409)
        menu.visible = visible
    if "parent_id" in data:
        raw = data.get("parent_id")
        if raw in (None, "", 0, "0"):
            menu.parent_id = None
        else:
            parent_id = as_int(raw, "parent_id")
            if parent_id == menu.id:
                raise ApiError("不能把自己设为上级菜单")
            parent = _get_menu(parent_id)
            if parent.permission_code:
                raise ApiError("页面菜单下不能再挂子菜单")
            if parent.id in {m.id for m in _descendants(menu)}:
                raise ApiError("不能把菜单移动到自己的子菜单下")
            menu.parent_id = parent.id

    session.commit()
    return ok(_node(menu), "菜单已更新")


@bp.delete("/<int:menu_id>")
@require_perm("menu:manage")
def delete_menu(menu_id: int):
    menu = _get_menu(menu_id)
    if menu.is_builtin:
        raise ApiError("内置菜单不可删除，可改名、隐藏或调整排序", status=409)
    if session.query(Menu).filter(Menu.parent_id == menu.id).count() > 0:
        raise ApiError("请先删除该分组下的子菜单", status=409)
    session.delete(menu)
    session.commit()
    return ok(None, "菜单已删除")


@bp.put("/<int:menu_id>/roles")
@require_perm("menu:manage")
def set_menu_roles(menu_id: int):
    menu = _get_menu(menu_id)
    data = payload()
    raw_ids = data.get("role_ids")
    if not isinstance(raw_ids, list):
        raise ApiError("role_ids 必须为数组")
    selected = {as_int(item, "role_id") for item in raw_ids}

    roles = session.query(Role).all()
    known = {role.id for role in roles}
    if selected - known:
        raise ApiError("包含不存在的角色", status=404)

    for role in roles:
        if role.code == "admin":
            continue  # 超级管理员始终可见
        current = {m.id for m in role.menus}
        if role.id in selected and menu.id not in current:
            role.menus.append(menu)
            _grant_permission(role, menu)
        elif role.id not in selected and menu.id in current:
            role.menus = [m for m in role.menus if m.id != menu.id]

    session.commit()
    return ok(_node(menu), "可见范围已保存")


@bp.get("/my")
@require_perm("menu:view")
def my_menu_scope():
    me = current_user()
    return ok(
        {
            "role": me.role.name if me.role else "",
            "menu_mode": me.menu_mode,
            "menu_ids": sorted(m.id for m in (me.menus if me.menu_mode == "custom" else (me.role.menus if me.role else []))),
        }
    )


def _grant_permission(role: Role, menu: Menu) -> None:
    code = menu.permission_code
    if not code:
        return
    if any(p.code == code for p in role.permissions):
        return
    permission = session.query(Permission).filter(Permission.code == code).first()
    if permission:
        role.permissions.append(permission)


def _descendants(menu: Menu) -> list[Menu]:
    result: list[Menu] = []
    stack = list(menu.children)
    while stack:
        node = stack.pop()
        result.append(node)
        stack.extend(node.children)
    return result
