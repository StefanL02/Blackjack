import pytest
from blackjack import (
    Hand,
    Rules,
    BasicStrategyEngine,
    HiLoStrategyEngine,
    resolve_code,
    FullHiLoRules,
    BasicStrategyRules,
    PlayingDeviationsOnlyRules,
)

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}


def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

class NoDASRules(Rules):
    DOUBLE_AFTER_SPLIT = False

# ============================================================
# resolve_code tests
# ============================================================

def test_resolve_code_logic():
    assert resolve_code("Dh", True, False, False, True) == "double"
    assert resolve_code("Dh", False, False, False, True) == "hit"
    assert resolve_code("Rh", True, False, False, True) == "hit"


def test_resolve_code_ds_falls_to_stand_when_double_not_allowed():
    assert resolve_code("Ds", False, False, False, True) == "stand"


def test_resolve_code_split_only_when_allowed():
    assert resolve_code("P", True, True, False, True) == "split"
    assert resolve_code("P", True, False, False, True) is None


def test_resolve_code_ph_hits_when_das_not_allowed():
    assert resolve_code("Ph", True, True, False, False) == "hit"

def test_resolve_code_unknown_defaults_to_hit():
    assert resolve_code("X", False, False, False, False) == "hit"


# ============================================================
# BasicStrategyEngine tests
# ============================================================

def test_basic_strategy_hard_16_vs_10_surrender():
    h = make_hand("10", "6")
    decision = BasicStrategyEngine.decide(h, c("10"), Rules, 1, True)
    assert decision == "surrender"


def test_basic_strategy_hard_16_vs_10_hits_if_surrender_not_available():
    h = make_hand("10", "6")
    decision = BasicStrategyEngine.decide(h, c("10"), Rules, 1, False)
    assert decision == "hit"


def test_basic_strategy_soft_18_vs_6_stands_or_doubles():
    h = make_hand("Ace", "7")
    decision = BasicStrategyEngine.decide(h, c("6"), Rules, 1, True)
    assert decision in ("double", "stand")


def test_basic_strategy_soft_18_vs_9_hits():
    h = make_hand("Ace", "7")
    decision = BasicStrategyEngine.decide(h, c("9"), Rules, 1, True)
    assert decision == "hit"


def test_basic_strategy_pair_8s_vs_10_splits():
    h = make_hand("8", "8")
    decision = BasicStrategyEngine.decide(h, c("10"), Rules, 1, True)
    assert decision == "split"


def test_basic_strategy_pair_aces_vs_6_splits():
    h = make_hand("Ace", "Ace")
    decision = BasicStrategyEngine.decide(h, c("6"), Rules, 1, True)
    assert decision == "split"


def test_basic_strategy_hard_11_vs_ace_doubles():
    h = make_hand("5", "6")
    decision = BasicStrategyEngine.decide(h, c("Ace"), Rules, 1, True)
    assert decision == "double"


def test_basic_strategy_hard_8_always_hits():
    h = make_hand("5", "3")
    decision = BasicStrategyEngine.decide(h, c("6"), Rules, 1, True)
    assert decision == "hit"


def test_basic_strategy_hard_17_always_stands():
    h = make_hand("10", "7")
    decision = BasicStrategyEngine.decide(h, c("Ace"), Rules, 1, True)
    assert decision == "stand"


def test_basic_strategy_split_aces_hand_forced_stand_after_one_extra_card():
    h = make_hand("Ace", "9")
    h.is_split_aces_hand = True
    decision = BasicStrategyEngine.decide(h, c("6"), Rules, 2, True)
    assert decision == "stand"

def test_basic_strategy_blocks_resplit_aces_when_not_allowed():
    h = make_hand("Ace", "Ace")
    h.is_split_aces_hand = True

    decision = BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=Rules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True
    )

    assert decision != "split"


