import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import chess.engine
from routers import game, websocket, auth
from database import engine
import models

load_dotenv()

# Ініціалізація бази даних
models.Base.metadata.create_all(bind=engine)

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "./engine/stockfish-windows-x86-64-avx2.exe")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Відкриваємо Stockfish один раз при старті сервера (асинхронно)
    transport, engine_instance = await chess.engine.popen_uci(STOCKFISH_PATH)
    app.state.engine = engine_instance
    print("✅ Stockfish запущено (асинхронно)!")
    yield
    # Закриваємо рушій при зупинці сервера
    try:
        await app.state.engine.quit()
        print("🛑 Stockfish зупинено.")
    except Exception:
        pass


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


# Підключаємо наші роутери
app.include_router(game.router)
app.include_router(websocket.router)
app.include_router(auth.router)
