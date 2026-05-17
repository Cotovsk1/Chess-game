# Chess Game

A full-stack web chess application with single-player (vs AI) and multiplayer modes, built with a **FastAPI** backend and a vanilla HTML/CSS/JavaScript frontend.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [Design Patterns](#design-patterns)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)

---

## Overview

Chess Game is a course-project chess platform where players can:

- Play against the **Stockfish** chess engine at 10 difficulty levels, or against a simple random-move bot.
- Play **multiplayer** games against other users in real time via WebSockets.
- Register, log in, and track their **ELO rating** (K=32, standard formula).
- Chat inside a game and manage a **friends list** with friend requests.
- Start a game from any position using a custom **FEN** string.
- Enjoy configurable **time controls** (initial time + increment per move).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) (Python) |
| ASGI server | [Uvicorn](https://www.uvicorn.org/) |
| Chess engine integration | [python-chess](https://python-chess.readthedocs.io/) + Stockfish (UCI) |
| Database ORM | [SQLAlchemy](https://www.sqlalchemy.org/) |
| Database | SQLite (`chess_base.db`) |
| Authentication | JWT via [python-jose](https://python-jose.readthedocs.io/), passwords hashed with [passlib/bcrypt](https://passlib.readthedocs.io/) |
| Real-time communication | WebSockets (FastAPI native) |
| Frontend | Vanilla HTML5 / CSS3 / JavaScript |
| Chess board UI | [chessboard.js](https://chessboardjs.com/) + jQuery |
| Testing | pytest + httpx |

---

## Project Structure

```
Chess-game/
├── requirements.txt          # Python dependencies
├── chess_base.db             # SQLite database (auto-created on first run)
│
├── backend/
│   ├── main.py               # FastAPI app entry point, lifespan, middleware, router registration
│   ├── database.py           # SQLAlchemy engine & session factory
│   ├── models.py             # ORM models (Player, Game, Move, Friendship, …)
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── game_logic.py         # Chess game logic — Strategy, Command, Observer patterns
│   ├── state_manager.py      # In-memory active-games store, WebSocket managers, cleanup loop
│   ├── utils.py              # ELO calculation helper
│   ├── start.bat             # Windows helper script (local / ngrok launch)
│   ├── pytest.ini            # pytest configuration
│   │
│   ├── routers/
│   │   ├── auth.py           # /auth — register, login, JWT, /me
│   │   ├── game.py           # /game — start, move, state, resign (single-player vs bot)
│   │   ├── websocket.py      # WebSocket endpoints (multiplayer & notifications)
│   │   ├── chat.py           # In-game chat endpoints
│   │   └── friends.py        # /friends — send/accept/decline friend requests, list friends
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_game_endpoints.py
│       ├── test_game_logic.py
│       ├── test_elo_logic.py
│       ├── test_utils.py
│       ├── engine_test.py
│       └── tests_db.py
│
└── frontend/
    ├── menu.html             # Main menu / landing page
    ├── index.html            # Single-player game (vs bot)
    ├── multiplayer.html      # Multiplayer game (WebSocket)
    ├── profile.html          # User profile page
    ├── edit_profile.html     # Profile edit page
    └── static/               # Frontend assets (CSS, JS, icons)
```

---

## Key Features

### Single-player vs Bot
`POST /game/start` creates a new game session (stored in memory as a `ChessGame` object and in SQLite). The player sends moves via `POST /game/play/{game_id}`; the server validates the human move and immediately plays the Stockfish (or random) bot response.

### Multiplayer
Players connect to `ws://.../ws/game/{game_id}` via WebSocket. The server broadcasts move events, game-over results, and timer updates to both clients in the room (max 2 per game).

### Authentication & Ratings
JWT tokens (HS256, 1-week expiry) protect user-specific endpoints. Each completed game updates the player's ELO rating against a bot ELO derived from the bot's difficulty level (`800 + level × 200`).

### Inactive-game Cleanup
A background `asyncio` task runs every 10 minutes and removes games that have had no activity for more than 1 hour.

---

## Design Patterns

`game_logic.py` deliberately demonstrates four classic GoF patterns:

| Pattern | Class(es) | Purpose |
|---------|-----------|---------|
| **Strategy** | `MoveStrategy`, `StockfishStrategy`, `RandomStrategy`, `HumanStrategy` | Swap the move-generation algorithm at runtime |
| **Command** | `Command`, `MoveCommand` | Encapsulate a move as an object; supports `undo()` |
| **Observer** | `GameSubject`, `Observer`, `CallbackObserver` | Notify WebSocket clients of game state changes |
| **Factory** | `StrategyFactory` | Create the correct strategy from a string type name |

---

## Database Schema

| Table | Description |
|-------|-------------|
| `player` | Registered users — username, email, bcrypt password hash, ELO rating |
| `game` | A chess game record — links white/black players, time control, result |
| `move` | Individual moves stored in UCI notation per game |
| `time_control` | Named time controls with initial seconds and increment |
| `game_result` | Lookup table: `InProgress`, `WhiteWins`, `BlackWins`, `Draw` |
| `friendship` | Friend pairs with `pending` / `accepted` status |
| `chat_message` | In-game chat messages linked to a game and player |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create a new account |
| `POST` | `/auth/login` | Obtain JWT access token |
| `GET` | `/auth/me` | Get current user profile |
| `PUT` | `/auth/update` | Update user profile details |
| `POST` | `/game/start` | Start a new game vs bot |
| `POST` | `/game/start_custom` | Start from a custom FEN position |
| `GET` | `/game/{game_id}` | Get current game state & timers |
| `POST` | `/game/play/{game_id}` | Submit a human move |
| `POST` | `/game/resign/{game_id}` | Resign the current game |
| `POST` | `/game/undo/{game_id}` | Undo the last move |
| `GET` | `/game/hint/{game_id}` | Get best move hint |
| `GET` | `/games/history` | Get user game history |
| `GET` | `/chat/global` | Get global chat messages |
| `GET` | `/chat/game/{game_id}` | Get in-game chat messages |
| `WS` | `/ws/game/{game_id}` | Multiplayer WebSocket connection |
| `WS` | `/ws/notifications` | Per-user notification WebSocket |
| `POST/GET/DELETE` | `/friends/...` | Friend requests and friend list management |

Interactive API docs are available at `http://127.0.0.1:8000/docs` when the server is running.

---

## Getting Started

### Prerequisites
- Python 3.10+
- [Stockfish](https://stockfishchess.org/download/) binary (place under `backend/engine/` or set `STOCKFISH_PATH` in `.env`)

### Installation

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Create a .env file in the project root
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" > .env
# Optionally:
# STOCKFISH_PATH=backend/engine/stockfish-windows-x86-64-avx2.exe
# DISABLE_STOCKFISH=1   # set to 1 to skip Stockfish (random-bot only)
```

### Running the server

**Windows (recommended):**
```bat
cd backend
start.bat
```
Choose option `1` for local play or `2` to expose via ngrok.

**Any platform:**
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000/ui/menu.html** in your browser.

### Running tests

```bash
cd backend
pytest
```
