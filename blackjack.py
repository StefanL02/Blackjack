import random
import csv
import os


# ============================================================
# RULES / CONFIG (single source of truth)
# ============================================================
class Rules:
    # Shoe
    NUM_DECKS = 6
    RESHUFFLE_AT_REMAINING = 0.25  # reshuffle when 25% of cards remain (75% penetration)

    # Dealer
    DEALER_HITS_SOFT_17 = True  # H17 (dealer hits soft 17)

    # Player options
    LATE_SURRENDER = True
    DOUBLE_ANY_TWO = True
    DOUBLE_AFTER_SPLIT = True  # DAS
    MAX_HANDS = 4  # up to 3 splits (4 hands total)

    # Split Aces restrictions
    SPLIT_ACES_ONE_CARD_ONLY = True      # after splitting Aces: deal 1 card per hand then auto-stand
    RESPLIT_ACES_ALLOWED = False         # if you draw another Ace after split, you cannot split again

    # Payouts
    BLACKJACK_PAYOUT_PROFIT = 1.5  # 3:2 profit (win = bet * 1.5, plus returning bet handled via winnings calc)


# ============================================================
# BASIC STRATEGY TABLES (4–8 decks, H17, DAS, Late Surrender)
# Dealer columns are: 2 3 4 5 6 7 8 9 10 A
#
# Codes:
#   H  = Hit
#   S  = Stand
#   Dh = Double if allowed, otherwise Hit
#   Ds = Double if allowed, otherwise Stand
#   P  = Split
#   Ph = Split if DAS allowed, otherwise Hit
#   Rh = Surrender if allowed, otherwise Hit
# ============================================================

DEALER_COLS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # 11 = Ace
DEALER_TO_IDX = {v: i for i, v in enumerate(DEALER_COLS)}

