"""Run MLflow UI without gunicorn (werkzeug dev server, no fork)."""
import os
from dotenv import load_dotenv

load_dotenv()

backend_uri = os.getenv("DATABASE_URL", "postgresql://localhost/mlplatform")
artifact_root = os.path.abspath("./mlruns")

os.environ.setdefault("MLFLOW_TRACKING_URI", backend_uri)

from mlflow.server.handlers import initialize_backend_stores
from mlflow.server import app

initialize_backend_stores(backend_uri, backend_uri, artifact_root)

print(f"\nMLflow UI → http://localhost:5001\n")
app.run(host="0.0.0.0", port=5001, threaded=True)
