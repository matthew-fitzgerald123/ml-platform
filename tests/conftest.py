import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    # Use a throwaway SQLite MLflow store so tests don't touch the Postgres
    # database whose MLflow schema may be out of sync with the installed version.
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MLFLOW_TRACKING_URI"] = f"sqlite:///{tmp}/mlflow.db"
        # Import after env is set so the ExperimentTracker picks up the URI.
        from app.main import app

        with TestClient(app) as c:
            yield c
