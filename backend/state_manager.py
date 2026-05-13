from fastapi import WebSocket

# Словник для зберігання всіх активних ігор
active_games = {}

# Клас для керування всіма активними WebSocket підключеннями
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []

        if len(self.active_connections[game_id]) >= 2:
            await websocket.send_json({"error": "Кімната заповнена!"})
            await websocket.close()
            return False

        self.active_connections[game_id].append(websocket)
        return True

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            self.active_connections[game_id].remove(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast_to_game(self, message: dict, game_id: str):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                await connection.send_json(message)

manager = ConnectionManager()


# Менеджер сповіщень для конкретних користувачів (друзі, запити тощо)
class NotificationManager:
    def __init__(self):
        # user_id -> list[WebSocket]  (один юзер може мати кілька вкладок)
        self.user_connections: dict[int, list[WebSocket]] = {}
        # user_id юзерів, які зараз у грі — їм не відправляємо сповіщення
        self.users_in_game: set[int] = set()

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    def set_in_game(self, user_id: int, in_game: bool):
        if in_game:
            self.users_in_game.add(user_id)
        else:
            self.users_in_game.discard(user_id)

    def is_online(self, user_id: int) -> bool:
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0

    async def send_to_user(self, user_id: int, message: dict, respect_game: bool = True):
        """Надсилає сповіщення юзеру. Якщо respect_game=True — не відправляє під час гри."""
        if respect_game and user_id in self.users_in_game:
            return
        if user_id in self.user_connections:
            dead = []
            for ws in self.user_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.user_connections[user_id].remove(ws)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]


notification_manager = NotificationManager()

import asyncio
from datetime import datetime

async def cleanup_inactive_games_loop():
    while True:
        try:
            await asyncio.sleep(600)  # Перевіряти кожні 10 хвилин
            now = datetime.now()
            to_delete = []
            for game_id, game in active_games.items():
                last_activity = game.last_move_time if game.last_move_time else game.created_at
                if (now - last_activity).total_seconds() > 3600:  # 1 година бездіяльності
                    to_delete.append(game_id)
            
            for game_id in to_delete:
                del active_games[game_id]
                if game_id in manager.active_connections:
                    del manager.active_connections[game_id]
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Помилка при очищенні неактивних ігор: {e}")