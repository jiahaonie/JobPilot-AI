"""用于隔离服务与查询细节的仓库协议。"""

from typing import Protocol, TypeVar

EntityT = TypeVar("EntityT")


class Repository(Protocol[EntityT]):
    """仓库实现共享的最小读取契约。"""

    def get(self, entity_id: int) -> EntityT | None:
        """返回实体；不存在时返回空值。"""
