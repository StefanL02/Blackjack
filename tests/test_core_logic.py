import pytest
from blackjack import Hand, BasicStrategyEngine, Rules, card_value_for_upcard, resolve_code


def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}


# card_value_for_upcard tests

def test_card_value_for_upcard_numbers():
    assert card_value_for_upcard(c("2")) == 2
    assert card_value_for_upcard(c("10")) == 10


def test_card_value_for_upcard_faces_and_ace():
    assert card_value_for_upcard(c("King")) == 10
    assert card_value_for_upcard(c("Queen")) == 10
    assert card_value_for_upcard(c("Jack")) == 10
    assert card_value_for_upcard(c("Ace")) == 11


# Hand.get_value / is_soft tests

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
    # A+9+9 would be 29, so Ace becomes 1 => 19
    assert h.get_value() == 19
    assert h.is_soft() is False  # Ace is forced to 1 here


def test_hand_value_multiple_aces_adjust():
    h = Hand()
    h.add_card(c("Ace"))
    h.add_card(c("Ace"))
    h.add_card(c("9"))
    # 11+11+9=31 => adjust one Ace to 1 => 21
    assert h.get_value() == 21
    assert h.is_soft() is True


def test_is_pair_true_and_false():
    h = Hand()
    h.add_card(c("8"))
    h.add_card(c("8"))
    assert h.is_pair() is True

    h2 = Hand()
    h2.add_card(c("8"))
    h2.add_card(c("9"))
    assert h2.is_pair() is False


def test_is_soft_17_helper():
    h = Hand()
    h.add_card(c("Ace"))
    h.add_card(c("6"))
    assert h.is_soft_17() is True

    h2 = Hand()
    h2.add_card(c("10"))
    h2.add_card(c("7"))
    assert h2.is_soft_17() is False



# BasicStrategyEngine tests


def decide(hand_cards, dealer_up_rank, *,
           late_surrender=True,
           das=True,
           double_any_two=True,
           dealer_peeked_no_bj=True,
           current_hand_count=1,
           is_split_hand=False):
    """Helper to build a hand and call the engine with adjustable rules."""
    class TestRules(Rules):
        LATE_SURRENDER = late_surrender
        DOUBLE_AFTER_SPLIT = das
        DOUBLE_ANY_TWO = double_any_two

    h = Hand()
    for r in hand_cards:
        h.add_card(c(r))
    h.is_split_hand = is_split_hand

    dealer_up = c(dealer_up_rank)
    return BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card=dealer_up,
        rules=TestRules,
        current_hand_count=current_hand_count,
        dealer_peeked_no_blackjack=dealer_peeked_no_bj
    )


def test_hard_total_rules_always_hit_under_9():
    assert decide(["2", "6"], "7") == "hit"     # hard 8 vs 7
    assert decide(["3", "5"], "Ace") == "hit"   # hard 8 vs A


def test_hard_total_rules_always_stand_17_plus():
    assert decide(["10", "7"], "10") == "stand"
    assert decide(["9", "8"], "Ace") == "stand"


def test_hard_11_double_vs_ace_h17_chart():
    # Your table says Dh across the row (H17 version)
    assert decide(["5", "6"], "Ace") == "double"


def test_soft_18_vs_9_hits_in_h17_chart():
    # soft 18 (A,7) vs 9 is hit in your table
    assert decide(["Ace", "7"], "9") == "hit"


def test_pair_8s_vs_ace_splits_by_table_when_no_special_case():
    # With just the table, it is split
    assert decide(["8", "8"], "Ace") == "split"


def test_surrender_only_allowed_on_two_cards_and_after_peek():
    # hard 16 vs 10 is Rh in your table => surrender if allowed
    assert decide(["9", "7"], "10", late_surrender=True, dealer_peeked_no_bj=True) == "surrender"

    # if dealer has NOT peeked / not confirmed no blackjack -> surrender not allowed -> should hit (Rh fallback)
    assert decide(["9", "7"], "10", late_surrender=True, dealer_peeked_no_bj=False) == "hit"

    # if hand has 3 cards, surrender should not be allowed
    # Example: 9,7,2 (total 18) would stand anyway by rules; pick a 3-card total 16 to force check
    assert decide(["9", "5", "2"], "10", late_surrender=True, dealer_peeked_no_bj=True) in ("hit", "stand")


def test_double_after_split_disabled_blocks_double():
    # Soft 18 vs 2 is "Dh" in your table (double if allowed else hit/stand depending)
    # If it's a split hand and DAS=False, doubling must be blocked -> should become hit/stand fallback
    action = decide(["Ace", "7"], "2", das=False, is_split_hand=True)
    assert action in ("hit", "stand")  # should NOT be "double"


def test_pair_face_cards_treated_as_10_for_pair_logic():
    # Q,Q vs 6 should NOT split; pair table for 10s is Stand
    assert decide(["Queen", "Queen"], "6") == "stand"

def test_basic_strategy_hard_16_vs_10_surrender():
    h = Hand()
    h.add_card({"rank": "10", "suit": "Hearts"})
    h.add_card({"rank": "6", "suit": "Clubs"})

    dealer = {"rank": "10", "suit": "Spades"}

    decision = BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card=dealer,
        rules=Rules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True
    )

    assert decision == "surrender"

def test_basic_strategy_hard_16_vs_10_hits():
    h = Hand()
    h.add_card({"rank": "10", "suit": "Hearts"})
    h.add_card({"rank": "6", "suit": "Clubs"})

    decision = BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card={"rank": "10", "suit": "Spades"},
        rules=Rules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True
    )

    assert decision in ("hit", "surrender")

def test_hand_pair_detection():
    h = Hand()
    h.add_card({"rank": "8", "suit": "Hearts"})
    h.add_card({"rank": "8", "suit": "Spades"})
    assert h.is_pair() is True

def test_hard_hand_not_soft():
     h = Hand()
     h.add_card({"rank": "10", "suit": "Hearts"})
     h.add_card({"rank": "7", "suit": "Clubs"})
     assert h.is_soft() is False

def test_hand_busts():
    h = Hand()
    h.add_card({"rank": "10", "suit": "Hearts"})
    h.add_card({"rank": "10", "suit": "Clubs"})
    h.add_card({"rank": "5", "suit": "Spades"})
    assert h.get_value() > 21

    #Hand value edge cases


def test_hand_multiple_aces_adjustment():
    h = Hand()
    h.add_card({"rank": "Ace", "suit": "Hearts"})
    h.add_card({"rank": "Ace", "suit": "Clubs"})
    h.add_card({"rank": "9", "suit": "Spades"})
    assert h.get_value() == 21

def test_is_soft_false_when_ace_counts_as_one():
    h = Hand()
    h.add_card({"rank": "Ace", "suit": "Hearts"})
    h.add_card({"rank": "King", "suit": "Clubs"})
    h.add_card({"rank": "9", "suit": "Spades"})
    assert h.is_soft() is False

def test_resolve_code_double_allowed():
    assert resolve_code("Dh", True, False, False, True) == "double"

def test_resolve_code_double_not_allowed():
    assert resolve_code("Dh", False, False, False, True) == "hit"

def test_resolve_code_surrender_not_allowed():
    assert resolve_code("Rh", True, False, False, True) == "hit"