# Hard totals (9–16). 8 and below always hit; 17+ always stand.
HARD_TABLE = {
    9:  ["H", "Dh", "Dh", "Dh", "Dh", "H", "H", "H", "H", "H"],
    10: ["Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "H", "H"],
    11: ["Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh"],  # H17: double vs Ace too
    12: ["H", "H", "S", "S", "S", "H", "H", "H", "H", "H"],
    13: ["S", "S", "S", "S", "S", "H", "H", "H", "H", "H"],
    14: ["S", "S", "S", "S", "S", "H", "H", "H", "H", "H"],
    15: ["S", "S", "S", "S", "S", "H", "H", "H", "Rh", "Rh"],  # H17: surrender vs 10 and Ace
    16: ["S", "S", "S", "S", "S", "H", "H", "Rh", "Rh", "Rh"],
}

# Soft totals (A,2=13 … A,9=20)
SOFT_TABLE = {
    13: ["H", "H", "H", "Dh", "Dh", "H", "H", "H", "H", "H"],
    14: ["H", "H", "H", "Dh", "Dh", "H", "H", "H", "H", "H"],
    15: ["H", "H", "Dh", "Dh", "Dh", "H", "H", "H", "H", "H"],
    16: ["H", "H", "Dh", "Dh", "Dh", "H", "H", "H", "H", "H"],
    17: ["H", "Dh", "Dh", "Dh", "Dh", "H", "H", "H", "H", "H"],
    18: ["Dh", "Ds", "Ds", "Ds", "Ds", "S", "S", "H", "H", "H"],  # H17: double vs 2; hit vs 9/10/A
    19: ["S", "S", "S", "S", "Ds", "S", "S", "S", "S", "S"],      # H17: double vs 6
    20: ["S"] * 10,
}

# Pairs (split table). Note: "Ph" depends on DAS.
PAIRS_TABLE = {
    "2":   ["Ph", "Ph", "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H"],
    "3":   ["Ph", "Ph", "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H"],
    "4":   ["H",  "H",  "H",  "Ph", "Ph", "H",  "H",  "H",  "H",  "H"],
    "5":   ["Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "Dh", "H",  "H"],  # treat like hard 10
    "6":   ["Ph", "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H",  "H"],
    "7":   ["P",  "P",  "P",  "P",  "P",  "P",  "H",  "H",  "H",  "H"],
    "8":   ["P",  "P",  "P",  "P",  "P",  "P",  "P",  "P",  "P",  "P"],  # special-case vs Ace for surrender below
    "9":   ["P",  "P",  "P",  "P",  "P",  "S",  "P",  "P",  "S",  "S"],
    "10":  ["S"] * 10,
    "Jack":["S"] * 10,
    "Queen":["S"] * 10,
    "King":["S"] * 10,
    "Ace": ["P"] * 10,
}


def card_value_for_upcard(card):
    r = card["rank"]
    if r.isdigit():
        return int(r)
    if r in ("Jack", "Queen", "King"):
        return 10
    return 11  # Ace


def resolve_code(code, can_double, can_split, can_surrender, das_allowed):
    if code == "H":
        return "hit"
    if code == "S":
        return "stand"
    if code == "Dh":
        return "double" if can_double else "hit"
    if code == "Ds":
        return "double" if can_double else "stand"
    if code == "P":
        return "split" if can_split else None
    if code == "Ph":
        # split only if DAS is allowed; otherwise hit
        return "split" if (can_split and das_allowed) else "hit"
    if code == "Rh":
        return "surrender" if can_surrender else "hit"
    return "hit"


class BasicStrategyEngine:
    @staticmethod
    def decide(hand, dealer_up_card, rules, current_hand_count, dealer_peeked_no_blackjack):
        dealer_up = card_value_for_upcard(dealer_up_card)
        d_idx = DEALER_TO_IDX[dealer_up]

        # Allowed actions (rule enforcement)
        can_surrender = (
            rules.LATE_SURRENDER
            and len(hand.cards) == 2
            and dealer_peeked_no_blackjack  # late surrender only after dealer peeks and doesn't have BJ
        )

        can_split = (
            len(hand.cards) == 2
            and hand.is_pair()
            and current_hand_count < rules.MAX_HANDS
        )

        if can_split and not rules.RESPLIT_ACES_ALLOWED:
            # If this hand was created by splitting Aces, never allow splitting again
            if getattr(hand, "is_split_aces_hand", False):
                can_split = False

        # Double: allowed on first two cards; disable after split if DAS is off
        can_double = (
            len(hand.cards) == 2
            and rules.DOUBLE_ANY_TWO
        )
        if getattr(hand, "is_split_hand", False) and not rules.DOUBLE_AFTER_SPLIT:
            can_double = False

        # Split Aces restriction: no doubling (hand is effectively forced-stand after 1 card anyway)
        if (rules.SPLIT_ACES_ONE_CARD_ONLY
                and getattr(hand, "is_split_aces_hand", False)):
            can_double = False

        # ---- Pairs table
        if hand.is_pair():
            r = hand.cards[0]["rank"]
            # Normalize 10-value ranks for PAIRS_TABLE lookup
            if r in ("Jack","Queen","King"):
                r = "10"
            code = PAIRS_TABLE.get(r, None)
            if code:
                action = resolve_code(
                    code[d_idx],
                    can_double=can_double,
                    can_split=can_split,
                    can_surrender=can_surrender,
                    das_allowed=rules.DOUBLE_AFTER_SPLIT,
                )
                if action:
                    return action  # split/double/hit/stand/surrender

        # ---- Soft totals
        if hand.is_soft():
            total = hand.get_value()
            # soft totals relevant are 13..20
            code_row = SOFT_TABLE.get(total, None)
            if code_row:
                return resolve_code(
                    code_row[d_idx],
                    can_double=can_double,
                    can_split=can_split,
                    can_surrender=can_surrender,
                    das_allowed=rules.DOUBLE_AFTER_SPLIT,
                )
            # default soft fallback
            return "hit" if total <= 17 else "stand"

        # ---- Hard totals
        total = hand.get_value()
        if total <= 8:
            return "hit"
        if total >= 17:
            return "stand"

        code_row = HARD_TABLE.get(total, None)
        if code_row:
            return resolve_code(
                code_row[d_idx],
                can_double=can_double,
                can_split=can_split,
                can_surrender=can_surrender,
                das_allowed=rules.DOUBLE_AFTER_SPLIT,
            )

        # fallback
        return "hit" if total < 17 else "stand"


# ============================================================
# CORE GAME CLASSES
# ============================================================

class DeckOfCards:
    def __init__(self):
        self.cards = []
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
        for suit in suits:
            for rank in ranks:
                self.cards.append({'rank': rank, 'suit': suit})

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self):
        return self.cards.pop() if self.cards else None

    def __len__(self):
        return len(self.cards)


class Shoe:
    def __init__(self, num_decks):
        self.decks = [DeckOfCards() for _ in range(num_decks)]
        self.all_cards = []
        for deck in self.decks:
            self.all_cards.extend(deck.cards)
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.all_cards)

    def deal(self):
        return self.all_cards.pop() if self.all_cards else None

    def __len__(self):
        return len(self.all_cards)


