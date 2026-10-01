import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Timestamps


class Faculty(Timestamps, Base):
    __tablename__ = "faculty"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(80))

    user = relationship("User", back_populates="faculty", lazy="raise")
