"""库存作业：入库、出库、流水查询。"""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, request

from ..db import session, stock_conn
from ..models import StockRecord
from ..security import current_user, require_perm
from .common import (
    ApiError,
    as_int,
    clean_str,
    fmt_dt,
    ok,
    page_args,
    parse_day,
    payload,
    require_fields,
)

bp = Blueprint("stock", __name__)

TYPE_LABEL = {"IN": "入库", "OUT": "出库"}


def serialize_record(record: StockRecord) -> dict:
    return {
        "id": record.id,
        "order_no": record.order_no,
        "product_id": record.product_id,
        "product_name": record.product_name,
        "product_code": record.product_code,
        "type": record.type,
        "type_label": TYPE_LABEL.get(record.type, record.type),
        "quantity": record.quantity,
        "before_stock": record.before_stock,
        "after_stock": record.after_stock,
        "operator_name": record.operator_name,
        "remark": record.remark or "",
        "created_at": fmt_dt(record.created_at),
    }


def _change_stock(kind: str) -> dict:
    data = payload()
    require_fields(data, "product_id", "quantity")
    product_id = as_int(data["product_id"], "商品", 1)
    quantity = as_int(data["quantity"], "数量", 1, 1000000)
    remark = clean_str(data.get("remark"), 200)
    user = current_user()
    now = datetime.now()

    with stock_conn() as conn:
        row = conn.execute(
            "SELECT id, code, name, stock, status, unit FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if not row:
            raise ApiError("商品不存在", status=404)
        if not row["status"]:
            raise ApiError("商品已停用，无法办理出入库", status=409)

        before = int(row["stock"] or 0)
        if kind == "OUT" and before < quantity:
            raise ApiError(f"库存不足，当前仅剩 {before} {row['unit']}", status=409)
        after = before + quantity if kind == "IN" else before - quantity

        stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        if kind == "OUT":
            cursor = conn.execute(
                "UPDATE products SET stock = stock - ?, updated_at = ? WHERE id = ? AND stock >= ?",
                (quantity, stamp, product_id, quantity),
            )
            if cursor.rowcount != 1:
                raise ApiError("库存不足，请刷新后重试", status=409)
        else:
            cursor = conn.execute(
                "UPDATE products SET stock = stock + ?, updated_at = ? WHERE id = ?",
                (quantity, stamp, product_id),
            )
            if cursor.rowcount != 1:
                raise ApiError("库存更新失败，请重试", status=409)

        cursor = conn.execute(
            """
            INSERT INTO stock_records
                (order_no, product_id, product_name, product_code, type, quantity,
                 before_stock, after_stock, operator_id, operator_name, remark, created_at)
            VALUES ('', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                row["name"],
                row["code"],
                kind,
                quantity,
                before,
                after,
                user.id,
                user.real_name,
                remark,
                stamp,
            ),
        )
        record_id = cursor.lastrowid
        prefix = "IN" if kind == "IN" else "OUT"
        order_no = f"{prefix}{now:%Y%m%d}{record_id:05d}"
        conn.execute("UPDATE stock_records SET order_no = ? WHERE id = ?", (order_no, record_id))

    return {
        "product_id": product_id,
        "product_name": row["name"],
        "stock": after,
        "quantity": quantity,
        "type": kind,
        "order_no": order_no,
        "created_at": stamp,
    }


@bp.post("/in")
@require_perm("stock:in")
def stock_in():
    result = _change_stock("IN")
    return ok(result, f"入库成功，{result['product_name']} 当前库存 {result['stock']}")


@bp.post("/out")
@require_perm("stock:out")
def stock_out():
    result = _change_stock("OUT")
    return ok(result, f"出库成功，{result['product_name']} 当前库存 {result['stock']}")


@bp.get("/records")
@require_perm("stock:view")
def list_records():
    record_type = request.args.get("type", "")
    keyword = clean_str(request.args.get("keyword"), 50)
    product_id = request.args.get("product_id")
    date_from = parse_day(request.args.get("date_from"))
    date_to = parse_day(request.args.get("date_to"), end=True)
    page, page_size = page_args()

    query = session.query(StockRecord)
    if record_type in {"IN", "OUT"}:
        query = query.filter(StockRecord.type == record_type)
    if product_id:
        query = query.filter(StockRecord.product_id == as_int(product_id, "product_id"))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            StockRecord.product_name.like(like)
            | StockRecord.order_no.like(like)
            | StockRecord.product_code.like(like)
        )
    if date_from:
        query = query.filter(StockRecord.created_at >= date_from)
    if date_to:
        query = query.filter(StockRecord.created_at <= date_to)

    total = query.count()
    rows = (
        query.order_by(StockRecord.created_at.desc(), StockRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok(
        {
            "items": [serialize_record(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@bp.get("/records/recent")
@require_perm("stock:view")
def recent_records():
    limit = min(as_int(request.args.get("limit", 10), "limit", 1, 50), 50)
    rows = session.query(StockRecord).order_by(StockRecord.id.desc()).limit(limit).all()
    return ok({"items": [serialize_record(r) for r in rows]})


@bp.get("/today")
@require_perm("stock:view")
def today_stats():
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    next_day = start + timedelta(days=1)
    rows = (
        session.query(StockRecord)
        .filter(StockRecord.created_at >= start, StockRecord.created_at < next_day)
        .all()
    )
    return ok(
        {
            "in": sum(r.quantity for r in rows if r.type == "IN"),
            "out": sum(r.quantity for r in rows if r.type == "OUT"),
            "count": len(rows),
        }
    )
