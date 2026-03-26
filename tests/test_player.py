import pytest
from blackjack import Player, Rules, FullHiLoRules, BasicStrategyRules

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

def test_player_choice_counter_uses_hilo_engine():
    p = Player(bet=10, balance=1000, max_hands=4, is_counter=True)
    hand = p.hands[0]
    hand.cards = [c("10"), c("6")]

    decision = p.choice(
        hand=hand,
        dealer_up_card=c("10"),
        rules=FullHiLoRules,
        dealer_peeked_no_blackjack=True,
        true_count=0
    )

    assert decision == "stand"


def test_player_choice_basic_player_uses_basic_strategy():
    p = Player(bet=10, balance=1000, max_hands=4, is_counter=False)
    hand = p.hands[0]
    hand.cards = [c("10"), c("6")]

    decision = p.choice(
        hand=hand,
        dealer_up_card=c("10"),
        rules=FullHiLoRules,
        dealer_peeked_no_blackjack=True,
        true_count=5
    )

    # Basic strategy also surrenders 16 vs 10 when surrender is available
    assert decision == "surrender"


def test_player_choice_counter_falls_back_to_basic_when_counting_disabled():
    p = Player(bet=10, balance=1000, max_hands=4, is_counter=True)
    hand = p.hands[0]
    hand.cards = [c("10"), c("6")]

    decision = p.choice(
        hand=hand,
        dealer_up_card=c("10"),
        rules=BasicStrategyRules,
        dealer_peeked_no_blackjack=True,
        true_count=5
    )

    assert decision == "surrender"