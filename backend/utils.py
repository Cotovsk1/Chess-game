def calculate_elo(player_elo: int, opponent_elo: int, result: float, k_factor: int = 32) -> int:
    """
    result: 1.0 for win, 0.5 for draw, 0.0 for loss
    """
    expected_score = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    new_elo = player_elo + k_factor * (result - expected_score)
    return round(new_elo)

