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


def test_betting_engine_tc_less_equal_zero_uses_lowest_ramp():
    bet = HiLoBettingEngine.get_bet(true_count=-1.2, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_le_0"]


def test_betting_engine_tc_zero_uses_lowest_ramp():
    bet = HiLoBettingEngine.get_bet(true_count=0.0, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_le_0"]


def test_betting_engine_tc_one_uses_tc_1_ramp():
    bet = HiLoBettingEngine.get_bet(true_count=1.0, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_1"]


def test_betting_engine_flooring_true_count_applies():
    bet = HiLoBettingEngine.get_bet(true_count=1.9, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_1"]


def test_betting_engine_tc_two_uses_tc_2_ramp():
    bet = HiLoBettingEngine.get_bet(true_count=2.1, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_2"]


def test_betting_engine_tc_three_uses_tc_3_ramp():
    bet = HiLoBettingEngine.get_bet(true_count=3.4, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_3"]


def test_betting_engine_tc_four_or_more_uses_highest_ramp():
    bet = HiLoBettingEngine.get_bet(true_count=4.0, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_ge_4"]


def test_betting_engine_tc_above_four_uses_highest_ramp():
    bet = HiLoBettingEngine.get_bet(true_count=7.8, rules=FullHiLoRules)
    assert bet == FullHiLoRules.BET_RAMP["tc_ge_4"]


# ============================================================
# Rules preset tests
# ============================================================

def test_basic_strategy_rules_disable_all_counting_features():
    assert BasicStrategyRules.COUNTING_ENABLED is False
    assert BasicStrategyRules.USE_PLAYING_DEVIATIONS is False
    assert BasicStrategyRules.USE_FAB4 is False
    assert BasicStrategyRules.USE_SPLIT_10_DEVIATIONS is False
    assert BasicStrategyRules.USE_INSURANCE_INDEX is False
    assert BasicStrategyRules.USE_BET_SPREAD is False


def test_counting_no_deviations_rules_only_enable_counting():
    assert CountingNoDeviationsRules.COUNTING_ENABLED is True
    assert CountingNoDeviationsRules.USE_PLAYING_DEVIATIONS is False
    assert CountingNoDeviationsRules.USE_FAB4 is False
    assert CountingNoDeviationsRules.USE_SPLIT_10_DEVIATIONS is False
    assert CountingNoDeviationsRules.USE_INSURANCE_INDEX is False
    assert CountingNoDeviationsRules.USE_BET_SPREAD is False


def test_counting_with_insurance_rules_only_enable_insurance_index():
    assert CountingWithInsuranceRules.COUNTING_ENABLED is True
    assert CountingWithInsuranceRules.USE_PLAYING_DEVIATIONS is False
    assert CountingWithInsuranceRules.USE_FAB4 is False
    assert CountingWithInsuranceRules.USE_SPLIT_10_DEVIATIONS is False
    assert CountingWithInsuranceRules.USE_INSURANCE_INDEX is True
    assert CountingWithInsuranceRules.USE_BET_SPREAD is False


def test_counting_with_bet_spread_rules_only_enable_spread():
    assert CountingWithBetSpreadRules.COUNTING_ENABLED is True
    assert CountingWithBetSpreadRules.USE_PLAYING_DEVIATIONS is False
    assert CountingWithBetSpreadRules.USE_FAB4 is False
    assert CountingWithBetSpreadRules.USE_SPLIT_10_DEVIATIONS is False
    assert CountingWithBetSpreadRules.USE_INSURANCE_INDEX is False
    assert CountingWithBetSpreadRules.USE_BET_SPREAD is True


def test_playing_deviations_only_rules_enable_only_playing_indices():
    assert PlayingDeviationsOnlyRules.COUNTING_ENABLED is True
    assert PlayingDeviationsOnlyRules.USE_PLAYING_DEVIATIONS is True
    assert PlayingDeviationsOnlyRules.USE_FAB4 is False
    assert PlayingDeviationsOnlyRules.USE_SPLIT_10_DEVIATIONS is False
    assert PlayingDeviationsOnlyRules.USE_INSURANCE_INDEX is False
    assert PlayingDeviationsOnlyRules.USE_BET_SPREAD is False


def test_full_hilo_no_bet_spread_rules_disable_only_spread():
    assert FullHiLoNoBetSpreadRules.COUNTING_ENABLED is True
    assert FullHiLoNoBetSpreadRules.USE_PLAYING_DEVIATIONS is True
    assert FullHiLoNoBetSpreadRules.USE_FAB4 is True
    assert FullHiLoNoBetSpreadRules.USE_SPLIT_10_DEVIATIONS is True
    assert FullHiLoNoBetSpreadRules.USE_INSURANCE_INDEX is True
    assert FullHiLoNoBetSpreadRules.USE_BET_SPREAD is False


def test_full_hilo_rules_enable_everything():
    assert FullHiLoRules.COUNTING_ENABLED is True
    assert FullHiLoRules.USE_PLAYING_DEVIATIONS is True
    assert FullHiLoRules.USE_FAB4 is True
    assert FullHiLoRules.USE_SPLIT_10_DEVIATIONS is True
    assert FullHiLoRules.USE_INSURANCE_INDEX is True
    assert FullHiLoRules.USE_BET_SPREAD is True


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