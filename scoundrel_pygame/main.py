"""Polished Pygame front end for the base game of Scoundrel."""

from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass

try:
    import pygame
except ImportError:
    print("Pygame is not installed. Run: python -m pip install -r requirements.txt")
    raise SystemExit(1)

from scoundrel.engine import Card, GameState, RuleError


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
        self.health_flash = 0.0
        self.shake = 0.0
        self.particles: list[Particle] = []
        self.rng = random.Random()
        self.started_at = time.monotonic()
        self.last_tick = time.monotonic()
        self.bg = self.make_background()

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

    def show_toast(self, message: str, duration=2.2) -> None:
        self.toast = (message.replace("♣", " Clubs").replace("♠", " Spades")
                      .replace("♥", " Hearts").replace("♦", " Diamonds"))
        self.toast_until = time.monotonic() + duration

    def new_game(self) -> None:
        self.game = GameState()
        self.scene = "game"
        self.overlay = None
        self.combat_index = None
        self.room_entered_at = time.monotonic()
        self.started_at = time.monotonic()
        self.particles.clear()
        self.show_toast("The dungeon has been shuffled.")

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
        self.show_toast(self.game.message)
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

    def handle_action(self, key: str) -> None:
        if key == "start" or key == "new":
            self.new_game()
        elif key == "quit":
            self.running = False
        elif key == "rules":
            self.overlay = "rules"
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
        self.button("start", pygame.Rect(495, 568, 290, 58), "BEGIN DESCENT", primary=True)
        self.button("rules", pygame.Rect(495, 642, 138, 48), "HOW TO PLAY")
        self.button("quit", pygame.Rect(647, 642, 138, 48), "QUIT")
        self.text("Original game by Zach Gage & Kurt Bieg  •  Pygame fan implementation", "tiny", (102, 120, 116), (640, 756), "center")

    def draw_health_panel(self) -> None:
        assert self.game
        rect = pygame.Rect(38, 138, 220, 390)
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
        ]
        for i, (label, value) in enumerate(stats):
            y = 333 + i * 41
            self.text(label, "small", MUTED, (64, y))
            self.text(value, "small", INK, (230, y), "topright")

    def draw_weapon_panel(self) -> None:
        assert self.game
        rect = pygame.Rect(1022, 138, 220, 390)
        self.panel(rect)
        self.text("EQUIPPED", "tiny", GOLD, (1048, 163))
        if not self.game.weapon:
            pygame.draw.circle(self.canvas, MUTED, (1132, 232), 18, width=2)
            pygame.draw.line(self.canvas, MUTED, (1120, 244), (1144, 220), 3)
            self.text("Bare hands", "subhead", INK, (1132, 291), "center")
            self.text("Monsters deal", "small", MUTED, (1132, 333), "center")
            self.text("their full value", "small", MUTED, (1132, 355), "center")
        else:
            weapon = self.game.weapon
            mini = pygame.Rect(1074, 196, 116, 150)
            pygame.draw.rect(self.canvas, (229, 234, 229), mini, border_radius=12)
            pygame.draw.rect(self.canvas, BLUE, mini, width=3, border_radius=12)
            self.text(weapon.rank, "card", CARD_INK, (1090, 207))
            self.suit_icon(self.canvas, "diamonds", mini.center, 48, RED)
            self.text(f"POWER  {weapon.value}", "button", INK, (1132, 372), "center")
            if self.game.weapon_limit is None:
                limit = "Any monster"
                note = "Unused"
            else:
                limit = f"Value ≤ {self.game.weapon_limit}"
                note = f"{len(self.game.weapon_kills)} slain"
            self.text(limit, "small", GOLD, (1132, 411), "center")
            self.text(note, "tiny", MUTED, (1132, 442), "center")
        self.text("Weapons stay until replaced.", "tiny", MUTED, (1132, 490), "center")

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
        self.text("THE DUNGEON", "tiny", GOLD, (40, 67))
        self.button("new", pygame.Rect(1054, 29, 88, 38), "NEW")
        self.button("rules", pygame.Rect(1152, 29, 90, 38), "RULES")
        pygame.draw.line(self.canvas, (76, 98, 93), (38, 92), (1242, 92), 1)

        self.draw_health_panel()
        self.draw_weapon_panel()

        final = self.game.is_final_room
        room_title = "FINAL CHAMBER" if final else f"ROOM {self.game.room_number:02d}"
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
        if not self.game.can_avoid:
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

        self.text("1–4 choose  •  R avoid  •  H rules  •  N new run", "tiny", (111, 134, 129), (640, 764), "center")
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
        img = self.fonts["small"].render(self.toast, True, INK)
        rect = pygame.Rect(0, 0, img.get_width() + 42, 44)
        rect.center = (640, 610)
        alpha = int(230 * clamp(remaining / .25, 0, 1))
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (16, 24, 24, alpha), layer.get_rect(), border_radius=20)
        layer.blit(img, img.get_rect(center=layer.get_rect().center))
        self.canvas.blit(layer, rect)

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
            self.text(f"Your weapon is bound to monsters value ≤ {self.game.weapon_limit}.", "small", RED, (640, 498), "center")
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
            ("3  WEAPONS — DIAMONDS", "Equipping is mandatory. After a kill, that weapon can only fight monsters no stronger than its last victim."),
            ("4  POTIONS — HEARTS", "Heal the card's value, up to 20 health. Only the first potion in each room heals."),
            ("5  AVOID", "Before acting, move the whole room to the dungeon's bottom. You cannot avoid twice in a row."),
            ("6  SURVIVE", "Clear the short final chamber to win. If you die, every unfaced monster worsens your negative score."),
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

    def draw_gameover(self) -> None:
        assert self.game
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 8, 9, 210))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(365, 126, 550, 550)
        self.panel(rect, color=(24, 34, 35, 255), radius=25, border=(224, 181, 92, 90))
        won = self.game.status == "won"
        self.text("DUNGEON CLEARED" if won else "THE DUNGEON CLAIMS YOU", "subhead", GOLD if won else RED, (640, 174), "center")
        self.text("FINAL SCORE", "tiny", MUTED, (640, 226), "center")
        self.text(str(self.game.score), "title", INK, (640, 291), "center")

        mins, secs = divmod(int(time.monotonic() - self.started_at), 60)
        stats = [
            ("Health", str(self.game.health)),
            ("Rooms faced", str(self.game.rooms_faced + (1 if won else 0))),
            ("Monsters slain", str(self.game.monsters_defeated)),
            ("Time", f"{mins:02d}:{secs:02d}"),
        ]
        for i, (label, value) in enumerate(stats):
            x = 430 + (i % 2) * 225
            y = 368 + (i // 2) * 70
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
            elif self.overlay == "gameover":
                self.draw_gameover()
            self.present()
        pygame.quit()


if __name__ == "__main__":
    ScoundrelApp().run()
