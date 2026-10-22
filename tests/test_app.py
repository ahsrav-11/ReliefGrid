import pytest
from app import create_app, db
from app.models import *


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/t.db"})
    import seed_data
    with app.app_context():
        seed_data.load()
    return app.test_client(), app


def login(c, u, p):
    return c.post("/login", data={"username": u, "password": p}, follow_redirects=True)


def test_rbac(client):
    c, _ = client
    assert c.get("/admin/disasters").status_code == 302
    login(c, "coastal", "center123")
    assert c.get("/admin/disasters").status_code == 403
    assert c.get("/allocation").status_code == 403


def test_full_workflow(client):
    c, app = client
    login(c, "admin", "admin123")
    r = c.post("/allocation/apply", data={"disaster_id": 1, "resource_id": 1, "mode": "priority"}, follow_redirects=True)
    assert b"Plan applied" in r.data
    with app.app_context():
        total = sum(s.reserved for s in Stock.query.filter_by(resource_id=1))
        assert total <= sum(s.quantity for s in Stock.query.filter_by(resource_id=1))
        d = Delivery.query.first(); did = d.id
    assert c.post(f"/deliveries/{did}/dispatch").status_code == 302
    c.post("/logout"); login(c, "coastal", "center123")
    c.post(f"/deliveries/{did}/confirm")
    with app.app_context():
        assert db.session.get(Delivery, did).status == "delivered"
    assert c.get("/dashboard").status_code == 200


def test_simulation_pages(client):
    c, _ = client
    login(c, "admin", "admin123")
    assert c.get("/simulation?disaster_id=1&resource_id=1&mode=priority&demand_pct=150&supply_pct=50").status_code == 200
    assert c.get("/reports").status_code == 200


def test_closed_disaster_blocks_requests_and_partial_not_fulfilled(client):
    c, app = client
    login(c, "admin", "admin123")
    c.post("/allocation/apply", data={"disaster_id": 1, "resource_id": 1, "mode": "priority"})
    with app.app_context():
        partial = Request.query.filter_by(status="partial").first()
        assert partial is not None
        rid = partial.id
        for d in Delivery.query.filter_by(request_id=rid):
            c.post(f"/deliveries/{d.id}/dispatch")
    c.post("/logout"); login(c, "riverside", "center123"); c.post("/logout"); login(c, "coastal", "center123")
    with app.app_context():
        owner = db.session.get(Request, rid).user.username
    c.post("/logout"); login(c, owner, "center123")
    with app.app_context():
        for d in Delivery.query.filter_by(request_id=rid):
            c.post(f"/deliveries/{d.id}/confirm")
        assert db.session.get(Request, rid).status == "partial"
    c.post("/logout"); login(c, "admin", "admin123")
    c.post("/admin/disasters/1/edit", data={"severity": 4, "status": "closed", "description": "x"})
    c.post("/logout"); login(c, "coastal", "center123")
    r = c.post("/requests/new", data={"resource_id": 1, "quantity": 5, "urgency": 3, "population": 10}, follow_redirects=True)
    assert b"closed" in r.data


def test_stock_log_csv_filter_profile(client):
    c, app = client
    login(c, "admin", "admin123")
    assert b"received" in c.get("/admin/stock-log").data
    r = c.get("/reports.csv")
    assert r.mimetype == "text/csv" and b"Resource,Requested" in r.data
    assert c.get("/requests?status=pending").status_code == 200
    c.post("/logout"); login(c, "coastal", "center123")
    assert c.get("/reports.csv").status_code == 403
    c.post("/profile", data={"full_name": "A", "phone": "1", "population": "1500", "password": ""})
    with app.app_context():
        assert User.query.filter_by(username="coastal").first().location.population == 1500
    r = c.post("/requests/new", data={"resource_id": 999, "quantity": 5, "urgency": 3, "population": 10}, follow_redirects=True)
    assert b"valid resource" in r.data


def test_passwords_hashed_and_csrf_enabled(client):
    _, app = client
    with app.app_context():
        u = User.query.filter_by(username="admin").first()
        assert "admin123" not in u.password_hash and u.password_hash.startswith(("scrypt", "pbkdf2"))
    strict = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert strict.test_client().post("/login", data={"username": "admin", "password": "admin123"}).status_code == 400  # no CSRF token


def test_database_url_is_configurable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert create_app().config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"
