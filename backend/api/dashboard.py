"""工作台看板：统计卡、低库存预警、趋势、最近操作。"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from flask import Blueprint
from sqlalchemy import func

from ..db import session
from ..models import Product, StockRecord
from ..security import require_perm
from .common import fmt_dt, ok

bp = Blueprint("dashboard", __name__)


@bp.get("/summary")
@require_perm("dashboard:view")
def summary():
    today_start = datetime.combine(date.today(), time.min)
    tomorrow = today_start + timedelta(days=1)

    product_total = session.query(func.count(Product.id)).filter(Product.status.is_(True)).scalar() or 0
    stock_total = (
        session.query(func.coalesce(func.sum(Product.stock), 0))
        .filter(Product.status.is_(True))
        .scalar()
        or 0
    )

    today_rows = (
        session.query(StockRecord.type, func.coalesce(func.sum(StockRecord.quantity), 0))
        .filter(StockRecord.created_at >= today_start, StockRecord.created_at < tomorrow)
        .group_by(StockRecord.type)
        .all()
    )
    today_map = {row[0]: int(row[1]) for row in today_rows}

    low_query = session.query(Product).filter(
        Product.status.is_(True), Product.stock < Product.safety_stock
    )
    low_count = low_query.count()
    low_products = low_query.order_by((Product.stock - Product.safety_stock).asc()).limit(20).all()

    start_day = today_start - timedelta(days=6)
    trend_rows = (
        session.query(
            func.date(StockRecord.created_at),
            StockRecord.type,
            func.coalesce(func.sum(StockRecord.quantity), 0),
        )
        .filter(StockRecord.created_at >= start_day)
        .group_by(func.date(StockRecord.created_at), StockRecord.type)
        .all()
    )
    trend_map: dict[str, dict[str, int]] = {}
    for day_value, record_type, qty in trend_rows:
        key = str(day_value)[:10]
        trend_map.setdefault(key, {"in": 0, "out": 0})[record_type.lower() if record_type == "OUT" else "in"] = int(qty)

    trend = []
    for offset in range(7):
        day = (start_day + timedelta(days=offset)).date()
        key = day.isoformat()
        values = trend_map.get(key, {"in": 0, "out": 0})
        trend.append({"date": key, "label": day.strftime("%m-%d"), "in": values.get("in", 0), "out": values.get("out", 0)})

    recent = (
        session.query(StockRecord)
        .order_by(StockRecord.created_at.desc(), StockRecord.id.desc())
        .limit(10)
        .all()
    )

    return ok(
        {
            "cards": {
                "product_total": int(product_total),
                "stock_total": int(stock_total),
                "today_in": int(today_map.get("IN", 0)),
                "today_out": int(today_map.get("OUT", 0)),
                "low_stock_count": int(low_count),
            },
            "low_stock": [
                {
                    "id": p.id,
                    "code": p.code,
                    "name": p.name,
                    "category": p.category or "",
                    "unit": p.unit or "件",
                    "stock": int(p.stock or 0),
                    "safety_stock": int(p.safety_stock or 0),
                    "gap": int(p.safety_stock or 0) - int(p.stock or 0),
                }
                for p in low_products
            ],
            "trend": trend,
            "recent": [
                {
                    "id": r.id,
                    "order_no": r.order_no,
                    "product_name": r.product_name,
                    "type": r.type,
                    "quantity": r.quantity,
                    "after_stock": r.after_stock,
                    "operator_name": r.operator_name,
                    "created_at": fmt_dt(r.created_at),
                }
                for r in recent
            ],
            "generated_at": fmt_dt(datetime.now()),
        }
    )
