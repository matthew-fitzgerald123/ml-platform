install:
	pip install -r requirements.txt

mlflow-ui:
	python run_mlflow_ui.py

serve:
	uvicorn app.main:app --reload --port 8080

test:
	pytest tests/ -v

demo:
	python notebooks/demo.py
