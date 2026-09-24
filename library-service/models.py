import uuid
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class Library(Base):
    __tablename__ = "library"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    library_uid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String(80), nullable=False)
    city = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_uid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)
    genre = Column(String(255), nullable=True)
    condition = Column(String(20), nullable=False, default="EXCELLENT")


class LibraryBook(Base):
    __tablename__ = "library_books"

    book_id = Column(Integer, ForeignKey("books.id"), primary_key=True)
    library_id = Column(Integer, ForeignKey("library.id"), primary_key=True)
    available_count = Column(Integer, nullable=False, default=0)