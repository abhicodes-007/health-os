.PHONY: start stop restart logs test test-unit test-integration lint

start:
	@docker compose up -d

stop:
	@docker compose down

restart: stop start

logs:
	@docker compose logs -f

test:
	@uv run pytest -q

test-unit:
	@uv run pytest -q -m "not integration"

test-integration:
	@uv run pytest -q -m integration

lint:
	@uv run ruff check .
