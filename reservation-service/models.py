import uuid
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class Reservation(Base):
    __tablename__ = "reservation"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reservation_uid = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4
    )
    username = Column(String(80), nullable=False)
    book_uid = Column(UUID(as_uuid=True), nullable=False)
    library_uid = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False, default="RENTED")
    start_date = Column(DateTime, nullable=False)
    till_date = Column(DateTime, nullable=False)