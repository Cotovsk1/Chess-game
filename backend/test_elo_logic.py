import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import models
from database import SessionLocal, engine
from utils import calculate_elo
from routers.game import update_player_elo

# Створюємо таблиці, якщо їх нема
models.Base.metadata.create_all(bind=engine)

def test_elo_update():
    db = SessionLocal()
    # Створюємо тестового гравця
    test_user = db.query(models.Player).filter(models.Player.username == "test_elo_user").first()
    if not test_user:
        test_user = models.Player(username="test_elo_user", email="test_elo@example.com", password_hash="hash", rating=1200)
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
    
    initial_rating = test_user.rating
    print(f"Initial rating: {initial_rating}")
    
    # Симулюємо перемогу над сильним суперником (2000)
    update_player_elo(db, test_user.id, 2000, 1.0)
    db.refresh(test_user)
    print(f"Rating after win: {test_user.rating}")
    assert test_user.rating > initial_rating
    
    # Симулюємо поразку (результат 0.0) від слабкого суперника (800)
    before_loss = test_user.rating
    print(f"Rating before loss to 800: {before_loss}")
    update_player_elo(db, test_user.id, 800, 0.0)
    db.refresh(test_user)
    print(f"Rating after loss to 800: {test_user.rating}")
    assert test_user.rating < before_loss
    
    print("ELO update test passed!")
    db.close()

if __name__ == "__main__":
    test_elo_update()
