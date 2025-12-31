"""Parse Goodreads RSS feeds."""

import asyncio
import html
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime

import httpx

from ..exceptions import RSSFetchError
from ..models import Book

SHELF_FEEDS = {
    "to-read": "https://www.goodreads.com/review/list_rss/{user_id}?shelf=to-read",
    "currently-reading": "https://www.goodreads.com/review/list_rss/{user_id}?shelf=currently-reading",
    "read": "https://www.goodreads.com/review/list_rss/{user_id}?shelf=read",
}


def _get_text(item: ET.Element, tag: str) -> str | None:
    """Get text content from an XML element."""
    elem = item.find(tag)
    return elem.text.strip() if elem is not None and elem.text else None


def _get_int(item: ET.Element, tag: str) -> int | None:
    """Get integer from an XML element."""
    text = _get_text(item, tag)
    if text and text.isdigit():
        return int(text)
    return None


def _get_float(item: ET.Element, tag: str) -> float | None:
    """Get float from an XML element."""
    text = _get_text(item, tag)
    if text:
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _parse_rss_date(item: ET.Element, tag: str) -> date | None:
    """Parse date from RSS format (e.g., 'Sat, 30 Dec 2025 00:00:00 -0800')."""
    text = _get_text(item, tag)
    if not text:
        return None
    try:
        # Try parsing with timezone offset
        # Format: "Sat, 04 Nov 2025 08:06:11 -0800"
        # Remove the timezone for simpler parsing
        date_str = text.rsplit(" ", 1)[0]
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S")
        return dt.date()
    except ValueError:
        return None


def _strip_html(text: str) -> str:
    """Strip HTML tags and decode entities from text."""
    # Remove CDATA wrapper if present
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    return text.strip()


def parse_rss_item(item: ET.Element, shelf: str) -> Book:
    """Parse a single RSS item element into a Book."""
    # Get basic fields
    book_id = _get_text(item, "book_id") or ""
    title = _get_text(item, "title") or ""
    author = _get_text(item, "author_name") or ""

    # Get review and clean HTML
    review = _get_text(item, "user_review")
    if review:
        review = _strip_html(review)

    # Get cover image URL (try large first, then fallback)
    cover_url = (
        _get_text(item, "book_large_image_url")
        or _get_text(item, "book_medium_image_url")
        or _get_text(item, "book_image_url")
    )

    # Get book description and clean HTML
    description = _get_text(item, "book_description")
    if description:
        description = _strip_html(description)

    return Book(
        book_id=book_id,
        title=title,
        author=author,
        isbn=_get_text(item, "isbn"),
        my_rating=_get_int(item, "user_rating") or 0,
        average_rating=_get_float(item, "average_rating") or 0.0,
        num_pages=_get_int(item, "num_pages"),
        year_published=_get_int(item, "book_published"),
        shelf=shelf,
        date_read=_parse_rss_date(item, "user_read_at"),
        date_added=_parse_rss_date(item, "user_date_added"),
        review=review,
        cover_image_url=cover_url,
        book_description=description,
    )


async def fetch_shelf_rss(user_id: str, shelf: str) -> list[Book]:
    """Fetch and parse all books from a shelf's RSS feed."""
    if shelf not in SHELF_FEEDS:
        raise RSSFetchError(shelf, f"Unknown shelf: {shelf}")

    url = SHELF_FEEDS[shelf].format(user_id=user_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RSSFetchError(shelf, str(e)) from e

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        raise RSSFetchError(shelf, f"Invalid XML: {e}") from e

    channel = root.find("channel")
    if channel is None:
        return []

    books = []
    for item in channel.findall("item"):
        try:
            books.append(parse_rss_item(item, shelf))
        except Exception:
            # Skip malformed items but continue parsing
            continue

    return books


async def fetch_all_shelves(user_id: str) -> list[Book]:
    """Fetch books from all standard shelves via RSS."""
    tasks = [fetch_shelf_rss(user_id, shelf) for shelf in SHELF_FEEDS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_books: list[Book] = []
    for i, result in enumerate(results):
        shelf = list(SHELF_FEEDS.keys())[i]
        if isinstance(result, BaseException):
            # Log error but continue with other shelves
            print(f"Warning: Failed to fetch {shelf} shelf: {result}")
        else:
            all_books.extend(result)

    return all_books
