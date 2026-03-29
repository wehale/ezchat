"""Hangman — guess the word before you're hanged."""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_WORDS = [
    "python", "kirbus", "adventure", "treasure", "dungeon", "dragon",
    "castle", "wizard", "knight", "potion", "scroll", "goblin",
    "crystal", "shadow", "phoenix", "enchant", "cipher", "realm",
    "tavern", "bridge", "forest", "cavern", "portal", "mystic",
    "rogue", "arcane", "throne", "scepter", "amulet", "gargoyle",
    "labyrinth", "phantom", "serpent", "volcano", "glacier",
    "fortress", "basilisk", "centaur", "unicorn", "pegasus",
]

_STAGES = [
    "  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========",
    "  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========",
    "  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========",
    "  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========",
    "  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========",
    "  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========",
    "  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========",
]


class HangmanGame(BaseGame):
    name        = "hangman"
    description = "Hangman"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._word = ""
        self._guessed: set[str] = set()
        self._wrong: int = 0
        self._over = False
        self._player = ""

    def start(self, players: list[str]) -> str:
        self._player = players[0]
        self._word = random.choice(_WORDS)
        return (
            "=== HANGMAN ===\n"
            "Guess the word one letter at a time.\n"
            "You have 6 wrong guesses before you're hanged!\n\n"
            + self._display()
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().lower()

        if text in ("quit", "q"):
            self._over = True
            return [(sender, f"The word was: {self._word}\nGame over.")]

        if len(text) == 1 and text.isalpha():
            return [(sender, self._guess(text))]

        # Try full word guess
        if len(text) > 1 and text.isalpha():
            if text == self._word:
                self._over = True
                return [(sender, f"YES! The word is {self._word}!\n\nYou win!")]
            else:
                self._wrong += 1
                if self._wrong >= 6:
                    self._over = True
                    return [(sender, f"Wrong word!\n\n{_STAGES[6]}\n\nThe word was: {self._word}\nYou lose!")]
                return [(sender, f"'{text}' is not the word.\n\n" + self._display())]

        return [(sender, "Guess a letter (a-z) or the whole word.")]

    @property
    def is_over(self) -> bool:
        return self._over

    def _guess(self, letter: str) -> str:
        if letter in self._guessed:
            return f"Already guessed '{letter}'.\n\n" + self._display()

        self._guessed.add(letter)

        if letter in self._word:
            if all(c in self._guessed for c in self._word):
                self._over = True
                return f"'{letter}' — correct!\n\n  {self._word}\n\nYou win!"
            return f"'{letter}' — correct!\n\n" + self._display()
        else:
            self._wrong += 1
            if self._wrong >= 6:
                self._over = True
                return f"'{letter}' — wrong!\n\n{_STAGES[6]}\n\nThe word was: {self._word}\nYou lose!"
            return f"'{letter}' — wrong!\n\n" + self._display()

    def _display(self) -> str:
        word_display = " ".join(c if c in self._guessed else "_" for c in self._word)
        guessed_str = " ".join(sorted(self._guessed)) if self._guessed else "(none)"
        return (
            f"{_STAGES[self._wrong]}\n\n"
            f"  {word_display}\n\n"
            f"Guessed: {guessed_str}\n"
            f"Wrong: {self._wrong}/6"
        )
