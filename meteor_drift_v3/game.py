"""Meteor Drift V3 - persistent arcade action and a 15-mission campaign."""

from __future__ import annotations

import json
import math
import random
import sys
from array import array
from dataclasses import dataclass
from pathlib import Path
import pygame


WIDTH, HEIGHT = 960, 600
FPS = 60
BG = (5, 8, 20)
WHITE = (238, 244, 255)
CYAN = (72, 225, 255)
GOLD = (255, 200, 72)
RED = (255, 84, 104)
GREEN = (95, 255, 165)
PURPLE = (197, 105, 255)
PINK = (255, 105, 205)

MODES = (
    {"name": "CRUISE", "spawn": 1.22, "speed": 0.86, "shots": 0.68, "score": 1.0},
    {"name": "ARCADE", "spawn": 0.94, "speed": 1.0, "shots": 1.0, "score": 1.25},
    {"name": "ONSLAUGHT", "spawn": 0.68, "speed": 1.22, "shots": 1.45, "score": 1.75},
)

CAMPAIGN_MISSIONS = (
    {
        "title": "FIRST CONTACT",
        "story": "A Voidling scout wing blocks the route to the outer colonies.",
        "orders": "Earn 500 points and break through.",
        "objective": "score", "target": 500, "difficulty": 0, "monsters": 0.52,
        "mix": (0.85, 0.15, 0.0),
    },
    {
        "title": "THE SHATTERED BELT",
        "story": "The shortest path cuts through an unstable asteroid field.",
        "orders": "Survive the belt for 30 seconds.",
        "objective": "survive", "target": 30, "difficulty": 0, "monsters": 0.18,
        "mix": (0.8, 0.2, 0.0),
    },
    {
        "title": "SCOUT PURGE",
        "story": "The scouts found the colony route. None can carry it home.",
        "orders": "Destroy 10 enemy craft.",
        "objective": "enemies", "target": 10, "difficulty": 1, "monsters": 0.82,
        "mix": (0.65, 0.35, 0.0),
    },
    {
        "title": "NEEDLE STORM",
        "story": "Dartwings tear through the convoy faster than targeting computers can track.",
        "orders": "Destroy 6 Dartwings.",
        "objective": "darts", "target": 6, "difficulty": 1, "monsters": 0.78,
        "mix": (0.25, 0.70, 0.05),
    },
    {
        "title": "BROKEN SUPPLY LINE",
        "story": "Medical transports are pinned behind a living wall of attackers.",
        "orders": "Earn 900 points to clear the lane.",
        "objective": "score", "target": 900, "difficulty": 1, "monsters": 0.66,
        "mix": (0.55, 0.35, 0.10),
    },
    {
        "title": "THE IRON GATE",
        "story": "Armored Bulwarks guard the jump corridor into hostile space.",
        "orders": "Destroy 3 Bulwarks.",
        "objective": "brutes", "target": 3, "difficulty": 1, "monsters": 0.72,
        "mix": (0.40, 0.20, 0.40),
    },
    {
        "title": "THE RAZOR RUN",
        "story": "Charge the jump drive by skimming danger at impossible range.",
        "orders": "Score 4 near misses.",
        "objective": "near", "target": 4, "difficulty": 1, "monsters": 0.62,
        "mix": (0.45, 0.45, 0.10),
    },
    {
        "title": "THE BLACK CURRENT",
        "story": "A dark-matter tide is carrying the swarm straight toward you.",
        "orders": "Survive for 40 seconds.",
        "objective": "survive", "target": 40, "difficulty": 1, "monsters": 0.70,
        "mix": (0.50, 0.35, 0.15),
    },
    {
        "title": "HEART OF THE SWARM",
        "story": "Strike the gathering fleet before it becomes unstoppable.",
        "orders": "Destroy 18 enemy craft.",
        "objective": "enemies", "target": 18, "difficulty": 2, "monsters": 0.88,
        "mix": (0.45, 0.40, 0.15),
    },
    {
        "title": "HEAVY WEATHER",
        "story": "Bulwarks advance through the storm like moving fortresses.",
        "orders": "Destroy 6 Bulwarks.",
        "objective": "brutes", "target": 6, "difficulty": 1, "monsters": 0.82,
        "mix": (0.30, 0.20, 0.50),
    },
    {
        "title": "CROSSFIRE",
        "story": "Every enemy wing converges on the last surviving relay station.",
        "orders": "Earn 1,800 points.",
        "objective": "score", "target": 1800, "difficulty": 1, "monsters": 0.80,
        "mix": (0.40, 0.40, 0.20),
    },
    {
        "title": "GHOST CORRIDOR",
        "story": "The safe route is gone. Thread the swarm and trust your nerve.",
        "orders": "Score 7 near misses.",
        "objective": "near", "target": 7, "difficulty": 2, "monsters": 0.74,
        "mix": (0.35, 0.50, 0.15),
    },
    {
        "title": "ACE HUNT",
        "story": "Elite Dartwings have marked your ship as their final trophy.",
        "orders": "Destroy 15 Dartwings.",
        "objective": "darts", "target": 15, "difficulty": 1, "monsters": 0.88,
        "mix": (0.20, 0.68, 0.12),
    },
    {
        "title": "THE SIEGE LINE",
        "story": "Orion's shields are visible ahead—and so is the entire invasion fleet.",
        "orders": "Destroy 30 enemy craft.",
        "objective": "enemies", "target": 30, "difficulty": 1, "monsters": 0.92,
        "mix": (0.38, 0.42, 0.20),
    },
    {
        "title": "LAST STAND AT ORION",
        "story": "Hold the line until the colony shield reaches full power.",
        "orders": "Survive the final onslaught for 75 seconds.",
        "objective": "survive", "target": 75, "difficulty": 2, "monsters": 0.90,
        "mix": (0.34, 0.43, 0.23),
    },
)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def circle_hit(a: pygame.Vector2, ar: float, b: pygame.Vector2, br: float) -> bool:
    return a.distance_squared_to(b) < (ar + br) ** 2


def make_tone(frequency: float, duration: float, volume: float = 0.25) -> pygame.mixer.Sound | None:
    """Create a tiny synthesized sound, while remaining safe on silent systems."""
    if not pygame.mixer.get_init():
        return None
    sample_rate, _, channels = pygame.mixer.get_init()
    count = int(sample_rate * duration)
    samples = array("h")
    for i in range(count):
        fade = min(1.0, (count - i) / max(1, count * 0.25))
        value = int(32767 * volume * fade * math.sin(2 * math.pi * frequency * i / sample_rate))
        for _ in range(channels):
            samples.append(value)
    return pygame.mixer.Sound(buffer=samples)


def play(sound: pygame.mixer.Sound | None) -> None:
    if sound is not None:
        sound.play()


@dataclass
class Bullet:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    radius: int = 4

    def update(self, dt: float) -> None:
        self.pos += self.velocity * dt

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, WHITE, self.pos, self.radius + 2)
        pygame.draw.circle(screen, CYAN, self.pos, self.radius)


