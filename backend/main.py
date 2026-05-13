import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import chess.engine

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from routers import game, websocket, auth, chat
from database import engine
from models import Base


# Ініціалізація бази даних
Base.metadata.create_all(bind=engine)

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "engine/stockfish-windows-x86-64-avx2.exe")


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    import asyncio
    from state_manager import cleanup_inactive_games_loop
    cleanup_task = asyncio.create_task(cleanup_inactive_games_loop())
    
    fastapi_app.state.engine = None
    if os.getenv("DISABLE_STOCKFISH", "0") in ("1", "true", "True"):
        print("ℹ️ Stockfish disabled by environment.")
        yield
        return
    try:
        engine_res = await chess.engine.popen_uci(STOCKFISH_PATH)
        if isinstance(engine_res, tuple) and len(engine_res) >= 2:
            fastapi_app.state.engine = engine_res[1]
        else:
            fastapi_app.state.engine = engine_res
        fastapi_app.state.engine_lock = asyncio.Lock()
        print("✅ Stockfish запущено (асинхронно)!")
    except Exception as e:
        fastapi_app.state.engine = None
        fastapi_app.state.engine_lock = None
        print(f"⚠️ Не вдалося запустити Stockfish: {e}")
    yield
    cleanup_task.cancel()
    if fastapi_app.state.engine:
        try:
            await fastapi_app.state.engine.quit()
            print("🛑 Stockfish зупинено.")
        except (chess.engine.EngineError, OSError) as e:
            print(f"⚠️ Помилка при зупинці Stockfish: {e}")

app = FastAPI(
    title="Chess API",
    description="API для курсової роботи з гри в шахи",
    lifespan=lifespan
)

# Для розробки дозволяємо всі origins. У production змінити ALLOWED_ORIGINS у .env
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
is_wildcard = allowed_origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=not is_wildcard,  # credentials несумісні з wildcard "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роздаємо frontend через FastAPI (вирішує проблему file:// CORS)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_path):
    app.mount("/ui", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.get("/")
def read_root():
    return {"message": "Шаховий сервер працює!"}

from fastapi.responses import Response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


# Підключаємо наші роутери
app.include_router(game.router, prefix="/game", tags=["game"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router)
