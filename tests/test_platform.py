import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200

def test_register_feature_set():
    r = client.post("/features/register", json={
        "name": "financial_signals",
        "schema": {"debt_to_income": "float", "credit_score": "int", "months_employed": "int"}
    })
    assert r.status_code == 200
    assert r.json()["name"] == "financial_signals"

def test_write_and_read_features():
    client.post("/features/write", json={
        "entity_id": "user_test_001",
        "feature_set": "financial_signals",
        "features": {"debt_to_income": 0.38, "credit_score": 712, "months_employed": 36}
    })
    r = client.get("/features/financial_signals/user_test_001")
    assert r.status_code == 200
    data = r.json()
    assert data["credit_score"] == 712
    assert data["debt_to_income"] == pytest.approx(0.38, rel=1e-3)

def test_get_historical_features():
    for i in range(3):
        client.post("/features/write", json={
            "entity_id": f"hist_user_{i}",
            "feature_set": "financial_signals",
            "features": {"debt_to_income": round(0.3 + i * 0.05, 2), "credit_score": 700 + i * 10, "months_employed": 12 + i * 6}
        })
    r = client.get("/features/financial_signals/history?entity_ids=hist_user_0,hist_user_1,hist_user_2")
    assert r.status_code == 200
    assert len(r.json()) == 3

def test_missing_features_returns_404():
    r = client.get("/features/financial_signals/nonexistent_entity")
    assert r.status_code == 404

def test_full_run_lifecycle():
    r = client.post("/experiments/run", json={
        "experiment": "credit_risk_test",
        "run_name": "lr_baseline",
        "params": {"model": "logistic_regression", "C": 1.0}
    })
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    r = client.post("/experiments/metrics", json={
        "run_id": run_id,
        "metrics": {"accuracy": 0.83, "f1": 0.80, "auc_roc": 0.88}
    })
    assert r.status_code == 200

    r = client.post(f"/experiments/finish/{run_id}")
    assert r.status_code == 200

def test_best_run():
    r = client.get("/experiments/credit_risk_test/best?metric=auc_roc&mode=max")
    assert r.status_code == 200
    assert "run_id" in r.json()
