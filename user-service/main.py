from fastapi import FastAPI, Depends, Header
from sqlalchemy.orm import Session

import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rating System")


@app.get("/manage/health")
def health_check():
    return {"status": "OK"}


@app.get("/rating")
def get_rating(
    x_user_name: str = Header(...),
    db: Session = Depends(get_db)
):
    rating = (
        db.query(models.Rating)
        .filter(models.Rating.username == x_user_name)
        .first()
    )

    if not rating:
        rating = models.Rating(
            username=x_user_name,
            stars=75
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)

    return {
        "username": rating.username,
        "stars": rating.stars
    }


@app.post("/rating/change")
def change_rating(
    data: dict,
    db: Session = Depends(get_db)
):
    username = data.get("username")
    delta = data.get("delta")

    if not username or delta is None:
        return {"error": "Invalid request"}

    rating = (
        db.query(models.Rating)
        .filter(models.Rating.username == username)
        .first()
    )

    if not rating:
        rating = models.Rating(
            username=username,
            stars=75
        )
        db.add(rating)
        db.flush()

    rating.stars = max(1, min(100, rating.stars + int(delta)))

    db.commit()
    db.refresh(rating)

    return {
        "stars": rating.stars
    }

