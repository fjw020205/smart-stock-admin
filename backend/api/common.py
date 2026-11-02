"""接口公共工具：统一响应、参数校验、分页。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from flask import jsonify, request

from ..config import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code if code is not None else status


def ok(data=None, message: str = "ok"):
    return jsonify({"code": 0, "message": message, "data": data})


def payload() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}
    return data


def require_fields(data: dict, *fields: str) -> None:
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ApiError(f"缺少必填参数：{field}")


def clean_str(value, max_len: int = 100, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text[:max_len]


def as_int(value, field: str, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{field}必须为整数")
    if minimum is not None and number < minimum:
        raise ApiError(f"{field}不能小于 {minimum}")
    if maximum is not None and number > maximum:
        raise ApiError(f"{field}不能大于 {maximum}")
    return number


def as_float(value, field: str, minimum: float = 0.0) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        raise ApiError(f"{field}必须为数字")
    if number < minimum:
        raise ApiError(f"{field}不能小于 {minimum}")
    return round(number, 2)


def as_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def page_args() -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(request.args.get("page_size", PAGE_SIZE_DEFAULT))
    except (TypeError, ValueError):
        size = PAGE_SIZE_DEFAULT
    return page, max(1, min(size, PAGE_SIZE_MAX))


def fmt_dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def fmt_date(value: date | None) -> str | None:
    return value.strftime("%Y-%m-%d") if value else None


def as_money(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return round(float(value), 2)


def parse_day(value: str | None, end: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        day = datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        raise ApiError("日期格式应为 YYYY-MM-DD")
    if end:
        return day.replace(hour=23, minute=59, second=59)
    return day
