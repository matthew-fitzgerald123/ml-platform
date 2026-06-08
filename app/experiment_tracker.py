import mlflow
from typing import Any
from dotenv import load_dotenv
import os

load_dotenv()


class ExperimentTracker:
    def __init__(self):
        # Read at init but don't call mlflow.set_tracking_uri yet — doing so
        # here would fix the URI at import time and break test overrides that
        # set MLFLOW_TRACKING_URI before constructing the TestClient.
        self._tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "postgresql://localhost/mlplatform")

    def _configure(self):
        # Re-read env each call so test fixtures can override MLFLOW_TRACKING_URI
        # after the module is imported.
        uri = os.getenv("MLFLOW_TRACKING_URI", self._tracking_uri)
        mlflow.set_tracking_uri(uri)

    def start_run(self, experiment: str, run_name: str, params: dict[str, Any]) -> str:
        self._configure()
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(params)
            return run.info.run_id

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int = 0):
        self._configure()
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metrics(metrics, step=step)

    def log_artifact(self, run_id: str, local_path: str):
        self._configure()
        with mlflow.start_run(run_id=run_id):
            mlflow.log_artifact(local_path)

    def finish(self, run_id: str, status: str = "FINISHED"):
        self._configure()
        with mlflow.start_run(run_id=run_id):
            mlflow.end_run(status=status)

    def best_run(self, experiment: str, metric: str, mode: str = "max") -> dict:
        self._configure()
        exp = mlflow.get_experiment_by_name(experiment)
        if not exp:
            return {}
        runs = mlflow.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=[f"metrics.{metric} {'DESC' if mode == 'max' else 'ASC'}"],
        )
        if runs.empty:
            return {}
        row = runs.iloc[0]
        return {
            "run_id":  row.run_id,
            "params":  {k[7:]: v for k, v in row.items() if k.startswith("params.")},
            "metrics": {k[8:]: v for k, v in row.items() if k.startswith("metrics.")},
        }

    def list_runs(self, experiment: str) -> list[dict]:
        self._configure()
        exp = mlflow.get_experiment_by_name(experiment)
        if not exp:
            return []
        runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
        return runs.to_dict(orient="records")
