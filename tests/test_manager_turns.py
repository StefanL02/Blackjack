from blackjack import GameManager, Rules, Hand

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

def test_handle_player_turns_split_aces_restriction_skips_hand():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    h = make_hand("Ace", "9", bet=10)
    h.is_split_aces_hand = True
    p.hands = [h]

    gm.dealer.dealer_hand = make_hand("6", "10")

    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    # no crash, hand unchanged, branch executed
    assert len(p.hands[0].cards) == 2

def test_handle_player_turns_counts_natural_blackjack():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.hands = [make_hand("Ace", "King", bet=10)]
    gm.dealer.dealer_hand = make_hand("6", "10")

    before = gm.stats["blackjacks"]
    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    assert gm.stats["blackjacks"] == before + 1

def test_handle_player_turns_stand_decision(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]
    p.hands = [make_hand("10", "7", bet=10)]
    gm.dealer.dealer_hand = make_hand("6", "10")

    monkeypatch.setattr(p, "choice", lambda *args, **kwargs: "stand")

    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    assert p.hands[0].get_value() == 17

def test_handle_player_turns_surrender_decision(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]
    p.hands = [make_hand("10", "6", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "7")

    monkeypatch.setattr(p, "choice", lambda *args, **kwargs: "surrender")

    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    assert p.hands[0].surrendered is True

def test_handle_player_turns_hit_adds_card(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.reshuffle_threshold = 0

    p = gm.dealer.players[0]
    p.hands = [make_hand("5", "4", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "7")

    decisions = iter(["hit", "stand"])
    monkeypatch.setattr(p, "choice", lambda *args, **kwargs: next(decisions))

    gm.shoe.all_cards = [c("2")]

    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    assert len(p.hands[0].cards) == 3
    assert p.hands[0].get_value() == 11

def test_handle_player_turns_double_updates_bet_and_adds_one_card(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.reshuffle_threshold = 0

    p = gm.dealer.players[0]
    p.balance = 100
    p.hands = [make_hand("5", "4", bet=10)]
    gm.dealer.dealer_hand = make_hand("6", "10")

    monkeypatch.setattr(p, "choice", lambda *args, **kwargs: "double")
    gm.shoe.all_cards = [c("2")]

    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    assert p.hands[0].bet == 20
    assert p.hands[0].doubled is True
    assert len(p.hands[0].cards) == 3
    assert p.balance == 90

def test_handle_player_turns_split_creates_two_hands(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.reshuffle_threshold = 0

    p = gm.dealer.players[0]
    p.balance = 100
    p.hands = [make_hand("8", "8", bet=10)]
    gm.dealer.dealer_hand = make_hand("6", "10")

    decisions = iter(["split", "stand", "stand"])
    monkeypatch.setattr(p, "choice", lambda *args, **kwargs: next(decisions))

    gm.shoe.all_cards = [c("3"), c("2")]

    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    assert len(p.hands) == 2
    assert p.balance == 90
    assert len(p.hands[0].cards) == 2
    assert len(p.hands[1].cards) == 2

def test_handle_player_turns_unknown_decision_falls_through(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]
    p.hands = [make_hand("10", "7", bet=10)]
    gm.dealer.dealer_hand = make_hand("6", "10")

    monkeypatch.setattr(p, "choice", lambda *args, **kwargs: "weird_action")

    gm.handle_player_turns(dealer_peeked_no_blackjack=True)

    assert p.hands[0].get_value() == 17

def test_handle_dealer_turn_stands_on_hard_17():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.dealer.dealer_hand = make_hand("10", "7")

    gm.handle_dealer_turn()

    assert gm.dealer.dealer_hand.get_value() == 17
    assert len(gm.dealer.dealer_hand.cards) == 2


def test_handle_dealer_turn_hits_under_17():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.reshuffle_threshold = 0
    gm.dealer.dealer_hand = make_hand("10", "6")
    gm.shoe.all_cards = [c("2")]  # pop() => 2

    gm.handle_dealer_turn()

    assert gm.dealer.dealer_hand.get_value() == 18
    assert len(gm.dealer.dealer_hand.cards) == 3


def test_handle_dealer_turn_hits_soft_17_when_rule_enabled():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.reshuffle_threshold = 0
    gm.dealer.dealer_hand = make_hand("Ace", "6")  # soft 17
    gm.shoe.all_cards = [c("2")]

    gm.handle_dealer_turn()

    assert len(gm.dealer.dealer_hand.cards) == 3
    assert gm.dealer.dealer_hand.get_value() == 19


def test_handle_dealer_turn_busts():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.reshuffle_threshold = 0
    gm.dealer.dealer_hand = make_hand("10", "6")
    gm.shoe.all_cards = [c("King")]

    gm.handle_dealer_turn()

    assert gm.dealer.dealer_hand.get_value() > 21


def test_handle_dealer_turn_breaks_if_no_card(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.dealer.dealer_hand = make_hand("10", "6")

    monkeypatch.setattr(gm, "_get_card_with_reshuffle", lambda visible=True: None)

    gm.handle_dealer_turn()

    assert gm.dealer.dealer_hand.get_value() == 16
    assert len(gm.dealer.dealer_hand.cards) == 2