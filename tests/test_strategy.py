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


# ============================================================
# HiLoStrategyEngine - playing deviations
# ============================================================

def test_hilo_16_vs_10_stands_at_tc_0():
    h = make_hand("10", "6")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=0
    )
    assert decision == "stand"


def test_hilo_16_vs_10_hits_below_tc_0_when_no_surrender():
    h = make_hand("10", "6")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=False,
        true_count=-1
    )
    assert decision == "hit"


def test_hilo_15_vs_10_stands_at_tc_4_when_no_surrender():
    h = make_hand("10", "5")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=False,
        true_count=4
    )
    assert decision == "stand"


def test_hilo_12_vs_3_stands_at_tc_2():
    h = make_hand("10", "2")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("3"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=2
    )
    assert decision == "stand"


def test_hilo_12_vs_2_stands_at_tc_3():
    h = make_hand("10", "2")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("2"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=3
    )
    assert decision == "stand"


def test_hilo_11_vs_ace_doubles_at_tc_1():
    h = make_hand("6", "5")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("Ace"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=1
    )
    assert decision == "double"


def test_hilo_9_vs_2_doubles_at_tc_1():
    h = make_hand("4", "5")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("2"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=1
    )
    assert decision == "double"


def test_hilo_10_vs_ace_doubles_at_tc_4():
    h = make_hand("4", "6")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("Ace"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=4
    )
    assert decision == "double"


def test_hilo_9_vs_7_doubles_at_tc_3():
    h = make_hand("4", "5")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("7"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=3
    )
    assert decision == "double"


def test_hilo_16_vs_9_stands_at_tc_5():
    h = make_hand("10", "6")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("9"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=5
    )
    assert decision == "stand"


# ============================================================
# HiLoStrategyEngine - negative deviations
# ============================================================

def test_hilo_12_vs_4_hits_when_tc_negative():
    h = make_hand("10", "2")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("4"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=-1
    )
    assert decision == "hit"


def test_hilo_12_vs_5_hits_when_tc_below_minus_2():
    h = make_hand("10", "2")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("5"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=-3
    )
    assert decision == "hit"


def test_hilo_12_vs_6_hits_when_tc_below_minus_1():
    h = make_hand("10", "2")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=-2
    )
    assert decision == "hit"


def test_hilo_13_vs_3_hits_when_tc_below_minus_2():
    h = make_hand("10", "3")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("3"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=-3
    )
    assert decision == "hit"


def test_hilo_13_vs_2_hits_when_tc_below_minus_1():
    h = make_hand("10", "3")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("2"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=-2
    )
    assert decision == "hit"


# ============================================================
# HiLoStrategyEngine - Fab 4
# ============================================================

def test_hilo_fab4_15_vs_10_surrenders_at_tc_0():
    h = make_hand("10", "5")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=0
    )
    assert decision == "surrender"


def test_hilo_fab4_14_vs_10_surrenders_at_tc_3():
    h = make_hand("8", "6")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=3
    )
    assert decision == "surrender"


def test_hilo_fab4_15_vs_9_surrenders_at_tc_2():
    h = make_hand("10", "5")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("9"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=2
    )
    assert decision == "surrender"


def test_hilo_fab4_15_vs_ace_surrenders_at_tc_1():
    h = make_hand("10", "5")
    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("Ace"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=1
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