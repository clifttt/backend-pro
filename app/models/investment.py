from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Numeric, String, Date, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .startup import Startup
    from .investor import Investor


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(primary_key=True)

    startup_id: Mapped[int] = mapped_column(ForeignKey("startups.id"), index=True)
    investor_id: Mapped[int] = mapped_column(ForeignKey("investors.id"), index=True)

    round: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    amount_usd: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    date: Mapped[str | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    startup: Mapped["Startup"] = relationship(back_populates="investments")
    investor: Mapped["Investor"] = relationship(back_populates="investments")

    # Composite index for the most common compound filter
    __table_args__ = (
        Index("ix_investments_startup_investor", "startup_id", "investor_id"),
        Index("ix_investments_date_amount", "date", "amount_usd"),
    )
