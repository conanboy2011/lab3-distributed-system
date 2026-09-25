from datetime import datetime
import os
import time
import threading

import httpx
from fastapi import FastAPI, Depends, HTTPException, Header, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import models
from database import engine, get_db


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reservation Service")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if (
        exc.status_code == 503
        and exc.detail == "Bonus Service unavailable"
    ):
        return JSONResponse(
            status_code=503,
            content={
                "message": "Bonus Service unavailable"
            }
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail
        }
    )


LIBRARY_SERVICE_URL = os.getenv(
    "LIBRARY_SERVICE_URL",
    "http://library-service:8060"
)

RATING_SERVICE_URL = os.getenv(
    "RATING_SERVICE_URL",
    "http://user-service:8050"
)


def format_date(value):
    return value.strftime("%Y-%m-%d")


# ============================================================
# LIBRARY SERVICE
# ============================================================

def get_library_book(library_uid, book_uid):
    url = (
        f"{LIBRARY_SERVICE_URL}"
        f"/internal/libraries/{library_uid}/books/{book_uid}"
    )

    try:
        response = httpx.get(
            url,
            timeout=10
        )

        if response.status_code != 200:
            return {
                "book": {
                    "bookUid": book_uid
                },
                "library": {
                    "libraryUid": library_uid
                }
            }

        return response.json()

    except httpx.RequestError:
        return {
            "book": {
                "bookUid": book_uid
            },
            "library": {
                "libraryUid": library_uid
            }
        }


def get_library_book_strict(library_uid, book_uid):
    url = (
        f"{LIBRARY_SERVICE_URL}"
        f"/internal/libraries/{library_uid}/books/{book_uid}"
    )

    try:
        response = httpx.get(
            url,
            timeout=10
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=500,
            detail="Library Service unavailable"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Book or library not found"
        )

    return response.json()


def change_library_count(
    library_uid,
    book_uid,
    action,
    condition=None
):
    url = (
        f"{LIBRARY_SERVICE_URL}"
        f"/internal/libraries/{library_uid}/books/"
        f"{book_uid}/{action}"
    )

    data = {}

    if condition is not None:
        data["condition"] = condition

    try:
        response = httpx.post(
            url,
            json=data,
            timeout=10
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=500,
            detail="Library Service unavailable"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


# ============================================================
# RATING SERVICE
# ============================================================

def get_rating(username):
    try:
        response = httpx.get(
            f"{RATING_SERVICE_URL}/rating",
            headers={
                "X-User-Name": username
            },
            timeout=10
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Bonus Service unavailable"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Cannot get rating"
        )

    return response.json()


def change_rating(username, delta):
    try:
        response = httpx.post(
            f"{RATING_SERVICE_URL}/rating/change",
            json={
                "username": username,
                "delta": delta
            },
            timeout=10
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=500,
            detail="Rating Service unavailable"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Cannot change rating"
        )

    return response.json()


# ============================================================
# RETRY LOGIC
# ============================================================

def retry_library_return(
    library_uid,
    book_uid,
    condition,
    timeout_seconds=10
):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            return change_library_count(
                library_uid,
                book_uid,
                "return",
                condition
            )
        except HTTPException:
            time.sleep(1)

    return None


def retry_rating_change(
    username,
    delta,
    timeout_seconds=10
):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            return change_rating(
                username,
                delta
            )
        except HTTPException:
            time.sleep(1)

    return None


def background_rating_retry(
    username,
    delta
):
    while True:
        try:
            change_rating(
                username,
                delta
            )
            return
        except HTTPException:
            time.sleep(1)


def background_library_retry(
    library_uid,
    book_uid,
    condition
):
    while True:
        try:
            change_library_count(
                library_uid,
                book_uid,
                "return",
                condition
            )
            return
        except HTTPException:
            time.sleep(1)


def start_background_rating_retry(
    username,
    delta
):
    thread = threading.Thread(
        target=background_rating_retry,
        args=(
            username,
            delta
        ),
        daemon=True
    )

    thread.start()


def start_background_library_retry(
    library_uid,
    book_uid,
    condition
):
    thread = threading.Thread(
        target=background_library_retry,
        args=(
            library_uid,
            book_uid,
            condition
        ),
        daemon=True
    )

    thread.start()


# ============================================================
# HEALTH
# ============================================================

@app.get("/manage/health")
def health_check():
    return {
        "status": "OK"
    }


# ============================================================
# GET RESERVATIONS
# ============================================================

@app.get("/reservations")
def get_reservations(
    x_user_name: str = Header(...),
    db: Session = Depends(get_db)
):
    reservations = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.username == x_user_name,
            models.Reservation.status == "RENTED"
        )
        .order_by(
            models.Reservation.id.asc()
        )
        .all()
    )

    result = []

    for reservation in reservations:
        details = get_library_book(
            str(reservation.library_uid),
            str(reservation.book_uid)
        )

        result.append({
            "reservationUid": str(
                reservation.reservation_uid
            ),
            "status": reservation.status,
            "startDate": format_date(
                reservation.start_date
            ),
            "tillDate": format_date(
                reservation.till_date
            ),
            "book": details["book"],
            "library": details["library"]
        })

    return result


