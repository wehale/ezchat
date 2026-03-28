"""Rock Paper Scissors — single player vs the machine."""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_CHOICES = ("rock", "paper", "scissors")
_ALIASES = {
    "r": "rock", "p": "paper", "s": "scissors",
    "rock": "rock", "paper": "paper", "scissors": "scissors",
}
_BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
_ART = {
    "rock":     "    ___\n---'   ____)\n      (_____)\n      (_____)\n      (____)\n---.__(___)",
    "paper":    "     ___\n---'    __)\n           ____)\n          _____)\n         _____)\n---._________)",
    "scissors": "    ___\n---'   __)\n          ____)\n       __)\n      (__)\n---.__(_)",
}


class RPSGame(BaseGame):
    name        = "rps"
    description = "Rock Paper Scissors"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._player: str = ""
        self._score_player: int = 0
        self._score_machine: int = 0
        self._rounds: int = 0
        self._over: bool = False

    def start(self, players: list[str]) -> str:
        self._player = players[0]
        return (
            "Rock Paper Scissors — best of 5!\n"
            "Type: rock (r), paper (p), or scissors (s)\n"
            "Type 'quit' to end early."
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().lower()

        if text in ("quit", "q"):
            self._over = True
            return [(sender, self._final_score())]

        choice = _ALIASES.get(text)
        if not choice:
            return [(sender, "Type: rock (r), paper (p), or scissors (s)")]

        machine = random.choice(_CHOICES)
        self._rounds += 1

        result_art = f"You: {choice}  vs  Machine: {machine}"

        if choice == machine:
            result = "Draw!"
        elif _BEATS[choice] == machine:
            self._score_player += 1
            result = "You win this round!"
        else:
            self._score_machine += 1
            result = "Machine wins this round!"

        score = f"Score: You {self._score_player} - {self._score_machine} Machine"

        if self._score_player >= 3 or self._score_machine >= 3:
            self._over = True
            return [(sender,
                f"{result_art}\n{result}\n\n{self._final_score()}")]

        return [(sender,
            f"{result_art}\n{result}\n{score}\n\nRound {self._rounds + 1} — rock, paper, or scissors?")]

    @property
    def is_over(self) -> bool:
        return self._over

    def _final_score(self) -> str:
        if self._score_player > self._score_machine:
            verdict = "You win! Nice job."
        elif self._score_machine > self._score_player:
            verdict = "Machine wins. Better luck next time!"
        else:
            verdict = "It's a tie!"
        return (
            f"Final: You {self._score_player} - {self._score_machine} Machine\n"
            f"{verdict}"
        )
