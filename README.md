# ♟ Chess Game — Курсова робота

Шахова гра з FastAPI бекендом, Stockfish рушієм, WebSocket мультиплеєром та системою авторизації гравців.

---

## 🚀 Запуск

### Локально
```
start.bat  →  вибери [1]
```
Відкриється: **http://127.0.0.1:8000/ui/menu.html**

---

### 🌐 Публічний доступ через ngrok

> Дозволяє грати з другом через інтернет — не потрібен VPN або порт-форвардинг.

#### Крок 1 — Запусти тунель
```
start.bat  →  вибери [2]
```
або вручну:
```bat
# Термінал 1 — сервер
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Термінал 2 — тунель
ngrok http 8000
```

#### Крок 2 — Скопіюй URL
ngrok покаже щось схоже на:
```
Forwarding  https://abc123xy.ngrok-free.app -> http://127.0.0.1:8000
```

#### Крок 3 — Відкрий у браузері
```
https://abc123xy.ngrok-free.app/ui/menu.html
```

#### Крок 4 — Поділися посиланням з другом
Для мультиплеєра друг відкриває той самий URL:
```
https://abc123xy.ngrok-free.app/ui/multiplayer.html
```

> ✅ **WebSocket автоматично перемикається на `wss://`** коли сторінка відкрита по `https://`

---

## 📁 Структура

```
Chess-game/
├── backend/
│   ├── main.py            ← FastAPI app + Stockfish lifespan
│   ├── game_logic.py      ← Логіка гри + Stockfish (Strategy/Command)
│   ├── schemas.py         ← Pydantic моделі
│   ├── models.py          ← SQLAlchemy ORM моделі (Player, Game, Move, …)
│   ├── database.py        ← SQLite підключення (SQLAlchemy)
│   ├── state_manager.py   ← In-memory сховище ігор + ConnectionManager
│   ├── utils.py           ← Розрахунок Elo рейтингу
│   ├── start.bat          ← Локальний / ngrok запуск
│   ├── .env               ← Конфіг (STOCKFISH_PATH, ALLOWED_ORIGINS, SECRET_KEY)
│   ├── requirements.txt
│   ├── test_auth.py       ← Тести авторизації
│   ├── test_elo_logic.py  ← Тести Elo
│   ├── test_logic_simple.py ← Тести логіки гри
│   ├── tests/             ← Додаткові тести
│   └── routers/
│       ├── game.py        ← REST API (start, play, resign, …)
│       ├── websocket.py   ← WS мультиплеєр
│       └── auth.py        ← Реєстрація / логін / JWT
└── frontend/
    ├── menu.html          ← Головне меню
    ├── index.html         ← Гра проти Stockfish
    └── multiplayer.html   ← Мультиплеєр P2P
```

---

## 🔧 Встановлення залежностей

```bash
pip install -r backend/requirements.txt
```

## 🎮 API Endpoints

| Метод | URL | Опис |
|-------|-----|------|
| `GET`    | `/` | Статус сервера |
| `POST`   | `/start` | Нова гра проти Stockfish (`level` 1-10, `time_control_id`) |
| `POST`   | `/start_custom` | Нова гра з кастомною позицією (FEN) |
| `POST`   | `/play/{id}` | Зробити хід |
| `GET`    | `/game/{id}` | Стан гри |
| `DELETE` | `/game/{id}` | Здатися |
| `WS`     | `/ws/play/{id}` | WebSocket мультиплеєр |
| `POST`   | `/auth/register` | Реєстрація нового гравця |
| `POST`   | `/auth/login` | Логін (повертає JWT токен) |
| `GET`    | `/auth/me` | Профіль поточного гравця |

