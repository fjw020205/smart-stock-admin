"""Flask 应用工厂：JSON 接口 + 两套前端静态托管。"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .api import auth, dashboard, menus, products, roles, stock, users
from .api.common import ApiError
from .config import APP_NAME, APP_SUBTITLE, VERSION, resource_root
from .db import session
from .security import AuthError

logger = logging.getLogger("smartstock")

BLUEPRINTS = [
    (auth.bp, "/api/auth"),
    (users.bp, "/api/users"),
    (roles.bp, "/api/roles"),
    (menus.bp, "/api/menus"),
    (products.bp, "/api/products"),
    (stock.bp, "/api/stock"),
    (dashboard.bp, "/api/dashboard"),
]


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=None,
        template_folder=str(resource_root() / "templates"),
    )
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

    for blueprint, prefix in BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=prefix)

    @app.get("/api/health")
    def health():
        return jsonify({"code": 0, "message": "ok", "data": {"app": "smart-stock", "version": VERSION}})

    @app.get("/")
    def entry():
        return render_template(
            "entry.html", app_name=APP_NAME, subtitle=APP_SUBTITLE, version=VERSION
        )

    @app.get("/pc")
    @app.get("/pc/")
    @app.get("/pc/<path:asset_path>")
    def pc_app(asset_path: str = "index.html"):
        return _spa("pc", asset_path)

    @app.get("/m")
    @app.get("/m/")
    @app.get("/m/<path:asset_path>")
    def mobile_app(asset_path: str = "index.html"):
        return _spa("m", asset_path)

    @app.get("/favicon.ico")
    def favicon():
        for candidate in ("pc/favicon.svg", "favicon.svg"):
            path = resource_root() / "static" / candidate
            if path.is_file():
                return send_from_directory(path.parent, path.name, max_age=86400)
        return ("", 204)

    @app.teardown_appcontext
    def cleanup(_exception=None):
        session.remove()

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify({"code": error.code, "message": error.message, "data": None}), error.status

    @app.errorhandler(AuthError)
    def handle_auth_error(error: AuthError):
        return jsonify({"code": error.code, "message": error.message, "data": None}), error.status

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if request.path.startswith("/api/"):
            return (
                jsonify({"code": error.code, "message": error.description or "请求异常", "data": None}),
                error.code,
            )
        return error

    @app.errorhandler(Exception)
    def handle_unexpected(error: Exception):
        logger.exception("未处理异常: %s", error)
        if request.path.startswith("/api/"):
            return jsonify({"code": 500, "message": "服务器开小差了，请稍后再试", "data": None}), 500
        return ("服务器内部错误", 500, {"Content-Type": "text/plain; charset=utf-8"})

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


def _spa(build: str, asset_path: str):
    base: Path = resource_root() / "static" / build
    index = base / "index.html"
    if not index.is_file():
        return (
            f"前端资源缺失：static/{build}/index.html\n请先执行构建脚本 build_exe.bat，"
            "或直接使用已打包的 exe。",
            503,
            {"Content-Type": "text/plain; charset=utf-8"},
        )

    if asset_path and asset_path != "index.html":
        candidate = base / asset_path
        try:
            is_file = candidate.is_file()
        except OSError:
            is_file = False
        if is_file:
            response = send_from_directory(base, asset_path)
            if "/assets/" in f"/{asset_path}":
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                response.headers["Cache-Control"] = "public, max-age=3600"
            return response
        if "." in Path(asset_path).name:
            return ("Not Found", 404, {"Content-Type": "text/plain; charset=utf-8"})

    response = send_from_directory(base, "index.html")
    response.headers["Cache-Control"] = "no-store"
    return response
