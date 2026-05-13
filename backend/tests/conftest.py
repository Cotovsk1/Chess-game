import os
import sys
import chess
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Шляхи
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["STOCKFISH_PATH"] = "dummy"

from main import app
from database import Base, get_db

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    
    mock_engine = AsyncMock()
    
    # РОЗУМНИЙ MOCK: Беремо дошку з аргументів і повертаємо легальний хід
    async def smart_play(board, limit):
        # Отримуємо перший доступний легальний хід
        move = next(iter(board.legal_moves))
        result = MagicMock()
        result.move = move
        return result

    mock_engine.play.side_effect = smart_play
    mock_engine.configure = AsyncMock()
    
    # Мокаємо popen_uci, щоб він повертав наш mock_engine
    mock_popen = AsyncMock(return_value=(AsyncMock(), mock_engine))
    
    with patch("chess.engine.popen_uci", mock_popen):
        with TestClient(app) as client:
            client.app.state.engine = mock_engine 
            yield client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(test_client):
    user_data = {"username": "testuser", "email": "test@t.com", "password": "password123"}
    test_client.post("/auth/register", json=user_data)
    
    response = test_client.post("/auth/login", data={
        "username": "testuser",
        "password": "password123"
    })
    
    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.json()}")
        
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}