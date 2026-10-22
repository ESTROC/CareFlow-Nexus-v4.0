.PHONY: test benchmark api web up down

test:
	cd backend && pytest -q
benchmark:
	python ml/evaluate_workflow.py
api:
	cd backend && uvicorn careflow.main:app --reload
web:
	cd frontend && npm run dev
up:
	docker compose up --build -d
down:
	docker compose down
