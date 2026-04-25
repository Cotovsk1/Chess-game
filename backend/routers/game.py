
import uuid
import chess
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from backend.schemas import MoveRequest, CustomGameRequest, StartGameRequest
from backend.state_manager import active_games
from backend.game_logic import ChessGame, StrategyFactory
from backend.database import get_db
from backend.routers.auth import get_optional_user
from backend import models

from backend.utils import calculate_elo

# Створюємо роутер
router = APIRouter()

def update_player_elo(db: Session, player_id: int, opponent_elo: int, result: float):
    if not player_id:
        return
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if player:
        new_elo = calculate_elo(player.rating, opponent_elo, result)
        player.rating = max(100, new_elo)
        db.commit()

def _game_over_response(game: ChessGame, db: Session = None) -> dict:
    """Формує відповідь про завершення гри"""
    result = game.board.result()
    white_res, black_res = 0.5, 0.5
    if result == "1-0":
        winner = "Перемога білих!"
        db_result = "WhiteWins"
        white_res, black_res = 1.0, 0.0
    elif result == "0-1":
        winner = "Перемога чорних (Stockfish)!"
        db_result = "BlackWins"
        white_res, black_res = 0.0, 1.0
    elif result == "1/2-1/2":
        winner = "Нічия!"
        db_result = "Draw"
        white_res, black_res = 0.5, 0.5
    else:
        winner = "Нічия!"
        db_result = "Draw"
        white_res, black_res = 0.5, 0.5

    if db and game.db_id:
        db_game = db.query(models.Game).filter(models.Game.id == game.db_id).first()
        if db_game:
            db_game.result = db_result
            db_game.white_player_id = game.white_player_id
            db_game.black_player_id = game.black_player_id
            db.commit()
            
            # Оновлюємо рейтинг гравця (якщо це гра проти бота)
            # Для бота використовуємо фіксований рейтинг залежно від рівня
            bot_elo = 800 + (game.level * 200) 
            if game.white_player_id:
                update_player_elo(db, game.white_player_id, bot_elo, white_res)
            elif game.black_player_id:
                update_player_elo(db, game.black_player_id, bot_elo, black_res)

    return {
        "status": "game_over",
        "result": result,
        "winner": winner,
        "fen": game.board.fen(),
        "is_check": game.board.is_check(),
    }

def record_move(db: Session, game_id: int, uci_move: str, move_number: int):
    if game_id:
        db_move = models.Move(game_id=game_id, notation=uci_move, move_number=move_number)
        db.add(db_move)
        db.commit()

@router.post("/start")
def start_game(
    request: StartGameRequest = None,
    db: Session = Depends(get_db),
    user: models.Player = Depends(get_optional_user)
):
    level = request.level if request else 5
    tc_id = request.time_control_id if request else None
    
    initial_time = None
    increment = 0
    
    if tc_id:
        tc = db.query(models.TimeControl).filter(models.TimeControl.id == tc_id).first()
        if tc:
            initial_time = tc.initial_time_sec
            increment = tc.increment_sec

    game_id = str(uuid.uuid4())

    # Створюємо гру в БД
    db_game = models.Game(
        result="InProgress", 
        white_player_id=user.id if user else None,
        time_control_id=tc_id
    )
    db.add(db_game)
    db.commit()
    db.refresh(db_game)

    active_games[game_id] = ChessGame(
        level=level, 
        db_id=db_game.id, 
        initial_time=initial_time, 
        increment=increment
    )
    active_games[game_id].white_player_id = user.id if user else None
    return {
        "game_id": game_id, 
        "message": "Нова гра створена!", 
        "level": level,
        "time_control": {"initial": initial_time, "increment": increment} if initial_time else None
    }

@router.post("/start_custom")
def start_custom_game(
    request: CustomGameRequest,
    db: Session = Depends(get_db),
    user: models.Player = Depends(get_optional_user)
):
    try:
        board = chess.Board(request.fen)
    except ValueError:
        raise HTTPException(status_code=400, detail="Некоректний формат FEN!")

    tc_id = request.time_control_id
    initial_time = None
    increment = 0
    
    if tc_id:
        tc = db.query(models.TimeControl).filter(models.TimeControl.id == tc_id).first()
        if tc:
            initial_time = tc.initial_time_sec
            increment = tc.increment_sec

    game_id = str(uuid.uuid4())

    db_game = models.Game(
        result="InProgress", 
        white_player_id=user.id if user else None,
        time_control_id=tc_id
    )
    db.add(db_game)
    db.commit()
    db.refresh(db_game)

    new_game = ChessGame(
        db_id=db_game.id, 
        initial_time=initial_time, 
        increment=increment
    )
    new_game.white_player_id = user.id if user else None
    new_game.board = board
    active_games[game_id] = new_game
    return {
        "game_id": game_id,
        "message": "Гра з кастомною позицією створена!",
        "fen": request.fen,
        "time_control": {"initial": initial_time, "increment": increment} if initial_time else None
    }

