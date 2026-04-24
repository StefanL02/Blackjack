import random
import csv
import os
import math


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

    #Insurance Rules
    INSURANCE_ENABLED = True
    INSURANCE_TC_THRESHOLD = 3  # take insurance if true_count >= 3

    # Hi-Lo Card Counting Config
    COUNTING_ENABLED = True
    HI_LO_TAGS = {
        "2": 1, "3": 1, "4": 1, "5": 1, "6": 1,
        "7": 0, "8": 0, "9": 0,
        "10": -1, "Jack": -1, "Queen": -1, "King": -1, "Ace": -1,
    }

    USE_PLAYING_DEVIATIONS = True
    USE_FAB4 = True
    USE_SPLIT_10_DEVIATIONS = True
    USE_INSURANCE_INDEX = True

    USE_BET_SPREAD = True
    MIN_BET = 10
    BET_RAMP = {
        "tc_le_0": 10,
        "tc_1": 20,
        "tc_2": 40,
        "tc_3": 60,
        "tc_ge_4": 80,
    }

class BasicStrategyRules(Rules):
    COUNTING_ENABLED = False
    USE_PLAYING_DEVIATIONS = False
    USE_FAB4 = False
    USE_SPLIT_10_DEVIATIONS = False
    USE_INSURANCE_INDEX = False
    USE_BET_SPREAD = False


class CountingNoDeviationsRules(Rules):
    COUNTING_ENABLED = True
    USE_PLAYING_DEVIATIONS = False
    USE_FAB4 = False
    USE_SPLIT_10_DEVIATIONS = False
    USE_INSURANCE_INDEX = False
    USE_BET_SPREAD = False


class CountingWithInsuranceRules(Rules):
    COUNTING_ENABLED = True
    USE_PLAYING_DEVIATIONS = False
    USE_FAB4 = False
    USE_SPLIT_10_DEVIATIONS = False
    USE_INSURANCE_INDEX = True
    USE_BET_SPREAD = False


class CountingWithBetSpreadRules(Rules):
    COUNTING_ENABLED = True
    USE_PLAYING_DEVIATIONS = False
    USE_FAB4 = False
    USE_SPLIT_10_DEVIATIONS = False
    USE_INSURANCE_INDEX = False
    USE_BET_SPREAD = True


class PlayingDeviationsOnlyRules(Rules):
    COUNTING_ENABLED = True
    USE_PLAYING_DEVIATIONS = True
    USE_FAB4 = False
    USE_SPLIT_10_DEVIATIONS = False
    USE_INSURANCE_INDEX = False
    USE_BET_SPREAD = False


class FullHiLoNoBetSpreadRules(Rules):
    COUNTING_ENABLED = True
    USE_PLAYING_DEVIATIONS = True
    USE_FAB4 = True
    USE_SPLIT_10_DEVIATIONS = True
    USE_INSURANCE_INDEX = True
    USE_BET_SPREAD = False


class FullHiLoRules(Rules):
    COUNTING_ENABLED = True
    USE_PLAYING_DEVIATIONS = True
    USE_FAB4 = True
    USE_SPLIT_10_DEVIATIONS = True
    USE_INSURANCE_INDEX = True
    USE_BET_SPREAD = True

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

        if (rules.SPLIT_ACES_ONE_CARD_ONLY
                and getattr(hand, "is_split_aces_hand", False)
                and len(hand.cards) >= 2):
            return "stand"

        if can_split and not rules.RESPLIT_ACES_ALLOWED:
            # Specifically block re-splitting only if it's a new pair of Aces
            if getattr(hand, "is_split_aces_hand", False) and hand.cards[0]["rank"] == "Ace":
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

