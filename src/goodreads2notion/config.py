"""Configuration loading for goodreads2notion."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .exceptions import ConfigurationError


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    notion_token: str
    database_id: str
    goodreads_user_id: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        token = os.getenv("NOTION_TOKEN")
        if not token:
            raise ConfigurationError(
                "NOTION_TOKEN environment variable is required. "
                "Get it from https://www.notion.so/my-integrations"
            )

        database_id = os.getenv("NOTION_DATABASE_ID")
        if not database_id:
            raise ConfigurationError(
                "NOTION_DATABASE_ID environment variable is required. "
                "Copy it from your Notion database URL."
            )

        return cls(
            notion_token=token,
            database_id=database_id,
            goodreads_user_id=os.getenv("GOODREADS_USER_ID"),
        )
