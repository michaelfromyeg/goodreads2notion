run:
	@python -m goodreads2notion.main

mypy:
	@python -m mypy goodreads2notion

check:
	@python -m ruff check goodreads2notion

format:
	@python -m ruff format goodreads2notion