@router.get("/game/{game_id}")
def get_game_state(game_id: str):
    """Отримати поточний стан гри"""
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Гру не знайдено!")

    game = active_games[game_id]
    
    # Оновлюємо таймер, якщо гра триває
    now = datetime.now()
    w_time, b_time = game.white_time, game.black_time
    if game.initial_time is not None and game.last_move_time is not None:
        elapsed = (now - game.last_move_time).total_seconds()
        if game.board.turn == chess.WHITE:
            w_time = max(0, w_time - elapsed)
        else:
            b_time = max(0, b_time - elapsed)

    return {
        "game_id": game_id,
        "fen": game.board.fen(),
        "turn": "white" if game.board.turn == chess.WHITE else "black",
        "is_game_over": game.board.is_game_over(),
        "result": game.board.result() if game.board.is_game_over() else None,
        "is_check": game.board.is_check(),
        "white_time": w_time,
        "black_time": b_time
    }

@router.delete("/game/{game_id}")
def resign_game(game_id: str, db: Session = Depends(get_db)):
    """Здатися / завершити гру достроково"""
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Гру не знайдено!")

    game = active_games[game_id]
    if game.db_id:
        db_game = db.query(models.Game).filter(models.Game.id == game.db_id).first()
        if db_game:
            # Якщо здався живий гравець (який зазвичай грає білими проти бота)
            db_game.result = "BlackWins"
            db.commit()

    del active_games[game_id]
    return {"status": "resigned", "message": "Гру завершено. Ви здалися."}

@router.post("/play/{game_id}")
async def play_move(game_id: str, request: MoveRequest, http_request: Request, db: Session = Depends(get_db)):
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Гру не знайдено!")

    game = active_games[game_id]

    # Перевіряємо промоцію: якщо хід в базу містить 5 символів (e.g. e7e8q), беремо як є
    uci_move = request.move
    if len(uci_move) == 4:
        # Перевіряємо чи це хід пішака на останню горизонталь
        try:
            move_check = chess.Move.from_uci(uci_move)
            piece = game.board.piece_at(move_check.from_square)
            if piece and piece.piece_type == chess.PAWN:
                to_rank = chess.square_rank(move_check.to_square)
                if to_rank == 7 or to_rank == 0:
                    uci_move = uci_move + request.promotion
        except Exception:
            pass

    try:
        # Використовуємо StrategyFactory та execute_move (Command)
        human_strategy = StrategyFactory.get_strategy("human", uci_move=uci_move)
        await game.execute_move(human_strategy)
        record_move(db, game.db_id, uci_move, len(game.board.move_stack))
    except ValueError:
        raise HTTPException(status_code=400, detail="Нелегальний хід!")

    # Зберігаємо FEN після ходу гравця — до ходу бота
    fen_after_human = game.board.fen()

    if game.board.is_game_over():
        resp = _game_over_response(game, db)
        del active_games[game_id]
        return resp

    # Хід Stockfish з використанням синглтон-рушія
    try:
        engine = http_request.app.state.engine
        # Використовуємо StrategyFactory та execute_move (Command)
        bot_strategy = StrategyFactory.get_strategy("stockfish", engine=engine, level=game.level)
        bot_move = await game.execute_move(bot_strategy)
        record_move(db, game.db_id, bot_move.uci(), len(game.board.move_stack))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка рушія: {str(e)}")

    if game.board.is_game_over():
        resp = _game_over_response(game, db)
        resp["fen_after_human"] = fen_after_human
        resp["bot_move"] = bot_move.uci()
        del active_games[game_id]
        return resp

    return {
        "status": "continue",
        "human_move": request.move,
        "bot_move": bot_move.uci(),
        "fen_after_human": fen_after_human,   # FEN після ходу гравця (до бота)
        "fen": game.board.fen(),               # FEN після ходу бота (фінальний)
        "turn": "white" if game.board.turn == chess.WHITE else "black",
        "is_check": game.board.is_check(),
    }