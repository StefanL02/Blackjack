import  pytest
from blackjack import GameManager, Rules, Hand

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

@pytest.mark.parametrize(
    "player_cards, dealer_cards, expected",
    [
        (("10", "10", "5"), ("10", "7"), "bust"),
        (("10", "7"), ("10", "8", "5"), "win"),
        (("Ace", "King"), ("10", "9"), "blackjack"),
        (("10", "9"), ("Ace", "King"), "lose"),
        (("Ace", "King"), ("Ace", "Queen"), "push"),
        (("10", "7"), ("10", "8"), "lose"),
        (("10", "8"), ("9", "9"), "push"),
    ]
)
def test_determine_outcome_cases(player_cards, dealer_cards, expected):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    assert gm.determine_outcome(make_hand(*player_cards), make_hand(*dealer_cards)) == expected

def test_determine_outcome_branches():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    h_s = make_hand("10", "6")
    h_s.surrendered = True
    assert gm.determine_outcome(h_s, make_hand("10", "7")) == "surrender"

def test_settle_bets_blackjack_payout():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.balance = 0
    p.hands = [make_hand("Ace", "King", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "9")

    gm.settle_bets()

    assert p.balance == 25.0
    assert gm.stats["wins"] == 1

def test_settle_bets_eliminates_player_with_zero_balance():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.balance = 0
    p.hands = [make_hand("10", "7", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "8")

    gm.settle_bets()

    assert p not in gm.dealer.players
    assert p in gm.eliminated_players

def test_settle_bets_math():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]
    p.balance = 0
    gm.dealer.dealer_hand = make_hand("10", "7")
    p.hands = [make_hand("10", "8", bet=10)] # Win
    gm.settle_bets()
    assert p.balance == 20

@pytest.mark.parametrize(
    "player_cards, dealer_cards, surrendered, start_balance, bet, expected_balance, stat_key",
    [
        (("Ace", "King"), ("10", "9"), False, 0, 10, 25.0, "wins"),
        (("10", "8"), ("9", "9"), False, 0, 10, 10, "pushes"),
        (("10", "6"), ("10", "7"), True, 0, 10, 5, "surrenders"),
        (("10", "10", "5"), ("10", "7"), False, 0, 10, 0, "busts"),
        (("10", "7"), ("10", "8"), False, 0, 10, 0, "losses"),
    ]
)
def test_settle_bets_outcomes(player_cards, dealer_cards, surrendered, start_balance, bet, expected_balance, stat_key):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    h = make_hand(*player_cards, bet=bet)
    h.surrendered = surrendered

    p.balance = start_balance
    p.hands = [h]
    gm.dealer.dealer_hand = make_hand(*dealer_cards)

    gm.settle_bets()

    assert p.balance == expected_balance
    assert gm.stats[stat_key] == 1