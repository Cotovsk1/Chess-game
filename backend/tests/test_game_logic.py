from pathlib import Path
import sys
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import chess
from unittest.mock import MagicMock, AsyncMock
from game_logic import ChessGame, MoveCommand, StockfishStrategy


@pytest.mark.anyio
async def test_move_command_execution():
    chess_game = ChessGame()
    initial_fen = chess_game.board.fen()
    
    # 1. Створюємо мок-стратегію
    mock_strategy = AsyncMock()
    test_move = chess.Move.from_uci("e2e4")
    mock_strategy.get_move.return_value = test_move
    
    # 2. Створюємо команду, передаючи і гру, і стратегію (як того вимагає твій код)
    command = MoveCommand(chess_game.board, mock_strategy)
    
    # 3. Виконуємо
    await command.execute()
    
    # Перевіряємо результат
    # Замість assert not chess_game.board.is_empty()
    assert len(chess_game.board.move_stack) > 0
    assert chess_game.board.move_stack[-1].uci() == "e2e4"
    assert chess_game.board.fen() != initial_fen

@pytest.mark.anyio
async def test_clock_management():
    # Тестуємо execute_move, який ти додав у ChessGame
    game = ChessGame(initial_time=600, increment=5)
    
    mock_strategy = AsyncMock()
    mock_strategy.get_move.return_value = chess.Move.from_uci("e2e4")
    
    # Перший хід
    await game.execute_move(mock_strategy)
    
    # Перевіряємо, чи ініціалізувався час останнього ходу
    assert game.last_move_time is not None
    # Оскільки elapsed було 0 при першому ході, час має бути initial + increment
    # (або просто initial, залежно від твоєї логіки в execute_move)
    assert game.white_time >= 600

@pytest.mark.anyio
async def test_stockfish_strategy_mocked():
    mock_engine = AsyncMock()
    mock_result = MagicMock()
    mock_result.move = chess.Move.from_uci("e2e4")
    mock_engine.play.return_value = mock_result
    # Додаємо мок для configure, бо він викликається в get_move
    mock_engine.configure = AsyncMock()
    
    strategy = StockfishStrategy(engine=mock_engine, level=1)
    move = await strategy.get_move(chess.Board())
    
    assert move.uci() == "e2e4"
    mock_engine.configure.assert_called_once()