def test_basic_strategy_no_double_after_split_when_das_disabled():
    h = make_hand("5", "4")
    h.is_split_hand = True

    decision = BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=NoDASRules,
        current_hand_count=2,
        dealer_peeked_no_blackjack=True
    )

    assert decision != "double"

def test_basic_strategy_pair_face_cards_normalized_to_tens():
    h = make_hand("Jack", "Jack")

    decision = BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=Rules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True
    )

    assert decision == "stand"

# ============================================================
# HiLoStrategyEngine - playing deviations
# ============================================================

@pytest.mark.parametrize(
    "player_cards, dealer_up, true_count",
    [
        (("10", "6"), "10", 0),  # 16 vs 10
        (("10", "5"), "10", 4),  # 15 vs 10
        (("10", "2"), "3", 2),   # 12 vs 3
        (("10", "2"), "2", 3),   # 12 vs 2
        (("10", "6"), "9", 5),   # 16 vs 9
    ]
)
def test_hilo_positive_stand_deviations(player_cards, dealer_up, true_count):
    h = make_hand(*player_cards)

    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c(dealer_up),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=true_count
    )

    assert decision == "stand"

@pytest.mark.parametrize(
    "player_cards, dealer_up, true_count",
    [
        (("6", "5"), "Ace", 1),   # 11 vs Ace
        (("4", "6"), "Ace", 4),   # 10 vs Ace
        (("4", "6"), "10", 4),    # 10 vs 10
        (("4", "5"), "2", 1),     # 9 vs 2
        (("4", "5"), "7", 3),     # 9 vs 7
    ]
)
def test_hilo_positive_double_deviations(player_cards, dealer_up, true_count):
    h = make_hand(*player_cards)

    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c(dealer_up),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=true_count
    )

    assert decision == "double"


# ============================================================
# HiLoStrategyEngine - negative deviations
# ============================================================

@pytest.mark.parametrize(
    "player_cards, dealer_up, true_count, expected",
    [
        (("10", "2"), "4", -1, "hit"),
        (("10", "2"), "5", -3, "hit"),
        (("10", "2"), "6", -2, "hit"),
        (("10", "3"), "3", -3, "hit"),
        (("10", "3"), "2", -2, "hit"),
    ]
)
def test_hilo_negative_deviations(player_cards, dealer_up, true_count, expected):
    h = make_hand(*player_cards)

    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c(dealer_up),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=true_count
    )

    assert decision == expected


# ============================================================
# HiLoStrategyEngine - Fab 4
# ============================================================

@pytest.mark.parametrize(
    "player_cards, dealer_up, true_count",
    [
        (("10", "5"), "10", 0),  # 15 vs 10
        (("8", "6"), "10", 3),   # 14 vs 10
        (("10", "5"), "9", 2),   # 15 vs 9
        (("10", "5"), "Ace", 1), # 15 vs Ace
    ]
)
def test_hilo_fab4_surrenders(player_cards, dealer_up, true_count):
    h = make_hand(*player_cards)

    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c(dealer_up),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=true_count
    )

    assert decision == "surrender"


# ============================================================
# HiLoStrategyEngine - split 10 deviations
# ============================================================

def test_hilo_split_10s_vs_5_at_tc_5():
    h = make_hand("10", "King")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("5"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=5
    )
    assert decision == "split"


def test_hilo_split_10s_vs_6_at_tc_4():
    h = make_hand("Jack", "Queen")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=4
    )
    assert decision == "split"


# ============================================================
# Fallback / switch behaviour
# ============================================================

def test_hilo_falls_back_to_basic_when_using_basic_rules():
    h = make_hand("10", "6")
    basic = BasicStrategyEngine.decide(h, c("10"), BasicStrategyRules, 1, True)

    hilo = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=BasicStrategyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=5
    )

    assert hilo == basic


def test_hilo_returns_basic_action_when_no_deviation_applies():
    h = make_hand("10", "7")
    basic = BasicStrategyEngine.decide(h, c("6"), FullHiLoRules, 1, True)

    hilo = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=5
    )

    assert hilo == basic

