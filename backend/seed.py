"""首次启动的初始化数据：权限、菜单、角色、账号、演示商品。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .config import LOW_STOCK_DEFAULT
from .models import Menu, Permission, Product, Role, StockRecord, User
from .security import hash_password

PERMISSIONS = [
    ("dashboard:view", "查看工作台", "工作台", 10),
    ("product:view", "查看商品", "商品", 20),
    ("product:create", "新增商品", "商品", 21),
    ("product:update", "编辑商品", "商品", 22),
    ("product:delete", "删除/停用商品", "商品", 23),
    ("stock:in", "入库办理", "库存", 30),
    ("stock:out", "出库办理", "库存", 31),
    ("stock:view", "查看出入库记录", "库存", 32),
    ("user:view", "查看用户", "系统", 40),
    ("user:create", "新增用户", "系统", 41),
    ("user:update", "编辑用户/启停", "系统", 42),
    ("user:delete", "删除用户", "系统", 43),
    ("user:reset", "重置密码", "系统", 44),
    ("user:grant", "配置用户菜单", "系统", 45),
    ("role:view", "查看角色", "系统", 50),
    ("role:manage", "维护角色与权限", "系统", 51),
    ("menu:view", "查看菜单", "系统", 60),
    ("menu:manage", "维护菜单", "系统", 61),
]

MENU_SEED = [
    # (name, path, icon, permission, parent_path, sort, visible)
    ("工作台", "/dashboard", "Odometer", "dashboard:view", None, 1, True),
    ("商品管理", "/products", "Goods", "product:view", None, 2, True),
    ("库存作业", "/group/stock", "Box", None, None, 3, True),
    ("入库办理", "/stock/in", "Download", "stock:in", "/group/stock", 1, True),
    ("出库办理", "/stock/out", "Upload", "stock:out", "/group/stock", 2, True),
    ("出入库记录", "/stock/records", "Tickets", "stock:view", "/group/stock", 3, True),
    ("系统管理", "/group/system", "Setting", None, None, 9, True),
    ("用户管理", "/system/users", "User", "user:view", "/group/system", 1, True),
    ("权限管理", "/system/roles", "Lock", "role:view", "/group/system", 2, True),
    ("菜单管理", "/system/menus", "Menu", "menu:view", "/group/system", 3, True),
]

STAFF_MENU_PATHS = {"/dashboard", "/products", "/group/stock", "/stock/in", "/stock/out", "/stock/records"}
STAFF_PERMISSIONS = {"dashboard:view", "product:view", "stock:in", "stock:out", "stock:view"}

DEMO_PRODUCTS = [
    # code, name, category, spec, unit, stock, safety, cost, sale
    ("SP00001", "青提茉莉冷萃原液", "咖啡原料", "500ml/瓶", "瓶", 36, 10, 18.5, 32.0),
    ("SP00002", "厚乳基底乳", "咖啡原料", "1L/盒", "盒", 24, 8, 12.0, 22.0),
    ("SP00003", "750ml 冷饮杯", "包装耗材", "500只/箱", "箱", 3, 5, 96.0, 150.0),
    ("SP00004", "吸管（独立包装）", "包装耗材", "1000支/包", "包", 12, 6, 28.0, 45.0),
    ("SP00005", "焦糖风味糖浆", "风味糖浆", "750ml/瓶", "瓶", 0, 5, 26.0, 42.0),
    ("SP00006", "抹茶粉", "咖啡原料", "100g/袋", "袋", 8, 4, 35.0, 58.0),
]


def seed_all(db: Session, include_demo: bool = True) -> None:
    _seed_permissions(db)
    _seed_menus(db)
    _seed_roles(db)
    _seed_users(db)
    if include_demo:
        _seed_demo_products(db)


def _seed_permissions(db: Session) -> None:
    existing = {p.code for p in db.query(Permission).all()}
    for code, name, module, sort in PERMISSIONS:
        if code not in existing:
            db.add(Permission(code=code, name=name, module=module, sort_order=sort))
    db.flush()


def _seed_menus(db: Session) -> None:
    if db.query(Menu).count() > 0:
        return
    by_path: dict[str, Menu] = {}
    for name, path, icon, permission, parent_path, sort, visible in MENU_SEED:
        parent = by_path.get(parent_path) if parent_path else None
        menu = Menu(
            name=name,
            path=path,
            icon=icon,
            permission_code=permission,
            parent_id=parent.id if parent else None,
            sort_order=sort,
            visible=visible,
            is_builtin=True,
        )
        db.add(menu)
        db.flush()
        by_path[path] = menu
    db.flush()


def _seed_roles(db: Session) -> None:
    permissions = {p.code: p for p in db.query(Permission).all()}
    menus = {m.path: m for m in db.query(Menu).all()}

    admin_role = db.query(Role).filter(Role.code == "admin").first()
    if not admin_role:
        admin_role = Role(code="admin", name="系统管理员", description="拥有全部权限", is_builtin=True)
        admin_role.permissions = list(permissions.values())
        admin_role.menus = list(menus.values())
        db.add(admin_role)

    staff_role = db.query(Role).filter(Role.code == "staff").first()
    if not staff_role:
        staff_role = Role(code="staff", name="普通员工", description="仅执行出入库作业", is_builtin=True)
        staff_role.permissions = [permissions[c] for c in STAFF_PERMISSIONS if c in permissions]
        staff_role.menus = [m for path, m in menus.items() if path in STAFF_MENU_PATHS]
        db.add(staff_role)

    db.flush()


def _seed_users(db: Session) -> None:
    # 只在全新数据库里创建默认账号，避免管理员删掉的员工在重启后被重新创建
    if db.query(User).count() > 0:
        return

    admin_role = db.query(Role).filter(Role.code == "admin").first()
    staff_role = db.query(Role).filter(Role.code == "staff").first()

    db.add(
        User(
            username="admin",
            password_hash=hash_password("Admin@123456"),
            real_name="系统管理员",
            role_id=admin_role.id,
            status=True,
            must_change_password=True,
            menu_mode="inherit",
        )
    )

    db.add(
        User(
            username="staff",
            password_hash=hash_password("Staff@123456"),
            real_name="张小明",
            phone="13800000000",
            role_id=staff_role.id,
            status=True,
            must_change_password=False,
            menu_mode="inherit",
        )
    )
    db.flush()


def _seed_demo_products(db: Session) -> None:
    if os.environ.get("SMARTSTOCK_SEED_DEMO", "1") == "0":
        return
    if db.query(Product).count() > 0:
        return

    admin = db.query(User).filter(User.username == "admin").first()
    operator_id = admin.id if admin else None
    operator_name = admin.real_name if admin else "系统"

    for index, (code, name, category, spec, unit, stock, safety, cost, sale) in enumerate(DEMO_PRODUCTS):
        product = Product(
            code=code,
            name=name,
            category=category,
            spec=spec,
            unit=unit,
            stock=stock,
            safety_stock=safety,
            cost_price=cost,
            sale_price=sale,
            status=True,
            remark="演示数据，可直接编辑或删除",
        )
        db.add(product)
        db.flush()
        if stock > 0:
            created = datetime.now() - timedelta(days=index % 3, hours=index)
            db.add(
                StockRecord(
                    order_no=f"INIT{created:%Y%m%d}{product.id:05d}",
                    product_id=product.id,
                    product_name=product.name,
                    product_code=product.code,
                    type="IN",
                    quantity=stock,
                    before_stock=0,
                    after_stock=stock,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    remark="期初入库（演示数据）",
                    created_at=created,
                )
            )
    db.flush()
