"""Oregon Trail — travel west and survive."""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_TOTAL_MILES = 2000
_EVENTS = [
    ("river", "You've reached a river crossing. The water looks deep."),
    ("hunt", "You see wild game in the distance."),
    ("trader", "A fellow traveler offers to trade supplies."),
    ("storm", "A terrible storm rolls in!"),
    ("thief", "Bandits attack your wagon!"),
    ("broken", "A wagon wheel breaks!"),
    ("illness", "A member of your party falls ill."),
    ("nothing", "The trail is peaceful today."),
    ("berries", "You find a patch of wild berries."),
    ("shortcut", "You spot a shortcut through the hills."),
]

_LANDMARKS = {
    200: "Kansas River Crossing",
    400: "Fort Kearney",
    600: "Chimney Rock",
    800: "Fort Laramie",
    1000: "Independence Rock",
    1200: "South Pass",
    1400: "Fort Bridger",
    1600: "Soda Springs",
    1800: "Fort Boise",
    1950: "Blue Mountains",
}


class OregonTrailGame(BaseGame):
    name        = "oregon"
    description = "Oregon Trail"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._miles = 0
        self._food = 500
        self._ammo = 100
        self._health = 100
        self._money = 200
        self._oxen = 2
        self._day = 1
        self._party = 4
        self._over = False
        self._state = "travel"  # "travel" | "event" | "shop"
        self._pending_event = ""
        self._player = ""

    def start(self, players: list[str]) -> str:
        self._player = players[0]
        return (
            "=== THE OREGON TRAIL ===\n"
            "The year is 1848. Your family of 4 is heading west\n"
            f"from Independence, Missouri to Oregon City — {_TOTAL_MILES} miles.\n\n"
            "Commands: travel, rest, hunt, status, quit\n\n"
            + self._status_brief()
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().lower()
        if text in ("quit", "q"):
            self._over = True
            return [(sender, f"You made it {self._miles} miles. The trail claims another party.")]

        if self._state == "event":
            return [(sender, self._handle_event(text))]

        return [(sender, self._handle_travel(text))]

    @property
    def is_over(self) -> bool:
        return self._over

    def _handle_travel(self, text: str) -> str:
        if text in ("status", "st"):
            return self._status_full()

        if text in ("rest", "r"):
            self._day += 1
            heal = random.randint(5, 15)
            self._health = min(100, self._health + heal)
            self._food -= self._party * 2
            return self._check_resources(f"You rest for a day. Health +{heal}.\n")

        if text in ("hunt", "h"):
            if self._ammo < 10:
                return "Not enough ammo to hunt. (need 10)"
            self._ammo -= 10
            self._day += 1
            self._food -= self._party * 2
            if random.random() < 0.7:
                food_gained = random.randint(30, 80)
                self._food += food_gained
                return self._check_resources(f"You bag some game! +{food_gained} food.\n")
            return self._check_resources("The hunt was unsuccessful.\n")

        if text in ("travel", "t", "go", ""):
            return self._do_travel()

        return "Commands: travel, rest, hunt, status, quit"

    def _do_travel(self) -> str:
        miles = random.randint(20, 50)
        if self._oxen < 2:
            miles = miles // 2
        self._miles += miles
        self._day += 1
        self._food -= self._party * 3
        self._health -= random.randint(0, 5)

        result = f"Day {self._day}: Traveled {miles} miles.\n"

        # Check landmarks
        for lm_miles, lm_name in _LANDMARKS.items():
            if self._miles >= lm_miles and self._miles - miles < lm_miles:
                result += f"\n*** {lm_name} ***\n"
                break

        # Check victory
        if self._miles >= _TOTAL_MILES:
            self._over = True
            return (
                result +
                f"\n=== YOU MADE IT TO OREGON! ===\n"
                f"Arrived on day {self._day} with {self._party} party members.\n"
                f"Food: {self._food}  Health: {self._health}  Money: ${self._money}\n"
                "Congratulations!"
            )

        # Random event
        if random.random() < 0.5:
            event_type, event_desc = random.choice(_EVENTS)
            self._pending_event = event_type
            self._state = "event"
            return self._check_resources(result + f"\n{event_desc}\n" + self._event_choices(event_type))

        return self._check_resources(result) + "\n" + self._status_brief()

    def _event_choices(self, event_type: str) -> str:
        if event_type == "river":
            return "Ford the river (f) or wait for ferry ($20) (w)?"
        if event_type == "hunt":
            return "Try to hunt? (y/n)"
        if event_type == "trader":
            return "Trade: buy food ($10 for 50), buy ammo ($10 for 20), or skip (s)?"
        if event_type == "storm":
            return "Take shelter (lose a day) or push through?"
        if event_type == "thief":
            return "Fight (f) or surrender supplies (s)?"
        if event_type == "broken":
            return "Repair ($30) or makeshift fix (risk)?"
        if event_type == "illness":
            return "Rest (2 days) or push on?"
        if event_type == "berries":
            return "Gather berries? (y/n)"
        if event_type == "shortcut":
            return "Take the shortcut (risky) or stay on the trail? (y/n)"
        return "Press enter to continue."

    def _handle_event(self, text: str) -> str:
        self._state = "travel"
        event = self._pending_event

        if event == "river":
            if text in ("w", "wait", "ferry"):
                if self._money >= 20:
                    self._money -= 20
                    return self._check_resources("Safe crossing by ferry. -$20\n") + "\n" + self._status_brief()
                return self._check_resources("Can't afford ferry. You ford the river.\n" + self._ford_river())
            return self._check_resources(self._ford_river())

        if event == "trader":
            if text in ("food", "f"):
                if self._money >= 10:
                    self._money -= 10
                    self._food += 50
                    return self._check_resources("Bought 50 food.\n") + "\n" + self._status_brief()
                return "Not enough money.\n" + self._status_brief()
            if text in ("ammo", "a"):
                if self._money >= 10:
                    self._money -= 10
                    self._ammo += 20
                    return self._check_resources("Bought 20 ammo.\n") + "\n" + self._status_brief()
                return "Not enough money.\n" + self._status_brief()
            return "You pass on the trade.\n" + self._status_brief()

        if event == "storm":
            if text in ("shelter", "s", "take"):
                self._day += 1
                self._food -= self._party * 2
                return self._check_resources("You wait out the storm.\n") + "\n" + self._status_brief()
            self._health -= random.randint(10, 25)
            return self._check_resources("The storm batters your party. Health drops!\n") + "\n" + self._status_brief()

        if event == "thief":
            if text in ("f", "fight"):
                if random.random() < 0.6:
                    self._ammo -= 5
                    return self._check_resources("You drive off the bandits!\n") + "\n" + self._status_brief()
                self._health -= 20
                stolen = random.randint(20, 50)
                self._money = max(0, self._money - stolen)
                return self._check_resources(f"Bandits wound you and steal ${stolen}!\n") + "\n" + self._status_brief()
            stolen_food = random.randint(30, 80)
            self._food = max(0, self._food - stolen_food)
            return self._check_resources(f"Bandits take {stolen_food} food.\n") + "\n" + self._status_brief()

        if event == "broken":
            if text in ("repair", "r") and self._money >= 30:
                self._money -= 30
                return self._check_resources("Wheel repaired. -$30\n") + "\n" + self._status_brief()
            if random.random() < 0.5:
                return self._check_resources("Makeshift fix holds!\n") + "\n" + self._status_brief()
            self._day += 2
            self._food -= self._party * 4
            return self._check_resources("Fix failed. Lost 2 days.\n") + "\n" + self._status_brief()

        if event == "illness":
            if text in ("rest", "r"):
                self._day += 2
                self._food -= self._party * 4
                self._health = min(100, self._health + 20)
                return self._check_resources("Rest helps. Health improved.\n") + "\n" + self._status_brief()
            if random.random() < 0.3:
                self._party -= 1
                if self._party <= 0:
                    self._over = True
                    return "Your last party member has died.\n\n*** GAME OVER ***"
                return self._check_resources(f"A party member has died. Party: {self._party}\n") + "\n" + self._status_brief()
            self._health -= 15
            return self._check_resources("They push through but everyone suffers.\n") + "\n" + self._status_brief()

        if event == "berries":
            if text in ("y", "yes", "gather"):
                self._food += random.randint(10, 30)
                return self._check_resources("You gather berries.\n") + "\n" + self._status_brief()
            return self._status_brief()

        if event == "shortcut":
            if text in ("y", "yes"):
                if random.random() < 0.6:
                    bonus = random.randint(30, 60)
                    self._miles += bonus
                    return self._check_resources(f"Shortcut works! +{bonus} extra miles.\n") + "\n" + self._status_brief()
                self._health -= 15
                return self._check_resources("Shortcut was a bad idea. Rough terrain!\n") + "\n" + self._status_brief()
            return self._status_brief()

        return self._status_brief()

    def _ford_river(self) -> str:
        if random.random() < 0.3:
            lost = random.randint(20, 50)
            self._food = max(0, self._food - lost)
            return f"Rough crossing! Lost {lost} food.\n"
        return "You ford the river safely.\n"

    def _check_resources(self, prefix: str) -> str:
        if self._food <= 0:
            self._food = 0
            self._health -= 20
            prefix += "No food! Your party is starving!\n"
        if self._health <= 0:
            self._over = True
            return prefix + "\nYour health has failed.\n\n*** YOU HAVE DIED ON THE TRAIL ***"
        if self._party <= 0:
            self._over = True
            return prefix + "\n*** GAME OVER ***"
        return prefix

    def _status_brief(self) -> str:
        progress = int((self._miles / _TOTAL_MILES) * 20)
        bar = "=" * progress + ">" + "." * (20 - progress)
        return (
            f"[{bar}] {self._miles}/{_TOTAL_MILES} mi\n"
            f"Day {self._day} | Food: {self._food} | Ammo: {self._ammo} | "
            f"Health: {self._health} | Party: {self._party} | ${self._money}"
        )

    def _status_full(self) -> str:
        return (
            f"=== Oregon Trail Status ===\n"
            f"Miles traveled: {self._miles}/{_TOTAL_MILES}\n"
            f"Day: {self._day}\n"
            f"Party members: {self._party}\n"
            f"Health: {self._health}/100\n"
            f"Food: {self._food}\n"
            f"Ammunition: {self._ammo}\n"
            f"Money: ${self._money}\n"
            f"Oxen: {self._oxen}"
        )
