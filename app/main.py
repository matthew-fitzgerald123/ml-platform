from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any
import redis, os
from dotenv import load_dotenv

from app.database import get_db, engine
from app.models import Base
from app.feature_store import FeatureStore
from app.experiment_tracker import ExperimentTracker

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ML Platform", version="1.0.0")

_redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
tracker = ExperimentTracker()

def get_fs(db: Session = Depends(get_db)) -> FeatureStore:
    return FeatureStore(db, _redis)

# ── Feature store ──────────────────────────────────────────

class RegisterReq(BaseModel):
    name: str
    schema: dict[str, str]

class WriteReq(BaseModel):
    entity_id: str
    feature_set: str
    features: dict[str, Any]

@app.post("/features/register", tags=["features"])
def register(req: RegisterReq, fs: FeatureStore = Depends(get_fs)):
    return fs.register(req.name, req.schema)

@app.get("/features", tags=["features"])
def list_feature_sets(fs: FeatureStore = Depends(get_fs)):
    return fs.list_feature_sets()

@app.post("/features/write", tags=["features"])
def write(req: WriteReq, fs: FeatureStore = Depends(get_fs)):
    fs.write(req.entity_id, req.feature_set, req.features)
    return {"status": "ok", "entity_id": req.entity_id}

@app.get("/features/{feature_set}/history", tags=["features"])
def get_historical(feature_set: str, entity_ids: str, fs: FeatureStore = Depends(get_fs)):
    ids = [i.strip() for i in entity_ids.split(",")]
    return fs.get_historical(ids, feature_set)

@app.get("/features/{feature_set}/{entity_id}", tags=["features"])
def get_online(feature_set: str, entity_id: str, fs: FeatureStore = Depends(get_fs)):
    result = fs.get(entity_id, feature_set)
    if not result:
        raise HTTPException(404, "Features not found")
    return result

# ── Experiment tracking ────────────────────────────────────

class RunReq(BaseModel):
    experiment: str
    run_name: str
    params: dict[str, Any]

class MetricsReq(BaseModel):
    run_id: str
    metrics: dict[str, float]
    step: int = 0

@app.post("/experiments/run", tags=["experiments"])
def start_run(req: RunReq):
    run_id = tracker.start_run(req.experiment, req.run_name, req.params)
    return {"run_id": run_id}

@app.post("/experiments/metrics", tags=["experiments"])
def log_metrics(req: MetricsReq):
    tracker.log_metrics(req.run_id, req.metrics, req.step)
    return {"status": "ok"}

@app.post("/experiments/finish/{run_id}", tags=["experiments"])
def finish_run(run_id: str):
    tracker.finish(run_id)
    return {"status": "finished"}

@app.get("/experiments/{name}/best", tags=["experiments"])
def best_run(name: str, metric: str = "accuracy", mode: str = "max"):
    result = tracker.best_run(name, metric, mode)
    if not result:
        raise HTTPException(404, "No runs found")
    return result

@app.get("/experiments/{name}/runs", tags=["experiments"])
def list_runs(name: str):
    return tracker.list_runs(name)

@app.get("/health")
def health():
    return {"status": "ok", "services": ["postgres", "redis", "mlflow"]}
