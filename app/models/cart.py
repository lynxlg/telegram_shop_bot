from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (UniqueConstraint("user_id", name="uq_carts_user_id"),)

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship("User", back_populates="cart")
    items: Mapped[list[CartItem]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )
