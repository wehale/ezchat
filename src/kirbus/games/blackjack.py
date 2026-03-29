"""Blackjack — beat the dealer to 21."""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_SUITS = ["♠", "♥", "♦", "♣"]
_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def _card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def _hand_value(hand: list[tuple[str, str]]) -> int:
    total = sum(_card_value(r) for r, _ in hand)
    aces = sum(1 for r, _ in hand if r == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def _show_hand(hand: list[tuple[str, str]]) -> str:
    return "  ".join(f"{r}{s}" for r, s in hand)


class BlackjackGame(BaseGame):
    name        = "blackjack"
    description = "Blackjack"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._deck: list[tuple[str, str]] = []
        self._player_hand: list[tuple[str, str]] = []
        self._dealer_hand: list[tuple[str, str]] = []
        self._chips = 100
        self._bet = 0
        self._over = False
        self._state = "betting"  # "betting" | "playing" | "done"
        self._player_name = ""

    def start(self, players: list[str]) -> str:
        self._player_name = players[0]
        return (
            "=== BLACKJACK ===\n"
            f"You have {self._chips} chips.\n"
            "Place your bet (1-100), or 'quit' to leave."
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().lower()
        if text in ("quit", "q"):
            self._over = True
            return [(sender, f"You leave with {self._chips} chips.")]

        if self._state == "betting":
            return [(sender, self._place_bet(text))]
        elif self._state == "playing":
            return [(sender, self._play(text))]
        else:
            return [(sender, self._new_round(text))]

    @property
    def is_over(self) -> bool:
        return self._over

    def _place_bet(self, text: str) -> str:
        if not text.isdigit():
            return f"Place a bet (1-{self._chips}), or 'quit'."
        bet = int(text)
        if bet < 1 or bet > self._chips:
            return f"Bet must be between 1 and {self._chips}."

        self._bet = bet
        self._deck = [(r, s) for s in _SUITS for r in _RANKS]
        random.shuffle(self._deck)

        self._player_hand = [self._deck.pop(), self._deck.pop()]
        self._dealer_hand = [self._deck.pop(), self._deck.pop()]

        pv = _hand_value(self._player_hand)
        if pv == 21:
            self._chips += int(self._bet * 1.5)
            self._state = "done"
            return (
                f"Dealer: {self._dealer_hand[0][0]}{self._dealer_hand[0][1]}  ??\n"
                f"You:    {_show_hand(self._player_hand)} ({pv})\n\n"
                f"BLACKJACK! You win {int(self._bet * 1.5)} chips!\n"
                f"Chips: {self._chips}\n\n"
                "Press enter to play again, or 'quit'."
            )

        self._state = "playing"
        return (
            f"Dealer: {self._dealer_hand[0][0]}{self._dealer_hand[0][1]}  ??\n"
            f"You:    {_show_hand(self._player_hand)} ({pv})\n\n"
            "Hit (h) or Stand (s)?"
        )

    def _play(self, text: str) -> str:
        if text in ("hit", "h"):
            self._player_hand.append(self._deck.pop())
            pv = _hand_value(self._player_hand)
            if pv > 21:
                self._chips -= self._bet
                self._state = "done"
                if self._chips <= 0:
                    self._over = True
                    return (
                        f"You:    {_show_hand(self._player_hand)} ({pv})\n\n"
                        "BUST! You're out of chips. Game over."
                    )
                return (
                    f"You:    {_show_hand(self._player_hand)} ({pv})\n\n"
                    f"BUST! You lose {self._bet} chips.\n"
                    f"Chips: {self._chips}\n\n"
                    "Press enter to play again, or 'quit'."
                )
            if pv == 21:
                return self._dealer_turn()
            return (
                f"Dealer: {self._dealer_hand[0][0]}{self._dealer_hand[0][1]}  ??\n"
                f"You:    {_show_hand(self._player_hand)} ({pv})\n\n"
                "Hit (h) or Stand (s)?"
            )
        elif text in ("stand", "s", ""):
            return self._dealer_turn()
        return "Hit (h) or Stand (s)?"

    def _dealer_turn(self) -> str:
        while _hand_value(self._dealer_hand) < 17:
            self._dealer_hand.append(self._deck.pop())

        dv = _hand_value(self._dealer_hand)
        pv = _hand_value(self._player_hand)

        result = (
            f"Dealer: {_show_hand(self._dealer_hand)} ({dv})\n"
            f"You:    {_show_hand(self._player_hand)} ({pv})\n\n"
        )

        if dv > 21:
            self._chips += self._bet
            result += f"Dealer busts! You win {self._bet} chips!"
        elif pv > dv:
            self._chips += self._bet
            result += f"You win {self._bet} chips!"
        elif dv > pv:
            self._chips -= self._bet
            result += f"Dealer wins. You lose {self._bet} chips."
        else:
            result += "Push — bet returned."

        self._state = "done"
        if self._chips <= 0:
            self._over = True
            return result + "\nYou're out of chips. Game over."

        return result + f"\nChips: {self._chips}\n\nPress enter to play again, or 'quit'."

    def _new_round(self, text: str) -> str:
        self._state = "betting"
        return f"Chips: {self._chips}\nPlace your bet (1-{self._chips}), or 'quit'."
