import pytest
from blackjack import Player, Rules

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def test_split_hand_success():
    p = Player(bet=10, balance=1000, max_hands=4)
    p.hands[0].cards = [c("8"), c("8")]
    assert p.split_hand(0) is True
    assert len(p.hands) == 2
    assert p.hands[0].is_split_hand is True

def test_split_hand_max_hands_guard():
    p = Player(bet=10, balance=1000, max_hands=1)
    p.hands[0].cards = [c("8"), c("8")]
    assert p.split_hand(0) is False

def test_player_str_format():
    p = Player(bet=10, balance=990, max_hands=4)
    assert "Balance: 990" in str(p)