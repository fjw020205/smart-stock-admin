"""后端接口回归测试：权限、库存一致性、菜单可见性。"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("SMARTSTOCK_DATA_DIR", tempfile.mkdtemp(prefix="smartstock-test-"))

import pytest  # noqa: E402

from backend.app import create_app  # noqa: E402
from backend.db import Base, SessionLocal, engine, init_db  # noqa: E402
from backend.models import Menu, Product, Role, StockRecord, User  # noqa: E402
from backend.seed import seed_all  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    seed_all(db)
    admin = db.query(User).filter(User.username == "admin").one()
    admin.must_change_password = False
    db.commit()
    db.close()

    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def login(client, username="admin", password="Admin@123456"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    return {"Authorization": f"Bearer {data['token']}"}, data


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["data"]["app"] == "smart-stock"


def test_login_and_wrong_password(client):
    headers, data = login(client)
    assert data["user"]["username"] == "admin"
    assert data["menus"]

    bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-pass1"})
    assert bad.status_code == 401
    assert "账号或密码错误" in bad.get_json()["message"]

    unauthorized = client.get("/api/products")
    assert unauthorized.status_code == 401


def test_staff_cannot_touch_system_apis(client):
    headers, data = login(client, "staff", "Staff@123456")
    assert [m["name"] for m in data["menus"]] == ["工作台", "商品管理", "库存作业"]
    assert "user:view" not in data["permissions"]

    assert client.get("/api/users", headers=headers).status_code == 403
    assert client.get("/api/roles", headers=headers).status_code == 403
    assert client.get("/api/menus", headers=headers).status_code == 403
    assert client.get("/api/products", headers=headers).status_code == 200


def test_must_change_password_gate(client):
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").one()
    admin.must_change_password = True
    db.commit()
    db.close()

    headers, data = login(client)
    blocked = client.get("/api/dashboard/summary", headers=headers)
    assert blocked.status_code == 403
    assert blocked.get_json()["code"] == 1002

    changed = client.put(
        "/api/auth/password",
        headers=headers,
        json={"old_password": "Admin@123456", "new_password": "Admin@2026"},
    )
    assert changed.status_code == 200
    new_token = changed.get_json()["data"]["token"]
    ok = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {new_token}"})
    assert ok.status_code == 200


def test_product_create_with_initial_stock(client):
    headers, _ = login(client)
    created = client.post(
        "/api/products",
        headers=headers,
        json={"name": "测试物料", "safety_stock": 5, "initial_stock": 9, "sale_price": 12.5},
    )
    assert created.status_code == 200, created.get_json()
    product = created.get_json()["data"]
    assert product["stock"] == 9
    assert product["code"].startswith("SP")

    records = client.get(f"/api/stock/records?keyword={product['code']}", headers=headers)
    assert records.get_json()["data"]["total"] == 1
    assert records.get_json()["data"]["items"][0]["type"] == "IN"


def test_stock_in_out_and_oversell(client):
    headers, _ = login(client)
    created = client.post(
        "/api/products", headers=headers, json={"name": "库存测试", "safety_stock": 5}
    ).get_json()["data"]
    product_id = created["id"]

    inbound = client.post(
        "/api/stock/in", headers=headers, json={"product_id": product_id, "quantity": 10}
    )
    assert inbound.status_code == 200
    assert inbound.get_json()["data"]["stock"] == 10

    outbound = client.post(
        "/api/stock/out", headers=headers, json={"product_id": product_id, "quantity": 4}
    )
    assert outbound.status_code == 200
    assert outbound.get_json()["data"]["stock"] == 6

    oversell = client.post(
        "/api/stock/out", headers=headers, json={"product_id": product_id, "quantity": 99}
    )
    assert oversell.status_code == 409

    db = SessionLocal()
    assert db.get(Product, product_id).stock == 6
    records = db.query(StockRecord).filter(StockRecord.product_id == product_id).all()
    assert [r.after_stock for r in records] == [10, 6]
    db.close()


def test_low_stock_alerts(client):
    headers, _ = login(client)
    product = client.post(
        "/api/products",
        headers=headers,
        json={"name": "低库存测试", "safety_stock": 5, "initial_stock": 4},
    ).get_json()["data"]
    assert product["low_stock"] is True

    summary = client.get("/api/dashboard/summary", headers=headers).get_json()["data"]
    assert summary["cards"]["low_stock_count"] >= 1
    assert any(item["id"] == product["id"] for item in summary["low_stock"])


def test_menu_visibility_follows_role(client):
    headers, _ = login(client)
    db = SessionLocal()
    staff_role = db.query(Role).filter(Role.code == "staff").one()
    product_menu = db.query(Menu).filter(Menu.path == "/products").one()
    staff_role.menus = [m for m in staff_role.menus if m.id != product_menu.id]
    db.commit()
    role_id = staff_role.id
    db.close()

    staff_headers, staff_data = login(client, "staff", "Staff@123456")
    names = [m["name"] for m in staff_data["menus"]]
    assert "商品管理" not in names

    # 通过角色菜单接口恢复
    client.put(f"/api/roles/{role_id}/menus", headers=headers, json={"menu_ids": [1, 2, 3, 4, 5, 6]})
    _, staff_data = login(client, "staff", "Staff@123456")
    assert "商品管理" in [m["name"] for m in staff_data["menus"]]


def user_id(username: str) -> int:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).one().id
    finally:
        db.close()


def test_user_menu_override(client):
    headers, _ = login(client)
    staff_id = user_id("staff")
    db = SessionLocal()
    product_menu = db.query(Menu).filter(Menu.path == "/products").one()
    product_menu_id = product_menu.id
    db.close()

    saved = client.put(
        f"/api/users/{staff_id}/menus",
        headers=headers,
        json={"mode": "custom", "menu_ids": [product_menu_id]},
    )
    assert saved.status_code == 200, saved.get_json()

    _, staff_data = login(client, "staff", "Staff@123456")
    assert [m["name"] for m in staff_data["menus"]] == ["商品管理"]

    restored = client.put(f"/api/users/{staff_id}/menus", headers=headers, json={"mode": "inherit"})
    assert restored.status_code == 200


def test_role_permission_change_takes_effect(client):
    headers, _ = login(client)
    db = SessionLocal()
    staff_role = db.query(Role).filter(Role.code == "staff").one()
    role_id = staff_role.id
    codes = [p.code for p in staff_role.permissions if p.code != "stock:out"]
    db.close()

    saved = client.put(f"/api/roles/{role_id}/permissions", headers=headers, json={"permissions": codes})
    assert saved.status_code == 200

    staff_headers, _ = login(client, "staff", "Staff@123456")
    product = client.post(
        "/api/products", headers=headers, json={"name": "权限测试", "initial_stock": 5}
    ).get_json()["data"]
    denied = client.post(
        "/api/stock/out", headers=staff_headers, json={"product_id": product["id"], "quantity": 1}
    )
    assert denied.status_code == 403


def test_delete_protections(client):
    headers, _ = login(client)
    denied = client.delete("/api/users/1", headers=headers)
    assert denied.status_code == 409

    db = SessionLocal()
    staff_role = db.query(Role).filter(Role.code == "staff").one()
    staff_role_id = staff_role.id
    db.close()
    role_in_use = client.delete(f"/api/roles/{staff_role_id}", headers=headers)
    assert role_in_use.status_code == 409

    # 有流水的商品不能删除
    product = client.post(
        "/api/products", headers=headers, json={"name": "待删商品", "initial_stock": 1}
    ).get_json()["data"]
    assert client.delete(f"/api/products/{product['id']}", headers=headers).status_code == 409


def test_disabled_user_token_invalid(client):
    headers, _ = login(client)
    staff_id = user_id("staff")
    response = client.patch(f"/api/users/{staff_id}/status", headers=headers, json={"status": False})
    assert response.status_code == 200

    staff = client.post("/api/auth/login", json={"username": "staff", "password": "Staff@123456"})
    assert staff.status_code == 403


def test_reseed_does_not_resurrect_deleted_data(client):
    db = SessionLocal()
    db.query(User).filter(User.username == "staff").delete()
    db.query(Product).delete()
    db.commit()
    db.close()

    db = SessionLocal()
    seed_all(db, include_demo=False)
    db.commit()
    assert db.query(User).filter(User.username == "staff").count() == 0
    assert db.query(Product).count() == 0
    db.close()


def test_menu_config_safeguards(client):
    headers, _ = login(client)
    staff_id = user_id("staff")

    empty_custom = client.put(
        f"/api/users/{staff_id}/menus", headers=headers, json={"mode": "custom", "menu_ids": []}
    )
    assert empty_custom.status_code == 400

    db = SessionLocal()
    menu = db.query(Menu).filter(Menu.path == "/system/menus").one()
    menu_id = menu.id
    db.close()
    hidden = client.put(f"/api/menus/{menu_id}", headers=headers, json={"visible": False})
    assert hidden.status_code == 409


def test_port_probe_skips_occupied_port():
    import socket

    from backend.server import pick_port

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("0.0.0.0", 0))
    occupied = probe.getsockname()[1]
    probe.listen(1)
    try:
        assert pick_port(occupied) != occupied
    finally:
        probe.close()
