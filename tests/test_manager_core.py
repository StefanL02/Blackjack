
from blackjack import GameManager, Rules, Hand
def c(rank, suit="Hearts"):
    return {"rank": str(rank), "suit": suit}

def make_hand(*ranks, bet=10):
    h = Hand(bet=bet)
    for r in ranks:
        h.add_card(c(r))
    return h

def test_place_bets_removes_broke_players():
    gm = GameManager(6, 2, rules=Rules, verbose=False)
    gm.dealer.players[0].balance = 5
    gm.place_bets()
    assert len(gm.dealer.players) == 1

def test_dealer_should_peek_logic():
    gm = GameManager(6, 1, rules=Rules, verbose=False)
    gm.dealer.dealer_hand = make_hand("Ace")
    assert gm.dealer_should_peek() is True

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