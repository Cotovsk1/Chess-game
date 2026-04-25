import chess
import chess.engine


def main():
    # Вказуємо шлях до бінарного файлу Stockfish (якщо він у цій же папці)
    engine_path = "../engine/stockfish-windows-x86-64-avx2.exe"

    # Створюємо екземпляр шахової дошки (початкова позиція)
    board = chess.Board()

    print("Початкова позиція:")
    print(board)
    print("-" * 20)

    # Робимо перший хід за білих (наприклад, e2-e4)
    board.push_san("e4")
    print("Після ходу e4:")
    print(board)
    print("-" * 20)

    # Підключаємося до Stockfish через протокол UCI
    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)

        # Просимо рушій подумати 0.5 секунди і знайти найкращий хід за чорних
        print("Stockfish думає...")
        result = engine.play(board, chess.engine.Limit(time=0.5))

        print(f"Stockfish обрав хід: {result.move}")

        # Робимо хід бота на дошці
        board.push(result.move)
        print("Позиція після ходу бота:")
        print(board)

        # Закриваємо процес рушія
        engine.quit()

    except Exception as e:
        print(f"Помилка при запуску Stockfish: {e}")


if __name__ == "__main__":
    main()