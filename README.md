# ML Platform: Feature Store + Experiment Tracking

A local ML platform with two core services: an online/offline feature store backed by Redis and PostgreSQL, and an MLflow-integrated experiment tracker. Built to support downstream agent and RAG projects.

## Stack

| Component | Library |
|---|---|
| API | FastAPI + uvicorn (port 8080) |
| Online feature cache | Redis |
| Offline feature store + run history | PostgreSQL + SQLAlchemy |
| Experiment tracking | MLflow |
| Data | pandas, scikit-learn, numpy |

## Setup

```bash
# Create database
createdb ml_platform

# Install dependencies
make install

# Start Redis (if not already running)
brew services start redis
```

## Running

```bash
# Start API server
make serve

# Open MLflow UI (separate terminal)
make mlflow-ui

# Run end-to-end demo
make demo

# Run tests
make test
```

## API Endpoints

### Feature Store

| Method | Path | Description |
|---|---|---|
| POST | `/features/register` | Register a new feature set with schema |
| POST | `/features/write` | Write features for an entity |
| GET | `/features/{set}/{entity_id}` | Online lookup (Redis) |
| GET | `/features/{set}/history` | Historical lookup (Postgres) |
| GET | `/features` | List all feature sets |

### Experiment Tracking

| Method | Path | Description |
|---|---|---|
| POST | `/experiments/run` | Start a new MLflow run |
| POST | `/experiments/metrics` | Log metrics to a run |
| POST | `/experiments/finish/{run_id}` | Mark a run complete |
| GET | `/experiments/{name}/best` | Best run by metric |
| GET | `/experiments/{name}/runs` | List all runs for an experiment |

Interactive docs at `http://localhost:8080/docs`.

## Project Structure

```
app/
  feature_store.py    Redis online store + Postgres historical store
  experiment_tracker.py  MLflow run management
  main.py             FastAPI app
  models.py           SQLAlchemy models
  database.py         engine + session
notebooks/
  demo.py             end-to-end feature write + experiment tracking demo
tests/
  test_platform.py    integration tests
```

## Notes

- The feature store serves as the data layer for the llm-agent (`lookup_entity` tool)
- MLflow tracking server runs locally via `run_mlflow_ui.py`
- Redis keys are prefixed by feature set name for namespace isolation
