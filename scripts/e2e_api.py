"""端到端接口测试：覆盖登录、商品、库存、用户、角色、菜单、看板、安全与并发。

运行前先启动服务：python run.py（端口 8000，使用独立测试数据目录）
运行：python scripts/e2e_api.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
ARTIFACTS = Path(os.environ.get("ARTIFACTS", "build/test-artifacts"))
ARTIFACTS.mkdir(parents=True, exist_ok=True)

results: list[dict] = []
tokens: dict[str, str] = {}
ids: dict[str, int] = {}


def request(method: str, path: str, data=None, token: str | None = None):
    url = BASE + urllib.parse.quote(path, safe="/?&=:%")
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        text = exc.read().decode("utf-8")
    except Exception as exc:  # 连接失败等
        return 0, {"message": str(exc)}, str(exc)
    try:
        return status, json.loads(text), text
    except json.JSONDecodeError:
        return status, None, text


def case(module: str, name: str, func):
    started = time.perf_counter()
    detail = ""
    try:
        detail = func() or ""
        results.append(
            {"module": module, "name": name, "status": "PASS", "ms": round((time.perf_counter() - started) * 1000, 1), "detail": detail}
        )
        print(f"[PASS] {module:6s} {name} {detail}")
    except AssertionError as exc:
        results.append(
            {"module": module, "name": name, "status": "FAIL", "ms": round((time.perf_counter() - started) * 1000, 1), "detail": str(exc)}
        )
        print(f"[FAIL] {module:6s} {name} -> {exc}")
    except Exception as exc:  # noqa: BLE001
        results.append(
            {"module": module, "name": name, "status": "ERROR", "ms": round((time.perf_counter() - started) * 1000, 1), "detail": repr(exc)}
        )
        print(f"[ERROR] {module:6s} {name} -> {exc!r}")


def expect(condition, message: str):
    if not condition:
        raise AssertionError(message)


def login(username: str, password: str):
    return request("POST", "/api/auth/login", {"username": username, "password": password})


# ---------------------------------------------------------------- 认证
def auth_cases():
    state: dict = {}

    def health():
        status, body, _ = request("GET", "/api/health")
        expect(status == 200 and body["data"]["app"] == "smart-stock", f"status={status}")

    def wrong_password():
        status, body, _ = login("admin", "wrong-pass1")
        expect(status == 401 and body["code"] == 401, f"status={status}")

    def admin_login():
        status, body, _ = login("admin", "Admin@123456")
        expect(status == 200, f"status={status}")
        data = body["data"]
        expect(data["user"]["must_change_password"] is True, "管理员首次登录应强制改密")
        expect(len(data["menus"]) == 4, f"菜单根节点应为 4，实际 {len(data['menus'])}")
        expect(len(data["permissions"]) >= 18, f"权限数异常 {len(data['permissions'])}")
        state["token"] = data["token"]

    def blocked_before_change():
        status, body, _ = request("GET", "/api/products", token=state["token"])
        expect(status == 403 and body["code"] == 1002, f"status={status} code={body.get('code')}")

    def weak_password():
        status, body, _ = request(
            "PUT",
            "/api/auth/password",
            {"old_password": "Admin@123456", "new_password": "12345678"},
            token=state["token"],
        )
        expect(status == 400, f"status={status}")

    def change_password():
        status, body, _ = request(
            "PUT",
            "/api/auth/password",
            {"old_password": "Admin@123456", "new_password": "Admin@2026"},
            token=state["token"],
        )
        expect(status == 200, f"status={status}")
        state["new_token"] = body["data"]["token"]
        tokens["admin"] = body["data"]["token"]

    def old_token_invalid():
        status, body, _ = request("GET", "/api/auth/me", token=state["token"])
        expect(status == 401, f"改密后旧 token 仍可用 status={status}")

    def me():
        status, body, _ = request("GET", "/api/auth/me", token=tokens["admin"])
        expect(status == 200 and body["data"]["user"]["username"] == "admin", f"status={status}")
        expect("user:view" in body["data"]["permissions"], "缺少 user:view")

    def staff_login():
        status, body, _ = login("staff", "Staff@123456")
        expect(status == 200, f"status={status}")
        data = body["data"]
        expect(data["user"]["role"]["code"] == "staff", "角色应为 staff")
        expect([m["name"] for m in data["menus"]] == ["工作台", "商品管理", "库存作业"], f"员工菜单异常: {[m['name'] for m in data['menus']]}")
        expect(data["user"]["must_change_password"] is False, "员工不应强制改密")
        tokens["staff"] = data["token"]

    def staff_forbidden():
        for path in ("/api/users", "/api/roles", "/api/menus"):
            status, body, _ = request("GET", path, token=tokens["staff"])
            expect(status == 403, f"{path} status={status}")

    def bad_token():
        status, _, _ = request("GET", "/api/auth/me", token="abc.def.ghi")
        expect(status == 401, f"status={status}")

    def logout():
        status, _, _ = request("POST", "/api/auth/logout", token=tokens["admin"])
        expect(status == 200, f"status={status}")

    def lock_account():
        status, _, _ = request(
            "POST",
            "/api/users",
            {
                "username": "lockuser",
                "password": "Lock@1234",
                "real_name": "锁定测试",
                "role_id": state["staff_role_id"],
                "must_change_password": False,
            },
            token=tokens["admin"],
        )
        expect(status == 200, f"创建用户失败 status={status}")
        for _ in range(5):
            login("lockuser", "bad-pass1")
        status, body, _ = login("lockuser", "Lock@1234")
        expect(status == 403 and "锁定" in body["message"], f"锁定未生效 status={status}")

    def roles_for_ids():
        status, body, _ = request("GET", "/api/roles", token=tokens["admin"])
        expect(status == 200, f"status={status}")
        state["staff_role_id"] = next(r["id"] for r in body["data"]["items"] if r["code"] == "staff")
        state["admin_role_id"] = next(r["id"] for r in body["data"]["items"] if r["code"] == "admin")

    # 创建锁定测试用户前需要 staff_role_id，先查角色
    case("认证", "健康检查", health)
    case("认证", "错误密码返回 401", wrong_password)
    case("认证", "管理员登录与首次改密标记", admin_login)
    case("认证", "未改密时业务接口被拦截", blocked_before_change)
    case("认证", "弱密码被拒绝", weak_password)
    case("认证", "修改密码成功并签发新 token", change_password)
    case("认证", "改密后旧 token 失效", old_token_invalid)
    case("认证", "获取当前用户与权限", me)
    case("认证", "员工登录与菜单范围", staff_login)
    case("认证", "员工访问系统管理接口被拒绝", staff_forbidden)
    case("认证", "伪造 token 被拒绝", bad_token)
    case("认证", "退出登录", logout)
    case("认证", "查询角色列表（准备数据）", roles_for_ids)
    case("认证", "连续错密码触发锁定", lock_account)


# ---------------------------------------------------------------- 商品
def product_cases():
    def create_plain():
        status, body, _ = request(
            "POST",
            "/api/products",
            {"name": "测试商品A", "category": "测试分类", "spec": "1件/盒", "unit": "盒", "safety_stock": 5, "sale_price": 9.9},
            token=tokens["admin"],
        )
        expect(status == 200, f"status={status} message={body.get('message')}")
        data = body["data"]
        expect(data["stock"] == 0 and data["code"].startswith("SP"), f"编码/库存异常 {data}")
        ids["product_a"] = data["id"]

    def create_initial():
        status, body, _ = request(
            "POST",
            "/api/products",
            {"code": "TST002", "name": "测试商品B", "unit": "件", "safety_stock": 5, "initial_stock": 10, "cost_price": 5, "sale_price": 12},
            token=tokens["admin"],
        )
        expect(status == 200, f"status={status}")
        data = body["data"]
        expect(data["stock"] == 10, f"期初库存异常 {data['stock']}")
        ids["product_b"] = data["id"]

    def duplicate_code():
        status, body, _ = request("POST", "/api/products", {"name": "重复编码", "code": "TST002"}, token=tokens["admin"])
        expect(status == 409, f"status={status}")

    def update_product():
        status, body, _ = request(
            "PUT",
            f"/api/products/{ids['product_b']}",
            {"name": "测试商品B-改", "sale_price": 19.9, "safety_stock": 6},
            token=tokens["admin"],
        )
        expect(status == 200, f"status={status}")
        data = body["data"]
        expect(data["name"] == "测试商品B-改" and data["stock"] == 10, f"更新异常 {data}")

    def search_filter():
        status, body, _ = request("GET", "/api/products?keyword=测试商品", token=tokens["admin"])
        expect(status == 200 and body["data"]["total"] >= 2, f"total={body['data'].get('total')}")
        status, body, _ = request("GET", "/api/products?low_stock=1", token=tokens["admin"])
        expect(status == 200, "低库存筛选失败")
        expect(any(item["id"] == ids["product_a"] for item in body["data"]["items"]), "低库存列表缺少 0 库存商品")

    def detail_404():
        status, _, _ = request("GET", "/api/products/999999", token=tokens["admin"])
        expect(status == 404, f"status={status}")

    def delete_without_records():
        status, _, _ = request("DELETE", f"/api/products/{ids['product_a']}", token=tokens["admin"])
        expect(status == 200, f"status={status}")

    def delete_with_records():
        status, body, _ = request("DELETE", f"/api/products/{ids['product_b']}", token=tokens["admin"])
        expect(status == 409, f"status={status}")

    def invalid_safety():
        status, _, _ = request("POST", "/api/products", {"name": "非法库存", "safety_stock": -1}, token=tokens["admin"])
        expect(status == 400, f"status={status}")

    def create_low_stock():
        status, body, _ = request(
            "POST",
            "/api/products",
            {"code": "TST003", "name": "低库存商品", "initial_stock": 3, "safety_stock": 5},
            token=tokens["admin"],
        )
        expect(status == 200, f"status={status}")
        ids["product_c"] = body["data"]["id"]
        expect(body["data"]["low_stock"] is True, "低库存标记未生效")

    case("商品", "新增商品（自动编码）", create_plain)
    case("商品", "新增商品（期初库存）", create_initial)
    case("商品", "重复编码被拒绝", duplicate_code)
    case("商品", "编辑商品且库存不变", update_product)
    case("商品", "搜索与低库存筛选", search_filter)
    case("商品", "不存在的商品返回 404", detail_404)
    case("商品", "删除无流水商品", delete_without_records)
    case("商品", "删除有流水商品被拒绝", delete_with_records)
    case("商品", "非法安全库存被拒绝", invalid_safety)
    case("商品", "创建低库存商品用于看板", create_low_stock)


# ---------------------------------------------------------------- 库存
def stock_cases():
    def inbound():
        status, body, _ = request(
            "POST", "/api/stock/in", {"product_id": ids["product_b"], "quantity": 5, "remark": "测试入库"}, token=tokens["admin"]
        )
        expect(status == 200, f"status={status}")
        expect(body["data"]["stock"] == 15, f"stock={body['data'].get('stock')}")
        expect(body["data"]["order_no"].startswith("IN"), "单号前缀错误")

    def outbound():
        status, body, _ = request(
            "POST", "/api/stock/out", {"product_id": ids["product_b"], "quantity": 3, "remark": "测试出库"}, token=tokens["admin"]
        )
        expect(status == 200, f"status={status}")
        expect(body["data"]["stock"] == 12, f"stock={body['data'].get('stock')}")

    def oversell():
        status, body, _ = request("POST", "/api/stock/out", {"product_id": ids["product_b"], "quantity": 999}, token=tokens["admin"])
        expect(status == 409 and "库存不足" in body["message"], f"status={status}")
        status, body, _ = request("GET", f"/api/products/{ids['product_b']}", token=tokens["admin"])
        expect(body["data"]["stock"] == 12, "超卖拦截后库存被修改")

    def zero_quantity():
        status, _, _ = request("POST", "/api/stock/in", {"product_id": ids["product_b"], "quantity": 0}, token=tokens["admin"])
        expect(status == 400, f"status={status}")

    def records_filter():
        status, body, _ = request("GET", f"/api/stock/records?product_id={ids['product_b']}", token=tokens["admin"])
        expect(status == 200 and body["data"]["total"] == 3, f"total={body['data'].get('total')}")
        status, body, _ = request("GET", "/api/stock/records?type=OUT", token=tokens["admin"])
        expect(status == 200 and body["data"]["total"] >= 1, "出库流水缺失")
        status, body, _ = request("GET", "/api/stock/records?keyword=TST002", token=tokens["admin"])
        expect(status == 200 and body["data"]["total"] >= 3, "按编码搜索流水失败")

    def recent():
        status, body, _ = request("GET", "/api/stock/records/recent?limit=5", token=tokens["admin"])
        expect(status == 200 and len(body["data"]["items"]) <= 5, f"len={len(body['data'].get('items', []))}")

    def disabled_product():
        request("PUT", f"/api/products/{ids['product_b']}", {"status": False}, token=tokens["admin"])
        status, body, _ = request("POST", "/api/stock/in", {"product_id": ids["product_b"], "quantity": 1}, token=tokens["admin"])
        expect(status == 409, f"status={status}")
        request("PUT", f"/api/products/{ids['product_b']}", {"status": True}, token=tokens["admin"])

    def concurrent_inbound():
        before_status, before_body, _ = request("GET", f"/api/products/{ids['product_b']}", token=tokens["admin"])
        before = before_body["data"]["stock"]
        errors: list[str] = []
        lock = threading.Lock()

        def worker():
            status, body, _ = request(
                "POST", "/api/stock/in", {"product_id": ids["product_b"], "quantity": 1, "remark": "并发测试"}, token=tokens["admin"]
            )
            if status != 200:
                with lock:
                    errors.append(f"{status}:{body.get('message')}")

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        expect(not errors, f"并发失败 {errors[:3]}")
        status, body, _ = request("GET", f"/api/products/{ids['product_b']}", token=tokens["admin"])
        after = body["data"]["stock"]
        expect(after == before + 10, f"并发后库存 {after}，期望 {before + 10}")
        return f"{before}→{after}"

    case("库存", "入库并更新库存", inbound)
    case("库存", "出库并更新库存", outbound)
    case("库存", "库存不足拦截且不改库存", oversell)
    case("库存", "数量为 0 被拒绝", zero_quantity)
    case("库存", "流水按商品/类型/编码筛选", records_filter)
    case("库存", "最近流水条数限制", recent)
    case("库存", "停用商品禁止出入库", disabled_product)
    case("库存", "10 并发入库库存准确", concurrent_inbound)


# ---------------------------------------------------------------- 用户
def user_cases():
    def create():
        status, body, _ = request(
            "POST",
            "/api/users",
            {"username": "tester1", "password": "Tester@123", "real_name": "测试员一", "phone": "13900000001", "role_id": 2, "must_change_password": False},
            token=tokens["admin"],
        )
        expect(status == 200, f"status={status} message={body.get('message')}")
        ids["tester1"] = body["data"]["id"]
        expect(body["data"]["role"]["code"] == "staff", "角色错误")

    def duplicate():
        status, _, _ = request(
            "POST",
            "/api/users",
            {"username": "tester1", "password": "Tester@123", "real_name": "重复", "role_id": 2},
            token=tokens["admin"],
        )
        expect(status == 409, f"status={status}")

    def list_search():
        status, body, _ = request("GET", "/api/users?keyword=tester1", token=tokens["admin"])
        expect(status == 200 and body["data"]["total"] >= 1, "搜索用户失败")
        expect("password_hash" not in json.dumps(body["data"]), "接口泄露了密码哈希")

    def update():
        status, body, _ = request("PUT", f"/api/users/{ids['tester1']}", {"real_name": "测试员一改", "phone": "13900000002"}, token=tokens["admin"])
        expect(status == 200 and body["data"]["real_name"] == "测试员一改", f"status={status}")

    def reset_password():
        status, _, _ = request("POST", f"/api/users/{ids['tester1']}/reset-password", {"new_password": "Reset@123"}, token=tokens["admin"])
        expect(status == 200, f"status={status}")
        status, _, _ = login("tester1", "Tester@123")
        expect(status == 401, "旧密码仍可登录")
        status, body, _ = login("tester1", "Reset@123")
        expect(status == 200, f"新密码登录失败 {status}")
        expect(body["data"]["user"]["must_change_password"] is True, "重置后未要求改密")
        tokens["tester1"] = body["data"]["token"]

    def must_change_gate():
        status, body, _ = request("GET", "/api/products", token=tokens["tester1"])
        expect(status == 403 and body["code"] == 1002, f"status={status}")

    def disable_user():
        status, _, _ = request("PATCH", f"/api/users/{ids['tester1']}/status", {"status": False}, token=tokens["admin"])
        expect(status == 200, f"status={status}")
        status, body, _ = login("tester1", "Reset@123")
        expect(status == 403, f"停用后仍可登录 status={status}")
        expect("停用" in body["message"], f"message={body.get('message')}")

    def self_guard():
        status, body, _ = request("DELETE", "/api/users/1", token=tokens["admin"])
        expect(status == 409, f"删除自己 status={status}")
        status, body, _ = request("PATCH", "/api/users/1/status", {"status": False}, token=tokens["admin"])
        expect(status == 409, f"停用自己 status={status}")

    def menu_override():
        status, body, _ = request("GET", "/api/users?keyword=staff", token=tokens["admin"])
        expect(status == 200, f"查询员工失败 status={status}")
        staff_user = next(item for item in body["data"]["items"] if item["username"] == "staff")
        staff_id = staff_user["id"]
        status, body, _ = request("GET", f"/api/users/{staff_id}/menus", token=tokens["admin"])
        expect(status == 200 and body["data"]["mode"] == "inherit", "默认应为继承")
        status, _, _ = request("PUT", f"/api/users/{staff_id}/menus", {"mode": "custom", "menu_ids": []}, token=tokens["admin"])
        expect(status == 400, f"空自定义菜单 status={status}")
        status, _, _ = request("PUT", f"/api/users/{staff_id}/menus", {"mode": "custom", "menu_ids": [2]}, token=tokens["admin"])
        expect(status == 200, f"status={status}")
        status, body, _ = login("staff", "Staff@123456")
        expect([m["name"] for m in body["data"]["menus"]] == ["商品管理"], f"用户级菜单异常 {[m['name'] for m in body['data']['menus']]}")
        status, _, _ = request("PUT", f"/api/users/{staff_id}/menus", {"mode": "inherit"}, token=tokens["admin"])
        expect(status == 200, f"status={status}")

    def delete_created():
        status, _, _ = request("DELETE", f"/api/users/{ids['tester1']}", token=tokens["admin"])
        expect(status == 200, f"status={status}")

    case("用户", "新增用户", create)
    case("用户", "重复账号被拒绝", duplicate)
    case("用户", "列表搜索且不泄露密码", list_search)
    case("用户", "编辑姓名与手机号", update)
    case("用户", "重置密码与强制改密", reset_password)
    case("用户", "未改密时业务接口被拦截", must_change_gate)
    case("用户", "停用账号后无法登录", disable_user)
    case("用户", "不能删除/停用自己", self_guard)
    case("用户", "用户级菜单覆盖与恢复", menu_override)
    case("用户", "删除用户", delete_created)


# ---------------------------------------------------------------- 角色与权限
def role_cases():
    def create_role():
        status, body, _ = request(
            "POST", "/api/roles", {"code": "auditor", "name": "审计员", "description": "只读商品与流水"}, token=tokens["admin"]
        )
        expect(status == 200, f"status={status} message={body.get('message')}")
        ids["auditor_role"] = body["data"]["id"]

    def duplicate_role():
        status, _, _ = request("POST", "/api/roles", {"code": "auditor", "name": "重复"}, token=tokens["admin"])
        expect(status == 409, f"status={status}")

    def set_menus_autogrant():
        status, body, _ = request("PUT", f"/api/roles/{ids['auditor_role']}/menus", {"menu_ids": [2]}, token=tokens["admin"])
        expect(status == 200, f"status={status}")
        expect("product:view" in body["data"]["permissions"], f"菜单未自动补齐权限: {body['data']['permissions']}")

    def set_permissions():
        status, body, _ = request(
            "PUT", f"/api/roles/{ids['auditor_role']}/permissions", {"permissions": ["product:view", "stock:view"]}, token=tokens["admin"]
        )
        expect(status == 200 and "stock:view" in body["data"]["permissions"], f"status={status}")

    def role_user_scope():
        status, body, _ = request(
            "POST",
            "/api/users",
            {"username": "auditor1", "password": "Audit@123", "real_name": "审计一号", "role_id": ids["auditor_role"], "must_change_password": False},
            token=tokens["admin"],
        )
        expect(status == 200, f"status={status}")
        ids["auditor_user"] = body["data"]["id"]
        status, body, _ = login("auditor1", "Audit@123")
        expect(status == 200, f"login status={status}")
        expect([m["name"] for m in body["data"]["menus"]] == ["商品管理"], f"角色菜单异常 {[m['name'] for m in body['data']['menus']]}")
        tokens["auditor"] = body["data"]["token"]
        status, _, _ = request("GET", "/api/users", token=tokens["auditor"])
        expect(status == 403, f"越权访问用户 status={status}")

    def update_role():
        status, body, _ = request("PUT", f"/api/roles/{ids['auditor_role']}", {"name": "审计员（改）"}, token=tokens["admin"])
        expect(status == 200 and body["data"]["name"] == "审计员（改）", f"status={status}")

    def guard_builtin():
        status, body, _ = request("PUT", "/api/roles/1/menus", {"menu_ids": [1]}, token=tokens["admin"])
        expect(status == 409, f"admin 角色被修改 status={status}")
        status, _, _ = request("DELETE", "/api/roles/2", token=tokens["admin"])
        expect(status == 409, f"内置角色被删除 status={status}")

    def delete_in_use():
        status, body, _ = request("DELETE", f"/api/roles/{ids['auditor_role']}", token=tokens["admin"])
        expect(status == 409, f"有用户的角色被删除 status={status}")

    def delete_user_then_role():
        status, _, _ = request("DELETE", f"/api/users/{ids['auditor_user']}", token=tokens["admin"])
        expect(status == 200, f"删除用户 status={status}")
        status, _, _ = request("DELETE", f"/api/roles/{ids['auditor_role']}", token=tokens["admin"])
        expect(status == 200, f"删除角色 status={status}")

    case("角色", "新建角色", create_role)
    case("角色", "角色标识重复被拒绝", duplicate_role)
    case("角色", "保存菜单自动补齐页面权限", set_menus_autogrant)
    case("角色", "保存功能权限", set_permissions)
    case("角色", "角色用户登录后的权限与菜单", role_user_scope)
    case("角色", "修改角色资料", update_role)
    case("角色", "内置角色保护", guard_builtin)
    case("角色", "有用户的角色不可删除", delete_in_use)
    case("角色", "移除用户后可删除角色", delete_user_then_role)


# ---------------------------------------------------------------- 菜单
def menu_cases():
    def list_tree():
        status, body, _ = request("GET", "/api/menus", token=tokens["admin"])
        expect(status == 200 and len(body["data"]["items"]) == 4, f"根菜单数={len(body['data'].get('items', []))}")
        flat = []
        def walk(items):
            for item in items:
                flat.append(item)
                walk(item.get("children", []))
        walk(body["data"]["items"])
        expect(len(flat) == 10, f"菜单总数={len(flat)}")
        ids["menus"] = {item["path"]: item["id"] for item in flat}

    def registry():
        status, body, _ = request("GET", "/api/menus/registry", token=tokens["admin"])
        expect(status == 200 and len(body["data"]["pages"]) == 8, f"页面数={len(body['data'].get('pages', []))}")
        expect(body["data"]["available"] == [], "所有页面都应已上架")

    def create_group():
        status, body, _ = request("POST", "/api/menus", {"type": "group", "name": "报表中心", "icon": "Folder", "sort": 8}, token=tokens["admin"])
        expect(status == 200, f"status={status}")
        ids["group"] = body["data"]["id"]

    def update_group():
        status, body, _ = request(
            "PUT", f"/api/menus/{ids['group']}", {"name": "数据报表", "sort": 7, "visible": False}, token=tokens["admin"]
        )
        expect(status == 200 and body["data"]["name"] == "数据报表" and body["data"]["visible"] is False, f"status={status}")

    def assign_staff():
        status, body, _ = request("PUT", f"/api/menus/{ids['group']}/roles", {"role_ids": [1, 2]}, token=tokens["admin"])
        expect(status == 200 and 2 in body["data"]["role_ids"], f"role_ids={body['data'].get('role_ids')}")

    def protect_menu_admin():
        status, body, _ = request("PUT", f"/api/menus/{ids['menus']['/system/menus']}", {"visible": False}, token=tokens["admin"])
        expect(status == 409, f"菜单管理被隐藏 status={status}")

    def delete_builtin():
        status, body, _ = request("DELETE", f"/api/menus/{ids['menus']['/products']}", token=tokens["admin"])
        expect(status == 409, f"内置菜单被删除 status={status}")

    def staff_cannot_manage():
        status, _, _ = request("POST", "/api/menus", {"type": "group", "name": "越权分组"}, token=tokens["staff"])
        expect(status == 403, f"status={status}")

    def delete_group():
        status, _, _ = request("DELETE", f"/api/menus/{ids['group']}", token=tokens["admin"])
        expect(status == 200, f"status={status}")

    case("菜单", "菜单树与角色信息", list_tree)
    case("菜单", "页面注册表", registry)
    case("菜单", "新增分组", create_group)
    case("菜单", "编辑分组名称/排序/显隐", update_group)
    case("菜单", "配置菜单可见角色", assign_staff)
    case("菜单", "菜单管理入口禁止隐藏", protect_menu_admin)
    case("菜单", "内置菜单禁止删除", delete_builtin)
    case("菜单", "员工无权维护菜单", staff_cannot_manage)
    case("菜单", "删除自定义分组", delete_group)


# ---------------------------------------------------------------- 看板
def dashboard_cases():
    def summary():
        status, body, _ = request("GET", "/api/dashboard/summary", token=tokens["admin"])
        expect(status == 200, f"status={status}")
        data = body["data"]
        expect(data["cards"]["product_total"] >= 1, "商品总数异常")
        expect(len(data["trend"]) == 7, f"趋势天数={len(data['trend'])}")
        expect(any(item["id"] == ids["product_c"] for item in data["low_stock"]), "低库存商品未进入看板")
        expect(data["cards"]["low_stock_count"] >= 1, "低库存数量异常")

    def trend_today():
        status, body, _ = request("GET", "/api/dashboard/summary", token=tokens["admin"])
        today = body["data"]["trend"][-1]
        expect(today["in"] >= 15, f"今日入库趋势={today['in']}")

    def staff_dashboard():
        status, body, _ = request("GET", "/api/dashboard/summary", token=tokens["staff"])
        expect(status == 200, f"员工看板 status={status}")

    case("看板", "统计卡/低库存/最近操作", summary)
    case("看板", "7 日趋势包含今日数据", trend_today)
    case("看板", "员工可查看看板", staff_dashboard)


# ---------------------------------------------------------------- 安全与边界
def security_cases():
    def sql_injection():
        status, body, _ = request("GET", "/api/products?keyword=%27%20OR%201%3D1%20--", token=tokens["admin"])
        expect(status == 200 and body["data"]["total"] == 0, f"疑似注入生效 total={body['data'].get('total')}")

    def page_size_cap():
        status, body, _ = request("GET", "/api/products?page_size=999", token=tokens["admin"])
        expect(status == 200 and body["data"]["page_size"] == 100, f"page_size={body['data'].get('page_size')}")

    def unknown_api():
        status, body, _ = request("GET", "/api/not-exists")
        expect(status == 404 and body["code"] == 404, f"status={status} body={body}")

    def method_not_allowed():
        status, body, _ = request("GET", "/api/auth/login")
        expect(status == 405, f"status={status}")
        expect(body is not None and "code" in body, "405 未返回 JSON")

    def tampered_token():
        token = tokens["admin"]
        status, _, _ = request("GET", "/api/auth/me", token=token[:-2] + "xx")
        expect(status == 401, f"status={status}")

    def xss_payload_stored_raw():
        status, body, _ = request(
            "POST", "/api/products", {"name": "<script>alert(1)</script>", "code": "XSS001"}, token=tokens["admin"]
        )
        expect(status == 200, f"status={status}")
        expect(body["data"]["name"] == "<script>alert(1)</script>", "特殊字符被意外改写")
        ids["xss_product"] = body["data"]["id"]

    def performance():
        elapsed = []
        for _ in range(20):
            started = time.perf_counter()
            status, _, _ = request("GET", "/api/dashboard/summary", token=tokens["admin"])
            expect(status == 200, f"status={status}")
            elapsed.append((time.perf_counter() - started) * 1000)
        avg = statistics.mean(elapsed)
        p95 = sorted(elapsed)[int(len(elapsed) * 0.95) - 1]
        expect(avg < 200, f"平均耗时过高 {avg:.1f}ms")
        return f"avg={avg:.1f}ms p95={p95:.1f}ms max={max(elapsed):.1f}ms"

    case("安全", "搜索框 SQL 注入无效", sql_injection)
    case("安全", "分页大小上限 100", page_size_cap)
    case("安全", "未知接口返回 JSON 404", unknown_api)
    case("安全", "错误方法返回 405", method_not_allowed)
    case("安全", "篡改 token 被拒绝", tampered_token)
    case("安全", "特殊字符按原文保存（前端转义）", xss_payload_stored_raw)
    case("性能", "看板接口 20 次响应耗时", performance)


def main():
    auth_cases()
    product_cases()
    stock_cases()
    user_cases()
    role_cases()
    menu_cases()
    dashboard_cases()
    security_cases()

    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = [item for item in results if item["status"] != "PASS"]
    summary = {
        "base": BASE,
        "total": len(results),
        "passed": passed,
        "failed": len(failed),
        "duration_ms": sum(item["ms"] for item in results),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (ARTIFACTS / "api-results.json").write_text(
        json.dumps({"summary": summary, "results": results, "tokens": tokens, "ids": ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("\n" + "=" * 64)
    print(f"合计 {summary['total']} 项，通过 {passed} 项，失败 {len(failed)} 项")
    for item in failed:
        print(f"  FAIL {item['module']} / {item['name']}: {item['detail']}")
    print("=" * 64)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
