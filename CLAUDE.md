# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

goodreads2notion syncs Goodreads library data to a Notion database. It supports:
- **CSV import**: Bootstrap from Goodreads CSV export (handles all books)
- **RSS sync**: Incremental updates from Goodreads RSS feeds (limited to ~100-200 recent items per shelf)

## Commands

```bash
# Show CLI help
make run

# Initialize Notion database schema
make init-schema

# Import from CSV export (bootstrap)
make sync-csv

# Sync from RSS feeds (incremental)
make sync-rss

# Show database status
make status

# Lint with ruff
make check

# Format code with ruff
make format

# Type check with ty
make typecheck

# Run tests
make test
```

## Dependencies

Managed with `uv`. Install with: `uv sync`

Key dependencies: httpx (async HTTP), pydantic (data models), click (CLI), python-dotenv (env vars)

Dev tools: ruff (lint/format), ty (type checking), pytest

## Architecture

```
src/goodreads2notion/
├── cli.py              # Click CLI commands
├── config.py           # Environment variable loading
├── models.py           # Pydantic Book model with Notion property conversion
├── exceptions.py       # Custom exception classes
├── parsers/
│   ├── csv_parser.py   # Parse Goodreads CSV export
│   └── rss_parser.py   # Parse Goodreads RSS feeds (async)
└── notion/
    ├── client.py       # Async Notion API client with rate limiting
    ├── schema.py       # Database schema definition and migration
    └── sync.py         # Upsert logic using Goodreads book_id as primary key
```

## Key Design Decisions

- **Deduplication**: Uses `Goodreads ID` (book_id) as primary key to prevent duplicates
- **Upsert strategy**: Builds lookup index from existing Notion pages, then creates or updates
- **Rate limiting**: 0.35s delay between Notion API calls (limit is 3 req/s)
- **Standard shelves only**: Syncs to-read, currently-reading, read (skips custom shelves)

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `NOTION_TOKEN`: Integration token from notion.so/my-integrations
- `NOTION_DATABASE_ID`: Database UUID from URL
- `GOODREADS_USER_ID`: User ID from Goodreads profile URL
