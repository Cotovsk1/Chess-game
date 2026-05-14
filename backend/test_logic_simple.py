import chess
from game_logic import ChessGame, HumanStrategy

def test_initial_board():
    game = ChessGame()
    assert game.board.fen() == chess.STARTING_FEN
    assert game.board.turn == chess.WHITE

def test_legal_move():
    game = ChessGame()
    # e2e4
    strategy = HumanStrategy("e2e4")
    move = game.make_move(strategy)
    assert move.uci() == "e2e4"
    assert game.board.piece_at(chess.E4).symbol() == "P"

def test_illegal_move():
    game = ChessGame()
    strategy = HumanStrategy("e2e5") # Білий пішак не може стрибнути на e5 з e2 одним ходом (хоча технічно e2e4 легально, e2e5 ні)
    try:
        game.make_move(strategy)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

if __name__ == "__main__":
    test_initial_board()
    test_legal_move()
    test_illegal_move()
    print("Tests passed!")
