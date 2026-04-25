import pytest
from backend.models import Player
from backend.utils import calculate_elo

def test_elo_db_integration(db_session):
    # Додаємо password_hash, бо це обов'язкове поле (NOT NULL)
    p1 = Player(username="p1", email="p1@t.com", rating=1200, password_hash="hash1")
    p2 = Player(username="p2", email="p2@t.com", rating=1200, password_hash="hash2")
    db_session.add_all([p1, p2])
    db_session.commit()
    
    # Використовуємо p1.rating, бо так поле називається в БД (судячи з помилки)
    new_rating = calculate_elo(p1.rating, p2.rating, 1.0)
    p1.rating = new_rating
    db_session.commit()
    
    assert p1.rating > 1200