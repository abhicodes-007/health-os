.PHONY: setup start stop restart logs pull-model test test-unit test-integration lint

setup:
	@bash setup.sh

start:
	@docker compose up -d
	@echo "WebUI → http://localhost:3000"

stop:
	@docker compose down

restart: stop start

logs:
	@docker compose logs -f

pull-model:
	@ollama pull $(MODEL)

test:
	@uv run pytest -q

test-unit:
	@uv run pytest -q -m "not integration"

test-integration:
	@uv run pytest -q -m integration

lint:
	@uv run ruff check .
