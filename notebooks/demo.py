"""
End-to-end ML Platform demo.
Requires: make mlflow + make serve running in separate terminals.
Run: make demo
"""
import requests, json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score

BASE = "http://localhost:8080"

def post(path, payload): return requests.post(f"{BASE}{path}", json=payload).json()
def get(path):           return requests.get(f"{BASE}{path}").json()

print("\n=== ML Platform Demo ===\n")

print("1. Registering feature set...")
post("/features/register", {
    "name": "credit_signals",
    "schema": {"debt_to_income": "float", "credit_score": "int", "months_employed": "int"}
})

print("2. Writing features for 10 entities...")
rng = np.random.default_rng(42)
for i in range(10):
    post("/features/write", {
        "entity_id": f"user_{i:03d}",
        "feature_set": "credit_signals",
        "features": {
            "debt_to_income":  round(float(rng.uniform(0.1, 0.6)), 3),
            "credit_score":    int(rng.integers(580, 800)),
            "months_employed": int(rng.integers(6, 60)),
        }
    })

print("3. Reading user_003 features (Redis online store)...")
features = get("/features/credit_signals/user_003")
print(f"   {json.dumps(features, indent=4)}")

print("\n4. Training 3 logistic regression variants...")
X, y = make_classification(n_samples=1000, n_features=8, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

for C in [0.01, 1.0, 100.0]:
    model = LogisticRegression(C=C, max_iter=500)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    run = post("/experiments/run", {
        "experiment": "credit_risk_demo",
        "run_name":   f"lr_C{C}",
        "params":     {"model": "logistic_regression", "C": C, "max_iter": 500}
    })
    run_id = run["run_id"]

    metrics = {
        "accuracy": round(accuracy_score(y_test, preds), 4),
        "f1":       round(f1_score(y_test, preds), 4),
        "auc_roc":  round(roc_auc_score(y_test, proba), 4),
    }
    post("/experiments/metrics", {"run_id": run_id, "metrics": metrics})
    post(f"/experiments/finish/{run_id}", {})
    print(f"   C={C:6.2f}  acc={metrics['accuracy']:.3f}  auc={metrics['auc_roc']:.3f}")

print("\n5. Best run by AUC-ROC:")
best = get("/experiments/credit_risk_demo/best?metric=auc_roc&mode=max")
print(f"   run_id:  {best['run_id']}")
print(f"   params:  {best['params']}")
print(f"   metrics: {best['metrics']}")

print(f"\nMLflow UI → http://localhost:5001")
print(f"API docs  → http://localhost:8080/docs")
print("\nDone.")
