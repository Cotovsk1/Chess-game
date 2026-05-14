from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, CheckConstraint, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Player(Base):
    __tablename__ = "player"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rating = Column(Integer, CheckConstraint('rating >= 100'), default=1200, nullable=False)
    created_at = Column(DateTime, server_default=func.now())  # Дата реєстрації

    # --- Нові поля для профілю ---
    status = Column(String(150), default="Граймо в шахи!", nullable=False)
    avatar_path = Column(String(255), nullable=True)  # Шлях до файлу на сервері

    # Зв'язок Many-to-Many сам на себе через таблицю friendship
    friends = relationship(
        "Player",
        secondary="friendship",
        primaryjoin="Player.id == Friendship.user1_id",
        secondaryjoin="Player.id == Friendship.user2_id",
        backref="added_by"
    )

class TimeControl(Base):
    __tablename__ = "time_control"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    initial_time_sec = Column(Integer, nullable=False)
    increment_sec = Column(Integer, nullable=False)

class Tournament(Base):
    __tablename__ = "tournament"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)

class Game(Base):
    __tablename__ = "game"

    id = Column(Integer, primary_key=True, index=True)
    white_player_id = Column(Integer, ForeignKey("player.id"), nullable=True)
    black_player_id = Column(Integer, ForeignKey("player.id"), nullable=True)
    time_control_id = Column(Integer, ForeignKey("time_control.id"), nullable=True)
    tournament_id = Column(Integer, ForeignKey("tournament.id"), nullable=True)
    result = Column(String(20), CheckConstraint("result IN ('WhiteWins', 'BlackWins', 'Draw', 'InProgress')"))
    played_at = Column(DateTime, server_default=func.now())

    white_player = relationship("Player", foreign_keys=[white_player_id])
    black_player = relationship("Player", foreign_keys=[black_player_id])
    moves = relationship("Move", back_populates="game", cascade="all, delete-orphan")

class Move(Base):
    __tablename__ = "move"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    move_number = Column(Integer, CheckConstraint('move_number > 0'), nullable=False)
    notation = Column(String(10), nullable=False)

    game = relationship("Game", back_populates="moves")

# Таблиця зв'язку для друзів
class Friendship(Base):
    __tablename__ = "friendship"

    user1_id = Column(Integer, ForeignKey("player.id", ondelete="CASCADE"), primary_key=True)
    user2_id = Column(Integer, ForeignKey("player.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(20), CheckConstraint("status IN ('pending', 'accepted', 'blocked')"), default="accepted")
    created_at = Column(DateTime, server_default=func.now())