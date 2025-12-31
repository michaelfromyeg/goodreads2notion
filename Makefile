.PHONY: help run init-schema sync-csv sync-rss status repair-covers check format typecheck test clean

help:
	@echo "Available commands:"
	@echo "  make run            - Show CLI help"
	@echo "  make init-schema    - Initialize Notion database schema"
	@echo "  make sync-csv       - Import from CSV export"
	@echo "  make sync-rss       - Sync from RSS feeds"
	@echo "  make status         - Show database status"
	@echo "  make repair-covers  - Fix missing/broken cover images"
	@echo "  make check          - Run linter (ruff)"
	@echo "  make format         - Format code (ruff)"
	@echo "  make typecheck      - Run type checker (ty)"
	@echo "  make test           - Run tests"

# CLI commands
run:
	@uv run goodreads2notion --help

init-schema:
	@uv run goodreads2notion init-schema

sync-csv:
	@uv run goodreads2notion import-csv ./goodreads_library_export.csv

sync-rss:
	@uv run goodreads2notion sync-rss --user-id 120686315

status:
	@uv run goodreads2notion status

repair-covers:
	@uv run goodreads2notion repair-covers

# Development commands
check:
	@uv run ruff check src tests

format:
	@uv run ruff format src tests

typecheck:
	@uvx ty check src

test:
	@uv run pytest

clean:
	rm -rf .ruff_cache .pytest_cache __pycache__ dist build *.egg-info .venv
