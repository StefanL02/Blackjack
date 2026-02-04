import random


class DeckOfCards:
    def __init__(self):
        self.cards = []
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
        for suit in suits:
            for rank in ranks:
                self.cards.append({'rank': rank, 'suit': suit})  # Changed to store rank and suit as a dictionary

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self):
        if len(self.cards) == 0:
            return None
        return self.cards.pop()

    def __len__(self):
        return len(self.cards)

    def __str__(self):
        return f'Deck of {len(self.cards)} cards'


class Shoe:
    def __init__(self, num_decks):
        self.decks = []
        for _ in range(num_decks):
            deck = DeckOfCards()
            self.decks.append(deck)
        self.all_cards = []
        for deck in self.decks:
            self.all_cards.extend(deck.cards)
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.all_cards)

    def deal(self):
        if len(self.all_cards) == 0:
            return None
        return self.all_cards.pop()

    def __len__(self):
        return len(self.all_cards)

    def __str__(self):
        return f'Shoe with {len(self.all_cards)} cards from {len(self.decks)} decks'


class Hand:
    def __init__(self, bet=0):
        self.cards = []
        self.bet = bet

    def add_card(self, card):
        self.cards.append(card)

    def get_value(self):

        value = 0
        for card in self.cards:
            if card['rank'].isdigit():
                value += int(card['rank'])
            elif card['rank'] in ['Jack', 'Queen', 'King']:
                value += 10
            elif card['rank'] == 'Ace':
                value += 11  # Assume Ace is 11 initially, can be adjusted later if needed

        # Adjust for Aces if value is over 21
        num_aces = sum(1 for card in self.cards if card['rank'] == 'Ace')
        while value > 21 and num_aces > 0:
            value -= 10
            num_aces -= 1

        return value

    def is_soft_17(self):
        value = self.get_value()
        if value == 17:
            # Check if there's an Ace that's currently counted as 11
            num_aces = 0
            for card in self.cards:
                if card['rank'] == 'Ace':
                    num_aces += 1
            # If there's an Ace and the current value is 17, it's a soft 17
            # unless all Aces are already counted as 1 to keep value <= 21.
            # The get_value() method already handles reducing Ace value from 11 to 1.
            # So, if value is 17 and there's an Ace, it must be a soft 17.
            # A hard 17 would not have an Ace that can be reduced to change the value.
            initial_value_with_aces_as_11 = 0
            for card in self.cards:
                if card['rank'].isdigit():
                    initial_value_with_aces_as_11 += int(card['rank'])
                elif card['rank'] in ['Jack', 'Queen', 'King']:
                    initial_value_with_aces_as_11 += 10
                elif card['rank'] == 'Ace':
                    initial_value_with_aces_as_11 += 11

            return (initial_value_with_aces_as_11 > 17 and value == 17 and num_aces > 0)
        return False

    def __str__(self):
        cards_str = ', '.join([f"{card['rank']} of {card['suit']}" for card in self.cards])
        return f'Hand: [{cards_str}], Bet: {self.bet}'