@dataclass
class EnemyBullet:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    radius: int = 6
    near_miss_checked: bool = False

    def __post_init__(self) -> None:
        self.previous_y = self.pos.y

    def update(self, dt: float) -> None:
        self.previous_y = self.pos.y
        self.pos += self.velocity * dt

    def draw(self, screen: pygame.Surface) -> None:
        tail = self.pos - self.velocity.normalize() * 12
        pygame.draw.line(screen, PINK, tail, self.pos, 5)
        pygame.draw.circle(screen, WHITE, self.pos, 3)


@dataclass
class Particle:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    color: tuple[int, int, int]
    life: float
    size: float

    def update(self, dt: float) -> None:
        self.pos += self.velocity * dt
        self.velocity *= 0.985
        self.life -= dt
        self.size = max(0, self.size - dt * 3)

    def draw(self, screen: pygame.Surface) -> None:
        if self.size > 0:
            pygame.draw.circle(screen, self.color, self.pos, int(self.size))


@dataclass
class Callout:
    pos: pygame.Vector2
    text: str
    life: float = 1.15

    def update(self, dt: float) -> None:
        self.pos.y -= 34 * dt
        self.life -= dt

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        alpha = int(255 * clamp(self.life / 0.3, 0, 1))
        label = font.render(self.text, True, WHITE)
        plate = pygame.Surface((label.get_width() + 34, label.get_height() + 16), pygame.SRCALPHA)
        color = (*GOLD, alpha)
        points = [(0, plate.get_height() // 2), (12, 0), (plate.get_width() - 12, 0),
                  (plate.get_width(), plate.get_height() // 2), (plate.get_width() - 12, plate.get_height()),
                  (12, plate.get_height())]
        pygame.draw.polygon(plate, (20, 12, 38, min(alpha, 220)), points)
        pygame.draw.polygon(plate, color, points, 2)
        label.set_alpha(alpha)
        plate.blit(label, label.get_rect(center=plate.get_rect().center))
        screen.blit(plate, plate.get_rect(center=self.pos))


class Asteroid:
    def __init__(self, level: int, speed_scale: float = 1.0) -> None:
        self.radius = random.randint(17, 38)
        self.pos = pygame.Vector2(random.randint(self.radius, WIDTH - self.radius), -self.radius)
        speed = (random.uniform(110, 180) + level * 12) * speed_scale
        self.velocity = pygame.Vector2(random.uniform(-45, 45), speed)
        self.previous_y = self.pos.y
        self.near_miss_checked = False
        self.rotation = random.uniform(0, 360)
        self.spin = random.uniform(-100, 100)
        self.hp = 2 if self.radius >= 32 else 1
        self.points = 20 if self.hp == 2 else 10
        count = random.randint(8, 11)
        self.shape = [
            (i * 360 / count, self.radius * random.uniform(0.78, 1.08))
            for i in range(count)
        ]

    def update(self, dt: float) -> None:
        self.previous_y = self.pos.y
        self.pos += self.velocity * dt
        self.rotation += self.spin * dt

    def draw(self, screen: pygame.Surface) -> None:
        points = []
        for angle, radius in self.shape:
            radians = math.radians(angle + self.rotation)
            points.append((self.pos.x + math.cos(radians) * radius,
                           self.pos.y + math.sin(radians) * radius))
        pygame.draw.polygon(screen, (44, 50, 72), points)
        pygame.draw.polygon(screen, (125, 137, 165), points, 2)
        shine = self.pos + pygame.Vector2(-self.radius * 0.25, -self.radius * 0.2)
        pygame.draw.circle(screen, (73, 80, 105), shine, max(3, self.radius // 5), 2)


class Alien:
    """A Galaga-like void monster that enters, strafes, fires, then dives away."""

    def __init__(self, level: int, speed_scale: float = 1.0, shot_scale: float = 1.0) -> None:
        self.enemy_kind = "voidling"
        self.radius = 22
        self.pos = pygame.Vector2(random.randint(55, WIDTH - 55), -35)
        self.previous_y = self.pos.y
        self.anchor_x = self.pos.x
        self.target_y = random.randint(105, 245)
        self.age = 0.0
        self.phase = random.random() * math.tau
        self.speed_scale = speed_scale
        self.shot_scale = shot_scale
        self.shot_timer = random.uniform(0.8, 1.8) / shot_scale
        self.hp = 2 + int(level >= 6)
        self.points = 45 + level * 3
        self.near_miss_checked = False

    def update(self, dt: float, player_pos: pygame.Vector2, level: int) -> EnemyBullet | None:
        self.age += dt
        self.previous_y = self.pos.y
        if self.age < 1.35:
            self.pos.y += (145 + level * 7) * self.speed_scale * dt
        elif self.age < 6.2:
            self.pos.x = self.anchor_x + math.sin(self.age * 2.4 + self.phase) * 85
            self.pos.y += (self.target_y - self.pos.y) * min(1.0, dt * 4)
        else:
            self.pos.x += math.sin(self.age * 3.8 + self.phase) * 95 * dt
            self.pos.y += (180 + level * 8) * self.speed_scale * dt

        self.pos.x = clamp(self.pos.x, self.radius, WIDTH - self.radius)
        self.shot_timer -= dt
        if 1.4 < self.age < 6.2 and self.shot_timer <= 0:
            self.shot_timer = random.uniform(1.15, 2.25) / self.shot_scale
            direction = player_pos - self.pos
            if direction.length_squared():
                direction = direction.normalize()
            speed = (220 + level * 9) * self.speed_scale
            return EnemyBullet(self.pos + (0, 18), direction * speed)
        return None

    def draw(self, screen: pygame.Surface) -> None:
        x, y = self.pos
        wing = 6 + math.sin(self.age * 8) * 4
        pygame.draw.polygon(screen, (82, 35, 112),
                            [(x - 28, y - wing), (x - 13, y - 15), (x, y - 8),
                             (x + 13, y - 15), (x + 28, y - wing), (x + 17, y + 16),
                             (x, y + 23), (x - 17, y + 16)])
        pygame.draw.polygon(screen, PURPLE,
                            [(x - 28, y - wing), (x - 13, y - 15), (x, y - 8),
                             (x + 13, y - 15), (x + 28, y - wing), (x + 17, y + 16),
                             (x, y + 23), (x - 17, y + 16)], 2)
        pygame.draw.circle(screen, PINK, (int(x - 8), int(y)), 4)
        pygame.draw.circle(screen, PINK, (int(x + 8), int(y)), 4)
        pygame.draw.circle(screen, WHITE, (int(x - 7), int(y - 1)), 1)
        pygame.draw.circle(screen, WHITE, (int(x + 9), int(y - 1)), 1)
        pygame.draw.arc(screen, PURPLE, (x - 11, y + 6, 22, 15), 0, math.pi, 2)


class Dartwing(Alien):
    """A fragile interceptor that zigzags aggressively and dives early."""

    def __init__(self, level: int, speed_scale: float = 1.0, shot_scale: float = 1.0) -> None:
        super().__init__(level, speed_scale, shot_scale)
        self.enemy_kind = "dartwing"
        self.radius = 17
        self.hp = 1
        self.points = 65 + level * 4
        self.target_y = random.randint(90, 180)
        self.shot_timer = random.uniform(0.7, 1.4) / shot_scale

    def update(self, dt: float, player_pos: pygame.Vector2, level: int) -> EnemyBullet | None:
        self.age += dt
        self.previous_y = self.pos.y
        if self.age < 0.9:
            self.pos.y += (210 + level * 9) * self.speed_scale * dt
        elif self.age < 3.8:
            self.pos.x = self.anchor_x + math.sin(self.age * 5.4 + self.phase) * 125
            self.pos.y += (self.target_y - self.pos.y) * min(1.0, dt * 5)
        else:
            self.pos.x += math.sin(self.age * 7.0 + self.phase) * 150 * dt
            self.pos.y += (300 + level * 12) * self.speed_scale * dt
        self.pos.x = clamp(self.pos.x, self.radius, WIDTH - self.radius)
        self.shot_timer -= dt
        if 1.0 < self.age < 3.8 and self.shot_timer <= 0:
            self.shot_timer = 99
            direction = player_pos - self.pos
            if direction.length_squared():
                direction = direction.normalize()
            return EnemyBullet(self.pos + (0, 12), direction * (270 + level * 10) * self.speed_scale, radius=5)
        return None

    def draw(self, screen: pygame.Surface) -> None:
        x, y = self.pos
        flicker = math.sin(self.age * 14) * 4
        points = [(x, y + 20), (x - 24 - flicker, y - 8), (x - 7, y - 3),
                  (x, y - 20), (x + 7, y - 3), (x + 24 + flicker, y - 8)]
        pygame.draw.polygon(screen, (32, 78, 118), points)
        pygame.draw.polygon(screen, CYAN, points, 2)
        pygame.draw.circle(screen, WHITE, (int(x), int(y - 4)), 3)


class Bulwark(Alien):
    """A slow armored enemy with extra health and heavy plasma shots."""

    def __init__(self, level: int, speed_scale: float = 1.0, shot_scale: float = 1.0) -> None:
        super().__init__(level, speed_scale, shot_scale)
        self.enemy_kind = "bulwark"
        self.radius = 31
        self.hp = 5
        self.points = 125 + level * 6
        self.target_y = random.randint(100, 205)
        self.shot_timer = random.uniform(1.1, 1.8) / shot_scale

    def update(self, dt: float, player_pos: pygame.Vector2, level: int) -> EnemyBullet | None:
        self.age += dt
        self.previous_y = self.pos.y
        if self.age < 1.8:
            self.pos.y += (96 + level * 4.5) * self.speed_scale * dt
        elif self.age < 8.5:
            self.pos.x = self.anchor_x + math.sin(self.age * 1.22 + self.phase) * 45
            self.pos.y += (self.target_y - self.pos.y) * min(1.0, dt * 3)
        else:
            self.pos.y += (114 + level * 6.2) * self.speed_scale * dt
        self.pos.x = clamp(self.pos.x, self.radius, WIDTH - self.radius)
        self.shot_timer -= dt
        if 1.9 < self.age < 8.5 and self.shot_timer <= 0:
            self.shot_timer = random.uniform(1.8, 2.7) / self.shot_scale
            direction = player_pos - self.pos
            if direction.length_squared():
                direction = direction.normalize()
            return EnemyBullet(self.pos + (0, 25), direction * (190 + level * 7) * self.speed_scale, radius=9)
        return None

    def return_to_top(self) -> None:
        """Start another attack pass without restoring damage already taken."""
        self.pos.update(random.randint(self.radius, WIDTH - self.radius), -self.radius)
        self.previous_y = self.pos.y
        self.anchor_x = self.pos.x
        self.target_y = random.randint(100, 205)
        self.age = 0.0
        self.phase = random.random() * math.tau
        self.shot_timer = random.uniform(1.1, 1.8) / self.shot_scale
        self.near_miss_checked = False

    def draw(self, screen: pygame.Surface) -> None:
        x, y = self.pos
        body = pygame.Rect(0, 0, 58, 44)
        body.center = self.pos
        pygame.draw.rect(screen, (90, 42, 48), body, border_radius=13)
        pygame.draw.rect(screen, RED, body, 3, border_radius=13)
        pygame.draw.polygon(screen, (55, 25, 38),
                            [(x - 38, y - 5), (x - 25, y - 24), (x - 18, y + 18),
                             (x + 18, y + 18), (x + 25, y - 24), (x + 38, y - 5)])
        pygame.draw.polygon(screen, RED,
                            [(x - 38, y - 5), (x - 25, y - 24), (x - 18, y + 18),
                             (x + 18, y + 18), (x + 25, y - 24), (x + 38, y - 5)], 2)
        pygame.draw.circle(screen, GOLD, (int(x), int(y)), 8)
        pygame.draw.circle(screen, WHITE, (int(x), int(y)), 3)


class PowerUp:
    COLORS = {"rapid": GREEN, "spread": GOLD, "shield": CYAN, "repair": RED}
    SYMBOLS = {"rapid": "R", "spread": "3", "shield": "S", "repair": "+"}

    def __init__(self, x: float, y: float, kind: str | None = None) -> None:
        self.pos = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 115)
        self.radius = 14
        self.phase = random.random() * math.tau
        self.kind = kind or random.choices(
            ("rapid", "spread", "shield", "repair"), weights=(36, 27, 25, 12), k=1
        )[0]

    def update(self, dt: float) -> None:
        self.pos += self.velocity * dt
        self.phase += dt * 5

    def draw(self, screen: pygame.Surface) -> None:
        pulse = 2 + int(math.sin(self.phase) * 2)
        color = self.COLORS[self.kind]
        pygame.draw.circle(screen, color, self.pos, self.radius + pulse, 2)
        pygame.draw.circle(screen, (20, 25, 48), self.pos, self.radius)
        pygame.draw.circle(screen, color, self.pos, self.radius, 2)
        font = pygame.font.Font(None, 24)
        symbol = font.render(self.SYMBOLS[self.kind], True, color)
        screen.blit(symbol, symbol.get_rect(center=self.pos))


class Player:
    def __init__(self) -> None:
        self.pos = pygame.Vector2(WIDTH / 2, HEIGHT - 80)
        self.radius = 18
        self.speed = 330
        self.cooldown = 0.0
        self.invulnerable = 0.0
        self.rapid_fire = 0.0
        self.spread_fire = 0.0
        self.shield = 0.0

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        direction = pygame.Vector2(
            int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a]),
            int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w]),
        )
        if direction.length_squared():
            direction = direction.normalize()
        self.pos += direction * self.speed * dt
        self.pos.x = clamp(self.pos.x, self.radius + 6, WIDTH - self.radius - 6)
        self.pos.y = clamp(self.pos.y, 70, HEIGHT - self.radius - 8)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.rapid_fire = max(0.0, self.rapid_fire - dt)
        self.spread_fire = max(0.0, self.spread_fire - dt)
        self.shield = max(0.0, self.shield - dt)

    def shoot(self) -> list[Bullet]:
        delay = 0.11 if self.rapid_fire > 0 else 0.24
        if self.cooldown > 0:
            return []
        self.cooldown = delay
        speed = 560 if self.rapid_fire > 0 else 520
        shots = [Bullet(self.pos + (0, -21), pygame.Vector2(0, -speed))]
        if self.spread_fire > 0:
            shots.extend([
                Bullet(self.pos + (-9, -16), pygame.Vector2(-145, -speed + 25)),
                Bullet(self.pos + (9, -16), pygame.Vector2(145, -speed + 25)),
            ])
        return shots

    def draw(self, screen: pygame.Surface) -> None:
        if self.invulnerable > 0 and int(self.invulnerable * 12) % 2 == 0:
            return
        x, y = self.pos
        if self.shield > 0:
            shield_radius = 27 + int(math.sin(pygame.time.get_ticks() * 0.009) * 2)
            pygame.draw.circle(screen, CYAN, self.pos, shield_radius, 2)
            pygame.draw.arc(screen, WHITE, (x - shield_radius, y - shield_radius,
                                             shield_radius * 2, shield_radius * 2), 0.2, 1.5, 2)
        pygame.draw.polygon(screen, (20, 98, 135), [(x - 18, y + 17), (x, y - 23), (x + 18, y + 17)])
        pygame.draw.polygon(screen, CYAN, [(x - 12, y + 13), (x, y - 15), (x + 12, y + 13)], 3)
        pygame.draw.circle(screen, WHITE, (int(x), int(y - 4)), 4)
        flame = random.randint(9, 17)
        pygame.draw.polygon(screen, GOLD, [(x - 6, y + 17), (x, y + 17 + flame), (x + 6, y + 17)])


