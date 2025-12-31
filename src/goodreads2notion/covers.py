"""Cover image utilities and repair logic."""

import asyncio
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .notion.client import NotionClient

# Open Library returns a tiny placeholder (~43 bytes) when no cover exists
PLACEHOLDER_MAX_SIZE = 1000  # bytes - real covers are much larger

# Cover sources in order of preference
OPEN_LIBRARY_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"


async def check_cover_valid(url: str, client: httpx.AsyncClient) -> bool:
    """Check if a cover URL returns a valid image (not a 1x1 placeholder)."""
    try:
        # Use HEAD request first to check Content-Length
        response = await client.head(url, timeout=10.0, follow_redirects=True)
        if response.status_code != 200:
            return False

        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < PLACEHOLDER_MAX_SIZE:
            return False

        return True
    except Exception:
        return False


async def get_open_library_cover(isbn: str, client: httpx.AsyncClient) -> str | None:
    """Get cover URL from Open Library, returns None if placeholder."""
    url = OPEN_LIBRARY_URL.format(isbn=isbn)
    if await check_cover_valid(url, client):
        return url
    return None


async def get_google_books_cover(isbn: str, client: httpx.AsyncClient) -> str | None:
    """Get cover URL from Google Books API (free, no API key needed)."""
    try:
        url = GOOGLE_BOOKS_URL.format(isbn=isbn)
        response = await client.get(url, timeout=10.0)
        if response.status_code != 200:
            return None

        data = response.json()
        items = data.get("items", [])
        if not items:
            return None

        return _extract_google_books_cover(items[0])
    except Exception:
        return None


def _extract_google_books_cover(item: dict) -> str | None:
    """Extract cover URL from a Google Books API item."""
    volume_info = item.get("volumeInfo", {})
    image_links = volume_info.get("imageLinks", {})

    # Try to get the largest available image
    for key in ["extraLarge", "large", "medium", "thumbnail", "smallThumbnail"]:
        if key in image_links:
            cover_url = image_links[key]
            # Upgrade to larger size by modifying the URL
            cover_url = cover_url.replace("zoom=1", "zoom=2")
            cover_url = cover_url.replace("&edge=curl", "")
            return cover_url

    return None


async def search_google_books_by_title(
    title: str, author: str | None, client: httpx.AsyncClient
) -> str | None:
    """Search Google Books by title and author to find a cover."""
    try:
        # Build search query
        query = f'intitle:"{title}"'
        if author:
            # Take first author name (before comma if "Last, First" format)
            author_name = author.split(",")[0].strip()
            query += f' inauthor:"{author_name}"'

        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5"
        response = await client.get(url, timeout=10.0)
        if response.status_code != 200:
            return None

        data = response.json()
        items = data.get("items", [])
        if not items:
            return None

        # Try each result until we find one with a cover
        for item in items:
            cover = _extract_google_books_cover(item)
            if cover:
                return cover

        return None
    except Exception:
        return None


async def find_best_cover(
    isbn: str | None = None,
    isbn13: str | None = None,
    title: str | None = None,
    author: str | None = None,
) -> str | None:
    """Try multiple sources to find a valid cover image."""
    async with httpx.AsyncClient() as client:
        # Try ISBN-based lookup first (more accurate)
        for isbn_to_try in [isbn13, isbn]:
            if not isbn_to_try:
                continue

            # Try Open Library first (better quality usually)
            cover = await get_open_library_cover(isbn_to_try, client)
            if cover:
                return cover

            # Fall back to Google Books by ISBN
            cover = await get_google_books_cover(isbn_to_try, client)
            if cover:
                return cover

        # If no ISBN or ISBN lookup failed, try title+author search
        if title:
            cover = await search_google_books_by_title(title, author, client)
            if cover:
                return cover

    return None


