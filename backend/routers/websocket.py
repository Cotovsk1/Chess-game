# imports
import json
import chess
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from state_manager import active_games, manager
from game_logic import CallbackObserver, StrategyFactory
from database import SessionLocal
import models
from routers.auth import ALGORITHM, SECRET_KEY
from jose import jwt
from utils import calculate_elo
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from jose import JWTError
from starlette.concurrency import run_in_threadpool
from routers.game import get_or_create_game_result

router = APIRouter()

def _get_user_from_token(token: str) -> Optional[models.Player]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        with SessionLocal() as db_session:
            user = db_session.query(models.Player).filter(models.Player.username == username).first()
            if user:
                db_session.expunge(user)
            return user
    except (JWTError, SQLAlchemyError):
        return None

def _record_ws_move(game_db_id: int, uci_move: str, move_number: int):
    if not game_db_id:
        return
    with SessionLocal() as db:
        db_move = models.Move(game_id=game_db_id, notation=uci_move, move_number=move_number)
        db.add(db_move)
        db.commit()

def _end_ws_game(game_db_id: int, result_str: str, white_id: int, black_id: int):
    if not game_db_id:
        return
    with SessionLocal() as db:
        db_game = db.query(models.Game).filter(models.Game.id == game_db_id).first()
        if db_game:
            db_game.result_id = get_or_create_game_result(db, result_str)
            db_game.white_player_id = white_id
            db_game.black_player_id = black_id
            
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

    user = await run_in_threadpool(_get_user_from_token, token)

    game = active_games[game_id]
    
    # Додаємо абстрактного спостерігача для цього підключення
    async def send_update(message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            pass
            
    observer = CallbackObserver(send_update)
    game.attach(observer)

    # Призначаємо кольори
    if game.white_client is None:
        game.white_client = websocket
        game.white_player_id = user.id if user else None
        my_color = "white"
    else:
        game.black_client = websocket
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
    if game.white_client and game.black_client:
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
            try:
                move_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Невалідний формат даних (очікується JSON)!"})
                continue
                
            uci_move = move_data.get("move")

            if uci_move:
                # --- Перевірка: чи підключені обидва гравці ---
                if game.white_client is None or game.black_client is None:
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
                    await run_in_threadpool(_record_ws_move, game.db_id, uci_move, len(game.board.move_stack))

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
                        await run_in_threadpool(_end_ws_game, game.db_id, db_res, game.white_player_id, game.black_player_id)

                        if game_id in active_games:
                            del active_games[game_id]

                except ValueError:
                    await websocket.send_json({"error": "Нелегальний хід!"})

    except WebSocketDisconnect:
        disconnected_color = None
        # Скидаємо WebSocket гравця, що відключився
        if game.white_client is websocket:
            game.white_client = None
            disconnected_color = "white"
        elif game.black_client is websocket:
            game.black_client = None
            disconnected_color = "black"

        game.detach(send_update)
        manager.disconnect(websocket, game_id)

        if game_id in active_games:
            if game.white_client is None and game.black_client is None:
                # Обидва гравці вийшли - нічия і очищення
                await run_in_threadpool(_end_ws_game, game.db_id, "Draw", game.white_player_id, game.black_player_id)
                del active_games[game_id]
            elif disconnected_color:
                await manager.broadcast_to_game(
                    {"type": "disconnect", "error": "Суперник відключився! У нього є 1 хвилина на повернення."},
                    game_id
                )
                
                # Запускаємо таймер на авто-поразку (60 секунд)
                import asyncio
                async def auto_forfeit(g_id: str, color: str):
                    await asyncio.sleep(60)
                    if g_id in active_games:
                        g = active_games[g_id]
                        # Якщо гравець так і не повернувся
                        if (color == "white" and g.white_client is None) or (color == "black" and g.black_client is None):
                            winner_res = "BlackWins" if color == "white" else "WhiteWins"
                            await run_in_threadpool(_end_ws_game, g.db_id, winner_res, g.white_player_id, g.black_player_id)
                            await manager.broadcast_to_game(
                                {"type": "game_over", "error": "Суперник покинув гру (таймаут). Ви перемогли!"},
                                g_id
                            )
                            if g_id in active_games:
                                del active_games[g_id]

                asyncio.create_task(auto_forfeit(game_id, disconnected_color))
