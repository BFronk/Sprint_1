"""Pure game rules for the 2011 base game of Scoundrel.

This module intentionally has no Pygame dependency so the rules can be tested
without opening a window.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from typing import Iterable


STANDARD_MONSTER_VALUE = 2 * sum(range(2, 15))  # Clubs + Spades = 208


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


@dataclass(frozen=True, slots=True)
class Upgrade:
    id: str
    title: str
    description: str
    cost: int
    kind: str
    amount: int


@dataclass(frozen=True, slots=True)
class Mutation:
    id: str
    title: str
    description: str
    kind: str
    amount: int


ROGUE_UPGRADES = (
    Upgrade("honed_edge", "Honed Edge", "+1 power to every equipped weapon", 0, "weapon", 1),
    Upgrade("vitality", "Vitality", "+3 maximum health and restore 3", 0, "max_health", 3),
    Upgrade("strong_tonic", "Strong Tonic", "+2 healing from every potion", 0, "potion", 2),
    Upgrade("iron_skin", "Iron Skin", "Take 1 less damage from every monster", 0, "armor", 1),
    Upgrade("field_dressing", "Field Dressing", "Restore 10 health now", 0, "heal", 10),
)

ROGUE_MUTATIONS = (
    Mutation("spade_fury", "Spade Fury", "Spade monsters gain +2 damage", "spades", 2),
    Mutation("club_armor", "Club Armor", "Weapons have 2 less power against Clubs", "clubs", 2),
    Mutation("bloodlust", "Bloodlust", "Barehanded fights deal +2 damage", "barehand", 2),
    Mutation("drought", "Drought", "Every potion restores 2 less health", "potions", 2),
)


def make_dungeon() -> list[Card]:
    """Return the 44 cards used by the original rules."""
    cards: list[Card] = []
    for suit in (Suit.CLUBS, Suit.SPADES):
        cards.extend(Card(suit, value) for value in range(2, 15))
    for suit in (Suit.HEARTS, Suit.DIAMONDS):
        cards.extend(Card(suit, value) for value in range(2, 11))
    assert len(cards) == 44 and len(set(cards)) == 44
    return cards


class RuleError(ValueError):
    """Raised when an action is not legal in the current state."""


class GameState:
    MAX_HEALTH = 20

    def __init__(self, seed: int | None = None, deck: Iterable[Card] | None = None,
                 mode: str = "classic", allow_equal_weapon_kills: bool = True):
        if mode not in ("classic", "marathon", "roguelike"):
            raise ValueError("mode must be 'classic', 'marathon', or 'roguelike'")
        self.mode = mode
        self.allow_equal_weapon_kills = allow_equal_weapon_kills
        self.dungeons_total = 2 if mode == "marathon" else 1
        self.target_rooms = 40 if mode == "roguelike" else None
        self.dungeon_number = 1
        self.rng = random.Random(seed)
        self.dungeon = list(deck) if deck is not None else make_dungeon()
        if deck is None:
            self.rng.shuffle(self.dungeon)

        self.max_health = self.MAX_HEALTH
        self.health = self.max_health
        self.weapon_bonus = 0
        self.potion_bonus = 0
        self.armor_bonus = 0
        self.shop_choices: list[Upgrade] = []
        self.upgrades_taken: list[str] = []
        self.active_mutations: list[Mutation] = []
        self.current_mutation: Mutation | None = None
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

    def _begin_next_dungeon(self) -> None:
        """Shuffle the next 44 cards without resetting the adventurer."""
        self.dungeon = make_dungeon()
        self.rng.shuffle(self.dungeon)
        self.dungeon_number += 1
        self._fill_room()
        self.message = f"Dungeon {self.dungeon_number} begins. Your wounds and weapon carry forward."

    def _begin_next_rogue_deck(self) -> None:
        self.dungeon = make_dungeon()
        self.rng.shuffle(self.dungeon)
        self.dungeon_number += 1
        self._fill_room()
        self.message = "A deeper deck waits below."

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
    def dungeons_cleared(self) -> int:
        return self.dungeons_total if self.status == "won" else self.dungeon_number - 1

    @property
    def rooms_remaining(self) -> int:
        return max(0, (self.target_rooms or self.rooms_faced) - self.rooms_faced)

    @property
    def effective_weapon_power(self) -> int:
        return (self.weapon.value + self.weapon_bonus) if self.weapon else 0

    def has_mutation(self, mutation_id: str) -> bool:
        return any(mutation.id == mutation_id for mutation in self.active_mutations)

    def effective_monster_value(self, monster: Card) -> int:
        bonus = 2 if monster.suit is Suit.SPADES and self.has_mutation("spade_fury") else 0
        return monster.value + bonus

    def weapon_power_against(self, monster: Card) -> int:
        penalty = 2 if monster.suit is Suit.CLUBS and self.has_mutation("club_armor") else 0
        return max(0, self.effective_weapon_power - penalty)

    def effective_potion_value(self, potion: Card) -> int:
        penalty = 2 if self.has_mutation("drought") else 0
        return max(0, potion.value + self.potion_bonus - penalty)

    @property
    def weapon_name(self) -> str:
        return self.weapon.label if self.weapon else "Bare hands"

    @property
    def score(self) -> int:
        if self.mode == "roguelike":
            return self.rooms_faced * 100 + self.monsters_defeated * 5 + max(0, self.health)
        if self.status == "won":
            bonus = self.last_card.value if (
                self.health == self.max_health
                and self.last_card is not None
                and self.last_card.kind == "potion"
            ) else 0
            return self.health + bonus
        if self.status == "lost":
            danger = sum(card.value for card in (*self.room, *self.dungeon) if card.kind == "monster")
            unentered_dungeons = self.dungeons_total - self.dungeon_number
            danger += unentered_dungeons * STANDARD_MONSTER_VALUE
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
        within_limit = (
            self.weapon_limit is None
            or monster.value < self.weapon_limit
            or (self.allow_equal_weapon_kills and monster.value == self.weapon_limit)
        )
        return (
            monster.kind == "monster"
            and self.weapon is not None
            and within_limit
        )

    def preview_damage(self, monster: Card, use_weapon: bool) -> int:
        if monster.kind != "monster":
            raise RuleError("Only monsters deal combat damage.")
        if use_weapon and not self.can_use_weapon(monster):
            raise RuleError("The equipped weapon cannot fight this monster.")
        monster_power = self.effective_monster_value(monster)
        if use_weapon and self.weapon:
            damage = max(0, monster_power - self.weapon_power_against(monster))
        else:
            bloodlust = 2 if self.has_mutation("bloodlust") else 0
            damage = monster_power + bloodlust
        return max(0, damage - self.armor_bonus)

    def _prepare_shop(self) -> None:
        self.status = "shop"
        remaining = [item for item in ROGUE_MUTATIONS if item not in self.active_mutations]
        self.current_mutation = self.rng.choice(remaining)
        self.active_mutations.append(self.current_mutation)
        sustain = [item for item in ROGUE_UPGRADES if item.kind in ("max_health", "heal")]
        technique = [item for item in ROGUE_UPGRADES if item.kind in ("weapon", "potion", "armor")]
        choices = [self.rng.choice(sustain), self.rng.choice(technique)]
        choices.append(self.rng.choice([item for item in ROGUE_UPGRADES if item not in choices]))
        self.rng.shuffle(choices)
        self.shop_choices = choices
        self.message = "The dungeon evolves. Choose one boon before descending."

    def _continue_roguelike(self) -> None:
        self.status = "playing"
        self.shop_choices.clear()
        self.current_mutation = None
        if not self.room and not self.dungeon:
            self._begin_next_rogue_deck()
        else:
            self._fill_room()

    def purchase_upgrade(self, upgrade_id: str) -> Upgrade:
        if self.mode != "roguelike" or self.status != "shop":
            raise RuleError("There is no open checkpoint shop.")
        upgrade = next((item for item in self.shop_choices if item.id == upgrade_id), None)
        if upgrade is None:
            raise RuleError("That upgrade is not available.")
        if upgrade.kind == "weapon":
            self.weapon_bonus += upgrade.amount
        elif upgrade.kind == "max_health":
            self.max_health += upgrade.amount
            self.health = min(self.max_health, self.health + upgrade.amount)
        elif upgrade.kind == "potion":
            self.potion_bonus += upgrade.amount
        elif upgrade.kind == "armor":
            self.armor_bonus += upgrade.amount
        elif upgrade.kind == "heal":
            self.health = min(self.max_health, self.health + upgrade.amount)
        self.upgrades_taken.append(upgrade.id)
        self._continue_roguelike()
        self.message = f"{upgrade.title} acquired."
        return upgrade

    def leave_shop(self) -> None:
        if self.mode != "roguelike" or self.status != "shop":
            raise RuleError("There is no open checkpoint shop.")
        raise RuleError("Choose one boon before continuing.")

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
                self.health = min(self.max_health, self.health + self.effective_potion_value(card))
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
            if self.mode == "roguelike":
                self.rooms_faced += 1
                if self.rooms_faced >= (self.target_rooms or 40):
                    self.status = "won"
                    self.message = "Forty rooms conquered. The descent is complete."
                    event["game_over"] = True
                elif self.rooms_faced % 8 == 0:
                    self._prepare_shop()
                    event["shop"] = True
                else:
                    if not self.room and not self.dungeon:
                        self._begin_next_rogue_deck()
                        event["new_dungeon"] = True
                    else:
                        self._fill_room()
                    event["new_room"] = True
                return event
            if not self.room and not self.dungeon:
                self.rooms_faced += 1
                if self.dungeon_number < self.dungeons_total:
                    self._begin_next_dungeon()
                    event["new_room"] = True
                    event["new_dungeon"] = True
                else:
                    self.status = "won"
                    self.message = "The marathon is complete." if self.mode == "marathon" else "The dungeon is clear."
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
