"""Lemonade Stand — run a lemonade business."""
from __future__ import annotations

import random

from kirbus.games import BaseGame

_WEATHER = ["sunny", "cloudy", "hot", "rainy", "stormy"]
_WEATHER_DEMAND = {"sunny": 1.0, "cloudy": 0.7, "hot": 1.5, "rainy": 0.3, "stormy": 0.1}
_DAYS = 14


class LemonadeStandGame(BaseGame):
    name        = "lemonade"
    description = "Lemonade Stand"
    min_players = 1
    max_players = 1

    def __init__(self) -> None:
        self._money = 20.0
        self._day = 0
        self._cups = 0
        self._lemons = 0
        self._sugar = 0
        self._signs = 0
        self._over = False
        self._state = "shop"  # "shop" | "price"
        self._weather = "sunny"
        self._forecast = "sunny"
        self._player = ""

    def start(self, players: list[str]) -> str:
        self._player = players[0]
        self._new_day()
        return (
            "=== LEMONADE STAND ===\n"
            f"Run your lemonade stand for {_DAYS} days.\n"
            "Buy supplies, set your price, and make a profit!\n\n"
            + self._shop_display()
        )

    def on_message(self, sender: str, text: str) -> list[tuple[str, str]]:
        text = text.strip().lower()
        if text in ("quit", "q"):
            self._over = True
            return [(sender, f"Final money: ${self._money:.2f} after {self._day} days.")]

        if self._state == "shop":
            return [(sender, self._handle_shop(text))]
        elif self._state == "price":
            return [(sender, self._handle_price(text))]
        return [(sender, "Type 'help' for commands.")]

    @property
    def is_over(self) -> bool:
        return self._over

    def _new_day(self) -> None:
        self._day += 1
        self._weather = self._forecast
        self._forecast = random.choice(_WEATHER)

    def _shop_display(self) -> str:
        return (
            f"=== Day {self._day} of {_DAYS} ===\n"
            f"Weather: {self._weather}  |  Tomorrow's forecast: {self._forecast}\n"
            f"Money: ${self._money:.2f}\n\n"
            f"Inventory: {self._cups} cups, {self._lemons} lemons, {self._sugar} sugar\n\n"
            "Buy supplies:\n"
            "  buy cups <qty>    — $0.50 each (you need 1 per glass)\n"
            "  buy lemons <qty>  — $0.25 each (1 per 2 glasses)\n"
            "  buy sugar <qty>   — $0.10 each (1 per 3 glasses)\n"
            "  buy signs <qty>   — $1.00 each (boosts demand)\n\n"
            "Type 'sell' when ready to open for business."
        )

    def _handle_shop(self, text: str) -> str:
        parts = text.split()
        if not parts:
            return self._shop_display()

        if parts[0] == "sell" or parts[0] == "open":
            if self._cups <= 0:
                return "You need cups to sell lemonade! Buy some first."
            self._state = "price"
            return "Set your price per glass (e.g. 0.25, 0.50, 1.00):"

        if parts[0] == "buy" and len(parts) >= 3:
            item = parts[1]
            if not parts[2].isdigit():
                return "Quantity must be a number."
            qty = int(parts[2])

            prices = {"cups": 0.50, "lemons": 0.25, "sugar": 0.10, "signs": 1.00}
            if item not in prices:
                return f"Buy what? Options: cups, lemons, sugar, signs"
            cost = prices[item] * qty
            if cost > self._money:
                max_qty = int(self._money / prices[item])
                return f"Can't afford {qty}. You can buy up to {max_qty}."
            self._money -= cost
            if item == "cups":
                self._cups += qty
            elif item == "lemons":
                self._lemons += qty
            elif item == "sugar":
                self._sugar += qty
            elif item == "signs":
                self._signs += qty
            return f"Bought {qty} {item} for ${cost:.2f}.\n\n" + self._shop_display()

        if parts[0] == "status":
            return self._shop_display()

        return self._shop_display()

    def _handle_price(self, text: str) -> str:
        try:
            price = float(text)
        except ValueError:
            return "Enter a price like 0.25, 0.50, 1.00:"

        if price <= 0 or price > 10:
            return "Price must be between $0.01 and $10.00."

        # Calculate sales
        weather_mult = _WEATHER_DEMAND.get(self._weather, 1.0)
        sign_mult = 1.0 + (self._signs * 0.2)
        price_factor = max(0.1, 2.0 - (price / 0.50))  # cheaper = more demand
        base_demand = random.randint(15, 40)
        demand = int(base_demand * weather_mult * sign_mult * price_factor)

        # How many can we actually make?
        max_from_cups = self._cups
        max_from_lemons = self._lemons * 2
        max_from_sugar = self._sugar * 3
        can_make = min(max_from_cups, max_from_lemons, max_from_sugar, demand)

        # Sell
        revenue = can_make * price
        self._money += revenue
        self._cups -= can_make
        self._lemons -= max(0, (can_make + 1) // 2)
        self._sugar -= max(0, (can_make + 2) // 3)
        self._signs = 0  # signs are per-day

        result = (
            f"\n=== Day {self._day} Results ===\n"
            f"Weather: {self._weather}\n"
            f"Price: ${price:.2f}/glass\n"
            f"Demand: {demand} customers\n"
            f"Sold: {can_make} glasses\n"
            f"Revenue: ${revenue:.2f}\n"
            f"Money: ${self._money:.2f}\n"
        )

        if can_make < demand:
            result += f"(Could have sold {demand - can_make} more — ran out of supplies!)\n"

        if self._day >= _DAYS:
            self._over = True
            return (
                result +
                f"\n=== GAME OVER ===\n"
                f"Final money: ${self._money:.2f}\n"
                f"{'Great job!' if self._money > 50 else 'Better luck next time!'}"
            )

        self._new_day()
        self._state = "shop"
        return result + "\n" + self._shop_display()
