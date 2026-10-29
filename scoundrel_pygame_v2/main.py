"""Polished Pygame front end for the base game of Scoundrel."""

from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Pygame is not installed. Run: python -m pip install -r requirements.txt")
    raise SystemExit(1)

from scoundrel.engine import Card, GameState, RuleError
from scoundrel.settings import SettingsStore


WIDTH, HEIGHT = 1280, 800
FPS = 60

INK = (231, 235, 229)
MUTED = (149, 160, 157)
GOLD = (224, 181, 92)
RED = (214, 76, 81)
GREEN = (78, 193, 139)
BLUE = (91, 146, 225)
PANEL = (20, 29, 31)
PANEL_2 = (27, 38, 39)
FELT_TOP = (20, 58, 52)
FELT_BOTTOM = (10, 31, 31)
CREAM = (237, 232, 215)
CARD_INK = (33, 35, 35)

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ease_out(t: float) -> float:
    return 1 - (1 - clamp(t, 0, 1)) ** 3


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple[int, int, int]
    radius: float


class ScoundrelApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Scoundrel — Card Dungeon")
        self.window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene = "title"
        self.overlay: str | None = None
        self.game: GameState | None = None
        self.combat_index: int | None = None
        self.hitboxes: dict[str, pygame.Rect] = {}
        self.mouse = (0, 0)
        self.card_hover: dict[str, float] = {}
        self.room_entered_at = time.monotonic()
        self.toast = ""
        self.toast_until = 0.0
        self.toast_started = 0.0
        self.toast_duration = 2.2
        self.toast_color = INK
        self.health_flash = 0.0
        self.shake = 0.0
        self.particles: list[Particle] = []
        self.rng = random.Random()
        self.started_at = time.monotonic()
        self.last_tick = time.monotonic()
        self.bg = self.make_background()
        self.settings = SettingsStore(Path(__file__).with_name("settings.json"))

        self.fonts = {
            "tiny": pygame.font.SysFont("Avenir Next,Arial", 14),
            "small": pygame.font.SysFont("Avenir Next,Arial", 17),
            "body": pygame.font.SysFont("Avenir Next,Arial", 21),
            "button": pygame.font.SysFont("Avenir Next,Arial", 19, bold=True),
            "subhead": pygame.font.SysFont("Avenir Next,Arial", 27, bold=True),
            "heading": pygame.font.SysFont("Avenir Next,Arial", 42, bold=True),
            "title": pygame.font.SysFont("Georgia,Times New Roman", 82, bold=True),
            "card": pygame.font.SysFont("Georgia,Times New Roman", 43, bold=True),
            "suit": pygame.font.SysFont("Georgia,Times New Roman", 70),
            "number": pygame.font.SysFont("Avenir Next,Arial", 34, bold=True),
        }

    def make_background(self) -> pygame.Surface:
        surface = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            color = tuple(int(lerp(FELT_TOP[i], FELT_BOTTOM[i], t)) for i in range(3))
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))
        rng = random.Random(19)
        grain = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(2600):
            x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
            alpha = rng.randrange(3, 12)
            grain.set_at((x, y), (255, 255, 255, alpha))
        surface.blit(grain, (0, 0))
        return surface

    def virtual_mouse(self, pos: tuple[int, int]) -> tuple[int, int]:
        ww, wh = self.window.get_size()
        scale = min(ww / WIDTH, wh / HEIGHT)
        ox = (ww - WIDTH * scale) / 2
        oy = (wh - HEIGHT * scale) / 2
        return int((pos[0] - ox) / scale), int((pos[1] - oy) / scale)

    def text(self, value: str, font: str, color=INK, pos=(0, 0), anchor="topleft", surface=None):
        target = surface or self.canvas
        img = self.fonts[font].render(value, True, color)
        rect = img.get_rect()
        setattr(rect, anchor, pos)
        target.blit(img, rect)
        return rect

    def suit_icon(self, surface: pygame.Surface, suit: str, center: tuple[int, int], size: int,
                  color: tuple[int, int, int]) -> None:
        """Draw a suit without relying on font glyph availability."""
        cx, cy = center
        s = size
        if suit in ("hearts", "♥"):
            r = max(2, int(s * .27))
            pygame.draw.circle(surface, color, (int(cx - s * .22), int(cy - s * .12)), r)
            pygame.draw.circle(surface, color, (int(cx + s * .22), int(cy - s * .12)), r)
            pygame.draw.polygon(surface, color, [(int(cx - s * .49), int(cy - s * .04)),
                                                  (int(cx + s * .49), int(cy - s * .04)),
                                                  (cx, int(cy + s * .55))])
        elif suit in ("diamonds", "♦"):
            pygame.draw.polygon(surface, color, [(cx, int(cy - s * .58)),
                                                  (int(cx + s * .42), cy),
                                                  (cx, int(cy + s * .58)),
                                                  (int(cx - s * .42), cy)])
        elif suit in ("clubs", "♣"):
            r = max(2, int(s * .25))
            pygame.draw.circle(surface, color, (cx, int(cy - s * .23)), r)
            pygame.draw.circle(surface, color, (int(cx - s * .25), int(cy + s * .05)), r)
            pygame.draw.circle(surface, color, (int(cx + s * .25), int(cy + s * .05)), r)
            pygame.draw.polygon(surface, color, [(int(cx - s * .09), int(cy + s * .1)),
                                                  (int(cx + s * .09), int(cy + s * .1)),
                                                  (int(cx + s * .2), int(cy + s * .52)),
                                                  (int(cx - s * .2), int(cy + s * .52))])
        else:  # spades
            r = max(2, int(s * .24))
            pygame.draw.polygon(surface, color, [(cx, int(cy - s * .58)),
                                                  (int(cx - s * .47), int(cy + s * .02)),
                                                  (cx, int(cy + s * .22)),
                                                  (int(cx + s * .47), int(cy + s * .02))])
            pygame.draw.circle(surface, color, (int(cx - s * .23), int(cy + s * .02)), r)
            pygame.draw.circle(surface, color, (int(cx + s * .23), int(cy + s * .02)), r)
            pygame.draw.polygon(surface, color, [(int(cx - s * .08), int(cy + s * .12)),
                                                  (int(cx + s * .08), int(cy + s * .12)),
                                                  (int(cx + s * .2), int(cy + s * .53)),
                                                  (int(cx - s * .2), int(cy + s * .53))])

    def panel(self, rect: pygame.Rect, color=PANEL, radius=18, border=(255, 255, 255, 16)) -> None:
        shadow = pygame.Surface((rect.w + 18, rect.h + 18), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 70), (9, 9, rect.w, rect.h), border_radius=radius)
        self.canvas.blit(shadow, (rect.x - 9, rect.y - 5))
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, color, layer.get_rect(), border_radius=radius)
        pygame.draw.rect(layer, border, layer.get_rect(), width=1, border_radius=radius)
        self.canvas.blit(layer, rect)

    def button(self, key: str, rect: pygame.Rect, label: str, *, primary=False, enabled=True, danger=False) -> None:
        self.hitboxes[key] = rect
        hovered = enabled and rect.collidepoint(self.mouse)
        if not enabled:
            fill, text_color, border = (37, 45, 45), (91, 101, 99), (55, 64, 63)
        elif danger:
            fill = (151, 50, 55) if hovered else (116, 42, 47)
            text_color, border = INK, (224, 104, 108)
        elif primary:
            fill = (232, 190, 99) if hovered else GOLD
            text_color, border = (29, 32, 31), (252, 217, 142)
        else:
            fill = (49, 67, 66) if hovered else (34, 48, 48)
            text_color, border = INK, (83, 105, 101)
        if hovered:
            glow = pygame.Surface((rect.w + 12, rect.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*border, 35), glow.get_rect(), border_radius=15)
            self.canvas.blit(glow, (rect.x - 6, rect.y - 6))
        pygame.draw.rect(self.canvas, fill, rect, border_radius=11)
        pygame.draw.rect(self.canvas, border, rect, width=1, border_radius=11)
        self.text(label, "button", text_color, rect.center, "center")

    def show_toast(self, message: str, duration=2.2, color=INK) -> None:
        self.toast = (message.replace("♣", " Clubs").replace("♠", " Spades")
                      .replace("♥", " Hearts").replace("♦", " Diamonds"))
        self.toast_duration = duration
        self.toast_started = time.monotonic()
        self.toast_until = self.toast_started + duration
        self.toast_color = color

    def new_game(self, mode: str | None = None) -> None:
        if mode is None:
            mode = self.game.mode if self.game else "classic"
        self.game = GameState(
            mode=mode,
            allow_equal_weapon_kills=self.settings.values["allow_equal_weapon_kills"],
        )
        self.scene = "game"
        self.overlay = None
        self.combat_index = None
        self.room_entered_at = time.monotonic()
        self.started_at = time.monotonic()
        self.particles.clear()
        label = "Two dungeons. One life." if mode == "marathon" else "The dungeon has been shuffled."
        self.show_toast(label)

    def spawn_particles(self, x: float, y: float, color: tuple[int, int, int], count=14) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(35, 125)
            self.particles.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed - 28,
                                           self.rng.uniform(.45, .85), color, self.rng.uniform(2, 5)))

    def select_card(self, index: int) -> None:
        if (not self.game or self.overlay or self.combat_index is not None
                or self.game.status != "playing" or not 0 <= index < len(self.game.room)):
            return
        card = self.game.room[index]
        if card.kind == "monster":
            forced_barehand = not self.game.can_use_weapon(card)
            if forced_barehand and not self.settings.values["confirm_forced_barehand"]:
                self.resolve(index, False)
                return
            self.combat_index = index
            return
        self.resolve(index, None)

    def resolve(self, index: int, use_weapon: bool | None) -> None:
        if not self.game:
            return
        old_health = self.game.health
        card = self.game.room[index]
        try:
            event = self.game.choose_card(index, use_weapon)
        except RuleError as exc:
            self.show_toast(str(exc))
            return
        self.combat_index = None
        cx = 640
        color = {"weapon": BLUE, "potion": GREEN, "monster": RED}[card.kind]
        self.spawn_particles(cx, 385, color, 18)
        if self.game.health < old_health:
            self.health_flash = 1.0
            self.shake = min(11.0, 2 + (old_health - self.game.health) * .7)
        if event.get("new_room"):
            self.room_entered_at = time.monotonic()
        if event.get("new_dungeon"):
            self.show_toast(self.game.message, color=GOLD)
        elif card.kind == "potion":
            healed = int(event.get("healed", 0))
            self.show_toast(f"+{healed} HEALTH" if healed else "NO HEALTH GAIN", color=RED)
        elif card.kind == "weapon":
            self.show_toast(f"EQUIPPED {card.rank} DIAMONDS", color=CARD_INK)
        else:
            damage = int(event.get("damage", 0))
            if event.get("used_weapon") and self.game.weapon:
                blocked = min(card.value, self.game.weapon.value)
                result = f"{blocked} BLOCKED  •  " + (f"-{damage} HEALTH" if damage else "NO DAMAGE")
                self.show_toast(result, color=CARD_INK)
            else:
                self.show_toast(f"-{damage} HEALTH", color=RED)
        if self.game.status != "playing":
            self.overlay = "gameover"

    def avoid(self) -> None:
        if not self.game:
            return
        try:
            self.game.avoid_room()
        except RuleError as exc:
            self.show_toast(str(exc))
            return
        self.room_entered_at = time.monotonic()
        self.show_toast(self.game.message)

    def ruleset_locked(self) -> bool:
        """Rules variants are immutable from the start to the end of a run."""
        return bool(self.scene == "game" and self.game and self.game.status == "playing")

    def handle_action(self, key: str) -> None:
        if key == "start_classic":
            self.new_game("classic")
        elif key == "start_marathon":
            self.new_game("marathon")
        elif key == "new":
            self.new_game()
        elif key == "quit":
            self.running = False
        elif key == "rules":
            self.overlay = "rules"
        elif key == "settings":
            self.overlay = "settings"
        elif key == "toggle_forced_barehand":
            enabled = self.settings.toggle("confirm_forced_barehand")
            self.show_toast("Forced-combat confirmation on." if enabled else "Forced barehand fights are now automatic.")
        elif key == "toggle_equal_weapon_kills":
            if self.ruleset_locked():
                self.show_toast("Weapon-chain rules are locked for this run.")
                return
            enabled = self.settings.toggle("allow_equal_weapon_kills")
            self.show_toast("Equal-rank weapon kills allowed." if enabled else "Weapons now require strictly descending kills.")
        elif key in ("close", "resume"):
            self.overlay = None
        elif key == "title":
            self.scene, self.overlay, self.combat_index = "title", None, None
        elif key == "avoid":
            self.avoid()
        elif key.startswith("card_"):
            self.select_card(int(key.split("_")[1]))
        elif key == "combat_weapon" and self.combat_index is not None:
            self.resolve(self.combat_index, True)
        elif key == "combat_bare" and self.combat_index is not None:
            self.resolve(self.combat_index, False)
        elif key == "combat_cancel":
            self.combat_index = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = self.virtual_mouse(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            point = self.virtual_mouse(event.pos)
            for key, rect in reversed(list(self.hitboxes.items())):
                if rect.collidepoint(point):
                    self.handle_action(key)
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.combat_index is not None:
                    self.combat_index = None
                elif self.overlay:
                    self.overlay = None if self.overlay != "gameover" else self.overlay
                elif self.scene == "game":
                    self.scene = "title"
            elif event.key in (pygame.K_h, pygame.K_QUESTION) and self.overlay != "gameover":
                self.overlay = None if self.overlay == "rules" else "rules"
            elif event.key == pygame.K_s and self.overlay != "gameover":
                self.overlay = None if self.overlay == "settings" else "settings"
            elif event.key == pygame.K_n:
                self.new_game()
            elif self.scene == "game" and not self.overlay:
                if pygame.K_1 <= event.key <= pygame.K_4:
                    self.select_card(event.key - pygame.K_1)
                elif event.key == pygame.K_r:
                    self.avoid()
                elif self.combat_index is not None and event.key == pygame.K_w:
                    if self.game and self.game.can_use_weapon(self.game.room[self.combat_index]):
                        self.resolve(self.combat_index, True)
                elif self.combat_index is not None and event.key == pygame.K_b:
                    self.resolve(self.combat_index, False)

    def draw_title(self) -> None:
        self.canvas.blit(self.bg, (0, 0))
        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(12):
            alpha = int(5 + i * 2.5)
            pygame.draw.rect(vignette, (0, 0, 0, alpha), (i * 12, i * 9, WIDTH - i * 24, HEIGHT - i * 18), width=16)
        self.canvas.blit(vignette, (0, 0))

        now = time.monotonic()
        for i, (rank, suit, red) in enumerate((("A", "spades", False), ("9", "hearts", True), ("7", "diamonds", True), ("K", "clubs", False))):
            x = 215 + i * 220
            y = 145 + math.sin(now * 1.2 + i * .8) * 5
            angle = (-8 + i * 5)
            mini = pygame.Surface((150, 205), pygame.SRCALPHA)
            pygame.draw.rect(mini, CREAM, mini.get_rect(), border_radius=14)
            c = RED if red else CARD_INK
            img = self.fonts["card"].render(rank, True, c)
            mini.blit(img, (16, 12))
            self.suit_icon(mini, suit, (75, 111), 54, c)
            rotated = pygame.transform.rotozoom(mini, angle, 1)
            self.canvas.blit(rotated, rotated.get_rect(center=(x + 75, y + 100)))

        self.text("S C O U N D R E L", "title", INK, (640, 415), "center")
        self.text("A ONE-DECK DESCENT", "small", GOLD, (640, 477), "center")
        self.text("Face the dungeon. Keep one card. Choose what it costs you.", "body", MUTED, (640, 521), "center")
        self.button("start_classic", pygame.Rect(412, 568, 218, 58), "CLASSIC  ×1", primary=True)
        self.button("start_marathon", pygame.Rect(650, 568, 218, 58), "MARATHON  ×2")
        self.button("rules", pygame.Rect(419, 646, 138, 44), "HOW TO PLAY")
        self.button("settings", pygame.Rect(571, 646, 138, 44), "SETTINGS")
        self.button("quit", pygame.Rect(723, 646, 138, 44), "QUIT")
        self.text("Original game by Zach Gage & Kurt Bieg  •  Pygame fan implementation", "tiny", (102, 120, 116), (640, 756), "center")

    def draw_health_panel(self) -> None:
        assert self.game
        rect = pygame.Rect(38, 138, 220, 580)
        self.panel(rect)
        self.text("VITALS", "tiny", GOLD, (64, 163))
        heart_color = (244, 97, 100) if self.health_flash > 0 else RED
        self.suit_icon(self.canvas, "hearts", (83, 218), 31, heart_color)
        self.text(str(self.game.health), "heading", INK, (118, 197))
        self.text("/ 20", "body", MUTED, (174, 214))
        bar = pygame.Rect(64, 251, 168, 10)
        pygame.draw.rect(self.canvas, (41, 52, 51), bar, border_radius=5)
        fill = bar.copy(); fill.w = int(bar.w * clamp(self.game.health / 20, 0, 1))
        if fill.w:
            pygame.draw.rect(self.canvas, heart_color, fill, border_radius=5)

        self.text("RUN", "tiny", GOLD, (64, 303))
        stats = [
            ("Room", str(self.game.room_number)),
            ("Cards left", str(self.game.cards_remaining)),
            ("Monsters", str(self.game.monsters_defeated)),
            ("Damage", str(self.game.damage_taken)),
            ("Rooms avoided", str(self.game.rooms_avoided)),
            ("Potions", str(self.game.potions_used)),
        ]
        for i, (label, value) in enumerate(stats):
            y = 333 + i * 41
            self.text(label, "small", MUTED, (64, y))
            self.text(value, "small", INK, (230, y), "topright")

    def draw_stack_card(self, card: Card, rect: pygame.Rect, rank_font: str = "subhead") -> None:
        """Draw a compact physical card for the weapon and its victims."""
        border = BLUE if card.kind == "weapon" else RED
        suit_color = RED if card.kind == "weapon" else CARD_INK
        shadow = pygame.Surface((rect.w + 10, rect.h + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 65), (6, 6, rect.w, rect.h), border_radius=11)
        self.canvas.blit(shadow, (rect.x - 5, rect.y - 4))
        pygame.draw.rect(self.canvas, CREAM, rect, border_radius=11)
        pygame.draw.rect(self.canvas, border, rect, width=3, border_radius=11)
        self.text(card.rank, rank_font, suit_color, (rect.x + 11, rect.y + 3))
        self.suit_icon(self.canvas, card.suit.value, (rect.right - 18, rect.y + 17), 10, suit_color)
        self.suit_icon(self.canvas, card.suit.value, rect.center, 35, suit_color)

    def draw_weapon_panel(self) -> None:
        assert self.game
        rect = pygame.Rect(1022, 138, 220, 580)
        self.panel(rect)
        if not self.game.weapon:
            ghost = pygame.Surface((136, 182), pygame.SRCALPHA)
            pygame.draw.rect(ghost, (120, 142, 136, 30), ghost.get_rect(), width=2, border_radius=13)
            pygame.draw.circle(ghost, (120, 142, 136, 35), (68, 88), 24, width=2)
            pygame.draw.line(ghost, (120, 142, 136, 35), (50, 108), (87, 69), 3)
            self.canvas.blit(ghost, (1064, 225))
            return

        kills = self.game.weapon_kills
        base_y = 158
        available_drop = 392
        step = min(44, max(14, available_drop // max(1, len(kills)))) if kills else 44
        rank_font = "subhead" if step >= 31 else "small" if step >= 21 else "tiny"
        self.draw_stack_card(self.game.weapon, pygame.Rect(1070, base_y, 124, 143), rank_font)
        if kills:
            for i, monster in enumerate(kills):
                stacked = pygame.Rect(1070, base_y + (i + 1) * step, 124, 143)
                visible_font = "subhead" if i == len(kills) - 1 else rank_font
                self.draw_stack_card(monster, stacked, visible_font)

    def draw_card(self, card: Card, index: int, rect: pygame.Rect, progress: float) -> None:
        key = f"card_{index}"
        hovered = rect.collidepoint(self.mouse) and self.combat_index is None and not self.overlay
        current = self.card_hover.get(key, 0.0)
        current += (1 if hovered else -1) * .13
        current = clamp(current, 0, 1)
        self.card_hover[key] = current
        rise = current * 13
        slide = (1 - ease_out(progress)) * 80
        draw_rect = rect.move(0, int(slide - rise))
        self.hitboxes[key] = draw_rect

        shadow = pygame.Surface((draw_rect.w + 24, draw_rect.h + 26), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(65 + current * 30)), (12, 13, draw_rect.w, draw_rect.h), border_radius=18)
        self.canvas.blit(shadow, (draw_rect.x - 12, draw_rect.y - 9))

        kind_color = {"monster": RED, "weapon": BLUE, "potion": GREEN}[card.kind]
        fill = tuple(min(255, c + int(current * 8)) for c in CREAM)
        pygame.draw.rect(self.canvas, fill, draw_rect, border_radius=17)
        pygame.draw.rect(self.canvas, kind_color, draw_rect, width=4 if hovered else 2, border_radius=17)

        suit_color = RED if card.kind in ("potion", "weapon") else CARD_INK
        self.text(card.rank, "card", suit_color, (draw_rect.x + 18, draw_rect.y + 12))
        self.suit_icon(self.canvas, card.suit.value, (draw_rect.x + 30, draw_rect.y + 67), 13, suit_color)
        self.suit_icon(self.canvas, card.suit.value, (draw_rect.centerx, draw_rect.y + 122), 47, suit_color)
        label = {"monster": "MONSTER", "weapon": "WEAPON", "potion": "POTION"}[card.kind]
        action = {"monster": f"DAMAGE  {card.value}", "weapon": f"POWER  {card.value}", "potion": f"HEAL  {card.value}"}[card.kind]
        self.text(label, "tiny", kind_color, (draw_rect.centerx, draw_rect.y + 186), "center")
        self.text(action, "button", CARD_INK, (draw_rect.centerx, draw_rect.y + 217), "center")
        self.text(str(index + 1), "tiny", (125, 127, 119), (draw_rect.centerx, draw_rect.bottom - 18), "center")

    def draw_game(self) -> None:
        assert self.game
        offset = int(math.sin(time.monotonic() * 48) * self.shake) if self.shake > .1 else 0
        self.canvas.blit(self.bg, (offset, 0))
        if offset > 0: self.canvas.blit(self.bg, (offset - WIDTH, 0))
        elif offset < 0: self.canvas.blit(self.bg, (offset + WIDTH, 0))

        self.text("SCOUNDREL", "subhead", INK, (38, 31))
        mode_label = "MARATHON MODE" if self.game.mode == "marathon" else "THE DUNGEON"
        self.text(mode_label, "tiny", GOLD, (40, 67))
        self.button("settings", pygame.Rect(930, 29, 114, 38), "SETTINGS")
        self.button("new", pygame.Rect(1054, 29, 88, 38), "NEW")
        self.button("rules", pygame.Rect(1152, 29, 90, 38), "RULES")
        pygame.draw.line(self.canvas, (76, 98, 93), (38, 92), (1242, 92), 1)

        self.draw_health_panel()
        self.draw_weapon_panel()

        final = self.game.is_final_room
        dungeon_tag = f"  •  DUNGEON {self.game.dungeon_number}/{self.game.dungeons_total}" if self.game.mode == "marathon" else ""
        room_title = ("FINAL CHAMBER" if final else f"ROOM {self.game.room_number:02d}") + dungeon_tag
        self.text(room_title, "subhead", GOLD if final else INK, (640, 135), "center")
        instruction = "Clear every remaining card" if final else f"Choose {self.game.actions_required - self.game.actions_this_room} more • one card carries forward"
        self.text(instruction, "small", MUTED, (640, 174), "center")

        count = len(self.game.room)
        card_w, card_h, gap = 170, 250, 22
        total = count * card_w + max(0, count - 1) * gap
        start_x = 640 - total // 2
        elapsed = time.monotonic() - self.room_entered_at
        for i, card in enumerate(self.game.room):
            rect = pygame.Rect(start_x + i * (card_w + gap), 224, card_w, card_h)
            progress = clamp((elapsed - i * .07) / .35, 0, 1)
            self.draw_card(card, i, rect, progress)

        avoid_text = "AVOID ROOM  [R]" if self.game.can_avoid else "AVOID UNAVAILABLE"
        self.button("avoid", pygame.Rect(508, 525, 264, 48), avoid_text, enabled=self.game.can_avoid)
        feedback_active = bool(self.toast and time.monotonic() <= self.toast_until + .08)
        if not self.game.can_avoid and not feedback_active:
            reason = "Face this room after avoiding the last." if self.game.previous_room_avoided else "A room can only be avoided before acting."
            if final: reason = "The final chamber cannot be avoided."
            self.text(reason, "tiny", MUTED, (640, 585), "center")

        legend = pygame.Rect(286, 631, 708, 84)
        self.panel(legend, color=(18, 31, 31, 225), radius=14)
        items = [("monster", "MONSTER", RED), ("diamonds", "WEAPON", BLUE), ("hearts", "POTION", GREEN)]
        for i, (symbol, label, color) in enumerate(items):
            x = 355 + i * 228
            if symbol == "monster":
                self.suit_icon(self.canvas, "spades", (x + 9, 666), 15, color)
                self.suit_icon(self.canvas, "clubs", (x + 29, 666), 15, color)
            else:
                self.suit_icon(self.canvas, symbol, (x + 18, 666), 18, color)
            self.text(label, "tiny", INK, (x + 46, 651))
            desc = ("Fight", "Equip", "Heal once/room")[i]
            self.text(desc, "tiny", MUTED, (x + 46, 674))

        self.text("1–4 choose  •  R avoid  •  H rules  •  S settings  •  N new run", "tiny", (111, 134, 129), (640, 764), "center")
        self.draw_particles()
        self.draw_toast()
        if self.combat_index is not None and not self.overlay:
            self.draw_combat()

    def draw_particles(self) -> None:
        for p in self.particles:
            alpha = int(255 * clamp(p.life * 1.7, 0, 1))
            layer = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(layer, (*p.color, alpha), (8, 8), max(1, int(p.radius)))
            self.canvas.blit(layer, (p.x - 8, p.y - 8))

    def draw_toast(self) -> None:
        remaining = self.toast_until - time.monotonic()
        if remaining <= 0 or not self.toast:
            return
        progress = clamp((time.monotonic() - self.toast_started) / self.toast_duration, 0, 1)
        y = int(616 - ease_out(min(1, progress / .72)) * 24)
        alpha = int(255 * clamp(remaining / .38, 0, 1))
        font = self.fonts["button"]
        img = font.render(self.toast, True, self.toast_color)
        dark_text = sum(self.toast_color) < 260
        shadow_color = (222, 216, 196) if dark_text else (3, 12, 13)
        shadow = font.render(self.toast, True, shadow_color)
        shadow.set_alpha(122 if dark_text else 158)

        # Build the text and its shadow once, then multiply the finished pixels'
        # alpha. Their visual relationship therefore cannot shift late in the fade.
        composed = pygame.Surface((img.get_width() + 8, img.get_height() + 9), pygame.SRCALPHA)
        composed.blit(shadow, (5, 5))
        composed.blit(img, (3, 2))
        composed.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        self.canvas.blit(composed, composed.get_rect(center=(640, y)))

    def draw_combat(self) -> None:
        assert self.game is not None and self.combat_index is not None
        if self.combat_index >= len(self.game.room):
            self.combat_index = None
            return
        card = self.game.room[self.combat_index]
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((2, 8, 9, 182))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(372, 187, 536, 426)
        self.panel(rect, color=(25, 35, 36, 255), radius=22, border=(224, 181, 92, 90))
        self.text("COMBAT", "tiny", GOLD, (640, 218), "center")
        name = f"{card.rank} OF {card.suit.value.upper()}"
        self.text(f"{name}  •  {card.value} DAMAGE", "heading", INK, (640, 270), "center")

        bare_damage = self.game.preview_damage(card, False)
        usable = self.game.can_use_weapon(card)
        weapon_damage = self.game.preview_damage(card, True) if usable else 0
        weapon_label = f"USE {self.game.weapon.rank} DIAMONDS  •  TAKE {weapon_damage}" if usable and self.game.weapon else "WEAPON CANNOT STRIKE"
        self.button("combat_weapon", pygame.Rect(430, 340, 420, 57), weapon_label, primary=usable, enabled=usable)
        self.button("combat_bare", pygame.Rect(430, 413, 420, 57), f"FIGHT BAREHANDED  •  TAKE {bare_damage}", danger=True)
        if self.game.weapon and not usable:
            operator = "≤" if self.game.allow_equal_weapon_kills else "<"
            self.text(f"Your weapon is bound to monsters value {operator} {self.game.weapon_limit}.", "small", RED, (640, 498), "center")
        else:
            self.text("Weapon use lowers its limit to this monster's value.", "small", MUTED, (640, 498), "center")
        self.button("combat_cancel", pygame.Rect(550, 536, 180, 40), "CANCEL  [ESC]")
        self.text("W use weapon  •  B barehanded", "tiny", MUTED, (640, 590), "center")

    def draw_rules(self) -> None:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 9, 218))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(178, 70, 924, 660)
        self.panel(rect, color=(23, 33, 34, 255), radius=24, border=(224, 181, 92, 80))
        self.text("HOW TO PLAY", "heading", INK, (230, 112))
        self.text("THE ORIGINAL 44-CARD RULESET", "tiny", GOLD, (232, 162))
        self.button("close", pygame.Rect(964, 104, 84, 40), "CLOSE")

        sections = [
            ("1  ENTER A ROOM", "Draw to four cards. Face three in any order; the untouched card begins the next room."),
            ("2  MONSTERS — CLUBS + SPADES", "Fight barehanded for full damage, or subtract your weapon's value from the hit."),
            ("3  WEAPONS — DIAMONDS", "Equipping is mandatory. Officially, later kills may be lower or equal; Settings offers a strict variant."),
            ("4  POTIONS — HEARTS", "Heal the card's value, up to 20 health. Only the first potion in each room heals."),
            ("5  AVOID", "Before acting, move the whole room to the dungeon's bottom. You cannot avoid twice in a row."),
            ("6  SURVIVE / MARATHON", "Clear the short final chamber to win—or carry health and weapon into a second 44-card dungeon."),
        ]
        for i, (heading, body) in enumerate(sections):
            col = i % 2
            row = i // 2
            x = 232 + col * 425
            y = 212 + row * 137
            self.text(heading, "button", (GREEN, RED, BLUE, GREEN, GOLD, RED)[i], (x, y))
            words = body.split()
            lines, line = [], ""
            for word in words:
                candidate = f"{line} {word}".strip()
                if self.fonts["small"].size(candidate)[0] > 360:
                    lines.append(line); line = word
                else: line = candidate
            lines.append(line)
            for j, content in enumerate(lines):
                self.text(content, "small", MUTED, (x, y + 34 + j * 24))
        self.text("TIP  Low monsters are often worth fighting barehanded to preserve a weapon's range.", "small", GOLD, (640, 657), "center")
        self.text("Press H or Esc to close", "tiny", MUTED, (640, 700), "center")

    def draw_settings(self) -> None:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 9, 218))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(285, 76, 710, 648)
        self.panel(rect, color=(23, 33, 34, 255), radius=24, border=(224, 181, 92, 80))
        self.text("SETTINGS", "heading", INK, (337, 118))
        self.text("SAVED AUTOMATICALLY TO SETTINGS.JSON", "tiny", GOLD, (339, 169))
        self.button("close", pygame.Rect(857, 112, 84, 40), "CLOSE")

        row = pygame.Rect(337, 210, 606, 148)
        pygame.draw.rect(self.canvas, (30, 43, 43), row, border_radius=16)
        pygame.draw.rect(self.canvas, (69, 89, 85), row, width=1, border_radius=16)
        self.text("CONFIRM FORCED BAREHAND FIGHTS", "button", INK, (366, 237))
        self.text("When your weapon cannot attack, optionally show", "small", MUTED, (366, 274))
        self.text("a confirmation before taking barehanded damage.", "small", MUTED, (366, 299))
        confirm = self.settings.values["confirm_forced_barehand"]
        self.button("toggle_forced_barehand", pygame.Rect(811, 246, 98, 48), "ON" if confirm else "OFF", primary=confirm)

        row = pygame.Rect(337, 382, 606, 165)
        pygame.draw.rect(self.canvas, (30, 43, 43), row, border_radius=16)
        pygame.draw.rect(self.canvas, (69, 89, 85), row, width=1, border_radius=16)
        self.text("ALLOW EQUAL-RANK WEAPON KILLS", "button", INK, (366, 409))
        self.text("On uses the official ≤ rule. Off requires each", "small", MUTED, (366, 446))
        self.text("weapon-assisted kill to be strictly lower than the last.", "small", MUTED, (366, 471))
        locked = self.ruleset_locked()
        equal = self.game.allow_equal_weapon_kills if locked and self.game else self.settings.values["allow_equal_weapon_kills"]
        self.button("toggle_equal_weapon_kills", pygame.Rect(811, 418, 98, 48), "ON" if equal else "OFF",
                    primary=equal, enabled=not locked)

        combat_behavior = "CONFIRMATION ON" if confirm else "AUTOMATIC FORCED COMBAT"
        rank_behavior = "OFFICIAL ≤ RULE" if equal else "STRICT DESCENDING VARIANT"
        if locked:
            rank_behavior += "  •  LOCKED FOR THIS RUN"
        self.text(combat_behavior, "small", GOLD if confirm else GREEN, (640, 590), "center")
        self.text(rank_behavior, "small", GREEN if equal else GOLD, (640, 620), "center")
        self.text("Press S or Esc to close", "tiny", MUTED, (640, 691), "center")

    def draw_gameover(self) -> None:
        assert self.game
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 9, 210))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(365, 126, 550, 550)
        self.panel(rect, color=(24, 34, 35, 255), radius=25, border=(224, 181, 92, 90))
        won = self.game.status == "won"
        marathon = self.game.mode == "marathon"
        victory_title = "MARATHON CLEARED" if won and self.game.mode == "marathon" else "DUNGEON CLEARED"
        self.text(victory_title if won else "THE DUNGEON CLAIMS YOU", "subhead", GOLD if won else RED, (640, 174), "center")
        self.text("FINAL SCORE", "tiny", MUTED, (640, 226), "center")
        self.text(str(self.game.score), "title", INK, (640, 275 if marathon else 291), "center")

        if marathon:
            cleared = self.game.dungeons_cleared
            self.text(f"DUNGEONS CLEARED  {cleared} / 2", "tiny", MUTED, (640, 333), "center")
            for i, numeral in enumerate(("I", "II")):
                cell = pygame.Rect(577 + i * 67, 351, 58, 32)
                complete = i < cleared
                fill = GOLD if complete else (38, 51, 51)
                border = (252, 217, 142) if complete else (76, 96, 92)
                pygame.draw.rect(self.canvas, fill, cell, border_radius=8)
                pygame.draw.rect(self.canvas, border, cell, width=1, border_radius=8)
                if complete:
                    pygame.draw.lines(self.canvas, CARD_INK, False,
                                      [(cell.x + 17, cell.y + 17), (cell.x + 25, cell.y + 24),
                                       (cell.x + 42, cell.y + 8)], 4)
                else:
                    self.text(numeral, "button", MUTED, cell.center, "center")

        mins, secs = divmod(int(time.monotonic() - self.started_at), 60)
        stats = [
            ("Health", str(self.game.health)),
            ("Rooms faced", str(self.game.rooms_faced)),
            ("Monsters slain", str(self.game.monsters_defeated)),
            ("Time", f"{mins:02d}:{secs:02d}"),
        ]
        for i, (label, value) in enumerate(stats):
            x = 430 + (i % 2) * 225
            y = (402 if marathon else 368) + (i // 2) * (62 if marathon else 70)
            self.text(label.upper(), "tiny", MUTED, (x, y))
            self.text(value, "subhead", INK, (x, y + 22))
        self.button("new", pygame.Rect(449, 532, 382, 56), "DESCEND AGAIN", primary=True)
        self.button("title", pygame.Rect(449, 603, 382, 42), "RETURN TO TITLE")

    def update(self, dt: float) -> None:
        self.health_flash = max(0, self.health_flash - dt * 2.8)
        self.shake *= .84
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx * dt; p.y += p.vy * dt
                p.vy += 120 * dt
                alive.append(p)
        self.particles = alive

    def present(self) -> None:
        ww, wh = self.window.get_size()
        scale = min(ww / WIDTH, wh / HEIGHT)
        size = (max(1, int(WIDTH * scale)), max(1, int(HEIGHT * scale)))
        frame = pygame.transform.smoothscale(self.canvas, size)
        self.window.fill((5, 11, 12))
        self.window.blit(frame, ((ww - size[0]) // 2, (wh - size[1]) // 2))
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, .05)
            self.mouse = self.virtual_mouse(pygame.mouse.get_pos())
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.hitboxes.clear()
            if self.scene == "title":
                self.draw_title()
            else:
                self.draw_game()
            if self.overlay == "rules":
                self.draw_rules()
            elif self.overlay == "settings":
                self.draw_settings()
            elif self.overlay == "gameover":
                self.draw_gameover()
            self.present()
        pygame.quit()


if __name__ == "__main__":
    ScoundrelApp().run()
