from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, CheckConstraint, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Player(Base):
    __tablename__ = "player"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rating = Column(Integer, default=1200, nullable=False)
    avatar_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    friendships_initiated = relationship("Friendship", foreign_keys="Friendship.user1_id", back_populates="user1")
    friendships_received = relationship("Friendship", foreign_keys="Friendship.user2_id", back_populates="user2")
    games_as_white = relationship("Game", foreign_keys="Game.white_player_id", back_populates="white_player")
    games_as_black = relationship("Game", foreign_keys="Game.black_player_id", back_populates="black_player")
    chat_messages = relationship("ChatMessage", back_populates="player")

class Friendship(Base):
    __tablename__ = "friendship"
    __table_args__ = (
        CheckConstraint("user1_id != user2_id", name="no_self_friendship"),
    )

    user1_id = Column(Integer, ForeignKey("player.id", ondelete="CASCADE"), primary_key=True)
    user2_id = Column(Integer, ForeignKey("player.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    user1 = relationship("Player", foreign_keys=[user1_id], back_populates="friendships_initiated")
    user2 = relationship("Player", foreign_keys=[user2_id], back_populates="friendships_received")

class GameResult(Base):
    __tablename__ = "game_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(50), nullable=False)

    games = relationship("Game", back_populates="game_result")

class TimeControl(Base):
    __tablename__ = "time_control"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    initial_time_sec = Column(Integer, nullable=False)
    increment_sec = Column(Integer, nullable=False)

    games = relationship("Game", back_populates="time_control")

class Tournament(Base):
    __tablename__ = "tournament"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)

class Game(Base):
    __tablename__ = "game"

    id = Column(Integer, primary_key=True, autoincrement=True)
    white_player_id = Column(Integer, ForeignKey("player.id"), nullable=False)
    black_player_id = Column(Integer, ForeignKey("player.id"), nullable=True)
    time_control_id = Column(Integer, ForeignKey("time_control.id"), nullable=False)
    played_at = Column(DateTime, server_default=func.now())
    result_id = Column(Integer, ForeignKey("game_result.id", ondelete="RESTRICT"), nullable=True)

    white_player = relationship("Player", foreign_keys=[white_player_id], back_populates="games_as_white")
    black_player = relationship("Player", foreign_keys=[black_player_id], back_populates="games_as_black")
    time_control = relationship("TimeControl", back_populates="games")
    game_result = relationship("GameResult", back_populates="games")
    moves = relationship("Move", back_populates="game")
    chat_messages = relationship("ChatMessage", back_populates="game")

class Move(Base):
    __tablename__ = "move"

    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"), primary_key=True)
    move_number = Column(Integer, primary_key=True)
    notation = Column(String(10), nullable=False)

    game = relationship("Game", back_populates="moves")

class ChatMessage(Base):
    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("game.id", ondelete="CASCADE"), nullable=True)
    player_id = Column(Integer, ForeignKey("player.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, server_default=func.now())

    game = relationship("Game", back_populates="chat_messages")
    player = relationship("Player", back_populates="chat_messages")