class HiLoStrategyEngine:
    @staticmethod
    def decide(hand, dealer_up_card, rules, current_hand_count, dealer_peeked_no_blackjack, true_count):
        basic_action = BasicStrategyEngine.decide(
            hand=hand,
            dealer_up_card=dealer_up_card,
            rules=rules,
            current_hand_count=current_hand_count,
            dealer_peeked_no_blackjack=dealer_peeked_no_blackjack,
        )

        tc = math.floor(true_count)
        dealer_up = card_value_for_upcard(dealer_up_card)
        total = hand.get_value()

        is_pair = hand.is_pair()
        is_soft = hand.is_soft()

        # Check for Surrender Deviations first (Fab 4)
        can_surrender = rules.LATE_SURRENDER and len(hand.cards) == 2 and dealer_peeked_no_blackjack

        if rules.USE_FAB4 and can_surrender and not is_soft and not is_pair:
            if total == 15 and dealer_up == 10 and tc >= 0: return "surrender"
            if total == 14 and dealer_up == 10 and tc >= 3: return "surrender"
            if total == 15 and dealer_up == 9 and tc >= 2: return "surrender"
            if total == 15 and dealer_up == 11 and tc >= 1: return "surrender"

        # 10,10 splitting deviations
        if rules.USE_SPLIT_10_DEVIATIONS and len(hand.cards) == 2:
            r1 = hand.cards[0]["rank"]
            r2 = hand.cards[1]["rank"]
            ten_value_pair = r1 in ("10", "Jack", "Queen", "King") and r2 in ("10", "Jack", "Queen", "King")

            if ten_value_pair:
                if current_hand_count < rules.MAX_HANDS:
                    if dealer_up == 5 and tc >= 5:
                        return "split"
                    if dealer_up == 6 and tc >= 4:
                        return "split"

        if rules.USE_PLAYING_DEVIATIONS:
            if not is_soft and not is_pair and total == 16 and dealer_up == 10 and tc >= 0:
                return "stand"

            if not is_soft and not is_pair and total == 15 and dealer_up == 10 and tc >= 4:
                return "stand"

            if not is_soft and total == 10 and dealer_up == 10 and len(hand.cards) == 2 and tc >= 4:
                return "double"

            if not is_soft and not is_pair and total == 12 and dealer_up == 3 and tc >= 2:
                return "stand"

            if not is_soft and not is_pair and total == 12 and dealer_up == 2 and tc >= 3:
                return "stand"

            if not is_soft and total == 11 and dealer_up == 11 and len(hand.cards) == 2 and tc >= 1:
                return "double"

            if not is_soft and total == 9 and dealer_up == 2 and len(hand.cards) == 2 and tc >= 1:
                return "double"

            if not is_soft and total == 10 and dealer_up == 11 and len(hand.cards) == 2 and tc >= 4:
                return "double"

            if not is_soft and total == 9 and dealer_up == 7 and len(hand.cards) == 2 and tc >= 3:
                return "double"

            if not is_soft and not is_pair and total == 16 and dealer_up == 9 and tc >= 5:
                return "stand"

            # Negative deviations
            if not is_soft and not is_pair and total == 12 and dealer_up == 4 and tc < 0:
                return "hit"

            if not is_soft and not is_pair and total == 12 and dealer_up == 5 and tc < -2:
                return "hit"

            if not is_soft and not is_pair and total == 12 and dealer_up == 6 and tc < -1:
                return "hit"

            if not is_soft and not is_pair and total == 13 and dealer_up == 3 and tc < -2:
                return "hit"

            if not is_soft and not is_pair and total == 13 and dealer_up == 2 and tc < -1:
                return "hit"

        return basic_action


class HiLoBettingEngine:
    @staticmethod
    def get_bet(true_count, rules):
        tc = math.floor(true_count)

        if not rules.USE_BET_SPREAD:
            return rules.MIN_BET

        if tc <= 0:
            return rules.BET_RAMP["tc_le_0"]
        elif tc == 1:
            return rules.BET_RAMP["tc_1"]
        elif tc == 2:
            return rules.BET_RAMP["tc_2"]
        elif tc == 3:
            return rules.BET_RAMP["tc_3"]
        else:
            return rules.BET_RAMP["tc_ge_4"]

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
        self.insurance_bet = 0.0


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

    def __init__(self, bet=0, balance=1000, max_hands=Rules.MAX_HANDS, is_counter=False):
        Player._player_counter += 1
        self.id = Player._player_counter  # Assign a unique ID
        self.hands = [Hand(bet)]
        self.balance = balance
        self.max_hands = max_hands
        self.is_counter = is_counter

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

    def choice(self, hand, dealer_up_card, rules, dealer_peeked_no_blackjack, true_count):
        if self.is_counter and rules.COUNTING_ENABLED:
            return HiLoStrategyEngine.decide(
                hand=hand,
                dealer_up_card=dealer_up_card,
                rules=rules,
                current_hand_count=len(self.hands),
                dealer_peeked_no_blackjack=dealer_peeked_no_blackjack,
                true_count=true_count,
            )

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
        card = self.game_manager._get_card_with_reshuffle(visible=False)
        if card:
            self.dealer_hand.add_card(card)

    def __str__(self):
        player_hands_str = "\n".join([f"Player {p.id}:\n{p}" for p in self.players])
        return f"Dealer's Hand: {self.dealer_hand}\n{player_hands_str}"


