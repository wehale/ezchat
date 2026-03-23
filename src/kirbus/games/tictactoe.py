"""Tic-tac-toe — two player, pure Python."""
from __future__ import annotations

from kirbus.games import BaseGame

_WINS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # cols
    (0, 4, 8), (2, 4, 6),              # diagonals
]


class TicTacToeGame(BaseGame):
    name        = "tictactoe"
    description = "Tic-tac-toe (2 players)"
    min_players = 2
    max_players = 2

    def __init__(self) -> None:
        self._board:   list[str] = [" "] * 9
        self._players: list[str] = []
        self._symbols: dict[str, str] = {}
        self._turn:    int = 0   # index into _players
        self._over:    bool = False

    def start(self, players: list[str]) -> str:
        self._players = players
        self._symbols = {players[0]: "X", players[1]: "O"}
        return (
            f"Tic-tac-toe: {players[0]} (X) vs {players[1]} (O)\n"
            f"{self._render()}\n"
            f"{players[0]}'s turn — reply with a number 1-9"
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        current = self._players[self._turn]
        other   = self._players[1 - self._turn]

        if sender != current:
            return [(sender, f"It's {current}'s turn, not yours.")]

        text = text.strip()
        if text.lower() in ("quit", "q"):
            self._over = True
            return [(p, "Game abandoned.") for p in self._players]

        if not text.isdigit() or not (1 <= int(text) <= 9):
            return [(sender, "Reply with a number 1-9.")]

        idx = int(text) - 1
        if self._board[idx] != " ":
            return [(sender, "That square is taken. Choose another.")]

        self._board[idx] = self._symbols[sender]
        board_str = self._render()

        winner = self._check_winner()
        if winner:
            self._over = True
            return [
                (current, f"{board_str}\nYou win! 🎉"),
                (other,   f"{board_str}\n{current} wins."),
            ]

        if " " not in self._board:
            self._over = True
            return [(p, f"{board_str}\nDraw!") for p in self._players]

        self._turn = 1 - self._turn
        next_player = self._players[self._turn]
        return [
            (current,     f"{board_str}\nGood move. {next_player}'s turn."),
            (next_player, f"{board_str}\nYour turn ({self._symbols[next_player]})."),
        ]

    @property
    def is_over(self) -> bool:
        return self._over

    def _render(self) -> str:
        b = self._board
        def cell(i): return b[i] if b[i] != " " else str(i + 1)
        return (
            f" {cell(0)} │ {cell(1)} │ {cell(2)} \n"
            f"───┼───┼───\n"
            f" {cell(3)} │ {cell(4)} │ {cell(5)} \n"
            f"───┼───┼───\n"
            f" {cell(6)} │ {cell(7)} │ {cell(8)} "
        )

    def _check_winner(self) -> str | None:
        for a, b, c in _WINS:
            if self._board[a] != " " and self._board[a] == self._board[b] == self._board[c]:
                return self._board[a]
        return None