class Hand:
    def __init__(self, bet=0):
        self.cards = []
        self.bet = bet
        self.surrendered = False
        self.doubled = False
        self.is_split_hand = False

        # Split Aces restrictions
        self.is_split_aces_hand = False
        self.split_aces_locked = False

    def add_card(self, card):
        self.cards.append(card)

    def is_pair(self):
        return len(self.cards) == 2 and self.cards[0]['rank'] == self.cards[1]['rank']

    def get_value(self):
        value = 0
        for card in self.cards:
            r = card['rank']
            if r.isdigit():
                value += int(r)
            elif r in ('Jack', 'Queen', 'King'):
                value += 10
            else:
                value += 11  # Ace as 11 initially

        # adjust Aces down
        num_aces = sum(1 for c in self.cards if c['rank'] == 'Ace')
        while value > 21 and num_aces > 0:
            value -= 10
            num_aces -= 1
        return value

    def is_soft(self):
        # Soft if an Ace can be treated as 11 without busting
        hard = 0
        aces = 0
        for c in self.cards:
            r = c['rank']
            if r.isdigit():
                hard += int(r)
            elif r in ('Jack', 'Queen', 'King'):
                hard += 10
            else:
                aces += 1
                hard += 1
        return aces > 0 and hard + 10 <= 21

    def is_soft_17(self):
        return self.get_value() == 17 and self.is_soft()

    def __str__(self):
        cards_str = ', '.join([f"{c['rank']} of {c['suit']}" for c in self.cards])
        return f'Hand: [{cards_str}], Bet: {self.bet}'


class Player:
    _player_counter = 0  # Class-level counter for unique IDs

    def __init__(self, bet=0, balance=1000, max_hands=Rules.MAX_HANDS):
        Player._player_counter += 1
        self.id = Player._player_counter  # Assign a unique ID
        self.hands = [Hand(bet)]
        self.balance = balance
        self.max_hands = max_hands

    def add_card_to_hand(self, card, hand_index=0):
        if 0 <= hand_index < len(self.hands):
            self.hands[hand_index].add_card(card)

    def split_hand(self, hand_index=0):
        if not (0 <= hand_index < len(self.hands)):
            return False

        if len(self.hands) >= self.max_hands:
            return False

        hand_to_split = self.hands[hand_index]
        if not hand_to_split.is_pair():
            return False

        splitting_aces = (hand_to_split.cards[0]["rank"] == "Ace")

        # create two hands
        new_hand1 = Hand(hand_to_split.bet)
        new_hand2 = Hand(hand_to_split.bet)
        new_hand1.is_split_hand = True
        new_hand2.is_split_hand = True

        if splitting_aces:
            new_hand1.is_split_aces_hand = True
            new_hand2.is_split_aces_hand = True

        new_hand1.add_card(hand_to_split.cards[0])
        new_hand2.add_card(hand_to_split.cards[1])



        self.hands.pop(hand_index)
        self.hands.insert(hand_index, new_hand2)
        self.hands.insert(hand_index, new_hand1)
        return True

    def choice(self, hand, dealer_up_card, rules, dealer_peeked_no_blackjack):
        return BasicStrategyEngine.decide(
            hand=hand,
            dealer_up_card=dealer_up_card,
            rules=rules,
            current_hand_count=len(self.hands),
            dealer_peeked_no_blackjack=dealer_peeked_no_blackjack,
        )

    def __str__(self):
        hands_str = "\n".join([f"  Hand {i+1}: {hand}" for i, hand in enumerate(self.hands)])
        return f"Player Hands:\n{hands_str}\nBalance: {self.balance}"


