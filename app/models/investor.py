from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .investment import Investment


class Investor(Base):
    __tablename__ = "investors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    fund_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    focus_area: Mapped[str | None] = mapped_column(String(255), nullable=True)

    investments: Mapped[list["Investment"]] = relationship(back_populates="investor")
