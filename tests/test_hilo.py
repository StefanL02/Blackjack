import pytest
from blackjack import (
    Hand,
    HiLoStrategyEngine,
    HiLoBettingEngine,
    BasicStrategyEngine,
    BasicStrategyRules,
    CountingNoDeviationsRules,
    CountingWithInsuranceRules,
    CountingWithBetSpreadRules,
    PlayingDeviationsOnlyRules,
    FullHiLoNoBetSpreadRules,
    FullHiLoRules,
)

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}


def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h


# ============================================================
# HiLoBettingEngine tests
# ============================================================

def test_betting_engine_returns_min_bet_when_spread_disabled():
    bet = HiLoBettingEngine.get_bet(true_count=5, rules=FullHiLoNoBetSpreadRules)
    assert bet == FullHiLoNoBetSpreadRules.MIN_BET

@pytest.mark.parametrize(
    "true_count, expected_key",
    [
        (-1.2, "tc_le_0"),
        (0.0, "tc_le_0"),
        (1.0, "tc_1"),
        (1.9, "tc_1"),   # checks flooring
        (2.1, "tc_2"),
        (3.4, "tc_3"),
        (4.0, "tc_ge_4"),
        (7.8, "tc_ge_4"),
    ]
)
def test_betting_engine_uses_correct_ramp_band(true_count, expected_key):
    bet = HiLoBettingEngine.get_bet(true_count=true_count, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP[expected_key]

# ============================================================
# Rules preset tests
# ============================================================

@pytest.mark.parametrize(
    "rules_cls, counting, playing, fab4, split10, insurance, spread",
    [
        (BasicStrategyRules, False, False, False, False, False, False),
        (CountingNoDeviationsRules, True, False, False, False, False, False),
        (CountingWithInsuranceRules, True, False, False, False, True, False),
        (CountingWithBetSpreadRules, True, False, False, False, False, True),
        (PlayingDeviationsOnlyRules, True, True, False, False, False, False),
        (FullHiLoNoBetSpreadRules, True, True, True, True, True, False),
        (FullHiLoRules, True, True, True, True, True, True),
    ]
)
def test_rule_presets_have_expected_flags(
    rules_cls, counting, playing, fab4, split10, insurance, spread
):
    assert rules_cls.COUNTING_ENABLED is counting
    assert rules_cls.USE_PLAYING_DEVIATIONS is playing
    assert rules_cls.USE_FAB4 is fab4
    assert rules_cls.USE_SPLIT_10_DEVIATIONS is split10
    assert rules_cls.USE_INSURANCE_INDEX is insurance
    assert rules_cls.USE_BET_SPREAD is spread


# ============================================================
# HiLoStrategyEngine switch behaviour tests
# ============================================================

def test_hilo_strategy_falls_back_to_basic_when_playing_deviations_disabled():
    h = make_hand("10", "6")

    basic = BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=CountingNoDeviationsRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=False,
    )

    hilo = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=CountingNoDeviationsRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=False,
        true_count=5,
    )

    assert hilo == basic


def test_hilo_strategy_falls_back_to_basic_when_no_deviation_triggered():
    h = make_hand("10", "7")

    basic = BasicStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
    )

    hilo = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=5,
    )

    assert hilo == basic


def test_hilo_strategy_does_not_use_fab4_when_disabled():
    h = make_hand("10", "5")

    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("10"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=5,
    )

    # With Fab 4 disabled but playing deviations on, 15 vs 10 at high count becomes stand, not surrender
    assert decision == "stand"


def test_hilo_strategy_does_not_split_tens_when_split_deviations_disabled():
    h = make_hand("Jack", "Queen")

    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=PlayingDeviationsOnlyRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=10,
    )

    # Falls back to basic strategy, which should stand on 20
    assert decision == "stand"


def test_hilo_strategy_uses_split_tens_when_enabled():
    h = make_hand("Jack", "Queen")

    decision = HiLoStrategyEngine.decide(
        hand=h,
        dealer_up_card=c("6"),
        rules=FullHiLoRules,
        current_hand_count=1,
        dealer_peeked_no_blackjack=True,
        true_count=4,
    )

    assert decision == "split"