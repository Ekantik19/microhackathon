# InsideMatch developer commands. `make dev` runs API (:8000) and web (:3000) in mock mode.
SHELL := /bin/bash
BACKEND := backend
FRONTEND := frontend
# Export only NEXT_PUBLIC_* from .env to the frontend (the backend reads .env itself).
NEXT_ENV := $(shell [ -f .env ] && grep -E '^NEXT_PUBLIC_[A-Z_]+=' .env | sed 's/[[:space:]]*\#.*//' | xargs)

.PHONY: help install dev dev-api dev-web test test-backend test-frontend lint format generate-data prewarm docker-build

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1

install:
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && pnpm install

dev:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) dev-api & \
	$(MAKE) dev-web & \
	wait

dev-api:
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port 8000

dev-web:
	cd $(FRONTEND) && env $(NEXT_ENV) pnpm dev --port 3000

test: test-backend test-frontend

test-backend:
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q

test-frontend:
	cd $(FRONTEND) && pnpm lint && pnpm typecheck

lint:
	cd $(BACKEND) && uv run ruff check . && uv run mypy app
	cd $(FRONTEND) && pnpm lint && pnpm typecheck

format:
	cd $(BACKEND) && uv run ruff format . && uv run ruff check --fix .

generate-data:
	cd $(BACKEND) && uv run python -m app.events.generator --seed 42 --match-id demo_01

prewarm:
	cd $(BACKEND) && uv run python ../scripts/prewarm_insights.py

docker-build:
	docker build -t insidematch-api -f $(BACKEND)/Dockerfile .
	docker build -t insidematch-web -f $(FRONTEND)/Dockerfile .
