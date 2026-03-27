
from blackjack import GameManager, Rules, Hand

def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

def test_start_round_returns_early_when_no_players_left(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    called = {
        "reshuffle": False,
        "place_bets": False,
        "deal_initial_cards": False,
    }

    def fake_reshuffle():
        called["reshuffle"] = True

    def fake_place_bets():
        called["place_bets"] = True
        gm.dealer.players = []

    def fake_deal_initial_cards():
        called["deal_initial_cards"] = True

    monkeypatch.setattr(gm, "_reshuffle_if_needed", fake_reshuffle)
    monkeypatch.setattr(gm, "place_bets", fake_place_bets)
    monkeypatch.setattr(gm.dealer, "deal_initial_cards", fake_deal_initial_cards)

    gm.start_round()

    assert gm.stats["rounds"] == 1
    assert called["reshuffle"] is True
    assert called["place_bets"] is True
    assert called["deal_initial_cards"] is False

def test_start_round_dealer_blackjack_branch(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    called = {
        "place_bets": False,
        "deal_initial_cards": False,
        "reveal_hole_card": False,
        "settle_bets": False,
        "handle_player_turns": False,
        "handle_dealer_turn": False,
    }

    def fake_place_bets():
        called["place_bets"] = True
        # keep players active
        for p in gm.dealer.players:
            p.hands = [Hand(bet=10)]

    def fake_deal_initial_cards():
        called["deal_initial_cards"] = True
        gm.dealer.dealer_hand = make_hand("Ace", "King")

    def fake_reveal_hole_card():
        called["reveal_hole_card"] = True

    def fake_settle_bets():
        called["settle_bets"] = True

    def fake_handle_player_turns(dealer_peeked_no_blackjack):
        called["handle_player_turns"] = True

    def fake_handle_dealer_turn():
        called["handle_dealer_turn"] = True

    monkeypatch.setattr(gm, "place_bets", fake_place_bets)
    monkeypatch.setattr(gm.dealer, "deal_initial_cards", fake_deal_initial_cards)
    monkeypatch.setattr(gm, "reveal_hole_card", fake_reveal_hole_card)
    monkeypatch.setattr(gm, "settle_bets", fake_settle_bets)
    monkeypatch.setattr(gm, "handle_player_turns", fake_handle_player_turns)
    monkeypatch.setattr(gm, "handle_dealer_turn", fake_handle_dealer_turn)

    gm.start_round()

    assert called["place_bets"] is True
    assert called["deal_initial_cards"] is True
    assert called["reveal_hole_card"] is True
    assert called["settle_bets"] is True
    assert called["handle_player_turns"] is False
    assert called["handle_dealer_turn"] is False



def test_start_round_does_not_offer_insurance_without_ace_upcard(monkeypatch):
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    called = {
        "offer_insurance": False,
    }

    def fake_place_bets():
        for p in gm.dealer.players:
            p.hands = [Hand(bet=10)]

    def fake_deal_initial_cards():
        gm.dealer.dealer_hand = make_hand("9", "7")

    def fake_offer_insurance():
        called["offer_insurance"] = True

    monkeypatch.setattr(gm, "place_bets", fake_place_bets)
    monkeypatch.setattr(gm.dealer, "deal_initial_cards", fake_deal_initial_cards)
    monkeypatch.setattr(gm, "offer_insurance", fake_offer_insurance)
    monkeypatch.setattr(gm, "handle_player_turns", lambda dealer_peeked_no_blackjack: None)
    monkeypatch.setattr(gm, "reveal_hole_card", lambda: None)
    monkeypatch.setattr(gm, "handle_dealer_turn", lambda: None)
    monkeypatch.setattr(gm, "settle_bets", lambda: None)

    gm.start_round()

    assert called["offer_insurance"] is False

def test_play_game_calls_start_round_correct_number_of_times(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    calls = {"count": 0}

    def fake_start_round():
        calls["count"] += 1

    monkeypatch.setattr(gm, "start_round", fake_start_round)

    gm.play_game(num_rounds=3)

    assert calls["count"] == 3