class Player:
    def __init__(self, bet=0, balance=1000, max_hands=4):
        self.hands = [Hand(bet)]  # A player can have multiple hands after splitting
        self.balance = balance  # Store the balance
        self.max_hands = max_hands  # Store the maximum number of hands allowed

    def add_card_to_hand(self, card, hand_index=0):
        """Adds a card to a specific hand."""
        if 0 <= hand_index < len(self.hands):
            self.hands[hand_index].add_card(card)
        else:
            print(f"Error: Hand index {hand_index} is out of range.")

    def split_hand(self, hand_index=0):
        """Splits a hand if possible (requires two cards of the same rank)."""
        if 0 <= hand_index < len(self.hands):
            hand_to_split = self.hands[hand_index]

            # Check if splitting would exceed the maximum allowed hands
            if len(self.hands) >= self.max_hands:
                print(f"Player already has {len(self.hands)} hands. Cannot split further.")
                return False  # Indicate that split was not performed

            if len(hand_to_split.cards) == 2 and hand_to_split.cards[0]['rank'] == hand_to_split.cards[1]['rank']:
                # Create two new hands
                new_hand1 = Hand(hand_to_split.bet)
                new_hand1.add_card(hand_to_split.cards[0])

                new_hand2 = Hand(hand_to_split.bet)
                new_hand2.add_card(hand_to_split.cards[1])

                # Remove the original hand and add the two new hands
                self.hands.pop(hand_index)
                self.hands.insert(hand_index,
                                  new_hand2)  # Insert in reverse order to maintain potential processing order
                self.hands.insert(hand_index, new_hand1)

                print(f"Hand {hand_index + 1} split into two hands.")
                return True  # Indicate that split was successful
            else:
                print(f"Hand {hand_index + 1} cannot be split.")
                return False  # Indicate that split was not performed
        else:
            print(f"Error: Hand index {hand_index} is out of range.")
            return False  # Indicate that split was not performed

    def choice(self, hand, dealer_up_card):
        """
        Determines the player's choice based on their hand and the dealer's up card.
        Includes basic splitting strategy and late surrender.
        """
        player_value = hand.get_value()
        dealer_up_value = 0
        if dealer_up_card and dealer_up_card['rank'].isdigit():
            dealer_up_value = int(dealer_up_card['rank'])
        elif dealer_up_card and dealer_up_card['rank'] in ['Jack', 'Queen', 'King']:
            dealer_up_value = 10
        elif dealer_up_card and dealer_up_card['rank'] == 'Ace':
            dealer_up_value = 11  # Assume Ace is 11 for dealer up card comparison

        # Late Surrender Strategy (Basic) - Can only surrender on the initial two cards
        if len(hand.cards) == 2:
            if player_value == 15 and dealer_up_value == 10:
                return "surrender"  # Surrender 15 against a dealer 10
            elif player_value == 16 and dealer_up_value in [9, 10, 11]:
                return "surrender"  # Surrender 16 against a dealer 9, 10, or Ace

        # Splitting Strategy (Basic) - Only if not surrendering
        if len(hand.cards) == 2 and hand.cards[0]['rank'] == hand.cards[1]['rank']:
            rank = hand.cards[0]['rank']
            if rank in ['Ace', '8']:
                return "split"  # Always split Aces and 8s
            elif rank in ['2', '3', '7'] and 2 <= dealer_up_value <= 7:
                return "split"  # Split 2s, 3s, 7s against dealer 2-7
            elif rank in ['4'] and dealer_up_value in [5, 6]:
                return "split"  # Split 4s against dealer 5-6
            elif rank in ['6'] and 2 <= dealer_up_value <= 6:
                return "split"  # Split 6s against dealer 2-6
            elif rank in ['9'] and dealer_up_value not in [7, 10, 11]:
                return "split"  # Split 9s against dealer 2-6, 8-9

        # Doubling Down Strategy (Basic) - Can only double on initial two cards
        if len(hand.cards) == 2:
            # Soft hand double down: Soft 16, 17, 18 vs dealer 4, 5, 6
            # This implicitly checks for Ace in hand due to player_value calculation and len(hand.cards) == 2
            if player_value in [16, 17, 18] and dealer_up_value in [4, 5, 6]:
                return "double"
            # Hard hand double down
            elif player_value == 9 and dealer_up_value in [3, 4, 5, 6]:
                return "double"
            elif player_value == 10 and dealer_up_value not in [10, 11]:
                return "double"
            elif player_value == 11 and dealer_up_value not in [11]:
                return "double"

        # Basic hit/stand logic if not surrendering, splitting, or doubling
        if player_value < 17:
            return "hit"
        else:
            return "stand"

    def __str__(self):
        hands_str = "\n".join([f"  Hand {i + 1}: {hand}" for i, hand in enumerate(self.hands)])
        return f"Player Hands:\n{hands_str}\nBalance: {self.balance}"  # Added balance to the string representation


