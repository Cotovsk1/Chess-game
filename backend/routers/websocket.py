# imports
import json
import chess
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.state_manager import active_games, manager
from backend.game_logic import WebSocketObserver, StrategyFactory
from backend.database import SessionLocal
from backend import models
from backend.routers.auth import ALGORITHM, SECRET_KEY
from jose import jwt
from backend.utils import calculate_elo
from typing import Callable, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from jose import JWTError

router = APIRouter()

def _get_user_from_token(token: str, db: Callable[[], Session]) -> Optional[models.Player]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        db_session = db()
        try:
            user = db_session.query(models.Player).filter(models.Player.username == username).first()
            return user
        finally:
            db_session.close()
    except (JWTError, SQLAlchemyError):
        return None


def _record_ws_move(game_db_id: int, uci_move: str, move_number: int):
    if not game_db_id:
        return
    db = SessionLocal()
    try:
        db_move = models.Move(game_id=game_db_id, notation=uci_move, move_number=move_number)
        db.add(db_move)
        db.commit()
    finally:
        db.close()


def _end_ws_game(game_db_id: int, result_str: str, white_id: int, black_id: int):
    if not game_db_id:
        return
    db = SessionLocal()
    try:
        db_game = db.query(models.Game).filter(models.Game.id == game_db_id).first()
        if db_game:
            db_game.result = result_str
            db_game.white_player_id = white_id
            db_game.black_player_id = black_id
            db.commit()
            
            # Оновлюємо рейтинг
            white = db.query(models.Player).filter(models.Player.id == white_id).first() if white_id else None
            black = db.query(models.Player).filter(models.Player.id == black_id).first() if black_id else None
            
            if white and black:
                w_res = 0.5
                if result_str == "WhiteWins": w_res = 1.0
                elif result_str == "BlackWins": w_res = 0.0
                b_res = 1.0 - w_res
                
                new_w_elo = calculate_elo(white.rating, black.rating, w_res)
                new_b_elo = calculate_elo(black.rating, white.rating, b_res)
                
                white.rating = max(100, new_w_elo)
                black.rating = max(100, new_b_elo)
                db.commit()
    finally:
        db.close()


@router.websocket("/ws/play/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, token: str = None):
    if game_id not in active_games:
        await websocket.accept()
        await websocket.send_json({"error": "Гру не знайдено!"})
        await websocket.close()
        return

    connected = await manager.connect(websocket, game_id)
    if not connected:
        return

    user = _get_user_from_token(token, SessionLocal)

    game = active_games[game_id]
    
    # Додаємо спостерігача для цього підключення
    observer = WebSocketObserver(websocket)
    game.attach(observer)

    # Призначаємо кольори
    if game.white_ws is None:
        game.white_ws = websocket
        game.white_player_id = user.id if user else None
        my_color = "white"
    else:
        game.black_ws = websocket
        game.black_player_id = user.id if user else None
        my_color = "black"

    await websocket.send_json({
        "type": "init", 
        "fen": game.board.fen(), 
        "color": my_color,
        "time_control": {
            "initial": game.initial_time,
            "increment": game.increment
        } if game.initial_time else None
    })

    # Якщо обидва гравці під'єдналися, повідомляємо про початок
    if game.white_ws and game.black_ws:
        # Установлюємо час старту першого ходу
        if game.initial_time is not None:
            game.last_move_time = datetime.now()
        
        await manager.broadcast_to_game(
            {"type": "start", "message": "Обидва гравці в кімнаті! Гра починається. Ходять білі."},
            game_id
        )

    try:
        while True:
            data = await websocket.receive_text()
            move_data = json.loads(data)
            uci_move = move_data.get("move")

            if uci_move:
                # --- Перевірка: чи підключені обидва гравці ---
                if game.white_ws is None or game.black_ws is None:
                    await websocket.send_json({"error": "Очікуємо другого гравця!"})
                    continue

                # --- Перевірка: чи цей гравець має право ходити ---
                player_color = game.get_player_color(websocket)
                board_turn = "white" if game.board.turn == chess.WHITE else "black"

                if player_color != board_turn:
                    await websocket.send_json({"error": "Не ваш хід!"})
                    continue

                try:
                    # Обробляємо промоцію
                    promotion = move_data.get("promotion", "q")
                    if len(uci_move) == 4:
                        move_check = chess.Move.from_uci(uci_move)
                        piece = game.board.piece_at(move_check.from_square)
                        if piece and piece.piece_type == chess.PAWN:
                            to_rank = chess.square_rank(move_check.to_square)
                            if to_rank == 7 or to_rank == 0:
                                uci_move = uci_move + promotion

                    # Використовуємо StrategyFactory та execute_move (Command)
                    human_strategy = StrategyFactory.get_strategy("human", uci_move=uci_move)
                    await game.execute_move(human_strategy)
                    _record_ws_move(game.db_id, uci_move, len(game.board.move_stack))

                    response = {
                        "type": "update",
                        "fen": game.board.fen(),
                        "move": uci_move,
                        "turn": "white" if game.board.turn == chess.WHITE else "black",
                        "is_game_over": game.board.is_game_over(),
                        "result": game.board.result() if game.board.is_game_over() else None,
                        "is_check": game.board.is_check(),
                        "white_time": game.white_time,
                        "black_time": game.black_time,
                    }

                    # Використовуємо Observer для сповіщення
                    await game.notify(response)

                    # Якщо гра закінчена — видаляємо її
                    if game.board.is_game_over():
                        res = game.board.result()
                        if res == "1-0":
                            db_res = "WhiteWins"
                        elif res == "0-1":
                            db_res = "BlackWins"
                        else:
                            db_res = "Draw"
                        _end_ws_game(game.db_id, db_res, game.white_player_id, game.black_player_id)

                        if game_id in active_games:
                            del active_games[game_id]

                except ValueError:
                    await websocket.send_json({"error": "Нелегальний хід!"})

    except WebSocketDisconnect:
        # Скидаємо WebSocket гравця, що відключився
        if game.white_ws is websocket:
            game.white_ws = None
        elif game.black_ws is websocket:
            game.black_ws = None

        game.detach(websocket)
        manager.disconnect(websocket, game_id)

        if game_id in active_games:
            await manager.broadcast_to_game(
                {"type": "disconnect", "error": "Суперник відключився!"},
                game_id
            )
