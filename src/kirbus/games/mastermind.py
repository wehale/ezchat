"""Mastermind — crack the secret color code."""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_COLORS = ["R", "G", "B", "Y", "O", "P"]  # Red, Green, Blue, Yellow, Orange, Purple
_COLOR_NAMES = {"R": "Red", "G": "Green", "B": "Blue", "Y": "Yellow", "O": "Orange", "P": "Purple"}
_CODE_LEN = 4
_MAX_GUESSES = 10


class MastermindGame(BaseGame):
    name        = "mastermind"
    description = "Mastermind"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._code: list[str] = []
        self._guesses: list[tuple[list[str], int, int]] = []  # (guess, exact, wrong_position)
        self._over = False
        self._player = ""

    def start(self, players: list[str]) -> str:
        self._player = players[0]
        self._code = [random.choice(_COLORS) for _ in range(_CODE_LEN)]
        colors = ", ".join(f"{k}={v}" for k, v in _COLOR_NAMES.items())
        return (
            "=== MASTERMIND ===\n"
            f"Crack the {_CODE_LEN}-color code in {_MAX_GUESSES} guesses.\n"
            f"Colors: {colors}\n\n"
            f"Enter {_CODE_LEN} letters, e.g.: RGBY\n"
            "* = right color, right position\n"
            "? = right color, wrong position\n"
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().upper()

        if text in ("QUIT", "Q"):
            self._over = True
            return [(sender, f"The code was: {' '.join(self._code)}\nGame over.")]

        if text == "HISTORY":
            return [(sender, self._history())]

        guess = [c for c in text if c in _COLORS]
        if len(guess) != _CODE_LEN:
            return [(sender, f"Enter exactly {_CODE_LEN} color letters ({', '.join(_COLORS)}).")]

        return [(sender, self._check_guess(guess))]

    @property
    def is_over(self) -> bool:
        return self._over

    def _check_guess(self, guess: list[str]) -> str:
        exact = sum(g == c for g, c in zip(guess, self._code))

        # Count wrong position
        code_counts: dict[str, int] = {}
        guess_counts: dict[str, int] = {}
        for g, c in zip(guess, self._code):
            if g != c:
                code_counts[c] = code_counts.get(c, 0) + 1
                guess_counts[g] = guess_counts.get(g, 0) + 1
        wrong_pos = sum(min(guess_counts.get(c, 0), code_counts.get(c, 0)) for c in _COLORS)

        self._guesses.append((guess, exact, wrong_pos))

        feedback = "*" * exact + "?" * wrong_pos + "-" * (_CODE_LEN - exact - wrong_pos)
        result = f"  {' '.join(guess)}  |  {feedback}"

        if exact == _CODE_LEN:
            self._over = True
            return (
                result + "\n\n"
                f"You cracked the code in {len(self._guesses)} guesses!"
            )

        if len(self._guesses) >= _MAX_GUESSES:
            self._over = True
            return (
                result + "\n\n"
                f"Out of guesses! The code was: {' '.join(self._code)}"
            )

        return result + f"\n  ({len(self._guesses)}/{_MAX_GUESSES} guesses)"

    def _history(self) -> str:
        if not self._guesses:
            return "No guesses yet."
        lines = ["Guess history:"]
        for i, (guess, exact, wrong) in enumerate(self._guesses):
            feedback = "*" * exact + "?" * wrong + "-" * (_CODE_LEN - exact - wrong)
            lines.append(f"  {i+1}. {' '.join(guess)}  |  {feedback}")
        lines.append(f"\n({len(self._guesses)}/{_MAX_GUESSES} guesses)")
        return "\n".join(lines)
