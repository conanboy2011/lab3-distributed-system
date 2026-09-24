from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Library Service")


@app.get("/manage/health")
def health_check():
    return {"status": "OK"}


@app.get("/libraries")
def get_libraries(
    city: str,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(models.Library).filter(
        models.Library.city == city
    )

    total_elements = query.count()

    libraries = (
        query
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "page": page,
        "pageSize": len(libraries),
        "totalElements": total_elements,
        "items": [
            {
                "libraryUid": str(library.library_uid),
                "name": library.name,
                "city": library.city,
                "address": library.address
            }
            for library in libraries
        ]
    }


@app.get("/libraries/{library_uid}/books")
def get_library_books(
    library_uid: str,
    page: int = 1,
    size: int = 25,
    showAll: bool = False,
    db: Session = Depends(get_db)
):
    library = (
        db.query(models.Library)
        .filter(models.Library.library_uid == library_uid)
        .first()
    )

    if not library:
        raise HTTPException(
            status_code=404,
            detail="Library not found"
        )

    query = (
        db.query(models.Book, models.LibraryBook)
        .join(
            models.LibraryBook,
            models.Book.id == models.LibraryBook.book_id
        )
        .filter(models.LibraryBook.library_id == library.id)
    )

    if not showAll:
        query = query.filter(
            models.LibraryBook.available_count > 0
        )

    total_elements = query.count()

    results = (
        query
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "page": page,
        "pageSize": len(results),
        "totalElements": total_elements,
        "items": [
            {
                "bookUid": str(book.book_uid),
                "name": book.name,
                "author": book.author,
                "genre": book.genre,
                "condition": book.condition,
                "availableCount": library_book.available_count
            }
            for book, library_book in results
        ]
    }


@app.get("/internal/libraries/{library_uid}/books/{book_uid}")
def get_book_for_reservation(
    library_uid: str,
    book_uid: str,
    db: Session = Depends(get_db)
):
    library = (
        db.query(models.Library)
        .filter(models.Library.library_uid == library_uid)
        .first()
    )

    if not library:
        raise HTTPException(
            status_code=404,
            detail="Library not found"
        )

    result = (
        db.query(models.Book, models.LibraryBook)
        .join(
            models.LibraryBook,
            models.Book.id == models.LibraryBook.book_id
        )
        .filter(
            models.Book.book_uid == book_uid,
            models.LibraryBook.library_id == library.id
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    book, library_book = result

    return {
        "book": {
            "bookUid": str(book.book_uid),
            "name": book.name,
            "author": book.author,
            "genre": book.genre,
            "condition": book.condition
        },
        "library": {
            "libraryUid": str(library.library_uid),
            "name": library.name,
            "address": library.address,
            "city": library.city
        },
        "availableCount": library_book.available_count
    }


@app.post("/internal/libraries/{library_uid}/books/{book_uid}/borrow")
def borrow_book(
    library_uid: str,
    book_uid: str,
    db: Session = Depends(get_db)
):
    library = (
        db.query(models.Library)
        .filter(models.Library.library_uid == library_uid)
        .first()
    )

    if not library:
        raise HTTPException(
            status_code=404,
            detail="Library not found"
        )

    result = (
        db.query(models.Book, models.LibraryBook)
        .join(
            models.LibraryBook,
            models.Book.id == models.LibraryBook.book_id
        )
        .filter(
            models.Book.book_uid == book_uid,
            models.LibraryBook.library_id == library.id
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    book, library_book = result

    if library_book.available_count <= 0:
        raise HTTPException(
            status_code=409,
            detail="Book is not available"
        )

    library_book.available_count -= 1

    db.commit()

    return {
        "availableCount": library_book.available_count
    }


@app.post("/internal/libraries/{library_uid}/books/{book_uid}/return")
def return_book(
    library_uid: str,
    book_uid: str,
    data: dict,
    db: Session = Depends(get_db)
):
    library = (
        db.query(models.Library)
        .filter(models.Library.library_uid == library_uid)
        .first()
    )

    if not library:
        raise HTTPException(
            status_code=404,
            detail="Library not found"
        )

    result = (
        db.query(models.Book, models.LibraryBook)
        .join(
            models.LibraryBook,
            models.Book.id == models.LibraryBook.book_id
        )
        .filter(
            models.Book.book_uid == book_uid,
            models.LibraryBook.library_id == library.id
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    book, library_book = result

    condition = data.get("condition")

    if condition not in ["EXCELLENT", "GOOD", "BAD"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid condition"
        )

    library_book.available_count += 1
    book.condition = condition

    db.commit()

    return {
        "availableCount": library_book.available_count,
        "condition": book.condition
    }
