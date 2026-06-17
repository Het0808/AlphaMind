.PHONY: install api ui test fmt

install:
	pip install -r requirements.txt

api:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	streamlit run ui/streamlit_app.py

test:
	pytest -q
