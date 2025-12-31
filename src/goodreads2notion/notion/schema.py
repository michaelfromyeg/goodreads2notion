"""Notion database schema definitions."""

from typing import Any

from .client import NotionClient

# Schema for the Goodreads books database
# "Name" (title) already exists, so we don't include it here
NOTION_SCHEMA: dict[str, dict[str, Any]] = {
    "Author": {"rich_text": {}},
    "Goodreads ID": {"rich_text": {}},
    "ISBN": {"rich_text": {}},
    "Shelf": {
        "select": {
            "options": [
                {"name": "to-read", "color": "blue"},
                {"name": "currently-reading", "color": "yellow"},
                {"name": "read", "color": "green"},
            ]
        }
    },
    "My Rating": {"number": {"format": "number"}},
    "Average Rating": {"number": {"format": "number"}},
    "Pages": {"number": {"format": "number"}},
    "Date Read": {"date": {}},
    "Date Added": {"date": {}},
    "Review": {"rich_text": {}},
    "Cover": {"files": {}},
}


async def ensure_schema(client: NotionClient, database_id: str) -> None:
    """
    Ensure the database has all required properties.

    Adds any missing properties from NOTION_SCHEMA.
    """
    # Get current database schema
    db = await client.get_database(database_id)
    existing_props = set(db.get("properties", {}).keys())

    # Find missing properties
    missing_props = {}
    for prop_name, prop_config in NOTION_SCHEMA.items():
        if prop_name not in existing_props:
            missing_props[prop_name] = prop_config

    if not missing_props:
        print("Database schema is up to date.")
        return

    print(f"Adding {len(missing_props)} missing properties: {list(missing_props.keys())}")

    # Update database with missing properties
    await client.update_database(database_id, missing_props)
    print("Database schema updated successfully.")
