import mlflow
from typing import Any
from dotenv import load_dotenv
import os

load_dotenv()

class ExperimentTracker:
    def __init__(self):
        mlflow.set_tracking_uri(
            os.getenv("MLFLOW_TRACKING_URI", "postgresql://localhost/mlplatform")
        )

    def start_run(self, experiment: str, run_name: str, params: dict[str, Any]) -> str:
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(params)
            return run.info.run_id

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int = 0):
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metrics(metrics, step=step)

    def log_artifact(self, run_id: str, local_path: str):
        with mlflow.start_run(run_id=run_id):
            mlflow.log_artifact(local_path)

    def finish(self, run_id: str, status: str = "FINISHED"):
        with mlflow.start_run(run_id=run_id):
            mlflow.end_run(status=status)

    def best_run(self, experiment: str, metric: str, mode: str = "max") -> dict:
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
        exp = mlflow.get_experiment_by_name(experiment)
        if not exp:
            return []
        runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
        return runs.to_dict(orient="records")
