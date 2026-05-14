# ♟ Chess Game — Курсова робота

Шахова гра з FastAPI бекендом, Stockfish рушієм та WebSocket мультиплеєром.

---

## 🚀 Запуск

### Локально
```
start.bat  →  вибери [1]
```
Відкриється: **http://127.0.0.1:8000/ui/menu.html**

---

### 🌐 Публічний доступ через DevTunnel

> Дозволяє грати з другом через інтернет — не потрібен VPN або порт-форвардинг.

#### Крок 1 — Запусти тунель
```
tunnel.bat
```
або вручну:
```bat
# Термінал 1 — сервер
cd chess_project\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Термінал 2 — тунель
devtunnel user login
devtunnel host -p 8000 --allow-anonymous
```

#### Крок 2 — Скопіюй URL
DevTunnel покаже щось схоже на:
```
Connect via browser: https://abc123xy-8000.euw.devtunnels.ms
```

#### Крок 3 — Відкрий у браузері
```
https://abc123xy-8000.euw.devtunnels.ms/ui/menu.html
```

#### Крок 4 — Поділися посиланням з другом
Для мультиплеєра друг відкриває той самий URL:
```
https://abc123xy-8000.euw.devtunnels.ms/ui/multiplayer.html
```

> ✅ **WebSocket автоматично перемикається на `wss://`** коли сторінка відкрита по `https://`

---

## 📁 Структура

```
Chess-game/
├── start.bat              ← Локальний запуск
├── tunnel.bat             ← DevTunnel запуск
├── chess_project/
│   ├── backend/
│   │   ├── main.py        ← FastAPI app
│   │   ├── game_logic.py  ← Логіка гри + Stockfish
│   │   ├── schemas.py     ← Pydantic моделі
│   │   ├── store.py       ← In-memory сховище ігор
│   │   ├── .env           ← Конфіг (STOCKFISH_PATH, ALLOWED_ORIGINS)
│   │   ├── requirements.txt
│   │   └── routers/
│   │       ├── game.py    ← REST API (start, play, resign)
│   │       └── websocket.py ← WS мультиплеєр
│   └── frontend/
│       ├── menu.html      ← Головне меню
│       ├── index.html     ← Гра проти Stockfish
│       └── multiplayer.html ← Мультиплеєр P2P
```

---

## 🔧 Встановлення залежностей

```bash
pip install -r chess_project/backend/requirements.txt
```

## 🎮 API Endpoints

| Метод | URL | Опис |
|-------|-----|------|
| `GET`  | `/` | Статус сервера |
| `POST` | `/start` | Нова гра (параметр `level` 1-10) |
| `POST` | `/play/{id}` | Зробити хід |
| `GET`  | `/game/{id}` | Стан гри |
| `DELETE` | `/game/{id}` | Здатися |
| `WS`   | `/ws/play/{id}` | WebSocket мультиплеєр |

