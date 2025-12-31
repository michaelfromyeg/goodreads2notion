"""CLI interface for goodreads2notion."""

import asyncio
from pathlib import Path

import click

from .config import Config
from .covers import CoverRepairer
from .exceptions import ConfigurationError
from .notion.client import NotionClient
from .notion.schema import ensure_schema
from .notion.sync import BookSyncer
from .parsers.csv_parser import load_csv
from .parsers.rss_parser import fetch_all_shelves, fetch_shelf_rss


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Goodreads to Notion sync tool."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.pass_context
def init_schema(ctx: click.Context) -> None:
    """Initialize/update Notion database schema with required properties."""
    try:
        config = Config.from_env()
    except ConfigurationError as e:
        raise click.ClickException(str(e)) from e

    async def run() -> None:
        client = NotionClient(config.notion_token)
        try:
            await ensure_schema(client, config.database_id)
            click.echo("Database schema initialized successfully!")
        finally:
            await client.close()

    asyncio.run(run())


@cli.command("import-csv")
@click.argument("csv_path", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Parse CSV but do not sync to Notion")
@click.pass_context
def import_csv(ctx: click.Context, csv_path: Path, dry_run: bool) -> None:
    """
    Bootstrap database from Goodreads CSV export.

    Example: goodreads2notion import-csv ./goodreads_library_export.csv
    """
    click.echo(f"Parsing {csv_path}...")
    books = load_csv(csv_path)
    click.echo(f"Found {len(books)} books in CSV (standard shelves only)")

    # Show shelf breakdown
    shelf_counts: dict[str, int] = {}
    for book in books:
        shelf_counts[book.shelf] = shelf_counts.get(book.shelf, 0) + 1
    for shelf, count in sorted(shelf_counts.items()):
        click.echo(f"  {shelf}: {count}")

    if dry_run:
        click.echo("\nDry run - not syncing to Notion")
        click.echo("\nSample books:")
        for book in books[:5]:
            click.echo(f"  - {book.title} by {book.author} ({book.shelf})")
        if len(books) > 5:
            click.echo(f"  ... and {len(books) - 5} more")
        return

    try:
        config = Config.from_env()
    except ConfigurationError as e:
        raise click.ClickException(str(e)) from e

    async def run() -> None:
        client = NotionClient(config.notion_token)
        try:
            syncer = BookSyncer(client, config.database_id)

            click.echo("\nSyncing to Notion...")
            state = await syncer.sync_books(books)

            click.echo("\nSync complete!")
            click.echo(f"  Added: {state.books_added}")
            click.echo(f"  Updated: {state.books_updated}")
            if state.errors:
                click.echo(f"  Errors: {len(state.errors)}")
                for err in state.errors[:5]:
                    click.echo(f"    - {err}")
                if len(state.errors) > 5:
                    click.echo(f"    ... and {len(state.errors) - 5} more errors")
        finally:
            await client.close()

    asyncio.run(run())


@cli.command("sync-rss")
@click.option("--user-id", required=True, help="Goodreads user ID")
@click.option(
    "--shelf",
    type=click.Choice(["all", "to-read", "currently-reading", "read"]),
    default="all",
    help="Which shelf to sync",
)
@click.pass_context
def sync_rss(ctx: click.Context, user_id: str, shelf: str) -> None:
    """
    Incremental sync from Goodreads RSS feeds.

    Example: goodreads2notion sync-rss --user-id 120686315
    """
    try:
        config = Config.from_env()
    except ConfigurationError as e:
        raise click.ClickException(str(e)) from e

    async def run() -> None:
        click.echo(f"Fetching RSS feeds for user {user_id}...")

        if shelf == "all":
            books = await fetch_all_shelves(user_id)
        else:
            books = await fetch_shelf_rss(user_id, shelf)

        click.echo(f"Found {len(books)} books in RSS feeds")

        if not books:
            click.echo("No books to sync.")
            return

        # Show shelf breakdown
        shelf_counts: dict[str, int] = {}
        for book in books:
            shelf_counts[book.shelf] = shelf_counts.get(book.shelf, 0) + 1
        for shelf_name, count in sorted(shelf_counts.items()):
            click.echo(f"  {shelf_name}: {count}")

        client = NotionClient(config.notion_token)
        try:
            syncer = BookSyncer(client, config.database_id)

            click.echo("\nSyncing to Notion...")
            state = await syncer.sync_books(books)

            click.echo("\nSync complete!")
            click.echo(f"  Added: {state.books_added}")
            click.echo(f"  Updated: {state.books_updated}")
            if state.errors:
                click.echo(f"  Errors: {len(state.errors)}")
        finally:
            await client.close()

    asyncio.run(run())


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show current sync status and database statistics."""
    try:
        config = Config.from_env()
    except ConfigurationError as e:
        raise click.ClickException(str(e)) from e

    async def run() -> None:
        client = NotionClient(config.notion_token)
        try:
            counts: dict[str, int] = {"to-read": 0, "currently-reading": 0, "read": 0, "other": 0}
            total = 0

            click.echo("Querying Notion database...")
            async for page in client.query_database_all(config.database_id):
                total += 1
                props = page.get("properties", {})
                shelf_prop = props.get("Shelf", {})
                shelf_select = shelf_prop.get("select")
                shelf_name = shelf_select.get("name", "other") if shelf_select else "other"
                if shelf_name in counts:
                    counts[shelf_name] += 1
                else:
                    counts["other"] += 1

            click.echo("\nNotion Database Status:")
            click.echo(f"  Total books: {total}")
            for shelf_name, count in counts.items():
                if count > 0:
                    click.echo(f"  {shelf_name}: {count}")
        finally:
            await client.close()

    asyncio.run(run())


@cli.command("repair-covers")
@click.option("--dry-run", is_flag=True, help="Scan but don't repair")
@click.pass_context
def repair_covers(ctx: click.Context, dry_run: bool) -> None:
    """Find and repair books with missing or broken cover images.

    Checks for:
    - Books with no cover URL
    - Books with 1x1 pixel placeholder images (Open Library fallback)

    Tries to find covers from:
    1. Open Library (by ISBN)
    2. Google Books API (by ISBN, no API key needed)
    """
    try:
        config = Config.from_env()
    except ConfigurationError as e:
        raise click.ClickException(str(e)) from e

    async def run() -> None:
        client = NotionClient(config.notion_token)
        try:
            repairer = CoverRepairer(client, config.database_id)
            result = await repairer.repair_all(dry_run=dry_run)

            click.echo("\nResults:")
            click.echo(f"  Scanned: {result['scanned']} books needing repair")
            click.echo(f"  Repaired: {result['repaired']}")
            click.echo(f"  Failed: {result['failed']}")
        finally:
            await client.close()

    asyncio.run(run())


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
