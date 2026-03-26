import pytest
import csv
from blackjack import GameManager, Rules, Hand, FullHiLoRules

class NoCountingRules(Rules):
    COUNTING_ENABLED = False
    USE_INSURANCE_INDEX = True

class NoInsuranceIndexRules(Rules):
    COUNTING_ENABLED = True
    USE_INSURANCE_INDEX = False

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

def test_dealer_deal_initial_cards_gives_two_cards_to_each_player_and_two_to_dealer():
    gm = GameManager(6, 2, rules=Rules, verbose=False)

    # fixed shoe order: pop() removes from end
    gm.shoe.all_cards = [
        c("2"), c("3"), c("4"), c("5"),
        c("6"), c("7"), c("8"), c("9")
    ]

    gm.dealer.dealer_hand = Hand()
    for p in gm.dealer.players:
        p.hands = [Hand(bet=10)]

    gm.dealer.deal_initial_cards()

    # each player should have 2 cards
    assert len(gm.dealer.players[0].hands[0].cards) == 2
    assert len(gm.dealer.players[1].hands[0].cards) == 2

    # dealer should have upcard + hole card
    assert len(gm.dealer.dealer_hand.cards) == 2


def test_dealer_string_representation_contains_dealer_and_players():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.dealer.dealer_hand = make_hand("Ace", "King")
    gm.dealer.players[0].hands = [make_hand("10", "7", bet=10)]

    s = str(gm.dealer)

    assert "Dealer's Hand:" in s
    assert "Player" in s
    assert "Balance:" in s

def test_log_prints_when_verbose_true(capsys):
    gm = GameManager(6, 1, rules=Rules, verbose=True)
    gm.log("hello test")

    captured = capsys.readouterr()
    assert "hello test" in captured.out

def test_reshuffle_if_needed_resets_count_and_hole_card_flag():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    gm.running_count = 7
    gm.true_count = 3
    gm.hole_card_revealed = True

    # force reshuffle condition
    gm.shoe.all_cards = [c("2")]  # very small shoe
    gm._reshuffle_if_needed()

    assert gm.running_count == 0
    assert gm.true_count == 0
    assert gm.hole_card_revealed is False
    assert len(gm.shoe) > 1

def test_get_card_with_reshuffle_visible_updates_running_count():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.running_count = 0
    gm.reshuffle_threshold = 0

    gm.shoe.all_cards = [c("2")]
    card = gm._get_card_with_reshuffle(visible=True)

    assert card["rank"] == "2"
    assert gm.running_count == 1


def test_get_card_with_reshuffle_hidden_does_not_update_running_count():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.running_count = 0
    gm.reshuffle_threshold = 0   # prevent reshuffle

    gm.shoe.all_cards = [c("2")]
    card = gm._get_card_with_reshuffle(visible=False)

    assert card["rank"] == "2"
    assert gm.running_count == 0

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

