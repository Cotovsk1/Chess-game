from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class MoveRequest(BaseModel):
    move: str
    promotion: str = "q"   # Фігура для промоції: q, r, b, n
    level: int = Field(5, ge=1, le=10)          # Рівень Stockfish 1-10


class StartGameRequest(BaseModel):
    level: int = Field(5, ge=1, le=10)
    time_control_id: int | None = None
    color: str = "w"  # 'w', 'b', або 'random'


class CustomGameRequest(BaseModel):
    fen: str
    level: int = Field(5, ge=1, le=10)
    time_control_id: int | None = None


class PlayerCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class PlayerResponse(BaseModel):
    id: int
    username: str
    email: str
    rating: int
    avatar_url: str | None = None
    status_text: str | None = None
    created_at: datetime | None = None
    is_active: bool = True




class Token(BaseModel):
    access_token: str
    token_type: str

class GameResponse(BaseModel):
    game_id: str
    board_fen: str
    status: str = "active"  
    last_move: str | None = None
    
    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    id: int
    player_id: int
    username: str
    message: str
    sent_at: datetime
    
    class Config:
        from_attributes = True


class FriendRequest(BaseModel):
    """Запит на додавання друга — по username"""
    username: str = Field(..., min_length=1, max_length=50)


class FriendshipResponse(BaseModel):
    """Відповідь з інфо про дружбу"""
    user_id: int
    username: str
    rating: int
    avatar_url: str | None = None
    status: str          # "pending" | "accepted"
    is_incoming: bool     # True = цей запит надійшов мені; False = я його відправив
    created_at: datetime

    class Config:
        from_attributes = True


class UserSearchResponse(BaseModel):
    """Результат пошуку гравців"""
    id: int
    username: str
    rating: int
    avatar_url: str | None = None
    is_friend: bool = False
    has_pending_request: bool = False

    class Config:
        from_attributes = True