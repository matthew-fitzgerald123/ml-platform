import pytest
from fastapi.testclient import TestClient


# ── Feature store ──────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200

def test_register_feature_set(client):
    r = client.post("/features/register", json={
        "name": "financial_signals",
        "schema": {"debt_to_income": "float", "credit_score": "int", "months_employed": "int"}
    })
    assert r.status_code == 200
    assert r.json()["name"] == "financial_signals"

def test_write_and_read_features(client):
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

def test_get_historical_features(client):
    for i in range(3):
        client.post("/features/write", json={
            "entity_id": f"hist_user_{i}",
            "feature_set": "financial_signals",
            "features": {"debt_to_income": round(0.3 + i * 0.05, 2), "credit_score": 700 + i * 10, "months_employed": 12 + i * 6}
        })
    r = client.get("/features/financial_signals/history?entity_ids=hist_user_0,hist_user_1,hist_user_2")
    assert r.status_code == 200
    assert len(r.json()) == 3

def test_missing_features_returns_404(client):
    r = client.get("/features/financial_signals/nonexistent_entity")
    assert r.status_code == 404

# ── Experiment tracking ────────────────────────────────────

def test_full_run_lifecycle(client):
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

def test_best_run(client):
    r = client.get("/experiments/credit_risk_test/best?metric=auc_roc&mode=max")
    assert r.status_code == 200
    assert "run_id" in r.json()

# ── Validation ─────────────────────────────────────────────

def test_write_rejects_wrong_type(client):
    client.post("/features/register", json={
        "name": "typed_signals",
        "schema": {"credit_score": "int:300:850", "label": "str"}
    })
    r = client.post("/features/write", json={
        "entity_id": "v_user_001",
        "feature_set": "typed_signals",
        "features": {"credit_score": "not-an-int", "label": "ok"}
    })
    assert r.status_code == 422

def test_write_rejects_out_of_range(client):
    r = client.post("/features/write", json={
        "entity_id": "v_user_002",
        "feature_set": "typed_signals",
        "features": {"credit_score": 900, "label": "ok"}
    })
    assert r.status_code == 422

def test_write_rejects_null_field(client):
    r = client.post("/features/write", json={
        "entity_id": "v_user_003",
        "feature_set": "typed_signals",
        "features": {"credit_score": None, "label": "ok"}
    })
    assert r.status_code == 422

def test_write_valid_passes_validation(client):
    r = client.post("/features/write", json={
        "entity_id": "v_user_004",
        "feature_set": "typed_signals",
        "features": {"credit_score": 720, "label": "prime"}
    })
    assert r.status_code == 200

# ── Model registry ─────────────────────────────────────────

def test_model_register_and_list(client):
    r = client.post("/models/register", json={
        "name": "credit-risk-model",
        "version": "v1",
        "artifact_uri": "s3://ml-platform/models/credit-risk/v1",
        "metrics": {"accuracy": 0.91, "auc_roc": 0.94},
        "params": {"n_estimators": 200, "max_depth": 6}
    })
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "v1"
    assert body["stage"] == "none"

    r = client.get("/models/credit-risk-model/versions")
    assert r.status_code == 200
    assert len(r.json()) >= 1

def test_model_promote_to_production(client):
    client.post("/models/register", json={
        "name": "credit-risk-model",
        "version": "v2",
        "artifact_uri": "s3://ml-platform/models/credit-risk/v2",
        "metrics": {"accuracy": 0.93}
    })
    r = client.post("/models/credit-risk-model/promote", json={"version": "v2", "stage": "production"})
    assert r.status_code == 200
    assert r.json()["stage"] == "production"

    r = client.get("/models/credit-risk-model/production")
    assert r.status_code == 200
    assert r.json()["version"] == "v2"

def test_model_promote_invalid_stage(client):
    r = client.post("/models/credit-risk-model/promote", json={"version": "v1", "stage": "released"})
    assert r.status_code == 422

def test_model_production_404_for_unknown(client):
    r = client.get("/models/nonexistent-model/production")
    assert r.status_code == 404

# ── Pipeline ───────────────────────────────────────────────

def test_pipeline_status(client):
    r = client.get("/pipeline/status")
    assert r.status_code == 200
    body = r.json()
    assert "running" in body
    assert "run_count" in body
