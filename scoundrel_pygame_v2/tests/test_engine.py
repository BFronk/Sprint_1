import unittest

from scoundrel.engine import Card, GameState, RuleError, Suit, make_dungeon


class ScoundrelRulesTests(unittest.TestCase):
    def test_base_deck_has_correct_44_cards(self):
        deck = make_dungeon()
        self.assertEqual(len(deck), 44)
        self.assertEqual(sum(c.kind == "monster" for c in deck), 26)
        self.assertEqual(sum(c.kind == "weapon" for c in deck), 9)
        self.assertEqual(sum(c.kind == "potion" for c in deck), 9)
        self.assertEqual(len(set(deck)), 44)

    def test_weapon_damage_and_binding_limit(self):
        deck = [
            Card(Suit.DIAMONDS, 5), Card(Suit.CLUBS, 12),
            Card(Suit.SPADES, 6), Card(Suit.CLUBS, 13), Card(Suit.HEARTS, 2)
        ]
        game = GameState(deck=deck)
        game.choose_card(0)
        game.choose_card(0, use_weapon=True)
        self.assertEqual(game.health, 13)
        self.assertEqual(game.weapon_limit, 12)
        game.choose_card(0, use_weapon=True)
        self.assertEqual(game.health, 12)
        self.assertEqual(game.weapon_limit, 6)
        with self.assertRaises(RuleError):
            game.preview_damage(Card(Suit.CLUBS, 13), True)

    def test_official_rule_allows_equal_rank_weapon_kills(self):
        deck = [
            Card(Suit.DIAMONDS, 5), Card(Suit.CLUBS, 8),
            Card(Suit.SPADES, 8), Card(Suit.HEARTS, 2), Card(Suit.CLUBS, 3),
        ]
        game = GameState(deck=deck, allow_equal_weapon_kills=True)
        game.choose_card(0)
        game.choose_card(0, use_weapon=True)
        self.assertTrue(game.can_use_weapon(game.room[0]))

    def test_strict_variant_requires_descending_weapon_kills(self):
        deck = [
            Card(Suit.DIAMONDS, 5), Card(Suit.CLUBS, 8),
            Card(Suit.SPADES, 8), Card(Suit.HEARTS, 2), Card(Suit.CLUBS, 3),
        ]
        game = GameState(deck=deck, allow_equal_weapon_kills=False)
        game.choose_card(0)
        game.choose_card(0, use_weapon=True)
        self.assertFalse(game.can_use_weapon(game.room[0]))
        with self.assertRaises(RuleError):
            game.preview_damage(game.room[0], True)

    def test_only_first_potion_in_room_heals(self):
        deck = [
            Card(Suit.HEARTS, 5), Card(Suit.HEARTS, 9),
            Card(Suit.CLUBS, 2), Card(Suit.SPADES, 3), Card(Suit.CLUBS, 4)
        ]
        game = GameState(deck=deck)
        game.health = 8
        first = game.choose_card(0)
        second = game.choose_card(0)
        self.assertEqual(first["healed"], 5)
        self.assertEqual(second["healed"], 0)
        self.assertEqual(game.health, 13)

    def test_cannot_avoid_twice_and_cards_go_to_bottom(self):
        deck = [Card(Suit.CLUBS, value) for value in range(2, 10)]
        game = GameState(deck=deck)
        first_room = list(game.room)
        game.avoid_room()
        self.assertFalse(game.can_avoid)
        self.assertEqual(game.dungeon[-4:], first_room)
        with self.assertRaises(RuleError):
            game.avoid_room()

    def test_short_final_room_must_be_cleared(self):
        deck = [Card(Suit.HEARTS, 2), Card(Suit.DIAMONDS, 3)]
        game = GameState(deck=deck)
        self.assertTrue(game.is_final_room)
        self.assertFalse(game.can_avoid)
        game.choose_card(0)
        self.assertEqual(game.status, "playing")
        game.choose_card(0)
        self.assertEqual(game.status, "won")

    def test_loss_score_includes_unfaced_monsters(self):
        deck = [
            Card(Suit.CLUBS, 14), Card(Suit.SPADES, 13),
            Card(Suit.CLUBS, 12), Card(Suit.HEARTS, 2), Card(Suit.SPADES, 10)
        ]
        game = GameState(deck=deck)
        game.health = 3
        game.choose_card(0, use_weapon=False)
        self.assertEqual(game.status, "lost")
        self.assertEqual(game.score, -46)  # -11 health, then 35 remaining monster value

    def test_marathon_adds_a_fresh_44_card_dungeon_and_carries_state(self):
        first_dungeon = [Card(Suit.DIAMONDS, 7), Card(Suit.CLUBS, 3)]
        game = GameState(seed=8, deck=first_dungeon, mode="marathon")
        game.health = 14
        game.choose_card(0)  # equip the weapon
        event = game.choose_card(0, use_weapon=True)
        self.assertTrue(event["new_dungeon"])
        self.assertEqual(game.status, "playing")
        self.assertEqual(game.dungeon_number, 2)
        self.assertEqual(game.cards_remaining, 44)
        self.assertEqual(len(set((*game.room, *game.dungeon))), 44)
        self.assertEqual(game.health, 14)
        self.assertEqual(game.weapon.value, 7)
        self.assertEqual(game.weapon_kills[0].value, 3)
        self.assertEqual(game.dungeons_cleared, 1)

    def test_marathon_first_dungeon_loss_scores_all_second_dungeon_monsters(self):
        deck = [Card(Suit.CLUBS, 14), Card(Suit.SPADES, 13)]
        game = GameState(deck=deck, mode="marathon")
        game.health = 3
        game.choose_card(0, use_weapon=False)
        self.assertEqual(game.health, -11)
        self.assertEqual(game.dungeons_cleared, 0)
        self.assertEqual(game.score, -232)  # -11, remaining 13, plus second dungeon's 208

    def test_classic_still_wins_after_short_final_room(self):
        game = GameState(deck=[Card(Suit.HEARTS, 2)], mode="classic")
        game.choose_card(0)
        self.assertEqual(game.status, "won")
        self.assertEqual(game.dungeons_cleared, 1)
        self.assertEqual(game.dungeon_number, 1)

    def test_marathon_only_wins_after_all_88_cards(self):
        game = GameState(seed=42, mode="marathon")
        actions = 0
        crossed_midpoint = False
        while game.status == "playing":
            # Keep this structural test alive; ordinary damage rules are tested separately.
            game.health = 10_000
            card = game.room[0]
            event = game.choose_card(0, False if card.kind == "monster" else None)
            crossed_midpoint |= bool(event.get("new_dungeon"))
            actions += 1
        self.assertTrue(crossed_midpoint)
        self.assertEqual(actions, 88)
        self.assertEqual(game.dungeon_number, 2)
        self.assertEqual(game.cards_remaining, 0)
        self.assertEqual(game.status, "won")
        self.assertEqual(game.dungeons_cleared, 2)


if __name__ == "__main__":
    unittest.main()