def test_offer_insurance_returns_early_when_counting_disabled():
    gm = GameManager(6, 1, rules=NoCountingRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = True
    p.hands = [make_hand("10", "9", bet=10)]
    gm.true_count = 10

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == 0.0

def test_offer_insurance_skips_basic_player():
    gm = GameManager(6, 1, rules=FullHiLoRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = False
    p.hands = [make_hand("10", "9", bet=10)]
    gm.true_count = 10

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == 0.0


def test_offer_insurance_counter_takes_insurance_at_threshold():
    gm = GameManager(6, 1, rules=FullHiLoRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = True
    p.balance = 100
    p.hands = [make_hand("10", "9", bet=10)]
    gm.true_count = FullHiLoRules.INSURANCE_TC_THRESHOLD

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == 5.0
    assert p.balance == 95.0


def test_offer_insurance_counter_declines_below_threshold():
    gm = GameManager(6, 1, rules=FullHiLoRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = True
    p.balance = 100
    p.hands = [make_hand("10", "9", bet=10)]
    gm.true_count = FullHiLoRules.INSURANCE_TC_THRESHOLD - 1

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == 0.0
    assert p.balance == 100


def test_offer_insurance_declines_if_not_enough_balance():
    gm = GameManager(6, 1, rules=FullHiLoRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = True
    p.balance = 4   # less than 0.5 * bet
    p.hands = [make_hand("10", "9", bet=10)]
    gm.true_count = 10

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == 0.0
    assert p.balance == 4


def test_offer_insurance_skips_hand_when_not_two_cards():
    gm = GameManager(6, 1, rules=FullHiLoRules, verbose=False)
    p = gm.dealer.players[0]
    p.is_counter = True
    p.balance = 100
    p.hands = [make_hand("10", "9", "2", bet=10)]
    gm.true_count = 10

    gm.offer_insurance()

    assert p.hands[0].insurance_bet == 0.0
    assert p.balance == 100

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

def test_get_next_run_id_returns_1_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    assert gm.run_id == 1


def test_get_next_run_id_returns_1_when_file_has_only_header(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with open("summary_stats.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Run ID", "rounds"])
        writer.writeheader()

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    assert gm.run_id == 1


def test_get_next_run_id_returns_last_plus_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with open("summary_stats.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Run ID", "rounds"])
        writer.writeheader()
        writer.writerow({"Run ID": 1, "rounds": 10})
        writer.writerow({"Run ID": 2, "rounds": 20})

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    assert gm.run_id == 3

def test_determine_outcome_player_bust():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    player_hand = make_hand("10", "10", "5")
    dealer_hand = make_hand("10", "7")

    assert gm.determine_outcome(player_hand, dealer_hand) == "bust"


def test_determine_outcome_dealer_bust_is_win():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    player_hand = make_hand("10", "7")
    dealer_hand = make_hand("10", "8", "5")

    assert gm.determine_outcome(player_hand, dealer_hand) == "win"


def test_determine_outcome_player_blackjack():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    player_hand = make_hand("Ace", "King")
    dealer_hand = make_hand("10", "9")

    assert gm.determine_outcome(player_hand, dealer_hand) == "blackjack"


def test_determine_outcome_dealer_blackjack_is_lose():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    player_hand = make_hand("10", "9")
    dealer_hand = make_hand("Ace", "King")

    assert gm.determine_outcome(player_hand, dealer_hand) == "lose"


def test_determine_outcome_both_blackjack_is_push():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    player_hand = make_hand("Ace", "King")
    dealer_hand = make_hand("Ace", "Queen")

    assert gm.determine_outcome(player_hand, dealer_hand) == "push"


def test_determine_outcome_normal_lose():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    player_hand = make_hand("10", "7")
    dealer_hand = make_hand("10", "8")

    assert gm.determine_outcome(player_hand, dealer_hand) == "lose"


def test_determine_outcome_normal_push():
    gm = GameManager(6, 1, rules=Rules, verbose=False)

    player_hand = make_hand("10", "8")
    dealer_hand = make_hand("9", "9")

    assert gm.determine_outcome(player_hand, dealer_hand) == "push"

def test_settle_bets_blackjack_payout():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.balance = 0
    p.hands = [make_hand("Ace", "King", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "9")

    gm.settle_bets()

    assert p.balance == 25.0
    assert gm.stats["wins"] == 1


def test_settle_bets_push_returns_bet():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.balance = 0
    p.hands = [make_hand("10", "8", bet=10)]
    gm.dealer.dealer_hand = make_hand("9", "9")

    gm.settle_bets()

    assert p.balance == 10
    assert gm.stats["pushes"] == 1


def test_settle_bets_surrender_returns_half_bet():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    h = make_hand("10", "6", bet=10)
    h.surrendered = True

    p.balance = 0
    p.hands = [h]
    gm.dealer.dealer_hand = make_hand("10", "7")

    gm.settle_bets()

    assert p.balance == 5
    assert gm.stats["surrenders"] == 1


def test_settle_bets_bust_loses_entire_bet():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.balance = 0
    p.hands = [make_hand("10", "10", "5", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "7")

    gm.settle_bets()

    assert p.balance == 0
    assert gm.stats["busts"] == 1


def test_settle_bets_lose_branch():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.balance = 0
    p.hands = [make_hand("10", "7", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "8")

    gm.settle_bets()

    assert p.balance == 0
    assert gm.stats["losses"] == 1

def test_settle_bets_eliminates_player_with_zero_balance():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    p = gm.dealer.players[0]

    p.balance = 0
    p.hands = [make_hand("10", "7", bet=10)]
    gm.dealer.dealer_hand = make_hand("10", "8")

    gm.settle_bets()

    assert p not in gm.dealer.players
    assert p in gm.eliminated_players

def test_play_game_calls_start_round_correct_number_of_times(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    calls = {"count": 0}

    def fake_start_round():
        calls["count"] += 1

    monkeypatch.setattr(gm, "start_round", fake_start_round)

    gm.play_game(num_rounds=3)

    assert calls["count"] == 3


