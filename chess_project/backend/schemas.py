from pydantic import BaseModel, EmailStr, Field


class MoveRequest(BaseModel):
    move: str
    promotion: str = "q"   # Фігура для промоції: q, r, b, n
    level: int = Field(5, ge=1, le=10)          # Рівень Stockfish 1-10


class StartGameRequest(BaseModel):
    level: int = Field(5, ge=1, le=10)
    time_control_id: int | None = None


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

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
