"""权限与菜单的领域逻辑：管理员判定、权限集合、菜单树。"""
from __future__ import annotations

from .db import session
from .models import Menu, Permission, User
from .security import ADMIN_ROLE


def is_admin(user: User) -> bool:
    return bool(user.role and user.role.code == ADMIN_ROLE)


def permission_codes(user: User) -> set[str]:
    if is_admin(user):
        return {p.code for p in session.query(Permission).all()}
    if not user.role:
        return set()
    return {p.code for p in user.role.permissions}


def menu_rows_for(user: User) -> list[Menu]:
    rows = (
        session.query(Menu)
        .filter(Menu.visible.is_(True))
        .order_by(Menu.sort_order, Menu.id)
        .all()
    )
    if is_admin(user):
        return rows

    if user.menu_mode == "custom":
        allowed = {m.id for m in user.menus}
    elif user.role:
        allowed = {m.id for m in user.role.menus}
    else:
        allowed = set()

    granted = permission_codes(user)
    result = []
    for menu in rows:
        if menu.id not in allowed:
            continue
        # 菜单绑定了权限码时，权限必须同时具备，避免"看得见、进不去"
        if menu.permission_code and menu.permission_code not in granted:
            continue
        result.append(menu)
    return result


def build_tree(rows: list[Menu], prune_empty_groups: bool = True) -> list[dict]:
    nodes: dict[int, dict] = {}
    for menu in rows:
        nodes[menu.id] = {
            "id": menu.id,
            "parent_id": menu.parent_id,
            "name": menu.name,
            "path": menu.path,
            "icon": menu.icon or "Menu",
            "sort": menu.sort_order,
            "permission": menu.permission_code,
            "visible": bool(menu.visible),
            "is_builtin": bool(menu.is_builtin),
            "children": [],
        }

    roots: list[dict] = []
    for menu in rows:
        node = nodes[menu.id]
        parent = nodes.get(menu.parent_id) if menu.parent_id else None
        if parent is not None:
            parent["children"].append(node)
        else:
            roots.append(node)

    def clean(items: list[dict]) -> list[dict]:
        cleaned = []
        for item in items:
            item["children"] = clean(item["children"])
            if prune_empty_groups and not item["permission"] and not item["children"]:
                continue
            cleaned.append(item)
        cleaned.sort(key=lambda n: (n["sort"], n["id"]))
        return cleaned

    return clean(roots)


def menu_tree_for(user: User) -> list[dict]:
    return build_tree(menu_rows_for(user))


def allowed_paths(menus: list[dict]) -> set[str]:
    paths: set[str] = set()

    def walk(items: list[dict]) -> None:
        for item in items:
            if item["permission"]:
                paths.add(item["path"])
            walk(item["children"])

    walk(menus)
    return paths


def flat_menu_ids(menus: list[dict]) -> set[int]:
    ids: set[int] = set()

    def walk(items: list[dict]) -> None:
        for item in items:
            ids.add(item["id"])
            walk(item["children"])

    walk(menus)
    return ids
