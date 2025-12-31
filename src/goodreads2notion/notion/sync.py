"""Sync logic for upserting books to Notion."""

import asyncio

from ..models import Book, SyncState
from .client import NotionClient


class BookSyncer:
    """Handles syncing books to Notion with upsert logic."""

    def __init__(self, client: NotionClient, database_id: str):
        self.client = client
        self.database_id = database_id
        self._book_id_to_page_id: dict[str, str] = {}

    async def build_lookup_index(self) -> None:
        """
        Query all existing books from Notion and build lookup index.

        This maps Goodreads book IDs to Notion page IDs for deduplication.
        """
        self._book_id_to_page_id = {}

        print("Building lookup index from existing Notion pages...")
        count = 0

        async for page in self.client.query_database_all(self.database_id):
            goodreads_id = self._extract_goodreads_id(page)
            if goodreads_id:
                self._book_id_to_page_id[goodreads_id] = page["id"]
            count += 1

        print(f"Indexed {len(self._book_id_to_page_id)} books with Goodreads IDs ({count} total)")

    def _extract_goodreads_id(self, page: dict) -> str | None:
        """Extract Goodreads ID from a Notion page's properties."""
        props = page.get("properties", {})
        gr_id_prop = props.get("Goodreads ID", {})
        rich_text = gr_id_prop.get("rich_text", [])
        if rich_text:
            return rich_text[0].get("plain_text", "")
        return None

    async def sync_book(self, book: Book) -> tuple[str, str]:
        """
        Sync a single book to Notion.

        Returns: (action, page_id) where action is "created" or "updated"
        """
        existing_page_id = self._book_id_to_page_id.get(book.book_id)

        if existing_page_id:
            # Update existing page
            await self.client.update_page(existing_page_id, book.notion_properties)
            return ("updated", existing_page_id)
        else:
            # Create new page
            new_page = await self.client.create_page(self.database_id, book.notion_properties)
            new_page_id = new_page["id"]
            # Update our index
            self._book_id_to_page_id[book.book_id] = new_page_id
            return ("created", new_page_id)

    async def sync_books(
        self,
        books: list[Book],
        rate_limit_delay: float = 0.35,
    ) -> SyncState:
        """
        Sync multiple books with rate limiting and progress tracking.

        Args:
            books: List of books to sync
            rate_limit_delay: Seconds to wait between API calls (Notion limit: 3 req/s)
        """
        state = SyncState()

        # Ensure we have the lookup index
        if not self._book_id_to_page_id:
            await self.build_lookup_index()

        total = len(books)
        for i, book in enumerate(books, 1):
            try:
                action, _ = await self.sync_book(book)
                if action == "created":
                    state.books_added += 1
                else:
                    state.books_updated += 1
                state.books_synced += 1

                # Progress logging
                if i % 10 == 0 or i == total:
                    print(f"Progress: {i}/{total} books synced")

                # Rate limiting
                await asyncio.sleep(rate_limit_delay)

            except Exception as e:
                error_msg = f"Failed to sync '{book.title}': {e}"
                state.errors.append(error_msg)
                print(f"  Error: {error_msg}")

        return state
