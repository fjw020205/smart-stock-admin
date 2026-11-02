"""已注册页面清单：菜单只能挂到这些页面上，避免配置出打不开的死链。"""
from __future__ import annotations

PAGES: list[dict] = [
    {"path": "/dashboard", "name": "工作台", "permission": "dashboard:view", "icon": "Odometer"},
    {"path": "/products", "name": "商品管理", "permission": "product:view", "icon": "Goods"},
    {"path": "/stock/in", "name": "入库办理", "permission": "stock:in", "icon": "Download"},
    {"path": "/stock/out", "name": "出库办理", "permission": "stock:out", "icon": "Upload"},
    {"path": "/stock/records", "name": "出入库记录", "permission": "stock:view", "icon": "Tickets"},
    {"path": "/system/users", "name": "用户管理", "permission": "user:view", "icon": "User"},
    {"path": "/system/roles", "name": "权限管理", "permission": "role:view", "icon": "Lock"},
    {"path": "/system/menus", "name": "菜单管理", "permission": "menu:view", "icon": "Menu"},
]

PAGE_BY_PATH = {page["path"]: page for page in PAGES}

# 模块展示顺序（权限矩阵分组用）
MODULE_ORDER = ["工作台", "商品", "库存", "系统"]
