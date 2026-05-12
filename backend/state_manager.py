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