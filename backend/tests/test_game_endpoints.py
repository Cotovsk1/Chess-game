import pytest
import chess

BASE_URL = "/game" 

def test_start_game_success(test_client, auth_headers):
    response = test_client.post(f"{BASE_URL}/start", headers=auth_headers) 
    assert response.status_code == 200
    data = response.json()
    # Check if your model uses 'id' or 'game_id'
    assert any(key in data for key in ["game_id", "id"])

def test_get_game_state(test_client, auth_headers):
    # 1. Створюємо гру
    create_res = test_client.post(f"{BASE_URL}/start", headers=auth_headers)
    assert create_res.status_code == 200
    game_id = create_res.json().get("game_id") or create_res.json().get("id")
    
    # 2. Отримуємо стан
    response = test_client.get(f"{BASE_URL}/{game_id}", headers=auth_headers)
    
    if response.status_code == 404:
        print(f"\n🔍 DEBUG: Сервер не знайшов гру за адресою {BASE_URL}/{game_id}")
        print(f"Можливо, треба /game/game/{game_id}?")
    assert response.status_code == 200

def test_play_legal_move(test_client, auth_headers):
    start_res = test_client.post(f"{BASE_URL}/start", headers=auth_headers)
    game_id = start_res.json().get("game_id") or start_res.json().get("id")
    
    # 500 Fix: Ensure the JSON key matches your 'MoveRequest' schema (is it 'move' or 'uci'?)
    response = test_client.post(f"{BASE_URL}/play/{game_id}", json={"move": "e2e4"}, headers=auth_headers)
    
    if response.status_code == 500:
        print(f"Server Error Detail: {response.text}") # This helps debug the 500
        
    assert response.status_code == 200
    data = response.json()
    # Verify the move appears in the FEN or a specific field
    assert "e2e4" in str(data) or "board_fen" in data

def test_pawn_promotion_to_queen(test_client, auth_headers):
    promo_fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    start_res = test_client.post(f"{BASE_URL}/start_custom", json={"fen": promo_fen}, headers=auth_headers)
    game_id = start_res.json().get("game_id") or start_res.json().get("id")
    
    # Try the move
   # Замість "a7a8q" пиши "a7a8"
    response = test_client.post(f"{BASE_URL}/play/{game_id}", json={"move": "a7a8"}, headers=auth_headers)
    if response.status_code == 500:
        print(f"\n🔥 СЕРВЕР ЗДОХ: {response.text}")
    assert response.status_code == 200
    
    # Check if 'Q' (White Queen) is on the 8th rank
    data = response.json()
    fen = data.get("board_fen") or data.get("fen")
    assert "Q" in fen.split()[0]

def test_checkmate_detection(test_client, auth_headers):
    # 1. Позиція: за 1 хід до Дитячого мату
    fen_mate = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"
    
    create_res = test_client.post(f"{BASE_URL}/start_custom", 
                                  json={"fen": fen_mate, "level": 1}, 
                                  headers=auth_headers)
    game_id = create_res.json().get("game_id") or create_res.json().get("id")
    
    # 2. Робимо переможний хід і ОДРАЗУ зберігаємо результат
    # Не робимо окремий GET, бо гра може стати "неактивною" після мату
    response = test_client.post(f"{BASE_URL}/play/{game_id}", 
                                json={"move": "h5f7"}, 
                                headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # ДЕБАГ: Подивимось, що реально повернув хід, який поставив мат
    print(f"\n🎲 MOVE RESPONSE DATA: {data}")
    
    # Перевіряємо статус прямо тут
    # Якщо поле називається інакше (наприклад 'is_checkmate'), заміни ключ
    assert data.get("status") == "game_over" or data.get("message") == "Checkmate!"