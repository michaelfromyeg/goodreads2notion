# goodreads2notion

Sync your Goodreads library to a Notion database.

## Features

- **CSV import**: Bootstrap from Goodreads CSV export (handles all books)
- **RSS sync**: Incremental updates from Goodreads RSS feeds (~100-200 recent items per shelf)
- **Deduplication**: Uses Goodreads book ID to prevent duplicates

## Setup

### 1. Create a Notion integration

1. Go to [notion.so/my-integrations](https://notion.so/my-integrations)
2. Create a new integration and copy the token

### 2. Create a Notion database

1. Create a new database in Notion
2. Share it with your integration (click "..." → "Connections" → select your integration)
3. Copy the database ID from the URL: `notion.so/<DATABASE_ID>?v=...`

### 3. Find your Goodreads user ID

Your user ID is in your Goodreads profile URL: `goodreads.com/user/show/<USER_ID>`

### 4. Configure environment

```bash
cp .env.example .env
```

Fill in your `.env`:
```
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id
GOODREADS_USER_ID=your_goodreads_user_id
```

## Local Usage

Requires [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync

# Initialize database schema
make init-schema

# Import from CSV export (one-time bootstrap)
make sync-csv

# Sync from RSS feeds (incremental)
make sync-rss

# Check database status
make status
```

## Automated Sync with GitHub Actions

To run the sync automatically every 6 hours:

### 1. Fork this repository

### 2. Add repository secrets

Go to your fork's **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|--------|-------|
| `NOTION_TOKEN` | Your Notion integration token |
| `NOTION_DATABASE_ID` | Your Notion database ID |
| `GOODREADS_USER_ID` | Your Goodreads user ID |

### 3. Enable the workflow

The workflow at `.github/workflows/sync.yml` runs automatically every 6 hours. You can also trigger it manually from the **Actions** tab.

## License

MIT
