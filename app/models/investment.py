from sqlalchemy import ForeignKey, Numeric, String, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(primary_key=True)

    startup_id: Mapped[int] = mapped_column(ForeignKey("startups.id"))
    investor_id: Mapped[int] = mapped_column(ForeignKey("investors.id"))

    round: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount_usd: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    announced_date: Mapped[str | None] = mapped_column(Date, nullable=True)

    startup: Mapped["Startup"] = relationship(back_populates="investments")
    investor: Mapped["Investor"] = relationship(back_populates="investments")
