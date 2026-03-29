"""Battleship — sink the computer's fleet."""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_SIZE = 8
_SHIPS = [("Carrier", 5), ("Battleship", 4), ("Cruiser", 3), ("Submarine", 3), ("Destroyer", 2)]


class BattleshipGame(BaseGame):
    name        = "battleship"
    description = "Battleship"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._enemy_board: list[list[str]] = []  # "." empty, "S" ship
        self._player_view: list[list[str]] = []  # "." unknown, "X" hit, "O" miss
        self._shots = 0
        self._hits = 0
        self._total_ship_cells = 0
        self._over = False
        self._player = ""

    def start(self, players: list[str]) -> str:
        self._player = players[0]
        self._enemy_board = [["." for _ in range(_SIZE)] for _ in range(_SIZE)]
        self._player_view = [["." for _ in range(_SIZE)] for _ in range(_SIZE)]

        for ship_name, ship_size in _SHIPS:
            self._place_ship(ship_size)
            self._total_ship_cells += ship_size

        return (
            "=== BATTLESHIP ===\n"
            f"Sink all {len(_SHIPS)} ships on the {_SIZE}x{_SIZE} grid.\n"
            "Fire by entering coordinates like: A3, B7, H1\n"
            "Columns: A-H, Rows: 1-8\n\n"
            + self._display()
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().lower()
        if text in ("quit", "q"):
            self._over = True
            return [(sender, f"Game over. You fired {self._shots} shots.\n\n" + self._reveal())]
        if text in ("board", "map"):
            return [(sender, self._display())]

        coord = self._parse_coord(text)
        if coord is None:
            return [(sender, "Enter coordinates like: A3, B7, H1 (or 'quit')")]

        row, col = coord
        return [(sender, self._fire(row, col))]

    @property
    def is_over(self) -> bool:
        return self._over

    def _place_ship(self, size: int) -> None:
        for _ in range(100):
            horizontal = random.choice([True, False])
            if horizontal:
                row = random.randint(0, _SIZE - 1)
                col = random.randint(0, _SIZE - size)
                if all(self._enemy_board[row][col + i] == "." for i in range(size)):
                    for i in range(size):
                        self._enemy_board[row][col + i] = "S"
                    return
            else:
                row = random.randint(0, _SIZE - size)
                col = random.randint(0, _SIZE - 1)
                if all(self._enemy_board[row + i][col] == "." for i in range(size)):
                    for i in range(size):
                        self._enemy_board[row + i][col] = "S"
                    return

    def _parse_coord(self, text: str) -> tuple[int, int] | None:
        text = text.strip().upper()
        if len(text) < 2 or len(text) > 2:
            return None
        col_ch, row_ch = text[0], text[1]
        if col_ch < "A" or col_ch > chr(ord("A") + _SIZE - 1):
            return None
        if not row_ch.isdigit() or int(row_ch) < 1 or int(row_ch) > _SIZE:
            return None
        return int(row_ch) - 1, ord(col_ch) - ord("A")

    def _fire(self, row: int, col: int) -> str:
        if self._player_view[row][col] != ".":
            return "Already fired there.\n\n" + self._display()

        self._shots += 1

        if self._enemy_board[row][col] == "S":
            self._player_view[row][col] = "X"
            self._hits += 1
            if self._hits >= self._total_ship_cells:
                self._over = True
                return (
                    f"HIT! You sank the last ship!\n\n"
                    f"You win in {self._shots} shots!\n\n"
                    + self._display()
                )
            return f"HIT!\n\n" + self._display()
        else:
            self._player_view[row][col] = "O"
            return f"Miss.\n\n" + self._display()

    def _display(self) -> str:
        cols = "  " + " ".join(chr(ord("A") + i) for i in range(_SIZE))
        lines = [cols]
        for r in range(_SIZE):
            row_str = f"{r+1} " + " ".join(self._player_view[r])
            lines.append(row_str)
        lines.append(f"\nShots: {self._shots}  Hits: {self._hits}/{self._total_ship_cells}")
        return "\n".join(lines)

    def _reveal(self) -> str:
        cols = "  " + " ".join(chr(ord("A") + i) for i in range(_SIZE))
        lines = ["Enemy fleet:", cols]
        for r in range(_SIZE):
            row_str = f"{r+1} " + " ".join(self._enemy_board[r])
            lines.append(row_str)
        return "\n".join(lines)
