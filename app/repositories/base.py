"""Repository protocols used to keep services independent of query details."""

from typing import Protocol, TypeVar

EntityT = TypeVar("EntityT")


class Repository(Protocol[EntityT]):
    """Minimal read contract shared by repository implementations."""

    def get(self, entity_id: int) -> EntityT | None:
        """Return an entity or None when it is not present."""