class Dealer:
    def __init__(self, shoe, num_players, game_manager):
        self.shoe = shoe
        self.players = [] # Initialize as empty, GameManager will populate with IDs
        self.dealer_hand = Hand()
        self.game_manager = game_manager

    def deal_initial_cards(self):
        # first card to each player
        for player in self.players:
            card = self.game_manager._get_card_with_reshuffle()
            if card:
                player.add_card_to_hand(card)

        # dealer upcard
        card = self.game_manager._get_card_with_reshuffle()
        if card:
            self.dealer_hand.add_card(card)

        # second card to each player
        for player in self.players:
            card = self.game_manager._get_card_with_reshuffle()
            if card:
                player.add_card_to_hand(card)

        # dealer hole card
        card = self.game_manager._get_card_with_reshuffle()
        if card:
            self.dealer_hand.add_card(card)

    def deal_card_to_player(self, player_index, hand_index):
        # This method is now problematic as player_index is a list index, not player.id
        # It will be called within handle_player_turns, which iterates over actual players.
        # The `player_index` here is actually the index in `self.players` list.
        if 0 <= player_index < len(self.players):
            card = self.game_manager._get_card_with_reshuffle()
            if card:
                self.players[player_index].add_card_to_hand(card, hand_index)

    def __str__(self):
        player_hands_str = "\n".join([f"Player {p.id}:\n{p}" for p in self.players])
        return f"Dealer's Hand: {self.dealer_hand}\n{player_hands_str}"


# ============================================================
# GAME MANAGER (rules enforced here + verbose logging)
# ============================================================

