import pytest
from blackjack import GameManager, Rules, Hand

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

def test_determine_outcome_branches():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    h_s = make_hand("10", "6")
    h_s.surrendered = True
    assert gm.determine_outcome(h_s, make_hand("10", "7")) == "surrender"

def test_place_bets_removes_broke_players():
    gm = GameManager(6, 2, rules=Rules, verbose=False)
    gm.dealer.players[0].balance = 5
    gm.place_bets()
    assert len(gm.dealer.players) == 1

def test_dealer_should_peek_logic():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.dealer.dealer_hand = make_hand("Ace")
    assert gm.dealer_should_peek() is True

def test_settle_bets_math():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]
    p.balance = 0
    gm.dealer.dealer_hand = make_hand("10", "7")
    p.hands = [make_hand("10", "8", bet=10)] # Win
    gm.settle_bets()
    assert p.balance == 20