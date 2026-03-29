"""Global Thermonuclear War — shall we play a game?

Inspired by WarGames (1983). Manage your nuclear arsenal,
defend against incoming strikes, and try to survive.
"""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_NATIONS = ["USSR", "China", "France", "UK", "India"]
_MAX_TURNS = 20


class NuclearWarGame(BaseGame):
    name        = "nuclearwar"
    description = "Global Thermonuclear War"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._missiles = 20
        self._defenses = 10
        self._cities = 10
        self._population = 250  # millions
        self._turn = 0
        self._defcon = 3  # 5=peace, 1=war
        self._enemies: dict[str, dict] = {}
        self._over = False
        self._player = ""

    def start(self, players: list[str]) -> str:
        self._player = players[0]
        for nation in _NATIONS:
            self._enemies[nation] = {
                "missiles": random.randint(8, 20),
                "defenses": random.randint(3, 8),
                "cities": random.randint(5, 10),
                "hostile": random.randint(20, 60),  # 0-100
                "alive": True,
            }
        return (
            "GREETINGS PROFESSOR FALKEN.\n"
            "SHALL WE PLAY A GAME?\n\n"
            "=== GLOBAL THERMONUCLEAR WAR ===\n\n"
            "You control the United States nuclear arsenal.\n"
            f"Survive {_MAX_TURNS} turns without losing all your cities.\n\n"
            "Commands: status, launch <nation> <qty>, defend,\n"
            "          diplomacy <nation>, intel, end turn, quit\n\n"
            + self._status_brief()
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().lower()
        if text in ("quit", "q"):
            self._over = True
            return [(sender, "A STRANGE GAME.\nTHE ONLY WINNING MOVE IS NOT TO PLAY.\n\nHOW ABOUT A NICE GAME OF CHESS?")]

        return [(sender, self._handle(text))]

    @property
    def is_over(self) -> bool:
        return self._over

    def _handle(self, text: str) -> str:
        parts = text.split()
        cmd = parts[0]

        if cmd in ("status", "st"):
            return self._status_full()
        if cmd == "intel":
            return self._intel()
        if cmd == "launch":
            return self._launch(parts)
        if cmd == "defend":
            return self._build_defense()
        if cmd in ("diplomacy", "diplo"):
            return self._diplomacy(parts)
        if cmd in ("end", "turn", "next"):
            return self._end_turn()
        if cmd == "help":
            return (
                "Commands:\n"
                "  status           — your forces and cities\n"
                "  intel            — intelligence on other nations\n"
                "  launch <nation> <qty> — launch missiles\n"
                "  defend           — build missile defense (+1)\n"
                "  diplomacy <nation> — attempt to reduce tensions\n"
                "  end turn         — advance to next turn\n"
                "  quit             — end the game"
            )

        return "Unknown command. Type 'help' for options."

    def _launch(self, parts: list[str]) -> str:
        if len(parts) < 3:
            alive = [n for n, d in self._enemies.items() if d["alive"]]
            return f"Launch at whom? Options: {', '.join(alive)}\nUsage: launch <nation> <qty>"

        target = parts[1].upper()
        if target not in self._enemies:
            # Try fuzzy match
            matches = [n for n in self._enemies if n.lower().startswith(parts[1])]
            if len(matches) == 1:
                target = matches[0]
            else:
                return f"Unknown nation. Options: {', '.join(n for n, d in self._enemies.items() if d['alive'])}"

        if not self._enemies[target]["alive"]:
            return f"{target} has already been destroyed."

        if not parts[2].isdigit():
            return "Specify number of missiles."
        qty = int(parts[2])
        if qty > self._missiles:
            return f"You only have {self._missiles} missiles."
        if qty <= 0:
            return "Must launch at least 1 missile."

        self._missiles -= qty
        self._defcon = max(1, self._defcon - 1)

        enemy = self._enemies[target]
        intercepted = min(qty, random.randint(0, enemy["defenses"]))
        hits = qty - intercepted
        cities_hit = min(hits, enemy["cities"])
        enemy["cities"] = max(0, enemy["cities"] - cities_hit)
        enemy["hostile"] = min(100, enemy["hostile"] + 30)

        # Increase all nations' hostility
        for n, d in self._enemies.items():
            if d["alive"] and n != target:
                d["hostile"] = min(100, d["hostile"] + 10)

        result = (
            f"*** LAUNCH DETECTED ***\n"
            f"Launched {qty} missiles at {target}.\n"
            f"Intercepted: {intercepted}\n"
            f"Hits: {hits}\n"
            f"Cities destroyed: {cities_hit}\n"
        )

        if enemy["cities"] <= 0:
            enemy["alive"] = False
            result += f"\n{target} HAS BEEN DESTROYED."

        # Check if all enemies destroyed
        if all(not d["alive"] for d in self._enemies.values()):
            self._over = True
            result += (
                f"\n\nALL NATIONS DESTROYED.\n"
                f"You 'win' with {self._cities} cities and {self._population}M people remaining.\n"
                "Was it worth it?"
            )

        return result

    def _build_defense(self) -> str:
        self._defenses += 1
        return f"Missile defense improved. Defense: {self._defenses}"

    def _diplomacy(self, parts: list[str]) -> str:
        if len(parts) < 2:
            return "Diplomacy with whom? Usage: diplomacy <nation>"
        target = parts[1].upper()
        matches = [n for n in self._enemies if n.lower().startswith(parts[1])]
        if len(matches) == 1:
            target = matches[0]
        elif target not in self._enemies:
            return f"Unknown nation."

        enemy = self._enemies[target]
        if not enemy["alive"]:
            return f"{target} no longer exists."

        if random.random() < 0.5:
            reduction = random.randint(5, 20)
            enemy["hostile"] = max(0, enemy["hostile"] - reduction)
            return f"Diplomacy with {target}: tensions reduced by {reduction}.\nHostility: {enemy['hostile']}%"
        else:
            return f"Diplomacy with {target}: talks break down. No change."

    def _end_turn(self) -> str:
        self._turn += 1
        result = f"\n=== TURN {self._turn} ===\n"

        # Enemy actions
        for nation, data in self._enemies.items():
            if not data["alive"]:
                continue

            # Hostility increases naturally
            data["hostile"] = min(100, data["hostile"] + random.randint(0, 5))

            # Enemy may launch
            if data["hostile"] > 70 and random.random() < (data["hostile"] / 200):
                qty = random.randint(1, min(5, data["missiles"]))
                data["missiles"] -= qty
                intercepted = min(qty, random.randint(0, self._defenses))
                hits = qty - intercepted
                cities_lost = min(hits, self._cities)
                pop_lost = cities_lost * random.randint(15, 30)
                self._cities -= cities_lost
                self._population = max(0, self._population - pop_lost)

                result += (
                    f"*** INCOMING FROM {nation}! ***\n"
                    f"  {qty} missiles launched, {intercepted} intercepted.\n"
                    f"  Cities lost: {cities_lost}, Casualties: {pop_lost}M\n"
                )

                if self._cities <= 0:
                    self._over = True
                    return result + "\nALL YOUR CITIES HAVE BEEN DESTROYED.\n\n*** GAME OVER ***"

        # Nations rebuild slightly
        for data in self._enemies.values():
            if data["alive"] and random.random() < 0.3:
                data["missiles"] = min(20, data["missiles"] + 1)

        # Check turn limit
        if self._turn >= _MAX_TURNS:
            self._over = True
            alive_enemies = sum(1 for d in self._enemies.values() if d["alive"])
            return (
                result +
                f"\n=== GAME OVER — {_MAX_TURNS} TURNS ===\n"
                f"Cities remaining: {self._cities}\n"
                f"Population: {self._population}M\n"
                f"Enemy nations standing: {alive_enemies}\n"
                f"{'Humanity survives... barely.' if self._cities > 5 else 'A pyrrhic survival.'}"
            )

        return result + self._status_brief()

    def _status_brief(self) -> str:
        return (
            f"DEFCON {self._defcon} | Cities: {self._cities} | "
            f"Pop: {self._population}M | Missiles: {self._missiles} | "
            f"Defense: {self._defenses} | Turn {self._turn}/{_MAX_TURNS}"
        )

    def _status_full(self) -> str:
        alive_enemies = sum(1 for d in self._enemies.values() if d["alive"])
        return (
            f"=== UNITED STATES STATUS ===\n"
            f"DEFCON: {self._defcon}\n"
            f"Turn: {self._turn}/{_MAX_TURNS}\n"
            f"Cities: {self._cities}\n"
            f"Population: {self._population}M\n"
            f"ICBMs: {self._missiles}\n"
            f"Missile Defense: {self._defenses}\n"
            f"Enemy nations standing: {alive_enemies}/{len(_NATIONS)}"
        )

    def _intel(self) -> str:
        lines = ["=== INTELLIGENCE REPORT ==="]
        for nation, data in self._enemies.items():
            if not data["alive"]:
                lines.append(f"  {nation:8s} — DESTROYED")
                continue
            threat = "LOW" if data["hostile"] < 40 else "MEDIUM" if data["hostile"] < 70 else "HIGH"
            lines.append(
                f"  {nation:8s} — {data['cities']} cities, "
                f"~{data['missiles']} ICBMs, Threat: {threat}"
            )
        return "\n".join(lines)
