"""Explicit relational schema creation command."""

from backend.app.core.database import Base, get_engine
from backend.app.models.chunk import Chunk
from backend.app.models.document import Document


def main() -> None:
    """Create known tables without coupling database health to app startup."""
    _ = (Document, Chunk)  # Imports register both models in Base.metadata.
    Base.metadata.create_all(bind=get_engine())


if __name__ == "__main__":
    main()
