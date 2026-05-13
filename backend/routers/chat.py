from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import get_db
from state_manager import active_games

router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("/global", response_model=List[schemas.ChatMessageResponse])
def get_global_chat(limit: int = 50, db: Session = Depends(get_db)):
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.game_id == None)
        .order_by(models.ChatMessage.sent_at.desc())
        .limit(limit)
        .all()
    )
    messages = messages[::-1]
    
    response = []
    for msg in messages:
        response.append({
            "id": msg.id,
            "player_id": msg.player_id,
            "username": msg.player.username if msg.player else "Unknown",
            "message": msg.message,
            "sent_at": msg.sent_at
        })
    return response

@router.get("/game/{game_id}", response_model=List[schemas.ChatMessageResponse])
def get_game_chat(game_id: str, limit: int = 50, db: Session = Depends(get_db)):
    if game_id not in active_games:
        return []
    
    db_id = active_games[game_id].db_id
    if not db_id:
        return []

    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.game_id == db_id)
        .order_by(models.ChatMessage.sent_at.desc())
        .limit(limit)
        .all()
    )
    messages = messages[::-1]
    
    response = []
    for msg in messages:
        response.append({
            "id": msg.id,
            "player_id": msg.player_id,
            "username": msg.player.username if msg.player else "Unknown",
            "message": msg.message,
            "sent_at": msg.sent_at
        })
    return response
