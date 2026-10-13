"""
Permission models for capability-based authorization.

Three tables:
- permission_catalog: reference catalog of all available permissions
- role_permission_templates: default permissions per role
- user_permissions: per-user permission overrides
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class PermissionCatalog(Base):
    """Reference catalog of all available permissions."""

    __tablename__ = "permission_catalog"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent: Mapped[str | None] = mapped_column(
        ForeignKey("permission_catalog.key"),
        nullable=True,
    )
    scope: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="module",
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class RolePermissionTemplate(Base):
    """Default permissions granted per role."""

    __tablename__ = "role_permission_templates"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("permission_catalog.key"),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("role", "permission_key", name="uq_role_permission"),)


class UserPermission(Base):
    """Per-user permission overrides."""

    __tablename__ = "user_permissions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_key: Mapped[str] = mapped_column(
        ForeignKey("permission_catalog.key"),
        nullable=False,
    )
    granted_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # True = additive grant (extra permission on top of role).
    # False = deny override (remove a role-granted permission from this user).
    granted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="permissions",
        foreign_keys=[user_id],
    )

    __table_args__ = (UniqueConstraint("user_id", "permission_key", name="uq_user_permission"),)
