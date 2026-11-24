"""Integration tests for FastAPI endpoints."""


def sample_payload():
    return {
        "profile": {"financial_year": "2026-27", "age_category": "below_60", "resident": True, "taxpayer_type": "individual"},
        "salary": {"basic_salary": 1500000},
        "house_property": {"property_type": "self_occupied", "home_loan_interest": 0},
        "capital_gains": {"entries": []},
        "business": {},
        "other_income": {},
        "deductions": {},
        "regime": "compare",
        "save_history": False,
    }


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_tax_years(client):
    r = client.get("/api/tax/years")
    assert r.status_code == 200
    years = r.json()["financial_years"]
    assert any(y["financial_year"] == "2026-27" for y in years)


def test_tax_rules(client):
    r = client.get("/api/tax/rules/2026-27")
    assert r.status_code == 200
    data = r.json()
    assert data["financial_year"] == "2026-27"
    assert "new_regime" in data


def test_calculate_compare(client):
    r = client.post("/api/tax/compare", json=sample_payload())
    assert r.status_code == 200
    data = r.json()
    assert data["recommended_regime"] == "new"
    assert "comparison_table" in data
    assert data["summary"]["new_final_tax"] == 97500


def test_calculate_single_regime(client):
    payload = sample_payload()
    payload["regime"] = "new"
    r = client.post("/api/tax/calculate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["regime"] == "new"
    assert data["tax_computation"]["final_tax_liability"] == 97500


def test_save_and_get_history(client):
    payload = sample_payload()
    payload["save_history"] = True
    payload["profile_name"] = "Test User"
    r = client.post("/api/tax/calculate", json=payload)
    assert r.status_code == 200

    h = client.get("/api/tax/history")
    assert h.status_code == 200
    items = h.json()["items"]
    assert len(items) >= 1
    item_id = items[0]["id"]

    detail = client.get(f"/api/tax/history/{item_id}")
    assert detail.status_code == 200
    assert "input" in detail.json()
    assert "result" in detail.json()

    d = client.delete(f"/api/tax/history/{item_id}")
    assert d.status_code == 200


def test_profiles_crud(client):
    # create
    r = client.post("/api/profiles", json={"name": "Alice", "age_category": "below_60", "resident": True, "taxpayer_type": "individual"})
    assert r.status_code == 200
    p = r.json()
    pid = p["id"]
    assert p["name"] == "Alice"

    # list
    r = client.get("/api/profiles")
    assert r.status_code == 200
    assert any(x["id"] == pid for x in r.json()["items"])

    # update
    r = client.put(f"/api/profiles/{pid}", json={"name": "Alice Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Alice Updated"

    # delete
    r = client.delete(f"/api/profiles/{pid}")
    assert r.status_code == 200


def test_export_pdf(client):
    r = client.post("/api/tax/export", json=sample_payload())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
