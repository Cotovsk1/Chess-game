from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List

import models
import schemas
from database import get_db
from routers.auth import get_current_user
from state_manager import notification_manager

router = APIRouter(tags=["friends"])


def _find_existing_friendship(db: Session, user_a_id: int, user_b_id: int) -> models.Friendship | None:
    """Знаходить запис дружби в обох напрямках."""
    return db.query(models.Friendship).filter(
        or_(
            and_(models.Friendship.user1_id == user_a_id, models.Friendship.user2_id == user_b_id),
            and_(models.Friendship.user1_id == user_b_id, models.Friendship.user2_id == user_a_id),
        )
    ).first()


def _friendship_to_response(friendship: models.Friendship, current_user_id: int) -> dict:
    """Конвертує запис Friendship у словник для FriendshipResponse."""
    is_initiator = friendship.user1_id == current_user_id
    other_user = friendship.user2 if is_initiator else friendship.user1
    return {
        "user_id": other_user.id,
        "username": other_user.username,
        "rating": other_user.rating,
        "avatar_url": other_user.avatar_url,
        "status": friendship.status,
        "is_incoming": not is_initiator,
        "created_at": friendship.created_at,
    }


# ─── Надіслати запит на дружбу ────────────────────────────────────────

@router.post("/request", response_model=schemas.FriendshipResponse, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    body: schemas.FriendRequest,
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Не можна додати себе
    if body.username == current_user.username:
        raise HTTPException(status_code=400, detail="Не можна надіслати запит самому собі")

    target = db.query(models.Player).filter(models.Player.username == body.username).first()
    if not target:
        raise HTTPException(status_code=404, detail="Гравця не знайдено")

    # Перевірка чи вже існує дружба або запит
    existing = _find_existing_friendship(db, current_user.id, target.id)
    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=409, detail="Ви вже друзі")
        elif existing.user1_id == current_user.id:
            raise HTTPException(status_code=409, detail="Запит вже надіслано")
        else:
            # Зустрічний запит — автоматично приймаємо дружбу
            existing.status = "accepted"
            db.commit()
            db.refresh(existing)

            # Сповіщення обом
            await notification_manager.send_to_user(target.id, {
                "type": "friend_accepted",
                "user_id": current_user.id,
                "username": current_user.username,
            })

            return _friendship_to_response(existing, current_user.id)

    # Створюємо новий запит
    friendship = models.Friendship(
        user1_id=current_user.id,
        user2_id=target.id,
        status="pending",
    )
    db.add(friendship)
    db.commit()
    db.refresh(friendship)

    # WebSocket сповіщення (тільки якщо НЕ в грі)
    await notification_manager.send_to_user(target.id, {
        "type": "friend_request",
        "user_id": current_user.id,
        "username": current_user.username,
        "avatar_url": current_user.avatar_url,
    })

    return _friendship_to_response(friendship, current_user.id)


# ─── Прийняти запит ──────────────────────────────────────────────────

@router.post("/accept/{user_id}", response_model=schemas.FriendshipResponse)
async def accept_friend_request(
    user_id: int,
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Шукаємо запит де user_id — ініціатор, current_user — отримувач
    friendship = db.query(models.Friendship).filter(
        models.Friendship.user1_id == user_id,
        models.Friendship.user2_id == current_user.id,
        models.Friendship.status == "pending",
    ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="Запит на дружбу не знайдено")

    friendship.status = "accepted"
    db.commit()
    db.refresh(friendship)

    # Сповіщення ініціатору
    await notification_manager.send_to_user(user_id, {
        "type": "friend_accepted",
        "user_id": current_user.id,
        "username": current_user.username,
    })

    return _friendship_to_response(friendship, current_user.id)


# ─── Відхилити запит ─────────────────────────────────────────────────

@router.post("/reject/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def reject_friend_request(
    user_id: int,
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendship = db.query(models.Friendship).filter(
        models.Friendship.user1_id == user_id,
        models.Friendship.user2_id == current_user.id,
        models.Friendship.status == "pending",
    ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="Запит на дружбу не знайдено")

    db.delete(friendship)
    db.commit()


# ─── Скасувати мій запит ─────────────────────────────────────────────

@router.delete("/cancel/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_friend_request(
    user_id: int,
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendship = db.query(models.Friendship).filter(
        models.Friendship.user1_id == current_user.id,
        models.Friendship.user2_id == user_id,
        models.Friendship.status == "pending",
    ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="Запит не знайдено")

    db.delete(friendship)
    db.commit()


# ─── Видалити друга ──────────────────────────────────────────────────

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(
    user_id: int,
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendship = _find_existing_friendship(db, current_user.id, user_id)
    if not friendship or friendship.status != "accepted":
        raise HTTPException(status_code=404, detail="Друга не знайдено")

    db.delete(friendship)
    db.commit()


# ─── Список друзів ───────────────────────────────────────────────────

@router.get("/", response_model=List[schemas.FriendshipResponse])
def get_friends(
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = db.query(models.Friendship).filter(
        or_(
            models.Friendship.user1_id == current_user.id,
            models.Friendship.user2_id == current_user.id,
        ),
        models.Friendship.status == "accepted",
    ).all()

    return [_friendship_to_response(f, current_user.id) for f in friendships]


# ─── Вхідні запити ───────────────────────────────────────────────────

@router.get("/requests/incoming", response_model=List[schemas.FriendshipResponse])
def get_incoming_requests(
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = db.query(models.Friendship).filter(
        models.Friendship.user2_id == current_user.id,
        models.Friendship.status == "pending",
    ).all()

    return [_friendship_to_response(f, current_user.id) for f in friendships]


# ─── Вихідні запити ──────────────────────────────────────────────────

@router.get("/requests/outgoing", response_model=List[schemas.FriendshipResponse])
def get_outgoing_requests(
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friendships = db.query(models.Friendship).filter(
        models.Friendship.user1_id == current_user.id,
        models.Friendship.status == "pending",
    ).all()

    return [_friendship_to_response(f, current_user.id) for f in friendships]


# ─── Пошук гравців ──────────────────────────────────────────────────

@router.get("/search", response_model=List[schemas.UserSearchResponse])
def search_users(
    q: str,
    limit: int = 20,
    current_user: models.Player = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Запит пошуку занадто короткий (мін. 2 символи)")

    players = (
        db.query(models.Player)
        .filter(
            models.Player.username.ilike(f"%{q}%"),
            models.Player.id != current_user.id,
        )
        .limit(limit)
        .all()
    )

    result = []
    for player in players:
        friendship = _find_existing_friendship(db, current_user.id, player.id)
        is_friend = friendship is not None and friendship.status == "accepted"
        has_pending = friendship is not None and friendship.status == "pending"

        result.append({
            "id": player.id,
            "username": player.username,
            "rating": player.rating,
            "avatar_url": player.avatar_url,
            "is_friend": is_friend,
            "has_pending_request": has_pending,
        })

    return result