class Dealer:
    def __init__(self, shoe, num_players, game_manager):  # Added game_manager
        self.shoe = shoe
        self.players = [Player(bet=0) for _ in range(num_players)]  # Use the new Player class
        self.dealer_hand = Hand()
        self.game_manager = game_manager  # Store reference to game_manager

    def deal_initial_cards(self):
        # Deal first card to each player and dealer
        for i, player in enumerate(self.players):
            card = self.game_manager._get_card_with_reshuffle()
            if card:
                player.add_card_to_hand(card)
            else:
                pass
        card = self.game_manager._get_card_with_reshuffle()  # Dealer gets first card
        if card:
            self.dealer_hand.add_card(card)
        else:
            pass

        # Deal second card to each player and dealer
        for i, player in enumerate(self.players):
            card = self.game_manager._get_card_with_reshuffle()
            if card:
                player.add_card_to_hand(card)
            else:
                pass
        card = self.game_manager._get_card_with_reshuffle()  # Dealer gets second card
        if card:
            self.dealer_hand.add_card(card)
        else:
            pass

    def deal_card_to_player(self, player_index, hand_index):
        """Deals a card to a specific hand of a specific player."""
        if 0 <= player_index < len(self.players):
            player = self.players[player_index]
            card = self.game_manager._get_card_with_reshuffle()
            if card:
                player.add_card_to_hand(card, hand_index)
                print(f"Dealt {card['rank']} of {card['suit']} to Player {player_index + 1}, Hand {hand_index + 1}")
            else:
                print("Shoe is empty. Cannot deal more cards.")
        else:
            print(f"Error: Player index {player_index} is out of range.")

    def __str__(self):
        player_hands_str = "\n".join([f"Player {i + 1}:\n{player}" for i, player in enumerate(self.players)])
        return f"Dealer's Hand: {self.dealer_hand}\n{player_hands_str}"


