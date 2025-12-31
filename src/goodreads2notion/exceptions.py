"""Custom exceptions for goodreads2notion."""


class GoodreadsNotionError(Exception):
    """Base exception for goodreads2notion."""


class ConfigurationError(GoodreadsNotionError):
    """Missing or invalid configuration."""


class CSVParseError(GoodreadsNotionError):
    """Error parsing CSV file."""

    def __init__(self, row_number: int, message: str):
        self.row_number = row_number
        super().__init__(f"Row {row_number}: {message}")


class RSSFetchError(GoodreadsNotionError):
    """Error fetching or parsing RSS feed."""

    def __init__(self, shelf: str, message: str):
        self.shelf = shelf
        super().__init__(f"Shelf '{shelf}': {message}")


class NotionAPIError(GoodreadsNotionError):
    """Error from Notion API."""

    def __init__(self, status_code: int, message: str, page_id: str | None = None):
        self.status_code = status_code
        self.page_id = page_id
        super().__init__(f"Notion API error ({status_code}): {message}")


class RateLimitError(NotionAPIError):
    """Notion API rate limit exceeded."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(429, f"Rate limited. Retry after {retry_after}s")


class SyncError(GoodreadsNotionError):
    """Error during sync operation."""

    def __init__(self, book_id: str, title: str, original_error: Exception):
        self.book_id = book_id
        self.title = title
        self.original_error = original_error
        super().__init__(f"Failed to sync '{title}' (ID: {book_id}): {original_error}")
