import pytest
from blackjack import BasicStrategyEngine, Rules, resolve_code

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def test_resolve_code_logic():
    # Double allowed
    assert resolve_code("Dh", True, False, False, True) == "double"
    # Double not allowed falls to hit
    assert resolve_code("Dh", False, False, False, True) == "hit"
    # Surrender not allowed falls to hit
    assert resolve_code("Rh", True, False, False, True) == "hit"

def test_basic_strategy_hard_16_vs_10_surrender():
    from blackjack import Hand
    h = Hand()
    h.add_card(c("10"))
    h.add_card(c("6"))
    decision = BasicStrategyEngine.decide(h, c("10"), Rules, 1, True)
    assert decision == "surrender"