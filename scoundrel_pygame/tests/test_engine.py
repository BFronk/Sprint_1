import unittest

from scoundrel.engine import Card, GameState, RuleError, Suit, make_dungeon


class ScoundrelRulesTests(unittest.TestCase):
    def test_base_deck_has_correct_44_cards(self):
        deck = make_dungeon()
        self.assertEqual(len(deck), 44)
        self.assertEqual(sum(c.kind == "monster" for c in deck), 26)
        self.assertEqual(sum(c.kind == "weapon" for c in deck), 9)
        self.assertEqual(sum(c.kind == "potion" for c in deck), 9)

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


if __name__ == "__main__":
    unittest.main()
