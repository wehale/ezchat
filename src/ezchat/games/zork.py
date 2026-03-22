"""Zork game — wraps the Jericho Z-machine interpreter.

Requires:  pip install jericho
Also needs a Zork .z5 game file.  Free/legal sources:
  - Zork I:   https://www.infocom-if.org/downloads/zork1.zip
  - Place the .z5 file at ~/.ezchat/games/zork1.z5
    or set EZCHAT_ZORK_FILE env var to its path.
"""
from __future__ import annotations

import os
from pathlib import Path

from ezchat.games import BaseGame

_DEFAULT_PATHS = [
    Path.home() / ".ezchat" / "games" / "zork1.z5",
    Path.home() / ".ezchat" / "games" / "zork1.z3",
    Path.home() / ".ezchat" / "games" / "zork.z5",
    Path.home() / ".ezchat" / "games" / "zork.z3",
    Path("/usr/share/games/zork/zork1.z5"),
    Path("/usr/share/games/zork/zork1.z3"),
]

_INSTALL_MSG = (
    "Zork requires the 'jericho' package and a Zork game file.\n"
    "Install jericho:  pip install jericho\n"
    "Get the game file: download zork1.z5 and place it at ~/.ezchat/games/zork1.z5"
)


def _find_game_file() -> Path | None:
    env = os.environ.get("EZCHAT_ZORK_FILE")
    if env:
        p = Path(env)
        if p.exists():
            return p
    for p in _DEFAULT_PATHS:
        if p.exists():
            return p
    return None


class ZorkGame(BaseGame):
    name        = "zork"
    description = "Zork I: The Great Underground Empire (single-player text adventure)"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._env    = None
        self._over   = False
        self._player: str = ""

    def start(self, players: list[str]) -> str:
        try:
            import jericho  # noqa: F401
        except ImportError:
            raise RuntimeError(_INSTALL_MSG)

        game_file = _find_game_file()
        if game_file is None:
            raise RuntimeError(
                "Zork game file not found.\n"
                "Download zork1.z5 and place it at ~/.ezchat/games/zork1.z5"
            )

        import jericho
        self._env    = jericho.FrotzEnv(str(game_file))
        self._player = players[0]
        obs, _info   = self._env.reset()
        return self._fmt(obs)

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        if self._env is None:
            return [(sender, "No active Zork session.")]

        cmd = text.strip()
        if cmd.lower() in ("quit", "q"):
            self._over = True
            self._env.close()
            return [(sender, "Zork session ended. Come back anytime!")]

        try:
            obs, _reward, done, _info = self._env.step(cmd)
        except Exception as exc:
            return [(sender, f"Zork error: {exc}")]

        if done:
            self._over = True

        return [(sender, self._fmt(obs))]

    @property
    def is_over(self) -> bool:
        return self._over

    @staticmethod
    def _fmt(text: str) -> str:
        return text.strip()
