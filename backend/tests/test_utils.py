import pytest
from pathlib import Path
import sys
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.utils import calculate_elo


def test_elo_calculation():
    # Якщо твоя функція повертає тільки нове ELO для одного гравця:
    new_rating = calculate_elo(1200, 1200, 1.0) # Раніше було (1200, 1200, result=1.0, k=32)
    assert isinstance(new_rating, int)
    assert new_rating > 1200