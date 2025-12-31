"""Data models for goodreads2notion."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Book(BaseModel):
    """Unified book model for both CSV and RSS sources."""

    # Primary identifier - Goodreads Book ID (used for deduplication)
    book_id: str

    # Core fields (present in both CSV and RSS)
    title: str
    author: str
    isbn: str | None = None
    isbn13: str | None = None
    my_rating: int = Field(ge=0, le=5, default=0)
    average_rating: float = Field(ge=0, le=5, default=0.0)
    num_pages: int | None = None
    year_published: int | None = None

    # Shelf/status info
    shelf: str  # "to-read", "currently-reading", "read"

    # Dates
    date_read: date | None = None
    date_added: date | None = None

    # Optional enrichment fields
    review: str | None = None
    cover_image_url: str | None = None
    book_description: str | None = None

    # CSV-only fields (not in RSS)
    publisher: str | None = None
    binding: str | None = None
    additional_authors: str | None = None
    original_publication_year: int | None = None
    private_notes: str | None = None
    read_count: int = 0

    @field_validator("isbn", "isbn13", mode="before")
    @classmethod
    def clean_isbn(cls, v: str | None) -> str | None:
        """Clean ISBN from CSV format like '=\"1234567890\"' to '1234567890'."""
        if v is None or v == "":
            return None
        # Remove ="..." wrapper from CSV export
        if isinstance(v, str) and v.startswith('="') and v.endswith('"'):
            v = v[2:-1]
        return v if v else None

    @field_validator("date_read", "date_added", mode="before")
    @classmethod
    def parse_date(cls, v: str | date | None) -> date | None:
        """Parse date from various formats."""
        if v is None or v == "":
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            # CSV format: "2025/12/30"
            if "/" in v:
                parts = v.split("/")
                if len(parts) == 3:
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
        return None

    @field_validator("my_rating", "read_count", mode="before")
    @classmethod
    def parse_int(cls, v: str | int | None) -> int:
        """Parse integer from string."""
        if v is None or v == "":
            return 0
        if isinstance(v, int):
            return v
        return int(v)

    @field_validator("average_rating", mode="before")
    @classmethod
    def parse_float(cls, v: str | float | None) -> float:
        """Parse float from string."""
        if v is None or v == "":
            return 0.0
        if isinstance(v, float):
            return v
        return float(v)

    @field_validator("num_pages", "year_published", "original_publication_year", mode="before")
    @classmethod
    def parse_optional_int(cls, v: str | int | None) -> int | None:
        """Parse optional integer from string."""
        if v is None or v == "":
            return None
        if isinstance(v, int):
            return v
        return int(v)

    @property
    def open_library_cover_url(self) -> str | None:
        """Generate Open Library cover URL from ISBN."""
        # Prefer ISBN-13, fall back to ISBN-10
        isbn = self.isbn13 or self.isbn
        if isbn:
            return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
        return None

    @property
    def notion_properties(self) -> dict[str, Any]:
        """Convert to Notion API property format."""
        props: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": self.title}}]},
            "Author": {"rich_text": [{"text": {"content": self.author}}]},
            "Goodreads ID": {"rich_text": [{"text": {"content": self.book_id}}]},
            "Shelf": {"select": {"name": self.shelf}},
        }

        if self.my_rating > 0:
            props["My Rating"] = {"number": self.my_rating}
        if self.average_rating > 0:
            props["Average Rating"] = {"number": self.average_rating}
        if self.isbn:
            props["ISBN"] = {"rich_text": [{"text": {"content": self.isbn}}]}
        if self.num_pages:
            props["Pages"] = {"number": self.num_pages}
        if self.date_read:
            props["Date Read"] = {"date": {"start": self.date_read.isoformat()}}
        if self.date_added:
            props["Date Added"] = {"date": {"start": self.date_added.isoformat()}}
        if self.review:
            # Truncate review to 2000 chars (Notion limit for rich_text)
            props["Review"] = {"rich_text": [{"text": {"content": self.review[:2000]}}]}

        # Use cover_image_url if available (RSS), otherwise generate from ISBN (Open Library)
        cover_url = self.cover_image_url or self.open_library_cover_url
        if cover_url:
            # Files & media type requires array of file objects
            props["Cover"] = {
                "files": [{"type": "external", "name": "Cover", "external": {"url": cover_url}}]
            }

        return props


class SyncState(BaseModel):
    """Track sync state for reporting."""

    last_sync_time: date | None = None
    books_synced: int = 0
    books_updated: int = 0
    books_added: int = 0
    errors: list[str] = Field(default_factory=list)