# ============================================================
# GAME MANAGER (rules enforced here + verbose logging)
# ============================================================

class GameManager:
    def __init__(self, num_decks, num_players, rules=Rules, verbose=True):
        self.rules_name = rules.__name__
        self.run_id = self._get_next_run_id()
        self.rules = rules
        self.verbose = verbose

        self.num_decks = num_decks
        self.shoe = Shoe(num_decks)

        self.running_count = 0
        self.update_true_count()
        self.hole_card_revealed = False

        self.eliminated_players = []
        self.initial_shoe_size = len(self.shoe)
        self.reshuffle_threshold = int(self.initial_shoe_size * self.rules.RESHUFFLE_AT_REMAINING)

        self.dealer = Dealer(self.shoe, num_players, self)
        # Create players with unique IDs
        self.dealer.players = [Player(bet=0, balance=100000, max_hands=Rules.MAX_HANDS, is_counter=False) for _ in range(num_players)]
        self.starting_bankroll = 100000

        # Assign roles: Only Player 1 is a Counter, everyone else is Basic Strategy
        for i, player in enumerate(self.dealer.players):
            if i == 0:  # The first player (Index 0)
                player.is_counter = True
                self.log(f"Player {player.id} assigned as THE COUNTER.")
            else:
                player.is_counter = False
                self.log(f"Player {player.id} assigned as BASIC STRATEGY.")

        # optional: basic stats (extend for Monte Carlo later)
        self.stats = {"rounds": 0, "hands": 0, "wins": 0, "losses": 0, "busts": 0, "pushes": 0, "blackjacks": 0, "surrenders": 0}

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
            self.running_count = 0
            self.update_true_count()  # Derives 0.0 correctly from the fresh shoe
            self.hole_card_revealed = False  # Ensures the new round's hole card isn't "pre-revealed"

    def _get_card_with_reshuffle(self, visible=True):
        self._reshuffle_if_needed()
        card = self.shoe.deal()
        if card and visible:
            self.update_running_count(card)
        return card

    def place_bets(self):
        self.log("\n--- Placing Bets ---")
        self.log(f"TC at betting time: {self.true_count:.2f}")
        for player in self.dealer.players[:]:
            if player.is_counter and self.rules.COUNTING_ENABLED:
                bet_amount = HiLoBettingEngine.get_bet(self.true_count, self.rules)
            else:
                bet_amount = self.rules.MIN_BET

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

    def reveal_hole_card(self):
        # If it's already counted, stop.
        if self.hole_card_revealed:
            return

        if len(self.dealer.dealer_hand.cards) >= 2:
            hole_card = self.dealer.dealer_hand.cards[1]
            self.update_running_count(hole_card)
            self.hole_card_revealed = True

    def update_running_count(self, card):
        if not card or not getattr(self.rules, "COUNTING_ENABLED", False):
            return

        # 1. Update Running Count
        self.running_count += self.rules.HI_LO_TAGS.get(card["rank"], 0)

        # 2. Automatically refresh the True Count
        self.update_true_count()

    def estimate_decks_remaining(self):
        remaining = len(self.shoe)
        return max(remaining / 52.0, 0.25)  # avoid divide-by-zero / tiny numbers

    def update_true_count(self):
        decks_rem = self.estimate_decks_remaining()
        self.true_count = self.running_count / decks_rem

    def start_round(self):
        self.stats["rounds"] += 1
        self.hole_card_revealed = False
        self.log("\nStarting a new round...")


        self._reshuffle_if_needed()

        self.place_bets()
        if not self.dealer.players:
            self.log("No players left in the game. Ending round.")
            return

        self.dealer.dealer_hand = Hand()
        self.dealer.deal_initial_cards()

        # 1. Offer Insurance (Only if dealer shows Ace)
        if self.rules.INSURANCE_ENABLED and card_value_for_upcard(self.dealer.dealer_hand.cards[0]) == 11:
            self.offer_insurance()

        self.log("\n--- Initial Deal ---")
        self.log(str(self.dealer))

        # 2. Check for Dealer Blackjack (The "Peek") -
        dealer_bj = self.dealer_has_blackjack()

        if dealer_bj:
            self.log("\nDealer has Blackjack!")
            self.reveal_hole_card()
            self.settle_bets()
            return

        # 3. Player Turns
        self.handle_player_turns(dealer_peeked_no_blackjack=True)

        # 4. Reveal hole card for the count, then dealer plays
        self.reveal_hole_card()
        self.handle_dealer_turn()
        self.settle_bets()

        self.log("\nRound finished.")

    def offer_insurance(self):
        # only relevant if counting is enabled
        if not self.rules.COUNTING_ENABLED or not self.rules.USE_INSURANCE_INDEX:
            return

        take = (self.true_count >= self.rules.INSURANCE_TC_THRESHOLD)

        for player in self.dealer.players:
            if not getattr(player, "is_counter", False):
                continue  # basic-strategy player: never offered / never takes insurance

            for hand in player.hands:
                if len(hand.cards) != 2:
                    continue
                ins = 0.5 * hand.bet
                if take and player.balance >= ins:
                    player.balance -= ins
                    hand.insurance_bet = ins
                    self.log(f"Player {player.id} (COUNTER) takes insurance: {ins} (TC={self.true_count:.2f})")
                else:
                    hand.insurance_bet = 0.0
                    self.log(f"Player {player.id} (COUNTER) declines insurance (TC={self.true_count:.2f})")

    def handle_player_turns(self, dealer_peeked_no_blackjack):
        self.log("\n--- Player Turns ---")
        self.log(f"TC at betting time: {self.true_count:.2f}")
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
                    if player.is_counter:
                        self.log(f"  Counter decision using TC={self.true_count:.2f}")
                    decision = player.choice(
                        hand,
                        dealer_up_card,
                        self.rules,
                        dealer_peeked_no_blackjack,
                        self.true_count
                    )
                    self.log(f"  Decision: {decision}, value: {hand.get_value()}, cards: {len(hand.cards)}")
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
                        self.log("  Surrender.")
                        break



                    elif decision == "double":

                        if len(hand.cards) == 2 and player.balance >= hand.bet:

                            player.balance -= hand.bet

                            hand.bet *= 2

                            hand.doubled = True

                            card = self._get_card_with_reshuffle()

                            if card:
                                player.add_card_to_hand(card, hand_index)

                            hand = player.hands[hand_index]

                            self.log(f"  Double. New bet: {hand.bet}. Hand: {hand}")

                            if hand.get_value() > 21:
                                self.log("  Bust!")

                            break

                        else:

                            self.log("  Double not allowed (insufficient funds) -> Hit.")

                            card = self._get_card_with_reshuffle()

                            if card:
                                player.add_card_to_hand(card, hand_index)

                            hand = player.hands[hand_index]

                            if hand.get_value() > 21:
                                self.log("  Bust!")

                                break



                    elif decision == "split":

                        if player.balance < hand.bet:
                            self.log("  Split not allowed (insufficient funds) -> Stand.")

                            break

                        if player.split_hand(hand_index):

                            player.balance -= hand.bet

                            for i in [hand_index, hand_index + 1]:

                                card = self._get_card_with_reshuffle()

                                if card:
                                    player.add_card_to_hand(card, i)

                            self.log(f"  Split performed. Remaining balance: {player.balance}")

                            self.log(f"DEBUG: number of hands = {len(player.hands)}")

                            split_done = True

                            break

                        else:  # ← same indent as "if player.split_hand"

                            self.log("  Split not allowed (max hands) -> Stand.")

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
        dealer_bj = self.dealer_has_blackjack()
        active_players = []

        for player in self.dealer.players:
            self.log(f"\nPlayer {player.id} (Balance: {player.balance}):")
            for hand in player.hands:
                self.stats["hands"] += 1
                outcome = self.determine_outcome(hand, dealer_hand)
                bet = hand.bet

                # 1. Main Hand Settlement & Metrics
                if outcome == "blackjack":
                    self.stats["wins"] += 1
                    # self.stats["blackjacks"] is already handled in handle_player_turns
                    winnings = bet * (1 + self.rules.BLACKJACK_PAYOUT_PROFIT)
                    self.log(f"  Hand: BLACKJACK! Profit: +{bet * 1.5}")
                elif outcome == "win":
                    self.stats["wins"] += 1
                    winnings = bet * 2
                    self.log(f"  Hand: WIN. Profit: +{bet}")
                elif outcome == "push":
                    self.stats["pushes"] += 1
                    winnings = bet
                    self.log(f"  Hand: PUSH. Bet returned.")
                elif outcome == "surrender":
                    self.stats["surrenders"] += 1  # Track specifically
                    winnings = bet * 0.5
                    self.log(f"  Hand: SURRENDER. Loss: -{bet * 0.5}")
                elif outcome == "bust":
                    self.stats["busts"] += 1
                    winnings = 0
                    self.log(f"  Hand: : {outcome.upper()}. Bust -{bet}")
                else:
                    self.stats["losses"] += 1
                    winnings = 0
                    self.log(f"  Hand: {outcome.upper()}. Loss: -{bet}")

                player.balance += winnings

                # 2. Insurance Settlement
                if hand.insurance_bet > 0:
                    if dealer_bj:
                        # 3:1 total return (2:1 profit + stake back)
                        ins_payout = hand.insurance_bet * 2
                        player.balance += ins_payout
                        self.log(f"  [INSURANCE WIN] +{hand.insurance_bet * 2} profit.")
                    else:
                        self.log(f"  [INSURANCE LOSS] Dealer no BJ. Stake lost.")

                    # IMPORTANT: Reset for safety
                    hand.insurance_bet = 0.0

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

        # --- Export summary stats ---
        file_exists_summary = os.path.isfile("summary_stats.csv")
        with open("summary_stats.csv", "a", newline="") as f_sum:
            writer_sum = csv.DictWriter(f_sum, fieldnames=["Run ID", "Ruleset"] + list(self.stats.keys()))
            if not file_exists_summary:
                writer_sum.writeheader()
            writer_sum.writerow({"Run ID": self.run_id, "Ruleset": self.rules_name, **self.stats})

        # --- Export player stats ---
        file_exists_player = os.path.isfile("player_stats.csv")
        with open("player_stats.csv", "a", newline="") as f_play:
            fieldnames = ["Run ID", "Player ID", "Role", "Start Bankroll", "Final Balance", "Net Profit"]
            writer_play = csv.DictWriter(f_play, fieldnames=fieldnames)
            if not file_exists_player:
                writer_play.writeheader()

            all_players = self.dealer.players + self.eliminated_players
            for player in all_players:
                role = "Counter" if player.is_counter else "Basic"
                writer_play.writerow({
                    "Run ID": self.run_id,
                    "Player ID": player.id,
                    "Role": role,
                    "Start Bankroll": self.starting_bankroll,
                    "Final Balance": player.balance,
                    "Net Profit": player.balance - self.starting_bankroll
                })

            print("\nCSV files exported:")
            print(os.path.abspath("summary_stats.csv"))
            print(os.path.abspath("player_stats.csv"))



if __name__ == "__main__":
    num_decks = Rules.NUM_DECKS
    num_players = 6
    num_rounds = 10000

    selected_rules = FullHiLoRules
    game_manager = GameManager(num_decks, num_players, rules=selected_rules, verbose=True)
    game_manager.play_game(num_rounds)