class CoverRepairer:
    """Repairs missing or broken covers in Notion database."""

    def __init__(self, notion_client: "NotionClient", database_id: str):
        self.client = notion_client
        self.database_id = database_id

    def _extract_book_info(self, page: dict) -> dict:
        """Extract relevant book info from Notion page."""
        props = page.get("properties", {})

        def get_text(prop_name: str) -> str | None:
            prop = props.get(prop_name, {})
            if "rich_text" in prop:
                texts = prop["rich_text"]
                return texts[0]["plain_text"] if texts else None
            if "title" in prop:
                titles = prop["title"]
                return titles[0]["plain_text"] if titles else None
            return None

        def get_files(prop_name: str) -> str | None:
            prop = props.get(prop_name, {})
            files = prop.get("files", [])
            if files:
                file_obj = files[0]
                if file_obj.get("type") == "external":
                    return file_obj.get("external", {}).get("url")
                elif file_obj.get("type") == "file":
                    return file_obj.get("file", {}).get("url")
            return None

        return {
            "page_id": page["id"],
            "title": get_text("Name"),
            "author": get_text("Author"),
            "isbn": get_text("ISBN"),
            "goodreads_id": get_text("Goodreads ID"),
            "cover_url": get_files("Cover"),
        }

    async def find_books_needing_covers(self) -> list[dict]:
        """Find all books with missing or broken covers."""
        books_to_repair = []

        print("Scanning database for books with missing/broken covers...")
        total = 0
        async with httpx.AsyncClient() as http_client:
            async for page in self.client.query_database_all(self.database_id):
                total += 1
                book_info = self._extract_book_info(page)

                needs_repair = False
                reason = ""

                if not book_info["cover_url"]:
                    needs_repair = True
                    reason = "no cover"
                else:
                    # Check if existing cover is valid
                    is_valid = await check_cover_valid(book_info["cover_url"], http_client)
                    if not is_valid:
                        needs_repair = True
                        reason = "broken cover (1x1 placeholder)"

                # Can repair if we have ISBN or title
                can_repair = book_info["isbn"] or book_info["title"]

                if needs_repair and can_repair:
                    book_info["reason"] = reason
                    books_to_repair.append(book_info)

                if total % 50 == 0:
                    print(
                        f"  Scanned {total} books, found {len(books_to_repair)} needing repair..."
                    )

                # Small delay to avoid hammering servers
                await asyncio.sleep(0.1)

        print(f"Scanned {total} books, {len(books_to_repair)} need cover repair")
        return books_to_repair

    async def repair_cover(self, book_info: dict) -> bool:
        """Attempt to repair a single book's cover."""
        isbn = book_info.get("isbn")
        title = book_info.get("title")
        author = book_info.get("author")

        # Parse ISBN-13 from ISBN field if it looks like one
        isbn13 = isbn if isbn and len(isbn) == 13 else None
        isbn10 = isbn if isbn and len(isbn) == 10 else None

        # Try to find a valid cover (ISBN first, then title+author)
        new_cover_url = await find_best_cover(
            isbn=isbn10, isbn13=isbn13, title=title, author=author
        )

        if not new_cover_url:
            return False

        # Update Notion page with new cover
        properties = {
            "Cover": {
                "files": [{"type": "external", "name": "Cover", "external": {"url": new_cover_url}}]
            }
        }

        await self.client.update_page(book_info["page_id"], properties)
        return True

    async def repair_all(self, dry_run: bool = False) -> dict:
        """Repair all books with missing/broken covers."""
        books = await self.find_books_needing_covers()

        if not books:
            return {"scanned": 0, "repaired": 0, "failed": 0}

        if dry_run:
            print(f"\nDry run - would attempt to repair {len(books)} books:")
            for book in books[:10]:
                print(f"  - {book['title']} ({book['reason']})")
            if len(books) > 10:
                print(f"  ... and {len(books) - 10} more")
            return {"scanned": len(books), "repaired": 0, "failed": 0}

        print(f"\nRepairing {len(books)} books...")
        repaired = 0
        failed = 0

        for i, book in enumerate(books, 1):
            try:
                success = await self.repair_cover(book)
                if success:
                    repaired += 1
                    print(f"  [{i}/{len(books)}] Repaired: {book['title']}")
                else:
                    failed += 1
                    print(f"  [{i}/{len(books)}] No cover found: {book['title']}")
            except Exception as e:
                failed += 1
                print(f"  [{i}/{len(books)}] Error: {book['title']} - {e}")

            # Rate limiting
            await asyncio.sleep(0.35)

        return {"scanned": len(books), "repaired": repaired, "failed": failed}
