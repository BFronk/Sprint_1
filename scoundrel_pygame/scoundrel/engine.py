"""Pure game rules for the 2011 base game of Scoundrel.

This module intentionally has no Pygame dependency so the rules can be tested
without opening a window.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from typing import Iterable


class Suit(str, Enum):
    CLUBS = "clubs"
    SPADES = "spades"
    HEARTS = "hearts"
    DIAMONDS = "diamonds"


@dataclass(frozen=True, slots=True)
class Card:
    suit: Suit
    value: int

    @property
    def kind(self) -> str:
        if self.suit in (Suit.CLUBS, Suit.SPADES):
            return "monster"
        if self.suit is Suit.DIAMONDS:
            return "weapon"
        return "potion"

    @property
    def rank(self) -> str:
        return {11: "J", 12: "Q", 13: "K", 14: "A"}.get(self.value, str(self.value))

    @property
    def symbol(self) -> str:
        return {
            Suit.CLUBS: "♣",
            Suit.SPADES: "♠",
            Suit.HEARTS: "♥",
            Suit.DIAMONDS: "♦",
        }[self.suit]

    @property
    def label(self) -> str:
        return f"{self.rank}{self.symbol}"


def make_dungeon() -> list[Card]:
    """Return the 44 cards used by the original rules."""
    cards: list[Card] = []
    for suit in (Suit.CLUBS, Suit.SPADES):
        cards.extend(Card(suit, value) for value in range(2, 15))
    for suit in (Suit.HEARTS, Suit.DIAMONDS):
        cards.extend(Card(suit, value) for value in range(2, 11))
    return cards


class RuleError(ValueError):
    """Raised when an action is not legal in the current state."""


class GameState:
    MAX_HEALTH = 20

    def __init__(self, seed: int | None = None, deck: Iterable[Card] | None = None):
        self.rng = random.Random(seed)
        self.dungeon = list(deck) if deck is not None else make_dungeon()
        if deck is None:
            self.rng.shuffle(self.dungeon)

        self.health = self.MAX_HEALTH
        self.room: list[Card] = []
        self.weapon: Card | None = None
        self.weapon_limit: int | None = None
        self.weapon_kills: list[Card] = []
        self.potion_used = False
        self.previous_room_avoided = False
        self.actions_this_room = 0
        self._actions_required = 3
        self.room_number = 0
        self.status = "playing"
        self.message = "Enter the first room."
        self.last_card: Card | None = None
        self.monsters_defeated = 0
        self.damage_taken = 0
        self.potions_used = 0
        self.rooms_faced = 0
        self.rooms_avoided = 0
        self._fill_room()

    @property
    def is_final_room(self) -> bool:
        return not self.dungeon

    @property
    def actions_required(self) -> int:
        return self._actions_required

    @property
    def can_avoid(self) -> bool:
        return (
            self.status == "playing"
            and not self.previous_room_avoided
            and self.actions_this_room == 0
            and len(self.room) == 4
            and bool(self.dungeon)
        )

    @property
    def cards_remaining(self) -> int:
        return len(self.dungeon) + len(self.room)

    @property
    def weapon_name(self) -> str:
        return self.weapon.label if self.weapon else "Bare hands"

    @property
    def score(self) -> int:
        if self.status == "won":
            bonus = self.last_card.value if (
                self.health == self.MAX_HEALTH
                and self.last_card is not None
                and self.last_card.kind == "potion"
            ) else 0
            return self.health + bonus
        if self.status == "lost":
            danger = sum(card.value for card in (*self.room, *self.dungeon) if card.kind == "monster")
            return self.health - danger
        return self.health

    def _fill_room(self) -> None:
        while len(self.room) < 4 and self.dungeon:
            self.room.append(self.dungeon.pop(0))
        self.room_number += 1
        self.actions_this_room = 0
        self._actions_required = len(self.room) if self.is_final_room else 3
        self.potion_used = False
        if self.is_final_room:
            self.message = "Final chamber — clear every card."
        else:
            self.message = "Choose three cards, in any order."

    def avoid_room(self) -> None:
        if not self.can_avoid:
            raise RuleError("This room cannot be avoided.")
        self.dungeon.extend(self.room)
        self.room.clear()
        self.previous_room_avoided = True
        self.rooms_avoided += 1
        self._fill_room()
        self.message = "You slipped away. The next room must be faced."

    def can_use_weapon(self, monster: Card) -> bool:
        return (
            monster.kind == "monster"
            and self.weapon is not None
            and (self.weapon_limit is None or monster.value <= self.weapon_limit)
        )

    def preview_damage(self, monster: Card, use_weapon: bool) -> int:
        if monster.kind != "monster":
            raise RuleError("Only monsters deal combat damage.")
        if use_weapon and not self.can_use_weapon(monster):
            raise RuleError("The equipped weapon cannot fight this monster.")
        return max(0, monster.value - self.weapon.value) if use_weapon and self.weapon else monster.value

    def choose_card(self, index: int, use_weapon: bool | None = None) -> dict[str, object]:
        if self.status != "playing":
            raise RuleError("The run is already over.")
        if not 0 <= index < len(self.room):
            raise RuleError("That card is not in the room.")

        card = self.room[index]
        if card.kind == "monster" and use_weapon is None:
            raise RuleError("Choose weapon or barehanded combat.")

        event: dict[str, object] = {"card": card, "kind": card.kind}
        self.previous_room_avoided = False

        if card.kind == "weapon":
            old_weapon = self.weapon
            self.weapon = card
            self.weapon_limit = None
            self.weapon_kills.clear()
            self.message = f"Equipped {card.label}."
            event.update(old_weapon=old_weapon, weapon=card)
        elif card.kind == "potion":
            before = self.health
            healed = 0
            if not self.potion_used:
                self.health = min(self.MAX_HEALTH, self.health + card.value)
                healed = self.health - before
                self.potion_used = True
                self.potions_used += 1
                self.message = f"Potion restored {healed} health." if healed else "Already at full health."
            else:
                self.message = "The second potion this room is discarded."
            event.update(healed=healed, wasted=self.potion_used and healed == 0)
        else:
            using_weapon = bool(use_weapon)
            damage = self.preview_damage(card, using_weapon)
            self.health -= damage
            self.damage_taken += damage
            self.monsters_defeated += 1
            if using_weapon:
                self.weapon_limit = card.value
                self.weapon_kills.append(card)
                self.message = f"{card.label} slain with {self.weapon.label}; took {damage} damage."
            else:
                self.message = f"Fought {card.label} barehanded; took {damage} damage."
            event.update(damage=damage, used_weapon=using_weapon)

        self.last_card = card
        self.room.pop(index)
        self.actions_this_room += 1

        if self.health <= 0:
            self.status = "lost"
            self.message = "You fell in the dungeon."
            event["game_over"] = True
            return event

        if self.actions_this_room >= self.actions_required:
            if not self.room and not self.dungeon:
                self.status = "won"
                self.message = "The dungeon is clear."
                event["game_over"] = True
            else:
                self.rooms_faced += 1
                self._fill_room()
                event["new_room"] = True
        return event

    def card_summary(self) -> dict[str, int]:
        cards = [*self.room, *self.dungeon]
        return {
            "monsters": sum(card.kind == "monster" for card in cards),
            "weapons": sum(card.kind == "weapon" for card in cards),
            "potions": sum(card.kind == "potion" for card in cards),
        }
