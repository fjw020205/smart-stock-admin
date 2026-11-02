"""商品管理：增删改查、分类、低库存标记。"""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import func, or_

from ..config import LOW_STOCK_DEFAULT
from ..db import session
from ..models import Product, StockRecord
from ..security import current_user, require_perm
from ..services import permission_codes
from .common import (
    ApiError,
    as_bool,
    as_float,
    as_int,
    clean_str,
    fmt_dt,
    ok,
    page_args,
    payload,
    require_fields,
)

bp = Blueprint("products", __name__)

PRODUCT_CODE_PATTERN = None  # 编码允许字母、数字、短横线，创建时校验


def serialize_product(product: Product) -> dict:
    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "category": product.category or "",
        "spec": product.spec or "",
        "unit": product.unit or "件",
        "stock": int(product.stock or 0),
        "safety_stock": int(product.safety_stock or 0),
        "cost_price": round(float(product.cost_price or 0), 2),
        "sale_price": round(float(product.sale_price or 0), 2),
        "status": bool(product.status),
        "remark": product.remark or "",
        "low_stock": int(product.stock or 0) < int(product.safety_stock or 0),
        "created_at": fmt_dt(product.created_at),
        "updated_at": fmt_dt(product.updated_at),
    }


def _get_product(product_id: int) -> Product:
    product = session.get(Product, product_id)
    if not product:
        raise ApiError("商品不存在", status=404)
    return product


def _validate_code(code: str, exclude_id: int | None = None) -> str:
    if not code:
        raise ApiError("商品编码不能为空")
    if not all(ch.isalnum() or ch in "-_" for ch in code):
        raise ApiError("商品编码只能包含字母、数字、短横线和下划线")
    query = session.query(Product).filter(Product.code == code)
    if exclude_id:
        query = query.filter(Product.id != exclude_id)
    if query.first():
        raise ApiError("商品编码已存在", status=409)
    return code


def _generate_code() -> str:
    max_id = session.query(func.max(Product.id)).scalar() or 0
    candidate = max_id + 1
    while session.query(Product).filter(Product.code == f"SP{candidate:05d}").first():
        candidate += 1
    return f"SP{candidate:05d}"


@bp.get("")
@require_perm("product:view")
def list_products():
    keyword = clean_str(request.args.get("keyword"), 50)
    category = clean_str(request.args.get("category"), 32)
    status = request.args.get("status")
    low_stock = request.args.get("low_stock")
    page, page_size = page_args()

    query = session.query(Product)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Product.name.like(like),
                Product.code.like(like),
                Product.category.like(like),
                Product.spec.like(like),
            )
        )
    if category:
        query = query.filter(Product.category == category)
    if status in {"0", "1"}:
        query = query.filter(Product.status.is_(status == "1"))
    if low_stock == "1":
        query = query.filter(Product.stock < Product.safety_stock)
    elif low_stock == "0":
        query = query.filter(Product.stock >= Product.safety_stock)

    total = query.count()
    rows = (
        query.order_by(Product.updated_at.desc(), Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    categories = [
        row[0]
        for row in session.query(Product.category).filter(Product.category != "").distinct().all()
        if row[0]
    ]
    return ok(
        {
            "items": [serialize_product(p) for p in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "categories": sorted(categories),
        }
    )


@bp.get("/<int:product_id>")
@require_perm("product:view")
def get_product(product_id: int):
    return ok(serialize_product(_get_product(product_id)))


@bp.post("")
@require_perm("product:create")
def create_product():
    data = payload()
    require_fields(data, "name")
    me = current_user()

    code = clean_str(data.get("code"), 32).upper() or _generate_code()
    code = _validate_code(code)

    safety_stock = as_int(
        data.get("safety_stock", LOW_STOCK_DEFAULT), "安全库存", 0, 999999
    )
    initial_stock = as_int(data.get("initial_stock", 0), "期初库存", 0, 999999)
    if initial_stock > 0 and "stock:in" not in permission_codes(me):
        raise ApiError("没有入库权限，不能设置期初库存", status=403)

    product = Product(
        code=code,
        name=clean_str(data.get("name"), 64),
        category=clean_str(data.get("category"), 32),
        spec=clean_str(data.get("spec"), 64),
        unit=clean_str(data.get("unit"), 16, "件") or "件",
        stock=0,
        safety_stock=safety_stock,
        cost_price=as_float(data.get("cost_price"), "成本价"),
        sale_price=as_float(data.get("sale_price"), "售价"),
        status=as_bool(data.get("status"), True),
        remark=clean_str(data.get("remark"), 200),
    )
    session.add(product)
    session.flush()

    if initial_stock > 0:
        product.stock = initial_stock
        session.add(
            StockRecord(
                order_no=f"INIT{product.created_at:%Y%m%d}{product.id:05d}",
                product_id=product.id,
                product_name=product.name,
                product_code=product.code,
                type="IN",
                quantity=initial_stock,
                before_stock=0,
                after_stock=initial_stock,
                operator_id=me.id,
                operator_name=me.real_name,
                remark="新增商品期初入库",
            )
        )

    session.commit()
    return ok(serialize_product(product), "商品已创建")


@bp.put("/<int:product_id>")
@require_perm("product:update")
def update_product(product_id: int):
    product = _get_product(product_id)
    data = payload()

    if "name" in data:
        name = clean_str(data.get("name"), 64)
        if not name:
            raise ApiError("商品名称不能为空")
        product.name = name
    if "category" in data:
        product.category = clean_str(data.get("category"), 32)
    if "spec" in data:
        product.spec = clean_str(data.get("spec"), 64)
    if "unit" in data:
        product.unit = clean_str(data.get("unit"), 16, "件") or "件"
    if "safety_stock" in data:
        product.safety_stock = as_int(data.get("safety_stock"), "安全库存", 0, 999999)
    if "cost_price" in data:
        product.cost_price = as_float(data.get("cost_price"), "成本价")
    if "sale_price" in data:
        product.sale_price = as_float(data.get("sale_price"), "售价")
    if "status" in data:
        product.status = as_bool(data.get("status"), True)
    if "remark" in data:
        product.remark = clean_str(data.get("remark"), 200)

    session.commit()
    return ok(serialize_product(product), "商品已更新")


@bp.delete("/<int:product_id>")
@require_perm("product:delete")
def delete_product(product_id: int):
    product = _get_product(product_id)
    if session.query(StockRecord).filter(StockRecord.product_id == product_id).count() > 0:
        raise ApiError("该商品已有出入库记录，不能删除，请改为停用", status=409)
    if int(product.stock or 0) != 0:
        raise ApiError("该商品仍有库存，请先出库清零", status=409)
    session.delete(product)
    session.commit()
    return ok(None, "商品已删除")
