import pytest
from blackjack import GameManager, Hand, Rules,  FullHiLoRules

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

class NoCountingRules(Rules):
    COUNTING_ENABLED = False
    USE_INSURANCE_INDEX = True

class NoInsuranceIndexRules(Rules):
    COUNTING_ENABLED = True
    USE_INSURANCE_INDEX = False

def test_offer_insurance_returns_early_when_counting_disabled():
    gm = GameManager(6, 1, rules=NoCountingRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = True
    p.hands = [make_hand("10", "9", bet=10)]
    gm.true_count = 10

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == 0.0

@pytest.mark.parametrize(
    "is_counter, balance, hand_cards, true_count, expected_insurance, expected_balance",
    [
        (False, 100, ("10", "9"), 10, 0.0, 100),
        (True, 100, ("10", "9"), FullHiLoRules.INSURANCE_TC_THRESHOLD, 5.0, 95.0),
        (True, 100, ("10", "9"), FullHiLoRules.INSURANCE_TC_THRESHOLD - 1, 0.0, 100),
        (True, 4, ("10", "9"), 10, 0.0, 4),
        (True, 100, ("10", "9", "2"), 10, 0.0, 100),
    ]
)
def test_offer_insurance_cases(is_counter, balance, hand_cards, true_count, expected_insurance, expected_balance):
    gm = GameManager(6, 1, rules=FullHiLoRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = is_counter
    p.balance = balance
    p.hands = [make_hand(*hand_cards, bet=10)]
    gm.true_count = true_count

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == expected_insurance
    assert p.balance == expected_balance