"""数据模型：用户 / 角色 / 权限 / 菜单 / 商品 / 出入库流水。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from .config import LOW_STOCK_DEFAULT
from .db import Base


def now() -> datetime:
    return datetime.now()


class TimestampMixin:
    created_at = Column(DateTime, default=now, nullable=False)
    updated_at = Column(DateTime, default=now, onupdate=now, nullable=False)


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

role_menus = Table(
    "role_menus",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True),
)

user_menus = Table(
    "user_menus",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(32), nullable=False)
    description = Column(String(200), default="")
    is_builtin = Column(Boolean, default=False, nullable=False)

    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    menus = relationship("Menu", secondary=role_menus, back_populates="roles", lazy="selectin")
    users = relationship("User", back_populates="role")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(64), nullable=False)
    module = Column(String(32), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Menu(Base, TimestampMixin):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(32), nullable=False)
    path = Column(String(128), nullable=False)
    icon = Column(String(32), default="Menu")
    sort_order = Column(Integer, default=0, nullable=False)
    visible = Column(Boolean, default=True, nullable=False)
    permission_code = Column(String(64), nullable=True)
    is_builtin = Column(Boolean, default=False, nullable=False)

    parent = relationship("Menu", remote_side=[id], back_populates="children")
    children = relationship(
        "Menu",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Menu.sort_order",
        single_parent=True,
    )
    roles = relationship("Role", secondary=role_menus, back_populates="menus")
    users = relationship("User", secondary=user_menus, back_populates="menus")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(32), nullable=False)
    phone = Column(String(20), default="")
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Boolean, default=True, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    menu_mode = Column(String(16), default="inherit", nullable=False)

    role = relationship("Role", back_populates="users", lazy="joined")
    menus = relationship("Menu", secondary=user_menus, back_populates="users", lazy="selectin")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(64), nullable=False, index=True)
    category = Column(String(32), default="")
    spec = Column(String(64), default="")
    unit = Column(String(16), default="件")
    stock = Column(Integer, default=0, nullable=False)
    safety_stock = Column(Integer, default=LOW_STOCK_DEFAULT, nullable=False)
    cost_price = Column(Numeric(10, 2, asdecimal=False), default=0)
    sale_price = Column(Numeric(10, 2, asdecimal=False), default=0)
    status = Column(Boolean, default=True, nullable=False)
    remark = Column(String(200), default="")

    records = relationship("StockRecord", back_populates="product")


class StockRecord(Base):
    __tablename__ = "stock_records"

    id = Column(Integer, primary_key=True)
    order_no = Column(String(32), unique=True, nullable=False)
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_name = Column(String(64), nullable=False)
    product_code = Column(String(32), nullable=False)
    type = Column(String(8), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    before_stock = Column(Integer, nullable=False)
    after_stock = Column(Integer, nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    operator_name = Column(String(32), nullable=False)
    remark = Column(String(200), default="")
    created_at = Column(DateTime, default=now, nullable=False, index=True)

    product = relationship("Product", back_populates="records")
