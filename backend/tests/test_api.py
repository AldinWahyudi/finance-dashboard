import io
from datetime import date


def _signup(client, email="user@example.com", password="password123"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_signup_login_and_me(client):
    headers = _signup(client, "a@b.com", "secret123")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"

    r2 = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "secret123"})
    assert r2.status_code == 409

    r3 = client.post(
        "/api/auth/login",
        data={"username": "a@b.com", "password": "secret123"},
    )
    assert r3.status_code == 200


def test_import_csv_and_dashboard(client):
    headers = _signup(client)
    csv_text = (
        "Tanggal,Remark,Debit,Credit,Saldo\n"
        "2024-03-01,GAJI BULANAN,0,10000000,10000000\n"
        "2024-03-05,GRAB TRANSPORT,25000,0,9975000\n"
        "2024-03-06,GOFOOD STARBUCKS,75000,0,9900000\n"
        "2024-04-01,GAJI BULANAN,0,10000000,19900000\n"
        "2024-04-02,INDOMARET,50000,0,19850000\n"
    )
    files = {"file": ("stmt.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    r = client.post("/api/transactions/import", files=files, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["bank"] == "Mandiri"
    assert data["inserted"] == 5
    assert data["skipped"] == 0

    files = {"file": ("stmt.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    r = client.post("/api/transactions/import", files=files, headers=headers)
    assert r.status_code == 200
    assert r.json()["inserted"] == 0
    assert r.json()["skipped"] == 5

    r = client.get("/api/dashboard/summary", headers=headers)
    assert r.status_code == 200
    s = r.json()
    assert s["total_income"] == 20000000.0
    assert s["total_expense"] == 150000.0
    assert len(s["monthly_spend"]) == 2

    r = client.get("/api/transactions", headers=headers)
    txs = r.json()
    cats = {t["description"]: t["category"] for t in txs}
    assert cats["GRAB TRANSPORT"] == "Transport"
    assert cats["GOFOOD STARBUCKS"] == "Food & Drink"
    assert cats["INDOMARET"] == "Groceries"


def test_rules_override_and_recategorize(client):
    headers = _signup(client)
    csv_text = (
        "Tanggal,Remark,Debit,Credit,Saldo\n"
        "2024-03-01,MY CUSTOM MERCHANT,50000,0,100000\n"
    )
    files = {"file": ("stmt.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    r = client.post("/api/transactions/import", files=files, headers=headers)
    assert r.status_code == 200

    r = client.post(
        "/api/rules",
        json={"keyword": "custom", "category": "Shopping", "priority": 10},
        headers=headers,
    )
    assert r.status_code == 201

    r = client.post("/api/transactions/recategorize", headers=headers)
    assert r.status_code == 200
    assert r.json()["updated"] == 1

    r = client.get("/api/transactions", headers=headers)
    assert r.json()[0]["category"] == "Shopping"


def test_budgets_over_budget_alert(client):
    headers = _signup(client)
    today = date.today().isoformat()
    r = client.post(
        "/api/transactions",
        json={
            "date": today,
            "amount": 750000,
            "type": "debit",
            "description": "GOFOOD LUNCH",
            "category": "Food & Drink",
        },
        headers=headers,
    )
    assert r.status_code == 201

    r = client.post(
        "/api/budgets",
        json={"category": "Food & Drink", "monthly_limit": 500000},
        headers=headers,
    )
    assert r.status_code == 201

    r = client.get("/api/budgets/status", headers=headers)
    assert r.status_code == 200
    status = r.json()
    assert len(status) == 1
    assert status[0]["over_budget"] is True
    assert status[0]["spent"] == 750000


def test_budget_status_excludes_future_month(client):
    """Transactions in future months must not be counted in current-month spend."""
    from datetime import date as _date

    headers = _signup(client)
    today = _date.today()
    # Always pick a date strictly after the current month.
    if today.month == 12:
        future = today.replace(year=today.year + 1, month=1, day=15)
    else:
        future = today.replace(month=today.month + 1, day=15)

    r = client.post(
        "/api/transactions",
        json={
            "date": future.isoformat(),
            "amount": 999999,
            "type": "debit",
            "description": "FUTURE EXPENSE",
            "category": "Food & Drink",
        },
        headers=headers,
    )
    assert r.status_code == 201

    r = client.post(
        "/api/budgets",
        json={"category": "Food & Drink", "monthly_limit": 500000},
        headers=headers,
    )
    assert r.status_code == 201

    r = client.get("/api/budgets/status", headers=headers)
    assert r.status_code == 200
    status = r.json()
    assert len(status) == 1
    assert status[0]["spent"] == 0
    assert status[0]["over_budget"] is False


def test_pdf_export(client):
    headers = _signup(client)
    r = client.post(
        "/api/transactions",
        json={
            "date": "2024-01-15",
            "amount": 100000,
            "type": "debit",
            "description": "TEST EXPENSE",
            "category": "Other",
        },
        headers=headers,
    )
    assert r.status_code == 201
    r = client.get("/api/export/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