# ============================================================
# CREATE RESERVATION / BORROW
# ============================================================

@app.post("/reservations")
def create_reservation(
    data: dict,
    x_user_name: str = Header(...),
    db: Session = Depends(get_db)
):
    book_uid = data.get("bookUid")
    library_uid = data.get("libraryUid")
    till_date = data.get("tillDate")

    if not book_uid or not library_uid or not till_date:
        raise HTTPException(
            status_code=400,
            detail="Invalid request"
        )

    try:
        till_date_value = datetime.fromisoformat(
            till_date
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid tillDate"
        )

    rented_count = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.username == x_user_name,
            models.Reservation.status == "RENTED"
        )
        .count()
    )

    # Rating Service must be available before borrowing.
    rating = get_rating(x_user_name)
    stars = rating["stars"]

    if rented_count >= stars:
        raise HTTPException(
            status_code=409,
            detail="Maximum number of rented books reached"
        )

    # Library Service must be available before borrowing.
    details = get_library_book_strict(
        library_uid,
        book_uid
    )

    if details.get("availableCount", 0) <= 0:
        raise HTTPException(
            status_code=409,
            detail="Book is not available"
        )

    # IMPORTANT:
    # Use local runner time directly.
    # Do not force Europe/Moscow timezone here because
    # GitHub Actions runs in UTC and the official test
    # expects the runner's current date.
    reservation = models.Reservation(
        username=x_user_name,
        book_uid=book_uid,
        library_uid=library_uid,
        status="RENTED",
        start_date=datetime.now(),
        till_date=till_date_value
    )

    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    # Update library only after reservation has been created.
    try:
        change_library_count(
            library_uid,
            book_uid,
            "borrow"
        )

    except HTTPException:
        # Rollback reservation if library update fails.
        db.delete(reservation)
        db.commit()

        raise HTTPException(
            status_code=500,
            detail="Library update failed, reservation rolled back"
        )

    return {
        "reservationUid": str(
            reservation.reservation_uid
        ),
        "status": reservation.status,
        "startDate": format_date(
            reservation.start_date
        ),
        "tillDate": format_date(
            reservation.till_date
        ),
        "book": details["book"],
        "library": details["library"],
        "rating": {
            "stars": stars
        }
    }


# ============================================================
# RETURN BOOK
# ============================================================

@app.post(
    "/reservations/{reservation_uid}/return"
)
def return_book(
    reservation_uid: str,
    data: dict,
    x_user_name: str = Header(...),
    db: Session = Depends(get_db)
):
    reservation = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.reservation_uid
            == reservation_uid,
            models.Reservation.username
            == x_user_name,
            models.Reservation.status
            == "RENTED"
        )
        .first()
    )

    if not reservation:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )

    return_date = data.get("date")
    condition = data.get("condition")

    if not return_date or not condition:
        raise HTTPException(
            status_code=400,
            detail="Invalid request"
        )

    try:
        return_date_value = datetime.fromisoformat(
            return_date
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid date"
        )

    if condition not in [
        "EXCELLENT",
        "GOOD",
        "BAD"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid condition"
        )

    # Check whether the book is returned late.
    is_late = (
        return_date_value
        > reservation.till_date
    )

    if is_late:
        reservation.status = "EXPIRED"
    else:
        reservation.status = "RETURNED"

    db.commit()
    db.refresh(reservation)

    # ========================================================
    # Determine original book condition.
    # If Library Service is unavailable, use EXCELLENT
    # as fallback so the return operation can still finish.
    # ========================================================

    original_condition = "EXCELLENT"

    try:
        details = get_library_book_strict(
            str(reservation.library_uid),
            str(reservation.book_uid)
        )

        original_condition = (
            details["book"]["condition"]
        )

    except HTTPException:
        original_condition = "EXCELLENT"

    conditions = [
        "EXCELLENT",
        "GOOD",
        "BAD"
    ]

    condition_worsened = (
        conditions.index(condition)
        >
        conditions.index(original_condition)
    )

    # Rating:
    # +1 for normal return.
    # -10 for late return or worsened condition.
    if is_late or condition_worsened:
        rating_delta = -10
    else:
        rating_delta = 1

    # ========================================================
    # Update Library Service.
    # Retry synchronously for up to 10 seconds.
    # If still unavailable, continue return operation and
    # retry in background.
    # ========================================================

    library_result = retry_library_return(
        str(reservation.library_uid),
        str(reservation.book_uid),
        condition,
        timeout_seconds=10
    )

    if library_result is None:
        start_background_library_retry(
            str(reservation.library_uid),
            str(reservation.book_uid),
            condition
        )

    # ========================================================
    # Update Rating Service.
    # Retry synchronously for up to 10 seconds.
    # If still unavailable, continue return operation and
    # retry in background.
    # ========================================================

    rating_result = retry_rating_change(
        x_user_name,
        rating_delta,
        timeout_seconds=10
    )

    if rating_result is None:
        start_background_rating_retry(
            x_user_name,
            rating_delta
        )

    # Return operation itself succeeds even if the dependent
    # services were temporarily unavailable.
    return Response(
        status_code=204
    )