class GameManager:
    def __init__(self, num_decks, num_players):
        self.num_decks = num_decks  # Store the initial number of decks
        self.shoe = Shoe(num_decks)
        self.eliminated_players = []  # Add a list to store eliminated players
        self.reshuffle_threshold_percentage = 25  # Reshuffle when 25% of cards remain
        self.initial_shoe_size = len(self.shoe)  # Store the initial size of the shoe
        self.reshuffle_threshold = int(self.initial_shoe_size * (
                    self.reshuffle_threshold_percentage / 100))  # Calculate the reshuffle threshold in cards
        # Pass max_hands=4 to the Player constructor when creating players
        self.dealer = Dealer(self.shoe, num_players, self)  # Pass self (GameManager instance) to Dealer
        self.dealer.players = [Player(bet=0, max_hands=4) for _ in
                               range(num_players)]  # Re-initialize players with max_hands

    def _get_card_with_reshuffle(self):
        """Checks if reshuffle is needed, performs it if so, and then deals a card."""

        if len(self.shoe) < self.reshuffle_threshold:
            print("\n--- Reshuffling Shoe ---")
            self.shoe = Shoe(self.num_decks)
            self.initial_shoe_size = len(self.shoe)
            self.reshuffle_threshold = int(self.initial_shoe_size * (self.reshuffle_threshold_percentage / 100))
            self.dealer.shoe = self.shoe  # IMPORTANT: Update the dealer's direct shoe reference to the new one
            print(f"Shoe reshuffled. New shoe size: {len(self.shoe)}")

        card = self.shoe.deal()
        return card

    def place_bets(self):
        print("\n--- Placing Bets ---")
        # Iterate over a copy of the players list to safely handle potential removal during betting
        for i, player in enumerate(self.dealer.players[:]):
            # For now, a fixed bet of 10. This can be made interactive later.
            bet_amount = 10
            print(f"Player {i + 1}: Current balance is {player.balance}, attempting to bet {bet_amount}.")
            if player.balance >= bet_amount:
                player.hands = [Hand(bet_amount)]  # Reset hands and set the bet
                player.balance -= bet_amount  # Deduct the bet from the player's balance
                print(f"Player {i + 1} placed a bet of {bet_amount}. Remaining balance: {player.balance}")
            else:
                # If insufficient funds, remove the player from the game for this round
                print(f"Player {i + 1} does not have enough funds to place a bet of {bet_amount}. Player eliminated.")
                self.eliminated_players.append(player)  # Add eliminated player to the new list
                self.dealer.players.remove(player)  # Remove the player directly if iterating over a copy

    def start_round(self):
        print("\nStarting a new round...")
        # Clear previous hands and reset bets for remaining players
        # The place_bets method now handles resetting hands and setting bets

        # Place bets and eliminate players with insufficient funds
        self.place_bets()

        # Check if any players are still in the game after placing bets
        if not self.dealer.players:
            print("No players left in the game. Ending round.")
            return

        # Ensure the Dealer's shoe reference is always synchronized with GameManager's shoe before any dealing
        self.dealer.shoe = self.shoe  # IMPORTANT: Synchronize dealer's shoe reference

        # Check if reshuffle is needed before starting a new round
        if len(self.shoe) < self.reshuffle_threshold:
            print("\n--- Reshuffling Shoe ---")
            self.shoe = Shoe(self.num_decks)  # Create a new shoe with the stored number of decks
            self.initial_shoe_size = len(self.shoe)  # Update initial shoe size
            self.reshuffle_threshold = int(
                self.initial_shoe_size * (self.reshuffle_threshold_percentage / 100))  # Recalculate threshold
            self.dealer.shoe = self.shoe  # IMPORTANT: Update the dealer's direct shoe reference to the new one
            print(f"Shoe reshuffled. New shoe size: {len(self.shoe)}")

        # Reset dealer hand for the new round
        self.dealer.dealer_hand = Hand()

        # print(str(self.dealer)) # Diagnostic print

        self.dealer.deal_initial_cards()  # Deal initial cards

        print("\n--- Initial Deal (Post-deal state) ---")
        print(str(self.dealer))  # Diagnostic print - THIS SHOULD HAVE CARDS IF DEALING WORKED

        # Check for dealer blackjack immediately after dealing initial cards
        if self.dealer.dealer_hand.get_value() == 21 and len(self.dealer.dealer_hand.cards) == 2:
            print("\nDealer has Blackjack!")
            # If dealer has blackjack, skip player turns and dealer turn, go straight to settling bets.
            # Outcomes for players (lose unless they also have blackjack for a push) will be handled in settle_bets.
        else:
            # Only handle player turns and dealer turn if dealer does NOT have blackjack
            self.handle_player_turns()

            # Handle dealer's turn
            self.handle_dealer_turn()

        # Settle bets and determine outcomes for remaining players
        self.settle_bets()

        # Elimination of players with zero or less balance is now handled in settle_bets or implicitly by not being included in the next round's place_bets
        print("\nRound finished.")
        print(str(self.dealer))

    def handle_player_turns(self):
        print("\n--- Player Turns ---")
        # Iterate over the actual players list as it's now updated after betting
        for player_index, player in enumerate(self.dealer.players):
            print(f"\nPlayer {player_index + 1}'s turn:")
            # Iterate through a copy of the hands list because splitting modifies the list
            hand_index = 0
            while hand_index < len(player.hands):
                hand = player.hands[hand_index]
                print(f"  Hand {hand_index + 1}: {hand}")

                # Check for immediate Blackjack (optional, but good for realism)
                if hand.get_value() == 21 and len(hand.cards) == 2:
                    print("  Blackjack!")
                    hand_index += 1
                    continue  # Move to the next hand

                # Check if the hand has already busted or stood in a previous hit/double
                if hand.get_value() > 21:
                    print("  Bust!")
                    hand_index += 1
                    continue  # Move to the next hand

                while hand.get_value() < 21:
                    # Pass the current hand and the dealer's up card to the player's choice method
                    # Add a check to ensure dealer_hand.cards is not empty
                    dealer_up_card = self.dealer.dealer_hand.cards[0] if self.dealer.dealer_hand.cards else None
                    decision = player.choice(hand, dealer_up_card)
                    if decision == 'hit':
                        card = self._get_card_with_reshuffle()
                        if card:
                            player.add_card_to_hand(card, hand_index)
                            print(
                                f"  Dealt {card['rank']} of {card['suit']} to Player {player_index + 1}, Hand {hand_index + 1}")
                            print(f"  Hand {hand_index + 1}: {hand}")  # Show hand after hitting
                            if hand.get_value() > 21:
                                print("  Bust!")
                                break  # Exit the inner while loop if busted
                        else:
                            print("  Shoe is empty. Cannot deal more cards.")
                            break  # Exit the inner while loop if shoe is empty
                    elif decision == 'stand':
                        print("  Standing on this hand.")
                        break  # Exit the inner while loop
                    elif decision == 'surrender':
                        print("  Player surrenders.")
                        hand.surrendered = True  # Mark the hand as surrendered
                        break  # Exit the inner while loop as the hand is finished
                    elif decision == 'split':
                        # The player.split_hand method now handles checking max_hands
                        if player.split_hand(hand_index):
                            # Only proceed if split was successful (i.e., not over max_hands)
                            if player.balance >= hand.bet:  # Check if player has enough for the new hand's bet
                                player.balance -= hand.bet  # Deduct the bet for the new hand
                                self.dealer.deal_card_to_player(player_index, hand_index)  # Deal to the first new hand
                                self.dealer.deal_card_to_player(player_index,
                                                                hand_index + 1)  # Deal to the second new hand
                                print(
                                    f"  Player {player_index + 1} split Hand {hand_index + 1}. Remaining balance: {player.balance}")
                                hand = player.hands[hand_index]  # Update hand reference to the first new hand
                                print(f"  New Hand {hand_index + 1}: {hand}")
                            else:
                                print(
                                    "  Insufficient balance to place bet for split hand. Player will stand on this hand.")
                                break  # Cannot split if insufficient funds, so force stand
                        else:
                            # If split_hand returned False (e.g., due to max_hands limit or invalid split)
                            print("  Cannot split this hand further. Player will stand on this hand.")
                            break  # Force stand if cannot split
                    elif decision == 'double':
                        if len(hand.cards) == 2:  # Can usually only double on initial two cards
                            if player.balance >= hand.bet:
                                player.balance -= hand.bet  # Deduct the additional bet for doubling
                                hand.bet *= 2
                                self.dealer.deal_card_to_player(player_index, hand_index)
                                print(
                                    f"  Doubled down on Hand {hand_index + 1}. New bet: {hand.bet}. Remaining balance: {player.balance}")
                                print(f"  Hand {hand_index + 1}: {hand}")  # Show hand after doubling
                                if hand.get_value() > 21:
                                    print("  Bust!")
                                break  # After doubling, the player's turn for this hand is over
                            else:
                                print("  Insufficient balance to double down. Player will stand.")
                                break  # Force stand if cannot double.
                        else:
                            print("  Cannot double down on this hand. Player will stand.")
                            break  # Force stand if not 2 cards.
                    else:
                        print(f"  Invalid decision '{decision}'. Player must hit, stand, surrender, split, or double.")
                        print("  Standing on this hand.")
                        break  # Exit the inner while loop

                hand_index += 1  # Move to the next hand

    def handle_dealer_turn(self):
        print("\n--- Dealer's Turn ---")
        dealer_hand = self.dealer.dealer_hand
        print(f"Dealer's Hand: {dealer_hand}")

        # Dealer hits until value is 17 or more, but hits on soft 17
        while dealer_hand.get_value() < 17 or (dealer_hand.get_value() == 17 and dealer_hand.is_soft_17()):
            card = self._get_card_with_reshuffle()
            if card:
                dealer_hand.add_card(card)
                print(f"Dealer hits: {card['rank']} of {card['suit']}")
                print(f"Dealer's Hand: {dealer_hand}")
                if dealer_hand.get_value() > 21:
                    print("Dealer busts!")
                    break
            else:
                print("Shoe is empty. Dealer cannot hit.")
                break

    def determine_outcome(self, player_hand, dealer_hand):
        """Determines the outcome of a single hand."""
        # Check if the hand was surrendered
        if hasattr(player_hand, 'surrendered') and player_hand.surrendered:
            return "surrender"

        player_value = player_hand.get_value()
        dealer_value = dealer_hand.get_value()

        if player_value > 21:
            return "bust"
        elif dealer_value > 21:
            return "win"  # Player wins if dealer busts
        elif player_value == 21 and len(player_hand.cards) == 2 and not (
                dealer_value == 21 and len(dealer_hand.cards) == 2):
            return "blackjack"  # Player has blackjack and dealer doesn't
        elif dealer_value == 21 and len(dealer_hand.cards) == 2 and not (
                player_value == 21 and len(player_hand.cards) == 2):
            return "lose"  # Dealer has blackjack and player doesn't
        elif player_value > dealer_value:
            return "win"
        elif player_value < dealer_value:
            return "lose"
        else:
            return "push"  # Player and dealer have the same value

    def settle_bets(self):
        print("\n--- Settling Bets ---")
        dealer_hand = self.dealer.dealer_hand
        active_players = []
        for player_index, player in enumerate(self.dealer.players):  # Iterate with index for cleaner output
            print(f"\nPlayer {player_index + 1} (Balance: {player.balance}):")  # Include initial balance for clarity
            for hand_index, hand in enumerate(player.hands):
                outcome = self.determine_outcome(hand, dealer_hand)
                bet = hand.bet
                winnings = 0
                outcome_message = f"  Hand {hand_index + 1} ({hand}):\n    Outcome: {outcome}"  # Start with hand and outcome, move outcome to new line

                if outcome == "win":
                    winnings = bet * 2
                    outcome_message += f", Payout: {bet}"
                elif outcome == "blackjack":
                    winnings = bet * 2.5
                    outcome_message += f", Payout: {bet * 1.5}"
                elif outcome == "push":
                    winnings = bet
                    outcome_message += ", Bet returned."
                elif outcome == "bust":
                    winnings = 0
                    outcome_message += ", Bet lost."
                elif outcome == "lose":
                    winnings = 0
                    outcome_message += ", Bet lost."
                elif outcome == "surrender":
                    winnings = bet * 0.5
                    player.balance += winnings  # Return half the bet immediately for surrender
                    outcome_message += f", Half bet returned: {winnings}"
                    print(outcome_message)  # Print surrender outcome and move to the next hand
                    continue

                player.balance += winnings  # Add winnings (or 0 for loss/bust) to the balance for other outcomes
                outcome_message += f". New balance: {player.balance}"  # Add new balance to the message
                print(outcome_message)  # Print the consolidated outcome message

            # Check if player is eliminated after all their hands are settled
            if player.balance > 0:
                active_players.append(player)
            else:
                print(f"\nPlayer {player_index + 1} has been eliminated with a balance of {player.balance}.")
                self.eliminated_players.append(player)

        self.dealer.players = active_players  # Update the players list to include only active players

    def play_game(self, num_rounds=5):
        """Plays multiple rounds of Blackjack."""
        round_num = 1
        while self.dealer.players and round_num <= num_rounds:
            print(f"\n===== Round {round_num} ====")
            self.start_round()
            round_num += 1

        print("\n===== Game Over =====")
        if not self.dealer.players:
            print("All players have been eliminated.")
        else:
            print(f"\nFinished {num_rounds} rounds.")
            print("Final Player Balances:")
            for i, player in enumerate(self.dealer.players):
                print(f"Player {i + 1}: {player.balance}")

        if self.eliminated_players:
            print("\nEliminated Players (Final Balance):")
            # Sort eliminated players by their original index if needed, for now just list them
            for i, player in enumerate(self.eliminated_players):
                print(
                    f"Eliminated Player {i + 1}: {player.balance}")  # Note: Index here is just order of elimination, not original player number


# --- Entry Point ---

if __name__ == "__main__":
    num_decks = 6
    num_players = 5
    num_rounds = 1000

    game_manager = GameManager(num_decks, num_players)
    game_manager.play_game(num_rounds)