class GameManager:
    def __init__(self, num_decks, num_players, rules=Rules, verbose=True):
        self.run_id = self._get_next_run_id()
        self.rules = rules
        self.verbose = verbose

        self.num_decks = num_decks
        self.shoe = Shoe(num_decks)

        self.eliminated_players = []
        self.initial_shoe_size = len(self.shoe)
        self.reshuffle_threshold = int(self.initial_shoe_size * self.rules.RESHUFFLE_AT_REMAINING)

        self.dealer = Dealer(self.shoe, num_players, self)
        # Create players with unique IDs
        self.dealer.players = [Player(bet=0, balance=1000, max_hands=Rules.MAX_HANDS) for _ in range(num_players)]
        self.starting_bankroll = 1000

        # optional: basic stats (extend for Monte Carlo later)
        self.stats = {"rounds": 0, "hands": 0, "wins": 0, "losses": 0, "pushes": 0, "blackjacks": 0, "surrenders": 0}

    def log(self, msg):
        if self.verbose:
            print(msg)

    def _reshuffle_if_needed(self):
        if len(self.shoe) < self.reshuffle_threshold:
            self.log("\n--- Reshuffling Shoe ---")
            self.shoe = Shoe(self.num_decks)
            self.initial_shoe_size = len(self.shoe)
            self.reshuffle_threshold = int(self.initial_shoe_size * self.rules.RESHUFFLE_AT_REMAINING)
            self.dealer.shoe = self.shoe
            self.log(f"Shoe reshuffled. New shoe size: {len(self.shoe)}")

    def _get_card_with_reshuffle(self):
        self._reshuffle_if_needed()
        return self.shoe.deal()

    def place_bets(self):
        self.log("\n--- Placing Bets ---")
        for player in self.dealer.players[:]: # Iterate over a copy to allow removal
            bet_amount = 10
            self.log(f"Player {player.id}: Current balance is {player.balance}, attempting to bet {bet_amount}.")
            if player.balance >= bet_amount:
                player.hands = [Hand(bet_amount)] # Reset hands and set the bet
                player.balance -= bet_amount # Deduct the bet from the player's balance
                self.log(f"Player {player.id} placed a bet of {bet_amount}. Remaining balance: {player.balance}")
            else:
                self.log(f"Player {player.id} does not have enough funds to place a bet of {bet_amount}. Player eliminated.")
                self.eliminated_players.append(player)
                self.dealer.players.remove(player)

    def dealer_has_blackjack(self):
        return self.dealer.dealer_hand.get_value() == 21 and len(self.dealer.dealer_hand.cards) == 2

    def dealer_should_peek(self):
        # Standard hole-card peek when upcard is Ace or 10-value
        up = self.dealer.dealer_hand.cards[0]
        v = card_value_for_upcard(up)
        return v in (10, 11)

    def start_round(self):
        self.stats["rounds"] += 1
        self.log("\nStarting a new round...")

        self.place_bets()
        if not self.dealer.players:
            self.log("No players left in the game. Ending round.")
            return

        self._reshuffle_if_needed()

        self.dealer.dealer_hand = Hand()
        self.dealer.deal_initial_cards()

        self.log("\n--- Initial Deal ---")
        self.log(str(self.dealer))

        # Dealer peek / immediate blackjack check
        dealer_peeked_no_blackjack = True
        if self.dealer_should_peek():
            if self.dealer_has_blackjack():
                self.log("\nDealer has Blackjack!")
                dealer_peeked_no_blackjack = False
            else:
                dealer_peeked_no_blackjack = True

        # If dealer has blackjack, skip player/dealer turns, settle directly
        if self.dealer_has_blackjack():
            self.settle_bets()
            return

        self.handle_player_turns(dealer_peeked_no_blackjack)
        self.handle_dealer_turn()
        self.settle_bets()

        self.log("\nRound finished.")
        self.log(str(self.dealer))

    def handle_player_turns(self, dealer_peeked_no_blackjack):
        self.log("\n--- Player Turns ---")
        # Need to find the index of the player in the current list for deal_card_to_player
        for player_current_list_index, player in enumerate(self.dealer.players):
            self.log(f"\nPlayer {player.id}'s turn:")
            hand_index = 0

            while hand_index < len(player.hands):
                hand = player.hands[hand_index]
                self.log(f"  Hand {hand_index + 1}: {hand}")

                # Split Aces restriction: once split-ace hand has received its 1 card, it is dead
                if (self.rules.SPLIT_ACES_ONE_CARD_ONLY
                        and getattr(hand, "is_split_aces_hand", False)
                        and len(hand.cards) >= 2):
                    self.log("  Split Aces restriction: stand (one card only).")
                    hand_index += 1
                    continue

                # Natural blackjack (player)
                if hand.get_value() == 21 and len(hand.cards) == 2:
                    self.stats["blackjacks"] += 1
                    self.log("  Blackjack!")
                    hand_index += 1
                    continue

                split_done = False
                while hand.get_value() < 21:
                    dealer_up_card = self.dealer.dealer_hand.cards[0]
                    decision = player.choice(hand, dealer_up_card, self.rules, dealer_peeked_no_blackjack)

                    if decision == "hit":
                        card = self._get_card_with_reshuffle()
                        if not card:
                            break
                        player.add_card_to_hand(card, hand_index)
                        hand = player.hands[hand_index]  # re-bind to be safe
                        self.log(f"  Hit: {card['rank']} of {card['suit']} -> {hand}")
                        self.log(f"  Debug: len(hand.cards)={len(hand.cards)} value={hand.get_value()}") # Temporary debug line
                        if hand.get_value() > 21:
                            self.log("  Bust!")
                            break

                    elif decision == "stand":
                        self.log("  Stand.")
                        break

                    elif decision == "surrender":
                        # late surrender only valid on first two cards; strategy enforces it already
                        hand.surrendered = True
                        self.stats["surrenders"] += 1
                        self.log("  Surrender.")
                        break

                    elif decision == "double":
                        # Double: take one card only, then stand
                        if len(hand.cards) == 2 and player.balance >= hand.bet:
                            player.balance -= hand.bet
                            hand.bet *= 2
                            hand.doubled = True
                            self.dealer.deal_card_to_player(player_current_list_index, hand_index)
                            hand = player.hands[hand_index] # re-bind after deal_card_to_player
                            self.log(f"  Double. New bet: {hand.bet}. Hand: {hand}")
                            if hand.get_value() > 21:
                                self.log("  Bust!")
                            break
                        else:
                            # fallback if not allowed
                            self.log("  Double not allowed -> Stand.")
                            break

                    elif decision == "split":
                        # Check funds for extra bet
                        if player.balance < hand.bet:
                            self.log("  Split not allowed (insufficient funds) -> Stand.")
                            break

                        if player.split_hand(hand_index):
                            player.balance -= hand.bet
                            # Deal one card to each new hand
                            # Note: when splitting, new hands are inserted at `hand_index` and `hand_index + 1`
                            # The current `hand_index` now refers to the first of the two new hands.
                            self.dealer.deal_card_to_player(player_current_list_index, hand_index) # Deal to the first new hand
                            self.dealer.deal_card_to_player(player_current_list_index, hand_index + 1) # Deal to the second new hand

                            # If this was a split of Aces, lock both hands (no further hits)
                            h1 = player.hands[hand_index]
                            h2 = player.hands[hand_index + 1]
                            if (self.rules.SPLIT_ACES_ONE_CARD_ONLY
                                and getattr(h1, "is_split_aces_hand", False)
                                and getattr(h2, "is_split_aces_hand", False)):
                                h1.split_aces_locked = True
                                h2.split_aces_locked = True

                            self.log(f"  Split performed. Remaining balance: {player.balance}")
                            split_done = True
                            break
                        else:
                            self.log("  Split not allowed -> Stand.")
                            break

                    else:
                        self.log(f"  Unknown decision {decision} -> Stand.")
                        break

                if split_done:
                    continue
                hand_index += 1

    def handle_dealer_turn(self):
        self.log("\n--- Dealer's Turn ---")
        dealer_hand = self.dealer.dealer_hand
        self.log(f"Dealer's Hand: {dealer_hand}")

        while dealer_hand.get_value() < 17 or (
            self.rules.DEALER_HITS_SOFT_17 and dealer_hand.get_value() == 17 and dealer_hand.is_soft_17()
        ):
            card = self._get_card_with_reshuffle()
            if not card:
                break
            dealer_hand.add_card(card)
            self.log(f"Dealer hits: {card['rank']} of {card['suit']} -> {dealer_hand}")
            if dealer_hand.get_value() > 21:
                self.log("Dealer busts!")
                break

    def _get_next_run_id(self):
        if not os.path.isfile("summary_stats.csv"):
            return 1

        with open("summary_stats.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                return 1
            return int(rows[-1]["Run ID"]) + 1

    def determine_outcome(self, player_hand, dealer_hand):
        if player_hand.surrendered:
            return "surrender"

        pv = player_hand.get_value()
        dv = dealer_hand.get_value()

        # busts
        if pv > 21:
            return "bust"
        if dv > 21:
            return "win"

        # natural blackjacks
        player_bj = (pv == 21 and len(player_hand.cards) == 2 and not getattr(player_hand, "is_split_hand", False))
        dealer_bj = (dv == 21 and len(dealer_hand.cards) == 2)
        if player_bj and not dealer_bj:
            return "blackjack"
        if dealer_bj and not player_bj:
            return "lose"
        if player_bj and dealer_bj:
            return "push"

        # normal compare
        if pv > dv:
            return "win"
        if pv < dv:
            return "lose"
        return "push"

    def settle_bets(self):
        self.log("\n--- Settling Bets ---")
        dealer_hand = self.dealer.dealer_hand
        active_players = []

        for player in self.dealer.players:
            self.log(f"\nPlayer {player.id} (Balance: {player.balance}):")
            for hand in player.hands:
                self.stats["hands"] += 1
                outcome = self.determine_outcome(hand, dealer_hand)
                bet = hand.bet
                winnings = 0

                if outcome == "win":
                    winnings = bet * 2
                    self.stats["wins"] += 1
                elif outcome == "blackjack":
                    # Return bet + profit(1.5*bet) = 2.5*bet
                    winnings = bet * (1 + self.rules.BLACKJACK_PAYOUT_PROFIT)
                    self.stats["wins"] += 1
                elif outcome == "push":
                    winnings = bet
                    self.stats["pushes"] += 1
                elif outcome == "surrender":
                    winnings = bet * 0.5
                    self.stats["losses"] += 1
                else:  # bust or lose
                    winnings = 0
                    self.stats["losses"] += 1

                player.balance += winnings
                self.log(f"  Hand (Bet: {bet}): Outcome: {outcome}, Winnings: {winnings}. New balance: {player.balance}")

            if player.balance > 0:
                active_players.append(player)
            else:
                self.log(f"Player {player.id} has been eliminated with a balance of {player.balance}.")
                self.eliminated_players.append(player)

        self.dealer.players = active_players

    def play_game(self, num_rounds=5):
        round_num = 1
        while self.dealer.players and round_num <= num_rounds:
            self.log(f"\n===== Round {round_num} =====")
            self.start_round()
            round_num += 1

        self.log("\n===== Game Over =====")
        if not self.dealer.players:
            self.log("All players have been eliminated.")
        else:
            self.log(f"Finished {num_rounds} rounds.")
            self.log("Final Player Balances:")
            for player in self.dealer.players:
                self.log(f"Player {player.id}: {player.balance}")

        if self.eliminated_players:
            self.log("\nEliminated Players (Final Balance):")
            for player in self.eliminated_players:
                self.log(f"Player {player.id}: {player.balance}")

        # summary stats (useful when verbose=False too)
        print("\n--- Summary Stats ---")
        print(self.stats)

        # Export summary stats
        file_exists = os.path.isfile("summary_stats.csv")
        with open("summary_stats.csv", "a", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["Run ID"] + list(self.stats.keys())
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow({
                "Run ID": self.run_id,
                **self.stats
            })

        # Export player stats
        file_exists = os.path.isfile("player_stats.csv")
        with open("player_stats.csv", "a", newline="") as f:
            fieldnames = [
                "Run ID",
                "Player ID",
                "Start Bankroll",
                "Final Balance",
                "Net Profit"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            all_players = self.dealer.players + self.eliminated_players
            for player in all_players:
                writer.writerow({
                    "Run ID": self.run_id,
                    "Player ID": player.id,
                    "Start Bankroll": self.starting_bankroll,
                    "Final Balance": player.balance,
                    "Net Profit": player.balance - self.starting_bankroll
                })

        print("\nCSV files exported:")
        print(os.path.abspath("summary_stats.csv"))
        print(os.path.abspath("player_stats.csv"))




if __name__ == "__main__":
    num_decks = Rules.NUM_DECKS
    num_players = 5
    num_rounds = 1000

    # Debug mode: verbose=True
    # Monte Carlo mode: verbose=False
    game_manager = GameManager(num_decks, num_players, rules=Rules, verbose=True)
    game_manager.play_game(num_rounds)