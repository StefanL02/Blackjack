import pytest
from blackjack import GameManager, Rules, Hand

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

def test_determine_outcome_surrender():
    gm = GameManager(Rules.NUM_DECKS, 1, rules=Rules, verbose=False)
    player = make_hand("10", "6")
    player.surrendered = True
    dealer = make_hand("10", "7")
    assert gm.determine_outcome(player, dealer) == "surrender"

def test_determine_outcome_player_bust():
    gm = GameManager(Rules.NUM_DECKS, 1, rules=Rules, verbose=False)
    player = make_hand("10", "10", "5")
    dealer = make_hand("10", "7")
    assert gm.determine_outcome(player, dealer) == "bust"

def test_determine_outcome_dealer_bust_player_wins():
    gm = GameManager(Rules.NUM_DECKS, 1, rules=Rules, verbose=False)
    player = make_hand("10", "7")
    dealer = make_hand("10", "10", "5")
    assert gm.determine_outcome(player, dealer) == "win"

def test_determine_outcome_blackjack_vs_non_bj():
    gm = GameManager(Rules.NUM_DECKS, 1, rules=Rules, verbose=False)
    player = make_hand("Ace", "King")          # BJ
    dealer = make_hand("10", "9", "2")         # 21 but not BJ
    assert gm.determine_outcome(player, dealer) == "blackjack"

def test_determine_outcome_push():
    gm = GameManager(Rules.NUM_DECKS, 1, rules=Rules, verbose=False)
    player = make_hand("10", "7")
    dealer = make_hand("9", "8")
    assert gm.determine_outcome(player, dealer) == "push"

def test_place_bets_eliminates_player_with_low_balance():
    gm = GameManager(Rules.NUM_DECKS, 2, rules=Rules, verbose=False)

    # Force one player to be broke
    gm.dealer.players[0].balance = 5
    gm.dealer.players[1].balance = 1000

    gm.place_bets()

    # broke player removed
    assert len(gm.dealer.players) == 1
    assert len(gm.eliminated_players) == 1

def test_handle_dealer_turn_hits_soft_17(monkeypatch):
    gm = GameManager(Rules.NUM_DECKS, 1, rules=Rules, verbose=False)
    gm.dealer.dealer_hand = make_hand("Ace", "6")  # soft 17

    # Next card makes it 19 and dealer stops
    deck = [c("2")]
    monkeypatch.setattr(gm, "_get_card_with_reshuffle", lambda: deck.pop())

    gm.handle_dealer_turn()
    assert gm.dealer.dealer_hand.get_value() == 19

def test_settle_bets_win_push_blackjack_surrender_loss():
    gm = GameManager(Rules.NUM_DECKS, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]
    p.balance = 0  # easier to assert changes

    # dealer = 17
    gm.dealer.dealer_hand = make_hand("10", "7", bet=0)

    # Create 5 hands covering branches
    h_win = make_hand("10", "8", bet=10)        # 18 beats 17 => win => +20
    h_push = make_hand("9", "8", bet=10)        # push => +10
    h_bj = make_hand("Ace", "King", bet=10)     # blackjack => +25 (3:2 profit)
    h_surr = make_hand("10", "6", bet=10)       # surrender => +5
    h_lose = make_hand("10", "6", bet=10)       # loses => +0

    h_surr.surrendered = True
    p.hands = [h_win, h_push, h_bj, h_surr, h_lose]

    gm.settle_bets()

    # Expected balance: 20 + 10 + 25 + 5 + 0 = 60
    assert p.balance == 60
