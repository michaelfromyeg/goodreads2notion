"""Parse Goodreads CSV export files."""

import csv
from collections.abc import Iterator
from pathlib import Path

from ..models import Book

# Map CSV column headers to Book model fields
CSV_FIELD_MAPPING = {
    "Book Id": "book_id",
    "Title": "title",
    "Author": "author",
    "Additional Authors": "additional_authors",
    "ISBN": "isbn",
    "ISBN13": "isbn13",
    "My Rating": "my_rating",
    "Average Rating": "average_rating",
    "Publisher": "publisher",
    "Binding": "binding",
    "Number of Pages": "num_pages",
    "Year Published": "year_published",
    "Original Publication Year": "original_publication_year",
    "Date Read": "date_read",
    "Date Added": "date_added",
    "Exclusive Shelf": "shelf",
    "My Review": "review",
    "Private Notes": "private_notes",
    "Read Count": "read_count",
}

# Standard shelves we support
STANDARD_SHELVES = {"to-read", "currently-reading", "read"}


def parse_csv(file_path: Path) -> Iterator[Book]:
    """
    Parse Goodreads CSV export file and yield Book objects.

    Only yields books on standard shelves (to-read, currently-reading, read).
    """
    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Map CSV columns to Book fields
            book_data: dict[str, str | int | float | None] = {}
            for csv_col, model_field in CSV_FIELD_MAPPING.items():
                value = row.get(csv_col, "").strip()
                if value:
                    book_data[model_field] = value

            # Skip books not on standard shelves
            shelf = book_data.get("shelf", "")
            if shelf not in STANDARD_SHELVES:
                continue

            yield Book(**book_data)  # type: ignore[arg-type]


def load_csv(file_path: Path) -> list[Book]:
    """Load all books from CSV into a list."""
    return list(parse_csv(file_path))
