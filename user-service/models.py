from sqlalchemy import Column, Integer, String
from database import Base


class Rating(Base):
    __tablename__ = "rating"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(80), nullable=False)
    stars = Column(Integer, nullable=False, default=1)