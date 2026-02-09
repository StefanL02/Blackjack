import pytest
from blackjack import Hand

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def test_hand_value_simple_no_aces():
    h = Hand()
    h.add_card(c("10"))
    h.add_card(c("7"))
    assert h.get_value() == 17
    assert h.is_soft() is False

def test_hand_value_soft_ace_detected():
    h = Hand()
    h.add_card(c("Ace"))
    h.add_card(c("6"))
    assert h.get_value() == 17
    assert h.is_soft() is True

def test_hand_value_ace_adjusts_to_avoid_bust():
    h = Hand()
    h.add_card(c("Ace"))
    h.add_card(c("9"))
    h.add_card(c("9"))
    assert h.get_value() == 19
    assert h.is_soft() is False

def test_hand_multiple_aces_adjustment():
    h = Hand()
    h.add_card(c("Ace"))
    h.add_card(c("Ace"))
    h.add_card(c("9"))
    assert h.get_value() == 21

def test_hand_pair_detection():
    h = Hand()
    h.add_card(c("8"))
    h.add_card(c("8"))
    assert h.is_pair() is True

def test_hand_busts():
    h = Hand()
    h.add_card(c("10"))
    h.add_card(c("10"))
    h.add_card(c("5"))
    assert h.get_value() > 21

def test_hand_triple_ace_adjustment():
    h = Hand()
    h.add_card(c("Ace")) # Value: 11
    h.add_card(c("Ace")) # Value: 12 (one ace becomes 1)
    h.add_card(c("Ace")) # Value: 13 (two aces become 1)
    h.add_card(c("9"))   # Value: 12 (all aces become 1)
    assert h.get_value() == 12
    assert h.is_soft() is False


def test_hand_face_cards():
    h = Hand()
    h.add_card(c("Jack"))
    h.add_card(c("Queen"))
    assert h.get_value() == 20

    h2 = Hand()
    h2.add_card(c("King"))
    h2.add_card(c("Ace"))
    assert h2.get_value() == 21  # Blackjack


def test_soft_to_hard_transition():
    h = Hand()
    h.add_card(c("Ace"))
    h.add_card(c("5"))  # Soft 16
    assert h.is_soft() is True

    h.add_card(c("10"))  # Now Hard 16 (Ace must be 1)
    assert h.get_value() == 16
    assert h.is_soft() is False

def test_hand_not_a_pair():
    h = Hand()
    h.add_card(c("King"))
    h.add_card(c("10"))
    # Even though both are value 10, they are not a "pair" for splitting
    assert h.is_pair() is False

def test_hand_string_representation():
    h = Hand(bet=50)
    h.add_card(c("Ace", "Spades"))
    h.add_card(c("King", "Clubs"))
    assert "Ace of Spades" in str(h)
    assert "Bet: 50" in str(h)