class Game:
    def __init__(self, save_path: Path | None = None) -> None:
        pygame.init()
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        except pygame.error:
            pass
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Meteor Drift V3")
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 76)
        self.large_font = pygame.font.Font(None, 46)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 21)
        self.shoot_sound = make_tone(760, 0.055, 0.12)
        self.hit_sound = make_tone(165, 0.13, 0.20)
        self.power_sound = make_tone(1040, 0.18, 0.16)
        self.near_sound = make_tone(1280, 0.09, 0.10)
        self.stars = [
            [random.randrange(WIDTH), random.randrange(HEIGHT), random.uniform(20, 105), random.choice((1, 1, 1, 2))]
            for _ in range(105)
        ]
        self.save_path = save_path or Path(__file__).with_name("save_data.json")
        loaded = self.load_save_data()
        self.high_score = int(loaded.get("high_score", 0))
        campaign = loaded.get("campaign", {})
        self.campaign_resume_stage = int(clamp(int(campaign.get("resume_stage", 0)), 0, len(CAMPAIGN_MISSIONS)))
        self.campaign_checkpoint_stage = int(clamp(int(campaign.get("checkpoint_stage", 0)), 0,
                                                   len(CAMPAIGN_MISSIONS) - 1))
        self.campaign_resume_stats = self.normalize_stats(campaign.get("resume_stats", {}))
        self.campaign_checkpoint_stats = self.normalize_stats(campaign.get("checkpoint_stats", {}))
        self.campaign_completed = bool(campaign.get("completed", False))
        self.mode_index = 1
        self.arcade_mode_index = 1
        self.game_type = "arcade"
        self.campaign_stage = 0
        self.state = "title"
        self.reset()

    def reset(self) -> None:
        self.player = Player()
        self.bullets: list[Bullet] = []
        self.asteroids: list[Asteroid] = []
        self.aliens: list[Alien] = []
        self.enemy_bullets: list[EnemyBullet] = []
        self.powerups: list[PowerUp] = []
        self.particles: list[Particle] = []
        self.callouts: list[Callout] = []
        self.score = 0
        self.near_misses = 0
        self.aliens_destroyed = 0
        self.dartwings_destroyed = 0
        self.bulwarks_destroyed = 0
        self.lives = 3
        self.elapsed = 0.0
        self.mission_elapsed = 0.0
        self.mission_score_start = 0
        self.mission_aliens_start = 0
        self.mission_darts_start = 0
        self.mission_brutes_start = 0
        self.mission_near_start = 0
        self.spawn_timer = 0.5
        self.shake = 0.0
        self.restart_armed_until = 0
        self.checkpoint_pending = False

    @staticmethod
    def default_stats() -> dict[str, int]:
        return {"score": 0, "lives": 4, "near_misses": 0, "enemies": 0, "darts": 0, "brutes": 0}

    @classmethod
    def normalize_stats(cls, value: object) -> dict[str, int]:
        defaults = cls.default_stats()
        if not isinstance(value, dict):
            return defaults
        result = {}
        for key, default in defaults.items():
            try:
                result[key] = max(0, int(value.get(key, default)))
            except (TypeError, ValueError):
                result[key] = default
        result["lives"] = int(clamp(result["lives"], 1, 5))
        return result

    def load_save_data(self) -> dict[str, object]:
        if not self.save_path.exists():
            return {}
        try:
            with self.save_path.open("r", encoding="utf-8") as save_file:
                value = json.load(save_file)
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return {}

    def write_save_data(self) -> None:
        data = {
            "version": 1,
            "high_score": self.high_score,
            "campaign": {
                "resume_stage": self.campaign_resume_stage,
                "checkpoint_stage": self.campaign_checkpoint_stage,
                "resume_stats": self.campaign_resume_stats,
                "checkpoint_stats": self.campaign_checkpoint_stats,
                "completed": self.campaign_completed,
            },
        }
        temporary = self.save_path.with_suffix(".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as save_file:
                json.dump(data, save_file, indent=2, sort_keys=True)
            temporary.replace(self.save_path)
        except OSError:
            pass

    def stats_snapshot(self, lives: int | None = None) -> dict[str, int]:
        return {
            "score": self.score,
            "lives": self.lives if lives is None else lives,
            "near_misses": self.near_misses,
            "enemies": self.aliens_destroyed,
            "darts": self.dartwings_destroyed,
            "brutes": self.bulwarks_destroyed,
        }

    def apply_stats(self, stats: dict[str, int]) -> None:
        self.score = stats["score"]
        self.lives = stats["lives"]
        self.near_misses = stats["near_misses"]
        self.aliens_destroyed = stats["enemies"]
        self.dartwings_destroyed = stats["darts"]
        self.bulwarks_destroyed = stats["brutes"]

    @property
    def mission(self) -> dict[str, object]:
        return CAMPAIGN_MISSIONS[self.campaign_stage]

    def start_arcade(self) -> None:
        self.game_type = "arcade"
        self.mode_index = self.arcade_mode_index
        self.reset()
        self.state = "playing"

    def start_campaign(self) -> None:
        self.game_type = "campaign"
        self.reset()
        if self.campaign_completed or self.campaign_resume_stage >= len(CAMPAIGN_MISSIONS):
            self.apply_stats(self.campaign_resume_stats)
            self.campaign_stage = len(CAMPAIGN_MISSIONS) - 1
            self.state = "campaign_complete"
            return
        self.campaign_stage = self.campaign_resume_stage
        self.apply_stats(self.campaign_resume_stats)
        self.prepare_mission()

    def start_new_campaign(self) -> None:
        self.campaign_resume_stage = 0
        self.campaign_checkpoint_stage = 0
        self.campaign_resume_stats = self.default_stats()
        self.campaign_checkpoint_stats = self.default_stats()
        self.campaign_completed = False
        self.write_save_data()
        self.start_campaign()

    def resume_checkpoint(self) -> None:
        self.game_type = "campaign"
        self.reset()
        self.campaign_stage = self.campaign_checkpoint_stage
        self.apply_stats(self.campaign_checkpoint_stats)
        self.prepare_mission()

    def prepare_mission(self) -> None:
        self.mode_index = int(self.mission["difficulty"])
        self.player = Player()
        self.bullets.clear()
        self.asteroids.clear()
        self.aliens.clear()
        self.enemy_bullets.clear()
        self.powerups.clear()
        self.particles.clear()
        self.callouts.clear()
        self.mission_elapsed = 0.0
        self.mission_score_start = self.score
        self.mission_aliens_start = self.aliens_destroyed
        self.mission_darts_start = self.dartwings_destroyed
        self.mission_brutes_start = self.bulwarks_destroyed
        self.mission_near_start = self.near_misses
        self.spawn_timer = 0.65
        self.restart_armed_until = 0
        self.state = "mission_brief"

    def mission_progress(self) -> tuple[int, int]:
        target = int(self.mission["target"])
        objective = self.mission["objective"]
        if objective == "score":
            current = self.score - self.mission_score_start
        elif objective == "survive":
            current = int(self.mission_elapsed)
        elif objective == "enemies":
            current = self.aliens_destroyed - self.mission_aliens_start
        elif objective == "darts":
            current = self.dartwings_destroyed - self.mission_darts_start
        elif objective == "brutes":
            current = self.bulwarks_destroyed - self.mission_brutes_start
        else:
            current = self.near_misses - self.mission_near_start
        return min(current, target), target

    def mission_progress_label(self) -> str:
        current, target = self.mission_progress()
        units = {"score": "POINTS", "survive": "SECONDS", "enemies": "ENEMIES", "darts": "DARTWINGS",
                 "brutes": "BULWARKS", "near": "NEAR MISSES"}
        return f"{units[str(self.mission['objective'])]}  {current} / {target}"

    def complete_mission(self) -> None:
        bonus = 250 * (self.campaign_stage + 1)
        self.score += bonus
        self.high_score = max(self.high_score, self.score)
        next_stage = self.campaign_stage + 1
        self.checkpoint_pending = next_stage < len(CAMPAIGN_MISSIONS) and next_stage % 3 == 0
        next_lives = 5 if self.checkpoint_pending else min(5, self.lives + 1)
        self.campaign_resume_stage = next_stage
        self.campaign_resume_stats = self.stats_snapshot(next_lives)
        if self.checkpoint_pending:
            self.campaign_checkpoint_stage = next_stage
            self.campaign_checkpoint_stats = dict(self.campaign_resume_stats)
        if next_stage >= len(CAMPAIGN_MISSIONS):
            self.campaign_completed = True
        self.write_save_data()
        self.state = "mission_complete"
        self.restart_armed_until = 0

    def advance_campaign(self) -> None:
        if self.campaign_stage + 1 >= len(CAMPAIGN_MISSIONS):
            self.state = "campaign_complete"
            return
        self.campaign_stage += 1
        self.apply_stats(self.campaign_resume_stats)
        self.checkpoint_pending = False
        self.prepare_mission()

    def restart_run(self) -> None:
        if self.game_type == "campaign":
            self.resume_checkpoint()
        else:
            self.start_arcade()

    def request_restart(self) -> None:
        now = pygame.time.get_ticks()
        if self.restart_armed_until and now <= self.restart_armed_until:
            self.restart_run()
        else:
            self.restart_armed_until = now + 750

    @property
    def level(self) -> int:
        return 1 + self.score // 180

    @property
    def combat_level(self) -> int:
        """Keep late campaign speed skill-based instead of letting cumulative score make it explode."""
        if self.game_type == "campaign" and self.campaign_stage >= 6:
            return 7 + (self.campaign_stage - 6) % 3
        return self.level

    @property
    def mode(self) -> dict[str, float | str]:
        return MODES[self.mode_index]

    def add_score(self, points: int) -> int:
        earned = max(1, int(points * float(self.mode["score"])))
        self.score += earned
        return earned

    def burst(self, pos: pygame.Vector2, color: tuple[int, int, int], count: int = 12) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(45, 210)
            self.particles.append(Particle(pos.copy(), pygame.Vector2(math.cos(angle), math.sin(angle)) * speed,
                                           color, random.uniform(0.25, 0.7), random.uniform(2, 5)))

    def damage_player(self) -> None:
        if self.player.invulnerable > 0:
            return
        if self.player.shield > 0:
            self.player.shield = 0
            self.player.invulnerable = 0.7
            self.shake = 0.18
            self.burst(self.player.pos, CYAN, 24)
            self.callouts.append(Callout(self.player.pos + (0, -45), "SHIELD SAVED YOU"))
            play(self.power_sound)
            return
        self.lives -= 1
        self.player.invulnerable = 2.0
        self.shake = 0.35
        self.burst(self.player.pos, RED, 24)
        play(self.hit_sound)
        if self.lives <= 0:
            self.high_score = max(self.high_score, self.score)
            self.state = "game_over"
            self.restart_armed_until = 0
            self.write_save_data()

    def award_near_miss(self, pos: pygame.Vector2, gap: float) -> None:
        closeness = clamp(1.0 - gap / 58.0, 0, 1)
        base = 45 + int(closeness * 35)
        earned = self.add_score(base)
        self.near_misses += 1
        self.callouts.append(Callout(pos.copy() + (0, -32), f"NEAR MISS  +{earned}"))
        self.burst(pos, GOLD, 8)
        play(self.near_sound)

    def check_near_miss(self, hazard: Asteroid | Alien | EnemyBullet) -> None:
        if hazard.near_miss_checked or hazard.previous_y > self.player.pos.y or hazard.pos.y <= self.player.pos.y:
            return
        hazard.near_miss_checked = True
        gap = abs(hazard.pos.x - self.player.pos.x) - hazard.radius - self.player.radius
        if 3 <= gap <= 58:
            self.award_near_miss((hazard.pos + self.player.pos) / 2, gap)

    def drop_powerup(self, pos: pygame.Vector2, chance: float) -> None:
        if random.random() < chance:
            self.powerups.append(PowerUp(pos.x, pos.y))

    def apply_powerup(self, powerup: PowerUp) -> None:
        if powerup.kind == "rapid":
            self.player.rapid_fire = 8.0
            label = "RAPID FIRE"
        elif powerup.kind == "spread":
            self.player.spread_fire = 9.0
            label = "TRIPLE SHOT"
        elif powerup.kind == "shield":
            self.player.shield = 12.0
            label = "ENERGY SHIELD"
        else:
            self.lives = min(5, self.lives + 1)
            label = "LIFE RESTORED"
        earned = self.add_score(25)
        self.callouts.append(Callout(powerup.pos.copy() + (0, -30), f"{label}  +{earned}"))
        self.burst(powerup.pos, PowerUp.COLORS[powerup.kind], 18)
        play(self.power_sound)

    def update_stars(self, dt: float) -> None:
        for star in self.stars:
            star[1] += star[2] * dt
            if star[1] > HEIGHT:
                star[0] = random.randrange(WIDTH)
                star[1] = 0

    def update(self, dt: float) -> None:
        self.update_stars(dt)
        if self.state != "playing":
            return
        self.elapsed += dt
        if self.game_type == "campaign":
            self.mission_elapsed += dt
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        if keys[pygame.K_SPACE]:
            new_bullets = self.player.shoot()
            if new_bullets:
                self.bullets.extend(new_bullets)
                play(self.shoot_sound)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            speed_scale = float(self.mode["speed"])
            if self.game_type == "campaign":
                monster_chance = float(self.mission["monsters"])
                enemy_mix = tuple(float(value) for value in self.mission["mix"])
            else:
                monster_chance = min(0.78, 0.34 + self.level * 0.055)
                dart_chance = min(0.38, max(0.0, (self.combat_level - 1) * 0.055))
                brute_chance = min(0.22, max(0.0, (self.combat_level - 3) * 0.035))
                enemy_mix = (1.0 - dart_chance - brute_chance, dart_chance, brute_chance)
            if random.random() < monster_chance and len(self.aliens) < 8:
                enemy_roll = random.random()
                if enemy_roll < enemy_mix[0]:
                    enemy = Alien(self.combat_level, speed_scale, float(self.mode["shots"]))
                elif enemy_roll < enemy_mix[0] + enemy_mix[1]:
                    enemy = Dartwing(self.combat_level, speed_scale, float(self.mode["shots"]))
                else:
                    enemy = Bulwark(self.combat_level, speed_scale, float(self.mode["shots"]))
                self.aliens.append(enemy)
            else:
                self.asteroids.append(Asteroid(self.combat_level, speed_scale))
            base_interval = max(0.24, random.uniform(0.54, 0.88) - self.combat_level * 0.036)
            self.spawn_timer = base_interval * float(self.mode["spawn"])

        for bullet in self.bullets:
            bullet.update(dt)
        for asteroid in self.asteroids:
            asteroid.update(dt)
        for alien in self.aliens:
            shot = alien.update(dt, self.player.pos, self.combat_level)
            if shot is not None:
                self.enemy_bullets.append(shot)
        for enemy_bullet in self.enemy_bullets:
            enemy_bullet.update(dt)
        for powerup in self.powerups:
            powerup.update(dt)
        for particle in self.particles:
            particle.update(dt)
        for callout in self.callouts:
            callout.update(dt)

        self.bullets = [b for b in self.bullets if -30 < b.pos.y and -30 < b.pos.x < WIDTH + 30]
        self.particles = [p for p in self.particles if p.life > 0]
        self.callouts = [c for c in self.callouts if c.life > 0]

        targets: list[Asteroid | Alien] = [*self.asteroids, *self.aliens]
        destroyed: set[Asteroid | Alien] = set()
        spent: set[int] = set()
        for target in targets:
            for index, bullet in enumerate(self.bullets):
                if index not in spent and circle_hit(target.pos, target.radius, bullet.pos, bullet.radius):
                    spent.add(index)
                    target.hp -= 1
                    self.burst(bullet.pos, GOLD, 5)
                    if target.hp <= 0:
                        destroyed.add(target)
                        self.add_score(target.points)
                        if isinstance(target, Alien):
                            self.aliens_destroyed += 1
                            if target.enemy_kind == "dartwing":
                                self.dartwings_destroyed += 1
                            elif target.enemy_kind == "bulwark":
                                self.bulwarks_destroyed += 1
                        color = PURPLE if isinstance(target, Alien) else GOLD
                        self.burst(target.pos, color, 18)
                        play(self.hit_sound)
                        self.drop_powerup(target.pos, 0.19 if isinstance(target, Alien) else 0.11)
                    break
        self.bullets = [b for i, b in enumerate(self.bullets) if i not in spent]

        asteroid_survivors = []
        for asteroid in self.asteroids:
            if asteroid in destroyed:
                continue
            if circle_hit(asteroid.pos, asteroid.radius * 0.82, self.player.pos, self.player.radius):
                self.damage_player()
                self.burst(asteroid.pos, (150, 160, 190), 14)
                continue
            self.check_near_miss(asteroid)
            if asteroid.pos.y - asteroid.radius > HEIGHT:
                continue
            asteroid_survivors.append(asteroid)
        self.asteroids = asteroid_survivors

        alien_survivors = []
        for alien in self.aliens:
            if alien in destroyed:
                continue
            if circle_hit(alien.pos, alien.radius * 0.88, self.player.pos, self.player.radius):
                self.damage_player()
                self.burst(alien.pos, PURPLE, 18)
                continue
            self.check_near_miss(alien)
            if alien.pos.y - alien.radius > HEIGHT:
                if isinstance(alien, Bulwark):
                    alien.return_to_top()
                    alien_survivors.append(alien)
                continue
            alien_survivors.append(alien)
        self.aliens = alien_survivors

        enemy_shot_survivors = []
        for enemy_bullet in self.enemy_bullets:
            if circle_hit(enemy_bullet.pos, enemy_bullet.radius, self.player.pos, self.player.radius):
                self.damage_player()
                self.burst(enemy_bullet.pos, PINK, 9)
                continue
            self.check_near_miss(enemy_bullet)
            if -30 < enemy_bullet.pos.x < WIDTH + 30 and enemy_bullet.pos.y < HEIGHT + 30:
                enemy_shot_survivors.append(enemy_bullet)
        self.enemy_bullets = enemy_shot_survivors

        kept_powerups = []
        for powerup in self.powerups:
            if circle_hit(powerup.pos, powerup.radius, self.player.pos, self.player.radius):
                self.apply_powerup(powerup)
            elif powerup.pos.y < HEIGHT + 20:
                kept_powerups.append(powerup)
        self.powerups = kept_powerups
        self.shake = max(0.0, self.shake - dt)
        if self.game_type == "campaign" and self.state == "playing":
            current, target = self.mission_progress()
            if current >= target:
                self.complete_mission()

    def text(self, message: str, font: pygame.font.Font, color: tuple[int, int, int], center: tuple[int, int]) -> None:
        surface = font.render(message, True, color)
        self.screen.blit(surface, surface.get_rect(center=center))

    def draw_background(self) -> None:
        self.screen.fill(BG)
        for x, y, speed, size in self.stars:
            shade = int(clamp(100 + speed, 110, 205))
            pygame.draw.circle(self.screen, (shade, shade, min(255, shade + 25)), (int(x), int(y)), size)
        pygame.draw.line(self.screen, (16, 28, 55), (0, 55), (WIDTH, 55), 1)

    def draw_hud(self) -> None:
        score = self.font.render(f"SCORE  {self.score:05d}", True, WHITE)
        if self.game_type == "campaign":
            center_text = f"MISSION {self.campaign_stage + 1}/{len(CAMPAIGN_MISSIONS)}  •  {self.mode['name']}"
        else:
            center_text = f"WAVE {self.level}  •  {self.mode['name']}"
        level = self.font.render(center_text, True, CYAN)
        self.screen.blit(score, (20, 17))
        self.screen.blit(level, (WIDTH // 2 - level.get_width() // 2, 17))
        near = self.small_font.render(f"NEAR MISSES  {self.near_misses}", True, GOLD)
        self.screen.blit(near, (20, 40))
        if self.game_type == "campaign":
            progress = self.small_font.render(self.mission_progress_label(), True, WHITE)
            self.screen.blit(progress, (WIDTH // 2 - progress.get_width() // 2, 40))
        for i in range(self.lives):
            x = WIDTH - 24 - i * 27
            pygame.draw.polygon(self.screen, RED, [(x - 9, 29), (x, 16), (x + 9, 29), (x, 25)])
        effects = []
        if self.player.rapid_fire > 0:
            effects.append(("RAPID", self.player.rapid_fire, 8.0, GREEN))
        if self.player.spread_fire > 0:
            effects.append(("TRIPLE", self.player.spread_fire, 9.0, GOLD))
        if self.player.shield > 0:
            effects.append(("SHIELD", self.player.shield, 12.0, CYAN))
        for index, (label, remaining, maximum, color) in enumerate(effects):
            x = 20 + index * 125
            width = int(108 * remaining / maximum)
            pygame.draw.rect(self.screen, (25, 38, 55), (x, HEIGHT - 20, 108, 7), border_radius=4)
            pygame.draw.rect(self.screen, color, (x, HEIGHT - 20, width, 7), border_radius=4)
            self.screen.blit(self.small_font.render(label, True, color), (x, HEIGHT - 42))
        if self.restart_armed_until and pygame.time.get_ticks() <= self.restart_armed_until:
            prompt = self.font.render("PRESS R AGAIN TO RESTART", True, RED)
            plate = pygame.Rect(0, 0, prompt.get_width() + 30, prompt.get_height() + 14)
            plate.center = (WIDTH // 2, HEIGHT - 48)
            pygame.draw.rect(self.screen, (35, 8, 18), plate, border_radius=7)
            pygame.draw.rect(self.screen, RED, plate, 2, border_radius=7)
            self.screen.blit(prompt, prompt.get_rect(center=plate.center))

    def draw(self) -> None:
        self.draw_background()
        if self.state == "title":
            self.text("METEOR DRIFT V3", self.title_font, CYAN, (WIDTH // 2, 78))
            self.text("ARCADE SURVIVAL  +  A 15-MISSION SAVED CAMPAIGN", self.font, PURPLE, (WIDTH // 2, 128))
            self.text("CHOOSE YOUR FLIGHT", self.small_font, (135, 150, 180), (WIDTH // 2, 180))
            choices = (("arcade", "A  ARCADE", 350), ("campaign", "C  CAMPAIGN", 610))
            for kind, label, center_x in choices:
                selected = self.game_type == kind
                rect = pygame.Rect(0, 0, 220, 50)
                rect.center = (center_x, 220)
                pygame.draw.rect(self.screen, (25, 35, 65) if selected else (10, 15, 32), rect, border_radius=8)
                pygame.draw.rect(self.screen, GOLD if selected else (65, 78, 110), rect, 2, border_radius=8)
                self.text(label, self.font, GOLD if selected else WHITE, rect.center)
            if self.game_type == "arcade":
                self.text("SELECT CHALLENGE WITH 1 / 2 / 3", self.small_font, (135, 150, 180),
                          (WIDTH // 2, 284))
                for index, mode in enumerate(MODES):
                    center_x = 260 + index * 220
                    selected = index == self.arcade_mode_index
                    rect = pygame.Rect(0, 0, 180, 46)
                    rect.center = (center_x, 325)
                    pygame.draw.rect(self.screen, (25, 35, 65) if selected else (10, 15, 32), rect, border_radius=8)
                    pygame.draw.rect(self.screen, GOLD if selected else (65, 78, 110), rect, 2, border_radius=8)
                    self.text(f"{index + 1}  {mode['name']}", self.font,
                              GOLD if selected else WHITE, rect.center)
                detail = "Chase an endless high score as the waves accelerate."
            else:
                self.text("15 MISSIONS  •  NEW ENEMIES  •  AUTOSAVE  •  CHECKPOINTS",
                          self.font, GOLD, (WIDTH // 2, 310))
                if self.campaign_completed:
                    detail = "Campaign complete. Press C to view your victory or N to begin again."
                elif self.campaign_resume_stage > 0:
                    detail = (f"Resume Mission {self.campaign_resume_stage + 1}  •  "
                              f"Protected checkpoint: Mission {self.campaign_checkpoint_stage + 1}")
                else:
                    detail = "Cross the frontier and defend Orion from the expanding swarm."
            self.text(detail, self.font, WHITE, (WIDTH // 2, 370))
            self.text("MOVE  •  WASD / Arrows       FIRE  •  Hold Space", self.font,
                      (175, 190, 215), (WIDTH // 2, 416))
            self.text("P pause  •  R twice restart  •  Esc quit", self.small_font,
                      (120, 135, 165), (WIDTH // 2, 452))
            if self.game_type == "campaign":
                self.text("C resume campaign  •  N start a new campaign", self.small_font,
                          (120, 135, 165), (WIDTH // 2, 478))
            if int(pygame.time.get_ticks() / 500) % 2:
                self.text("PRESS ENTER TO LAUNCH", self.large_font, GOLD, (WIDTH // 2, 515))
        else:
            offset = pygame.Vector2(random.randint(-6, 6), random.randint(-6, 6)) if self.shake > 0 else pygame.Vector2()
            world = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for bullet in self.bullets:
                bullet.draw(world)
            for asteroid in self.asteroids:
                asteroid.draw(world)
            for alien in self.aliens:
                alien.draw(world)
            for enemy_bullet in self.enemy_bullets:
                enemy_bullet.draw(world)
            for powerup in self.powerups:
                powerup.draw(world)
            for particle in self.particles:
                particle.draw(world)
            self.player.draw(world)
            for callout in self.callouts:
                callout.draw(world, self.small_font)
            self.screen.blit(world, offset)
            self.draw_hud()

            if self.state == "paused":
                veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                veil.fill((2, 4, 12, 185))
                self.screen.blit(veil, (0, 0))
                self.text("PAUSED", self.title_font, WHITE, (WIDTH // 2, HEIGHT // 2 - 20))
                self.text("Press P to continue", self.font, CYAN, (WIDTH // 2, HEIGHT // 2 + 45))
            elif self.state == "mission_brief":
                veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                veil.fill((3, 5, 16, 225))
                self.screen.blit(veil, (0, 0))
                self.text(f"MISSION {self.campaign_stage + 1} OF {len(CAMPAIGN_MISSIONS)}",
                          self.small_font, CYAN, (WIDTH // 2, 150))
                self.text(str(self.mission["title"]), self.large_font, GOLD, (WIDTH // 2, 205))
                self.text(str(self.mission["story"]), self.font, WHITE, (WIDTH // 2, 275))
                self.text(str(self.mission["orders"]), self.font, PURPLE, (WIDTH // 2, 326))
                self.text(f"Lives remaining: {self.lives}", self.small_font, (150, 165, 195),
                          (WIDTH // 2, 374))
                self.text("PRESS ENTER TO BEGIN", self.large_font, CYAN, (WIDTH // 2, 450))
            elif self.state == "mission_complete":
                veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                veil.fill((3, 14, 18, 220))
                self.screen.blit(veil, (0, 0))
                self.text("MISSION COMPLETE", self.title_font, GREEN, (WIDTH // 2, 190))
                self.text(str(self.mission["title"]), self.large_font, WHITE, (WIDTH // 2, 260))
                bonus = 250 * (self.campaign_stage + 1)
                self.text(f"Mission bonus  +{bonus}     Total score  {self.score}", self.font, GOLD,
                          (WIDTH // 2, 328))
                reward = ("CHECKPOINT READY — full repairs and progress protected."
                          if self.checkpoint_pending else "A life will be restored before the next mission.")
                self.text(reward, self.small_font, CYAN,
                          (WIDTH // 2, 372))
                self.text("PRESS ENTER TO CONTINUE", self.large_font, WHITE, (WIDTH // 2, 448))
            elif self.state == "checkpoint":
                veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                veil.fill((3, 15, 20, 230))
                self.screen.blit(veil, (0, 0))
                checkpoint_number = (self.campaign_stage + 1) // 3
                self.text("CHECKPOINT SECURED", self.title_font, GREEN, (WIDTH // 2, 175))
                self.text(f"SECTOR {checkpoint_number} COMPLETE  •  MISSIONS {self.campaign_stage - 1}–{self.campaign_stage + 1}",
                          self.font, CYAN, (WIDTH // 2, 245))
                self.text("Progress saved  •  Hull fully repaired  •  New sector unlocked",
                          self.font, WHITE, (WIDTH // 2, 310))
                self.text(f"If you fall, you return at Mission {self.campaign_stage + 2}.",
                          self.small_font, GOLD, (WIDTH // 2, 356))
                self.text("PRESS ENTER TO CONTINUE", self.large_font, GREEN, (WIDTH // 2, 440))
            elif self.state == "game_over":
                veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                veil.fill((8, 3, 10, 200))
                self.screen.blit(veil, (0, 0))
                self.text("MISSION FAILED" if self.game_type == "campaign" else "SHIP LOST",
                          self.title_font, RED, (WIDTH // 2, 205))
                self.text(f"Score  {self.score}     Best  {self.high_score}", self.large_font, WHITE,
                          (WIDTH // 2, 292))
                summary = (f"Mission {self.campaign_stage + 1}  •  Near misses {self.near_misses}"
                           if self.game_type == "campaign"
                           else f"{self.mode['name']}  •  Near misses {self.near_misses}")
                self.text(summary, self.font, CYAN,
                          (WIDTH // 2, 343))
                self.text("Enter to restart  •  Or press R twice", self.font, GOLD,
                          (WIDTH // 2, 395))
                self.text("Esc to quit", self.small_font, (140, 150, 175), (WIDTH // 2, 435))
            elif self.state == "campaign_complete":
                veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                veil.fill((4, 10, 24, 225))
                self.screen.blit(veil, (0, 0))
                self.text("ORION SAVED", self.title_font, GOLD, (WIDTH // 2, 170))
                self.text("CAMPAIGN COMPLETE", self.large_font, CYAN, (WIDTH // 2, 235))
                self.text(f"Final score  {self.score}     Near misses  {self. 
                                                                        ar_misses}",
                          self.font, WHITE, (WIDTH // 2, 310))
                self.text("The colony lights answer across the dark. You made it home.",
                          self.font, PURPLE, (WIDTH // 2, 362))
                self.text("PRESS ENTER FOR TITLE", self.large_font, GOLD, (WIDTH // 2, 450))
        pygame.display.flip()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            self.high_score = max(self.high_score, self.score)
            self.write_save_data()
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.high_score = max(self.high_score, self.score)
                self.write_save_data()
                return False
            if self.state == "title" and event.key == pygame.K_a:
                self.game_type = "arcade"
            if self.state == "title" and event.key == pygame.K_c:
                self.game_type = "campaign"
            if self.state == "title" and event.key == pygame.K_n:
                self.game_type = "campaign"
                self.start_new_campaign()
            if (event.key in (pygame.K_1, pygame.K_2, pygame.K_3)
                    and self.state == "title" and self.game_type == "arcade"):
                self.arcade_mode_index = event.key - pygame.K_1
                self.mode_index = self.arcade_mode_index
            if event.key == pygame.K_r and self.state != "title":
                self.request_restart()
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.state == "title":
                    if self.game_type == "campaign":
                        self.start_campaign()
                    else:
                        self.start_arcade()
                elif self.state == "game_over":
                    self.restart_run()
                elif self.state == "mission_brief":
                    self.state = "playing"
                elif self.state == "mission_complete":
                    if self.checkpoint_pending:
                        self.state = "checkpoint"
                    else:
                        self.advance_campaign()
                elif self.state == "checkpoint":
                    self.advance_campaign()
                elif self.state == "campaign_complete":
                    self.state = "title"
            if event.key == pygame.K_p:
                if self.state == "playing":
                    self.state = "paused"
                elif self.state == "paused":
                    self.state = "playing"
        return True

    def run(self) -> None:
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                running = self.handle_event(event) and running
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    try:
        Game().run()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit(0)
