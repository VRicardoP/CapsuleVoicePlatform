"""
Base repository pattern for data access.
Provides common CRUD operations with audit logging.
"""

from collections.abc import Sequence
from datetime import UTC
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):  # noqa: UP046
    """
    Base repository with common CRUD operations.

    All data access goes through repositories to ensure:
    - Consistent query patterns
    - Audit trail integration
    - RLS context setting
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Get a single record by ID."""
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
    ) -> Sequence[ModelType]:
        """Get all records with pagination."""
        query = select(self.model)

        if order_by:
            if hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by).desc())
        elif hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, filters: list | None = None) -> int:
        """Count total records, optionally applying filter clauses."""
        query = select(func.count()).select_from(self.model)
        if filters:
            for f in filters:
                query = query.where(f)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        id: UUID,
        obj_in: dict[str, Any],
    ) -> ModelType | None:
        """Update a record by ID."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None

        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: UUID) -> bool:
        """Hard delete a record by ID."""
        result = await self.session.execute(delete(self.model).where(self.model.id == id))
        return result.rowcount > 0

    async def soft_delete(self, id: UUID) -> ModelType | None:
        """
        Soft delete a record (set deleted_at).
        Used for GDPR compliance before blocking.
        """
        from datetime import datetime

        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None

        if hasattr(db_obj, "deleted_at"):
            db_obj.deleted_at = datetime.now(UTC)
            await self.session.flush()
            await self.session.refresh(db_obj)

        return db_obj

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists by ID."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar_one() > 0
