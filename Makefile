install:
	pip install -r requirements.txt

mlflow-ui:
	python run_mlflow_ui.py

serve:
	uvicorn app.main:app --reload --port 8080

test:
	pytest tests/ -v

lint:
	python -m py_compile app/main.py app/feature_store.py app/validator.py \
	    app/model_registry.py app/scheduler.py app/models.py app/database.py \
	    app/experiment_tracker.py
	@echo "Lint OK"

demo:
	python notebooks/demo.py
