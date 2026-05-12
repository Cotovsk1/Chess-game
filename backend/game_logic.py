import chess
import chess.engine
from datetime import datetime
from abc import ABC, abstractmethod
# --- 1. Патерн Команда: Інкапсуляція ходів ---
class Command(ABC):
    @abstractmethod
    async def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass

class MoveCommand(Command):
    def __init__(self, board: chess.Board, strategy: MoveStrategy):
        self.game = None  # Це буде встановлено при виконанні
        self.board = board
        self.strategy = strategy
        self.move = None

    async def execute(self):
        self.move = await self.strategy.get_move(self.board)
        self.board.push(self.move)
        return self.move

    def undo(self):
        if self.move:
            self.board.pop()
            self.move = None

# --- 2. Патерн Фабрика: Створення стратегій ---
class StrategyFactory:
    @staticmethod
    def get_strategy(strategy_type: str, **kwargs) -> MoveStrategy:
        if strategy_type == "human":
            return HumanStrategy(kwargs.get("uci_move"))
        elif strategy_type == "stockfish":
            return StockfishStrategy(kwargs.get("engine"), kwargs.get("level", 5), kwargs.get("lock"))
        elif strategy_type == "easy_bot":
            return RandomStrategy()
        raise ValueError(f"Unknown strategy type: {strategy_type}")

# --- 3. Патерн Спостерігач (Observer) ---
class Observer(ABC):
    @abstractmethod
    async def update_state(self, message: dict):
        pass

class CallbackObserver(Observer):
    def __init__(self, callback):
        self.callback = callback

    async def update_state(self, message: dict):
        try:
            await self.callback(message)
        except Exception:
            pass

class GameSubject:
    def __init__(self):
        self._observers = []

    def attach(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer):
        for obs in self._observers:
            if getattr(obs, 'callback', None) == observer or obs == observer:
                self._observers.remove(obs)
                break

    async def notify(self, message: dict):
        for observer in self._observers:
            await observer.update_state(message)

# --- 4. Патерн Стратегія: Загальний інтерфейс ---
class MoveStrategy(ABC):
    """Абстрактний клас для стратегії ходу"""
    @abstractmethod
    async def get_move(self, board: chess.Board) -> chess.Move:
        pass

# --- 2. Конкретна стратегія: Хід від Stockfish ---
class StockfishStrategy(MoveStrategy):
    # Рівні 1-10 → Stockfish Skill Level 0-20 і time limit
    LEVEL_CONFIG = {
        1:  {"skill": 0,  "time": 0.05},
        2:  {"skill": 2,  "time": 0.05},
        3:  {"skill": 4,  "time": 0.1},
        4:  {"skill": 6,  "time": 0.1},
        5:  {"skill": 9,  "time": 0.2},
        6:  {"skill": 12, "time": 0.3},
        7:  {"skill": 14, "time": 0.4},
        8:  {"skill": 16, "time": 0.5},
        9:  {"skill": 18, "time": 0.7},
        10: {"skill": 20, "time": 1.0},
    }

    def __init__(self, engine: chess.engine.UciProtocol, level: int = 5, lock=None):
        self.engine = engine
        self.level = max(1, min(10, level))  # Обмежуємо 1-10
        self.lock = lock

    async def get_move(self, board: chess.Board) -> chess.Move:
        cfg = self.LEVEL_CONFIG[self.level]
        if self.lock:
            async with self.lock:
                await self.engine.configure({"Skill Level": cfg["skill"]})
                result = await self.engine.play(board, chess.engine.Limit(time=cfg["time"]))
                return result.move
        else:
            await self.engine.configure({"Skill Level": cfg["skill"]})
            result = await self.engine.play(board, chess.engine.Limit(time=cfg["time"]))
            return result.move

# --- 2.1 Конкретна стратегія: Легкий бот (Random) ---
class RandomStrategy(MoveStrategy):
    async def get_move(self, board: chess.Board) -> chess.Move:
        import random
        return random.choice(list(board.legal_moves))

# --- 3. Конкретна стратегія: Хід від людини ---
class HumanStrategy(MoveStrategy):
    def __init__(self, uci_move: str):
        # Отримуємо хід у форматі рядка (наприклад, "e2e4"), який прийде з клієнта
        self.uci_move = uci_move

    async def get_move(self, board: chess.Board) -> chess.Move:
        move = chess.Move.from_uci(self.uci_move)
        if move in board.legal_moves:
            return move
        raise ValueError("Нелегальний хід або фігура не може так ходити!")

# --- 7. Контекст: Сама гра ---
class ChessGame(GameSubject):
    def __init__(self, level: int = 5, db_id: int = None, initial_time: int = None, increment: int = 0):
        super().__init__()
        self.board = chess.Board()
        self.level = max(1, min(10, level))
        # Для мультиплеєра: зберігаємо ідентифікатори клієнтів
        self.white_client = None
        self.black_client = None
        self.white_player_id = None
        self.black_player_id = None
        self.db_id = db_id
        self.created_at = datetime.now()
        self.history = []  # Список виконаних команд

        # Контроль часу
        self.initial_time = float(initial_time) if initial_time is not None else None  # в секундах
        self.increment = float(increment)
        self.white_time = self.initial_time
        self.black_time = self.initial_time
        self.last_move_time = None

    async def execute_move(self, strategy: MoveStrategy):
        """Виконує хід через патерн Команда та оновлює таймер"""
        now = datetime.now()
        if self.initial_time is not None and self.last_move_time is not None:
            elapsed = (now - self.last_move_time).total_seconds()
            if self.board.turn == chess.WHITE and self.white_time is not None:
                self.white_time = max(0.0, self.white_time - elapsed)
                if self.white_time > 0:
                    self.white_time += self.increment
            elif self.black_time is not None:
                self.black_time = max(0.0, self.black_time - elapsed)
                if self.black_time > 0:
                    self.black_time += self.increment
        
        self.last_move_time = now

        command = MoveCommand(self.board, strategy)
        move = await command.execute()
        self.history.append(command)
        return move

    def undo_move(self):
        """Скасовує останній хід"""
        if self.history:
            command = self.history.pop()
            command.undo()
            return True
        return False


    def get_player_color(self, client) -> str | None:
        """Повертає колір гравця за його ідентифікатором"""
        if client is self.white_client:
            return "white"
        if client is self.black_client:
            return "black"
        return None
