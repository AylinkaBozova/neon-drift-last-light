import math
import random
import sys
from dataclasses import dataclass

import pygame

# ============================================================
# NEON DRIFT
# A complete single-file arcade game made with Python + Pygame.
# No external images, sounds, or fonts are required.
# ============================================================

pygame.init()
pygame.mixer.quit()

WIDTH, HEIGHT = 1200, 720
FPS = 60
TITLE = "NEON DRIFT // LAST LIGHT"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# Fonts
FONT_BIG = pygame.font.Font(None, 86)
FONT_HUGE = pygame.font.Font(None, 128)
FONT_MED = pygame.font.Font(None, 34)
FONT_SMALL = pygame.font.Font(None, 24)
FONT_TINY = pygame.font.Font(None, 18)

# Colors
BLACK = (4, 6, 16)
WHITE = (240, 248, 255)
CYAN = (54, 240, 255)
PINK = (255, 58, 174)
PURPLE = (146, 80, 255)
YELLOW = (255, 221, 70)
GREEN = (75, 255, 145)
RED = (255, 72, 90)
BLUE = (75, 125, 255)

# Game states
MENU = "menu"
PLAYING = "playing"
PAUSED = "paused"
GAME_OVER = "game_over"
VICTORY = "victory"


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lerp(a, b, t):
    return a + (b - a) * t


def draw_text(surface, text, font, color, pos, center=False, shadow=True):
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        sh_rect = sh.get_rect()
        if center:
            sh_rect.center = (pos[0] + 3, pos[1] + 3)
        else:
            sh_rect.topleft = (pos[0] + 3, pos[1] + 3)
        surface.blit(sh, sh_rect)
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(img, rect)


def glow_circle(surface, pos, radius, color, alpha=90):
    # Cheap soft glow without external assets.
    size = int(radius * 4)
    if size <= 2:
        return
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for r in range(int(radius * 1.9), max(1, int(radius * 0.55)), -3):
        a = int(alpha * (1 - (r - radius * 0.55) / (radius * 1.35)))
        a = clamp(a, 0, alpha)
        pygame.draw.circle(glow, (*color, a), (cx, cy), r)
    surface.blit(glow, (int(pos[0] - cx), int(pos[1] - cy)))


def polygon_center(points):
    x = sum(p[0] for p in points) / len(points)
    y = sum(p[1] for p in points) / len(points)
    return x, y


class Particle:
    def __init__(self, x, y, color, speed=100, life=0.6, size=3):
        angle = random.uniform(0, math.tau)
        velocity = random.uniform(speed * 0.25, speed)
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * velocity
        self.color = color
        self.life = life * random.uniform(0.7, 1.25)
        self.max_life = self.life
        self.size = random.uniform(size * 0.5, size * 1.4)

    def update(self, dt):
        self.pos += self.vel * dt
        self.vel *= 0.94 ** (dt * 60)
        self.life -= dt
        return self.life > 0

    def draw(self, surface, camera):
        ratio = max(0, self.life / self.max_life)
        p = self.pos - camera
        radius = max(1, int(self.size * ratio))
        pygame.draw.circle(surface, (*self.color, int(220 * ratio)), (int(p.x), int(p.y)), radius)


class Star:
    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.z = random.uniform(0.2, 1.0)
        self.twinkle = random.uniform(0, math.tau)

    def update(self, dt, speed):
        self.y += speed * self.z * dt * 0.18
        self.twinkle += dt * (1 + self.z * 4)
        if self.y > HEIGHT + 5:
            self.y = -5
            self.x = random.uniform(0, WIDTH)

    def draw(self, surface):
        brightness = int(90 + 120 * self.z * (0.75 + 0.25 * math.sin(self.twinkle)))
        c = (brightness // 2, brightness, brightness)
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), max(1, int(self.z * 2)))


class Bullet:
    def __init__(self, x, y, velocity):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(velocity)
        self.life = 1.4
        self.radius = 5

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
        return self.life > 0 and -50 < self.pos.x < WIDTH + 50 and -50 < self.pos.y < HEIGHT + 50

    def draw(self, surface, camera):
        p = self.pos - camera
        glow_circle(surface, p, 7, CYAN, 70)
        pygame.draw.circle(surface, WHITE, (int(p.x), int(p.y)), self.radius)
        pygame.draw.circle(surface, CYAN, (int(p.x), int(p.y)), self.radius - 2)


class Enemy:
    def __init__(self, x, y, kind, difficulty):
        self.pos = pygame.Vector2(x, y)
        self.kind = kind
        self.phase = random.uniform(0, math.tau)
        self.hit_flash = 0

        if kind == "hunter":
            self.radius = 18
            self.hp = 2 + int(difficulty * 0.15)
            self.max_hp = self.hp
            self.speed = 115 + difficulty * 5
            self.color = PINK
            self.score = 150
        elif kind == "tank":
            self.radius = 30
            self.hp = 8 + int(difficulty * 0.45)
            self.max_hp = self.hp
            self.speed = 55 + difficulty * 2
            self.color = PURPLE
            self.score = 450
        else:
            self.radius = 14
            self.hp = 1 + int(difficulty * 0.08)
            self.max_hp = self.hp
            self.speed = 180 + difficulty * 7
            self.color = YELLOW
            self.score = 250

    def update(self, dt, target):
        self.phase += dt * 4
        direction = target - self.pos
        distance = max(1, direction.length())
        direction.normalize_ip()

        if self.kind == "hunter":
            wiggle = pygame.Vector2(-direction.y, direction.x) * math.sin(self.phase) * 0.45
            velocity = (direction + wiggle).normalize() * self.speed
        elif self.kind == "tank":
            velocity = direction * self.speed
        else:
            velocity = direction * self.speed * (1 + 0.12 * math.sin(self.phase * 2))

        self.pos += velocity * dt
        self.hit_flash = max(0, self.hit_flash - dt)

    def hit(self, damage):
        self.hp -= damage
        self.hit_flash = 0.09
        return self.hp <= 0

    def draw(self, surface, camera):
        p = self.pos - camera
        color = WHITE if self.hit_flash > 0 else self.color
        glow_circle(surface, p, self.radius * 1.2, self.color, 45)

        if self.kind == "tank":
            points = []
            for i in range(8):
                a = i * math.tau / 8 + math.pi / 8
                r = self.radius if i % 2 == 0 else self.radius * 0.78
                points.append((p.x + math.cos(a) * r, p.y + math.sin(a) * r))
            pygame.draw.polygon(surface, color, points, width=3)
            pygame.draw.circle(surface, color, (int(p.x), int(p.y)), 7, width=2)
        elif self.kind == "hunter":
            points = [
                (p.x, p.y - self.radius),
                (p.x + self.radius, p.y + self.radius),
                (p.x, p.y + self.radius * 0.45),
                (p.x - self.radius, p.y + self.radius),
            ]
            pygame.draw.polygon(surface, color, points, width=3)
        else:
            pygame.draw.circle(surface, color, (int(p.x), int(p.y)), self.radius, width=3)
            pygame.draw.line(surface, color,
                             (int(p.x - 8), int(p.y)),
                             (int(p.x + 8), int(p.y)), 3)
            pygame.draw.line(surface, color,
                             (int(p.x), int(p.y - 8)),
                             (int(p.x), int(p.y + 8)), 3)

        # HP bar
        if self.max_hp > 2:
            w = self.radius * 2
            ratio = clamp(self.hp / self.max_hp, 0, 1)
            pygame.draw.rect(surface, (30, 30, 50),
                             (p.x - w / 2, p.y - self.radius - 11, w, 4))
            pygame.draw.rect(surface, self.color,
                             (p.x - w / 2, p.y - self.radius - 11, w * ratio, 4))


class Pickup:
    TYPES = ("energy", "shield", "overdrive")

    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.kind = random.choices(self.TYPES, weights=[55, 25, 20])[0]
        self.life = 10
        self.phase = random.uniform(0, math.tau)
        self.radius = 12

    def update(self, dt):
        self.life -= dt
        self.phase += dt * 5
        return self.life > 0

    def draw(self, surface, camera):
        p = self.pos - camera
        pulse = 1 + 0.15 * math.sin(self.phase)
        color = {"energy": CYAN, "shield": GREEN, "overdrive": YELLOW}[self.kind]
        glow_circle(surface, p, 18 * pulse, color, 45)
        pygame.draw.circle(surface, color, (int(p.x), int(p.y)), int(10 * pulse), width=2)
        if self.kind == "energy":
            pygame.draw.polygon(surface, color, [
                (p.x + 2, p.y - 8),
                (p.x - 3, p.y + 1),
                (p.x + 1, p.y + 1),
                (p.x - 2, p.y + 9),
                (p.x + 6, p.y - 2),
                (p.x + 2, p.y - 2)
            ])
        elif self.kind == "shield":
            pygame.draw.circle(surface, color, (int(p.x), int(p.y)), 6, width=2)
            pygame.draw.line(surface, color, (p.x - 5, p.y), (p.x + 5, p.y), 2)
        else:
            pygame.draw.line(surface, color, (p.x - 7, p.y), (p.x + 7, p.y), 2)
            pygame.draw.line(surface, color, (p.x, p.y - 7), (p.x, p.y + 7), 2)


class Boss:
    def __init__(self, difficulty):
        self.pos = pygame.Vector2(WIDTH / 2, -120)
        self.target_y = 145
        self.radius = 74
        self.max_hp = 220 + difficulty * 14
        self.hp = self.max_hp
        self.phase = 0
        self.shoot_timer = 1.5
        self.dash_timer = 4.0
        self.flash = 0
        self.alive = True

    def update(self, dt, player_pos, bullets):
        self.phase += dt
        self.flash = max(0, self.flash - dt)

        if self.pos.y < self.target_y:
            self.pos.y = lerp(self.pos.y, self.target_y, min(1, dt * 1.8))

        # Hovering movement
        self.pos.x = WIDTH / 2 + math.sin(self.phase * 0.75) * 330

        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 0.8
            base = math.atan2(player_pos.y - self.pos.y, player_pos.x - self.pos.x)
            for offset in (-0.22, -0.11, 0, 0.11, 0.22):
                a = base + offset
                bullets.append(
                    EnemyBullet(self.pos.x, self.pos.y + 35,
                                pygame.Vector2(math.cos(a), math.sin(a)) * 230)
                )

    def hit(self, damage):
        self.hp -= damage
        self.flash = 0.08
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surface, camera):
        p = self.pos - camera
        color = WHITE if self.flash > 0 else RED
        glow_circle(surface, p, self.radius * 1.35, RED, 55)

        points = []
        for i in range(12):
            a = i * math.tau / 12 + self.phase * 0.15
            r = self.radius if i % 2 == 0 else self.radius * 0.78
            points.append((p.x + math.cos(a) * r, p.y + math.sin(a) * r))
        pygame.draw.polygon(surface, color, points, width=4)

        pygame.draw.circle(surface, color, (int(p.x), int(p.y)), 25, width=3)
        pygame.draw.circle(surface, RED, (int(p.x), int(p.y)), 9)
        for i in range(4):
            a = self.phase * 0.5 + i * math.pi / 2
            end = (p.x + math.cos(a) * 52, p.y + math.sin(a) * 52)
            pygame.draw.line(surface, color, (p.x, p.y), end, 3)

        # Boss health bar
        w = 620
        x = WIDTH / 2 - w / 2
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        pygame.draw.rect(surface, (25, 15, 25), (x, 28, w, 14), border_radius=5)
        pygame.draw.rect(surface, RED, (x, 28, w * ratio, 14), border_radius=5)
        draw_text(surface, "THE WARDEN", FONT_SMALL, WHITE, (WIDTH / 2, 17), center=True)


class EnemyBullet:
    def __init__(self, x, y, velocity):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(velocity)
        self.radius = 6
        self.life = 5

    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, camera):
        p = self.pos - camera
        glow_circle(surface, p, 10, RED, 55)
        pygame.draw.circle(surface, RED, (int(p.x), int(p.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(p.x), int(p.y)), 2)


class Player:
    def __init__(self):
        self.pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.velocity = pygame.Vector2()
        self.radius = 18
        self.speed = 360
        self.hp = 100
        self.max_hp = 100
        self.energy = 100
        self.max_energy = 100
        self.shield = 0
        self.fire_timer = 0
        self.invuln = 0
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.overdrive = 0
        self.angle = -math.pi / 2
        self.trail_timer = 0

    def update(self, dt, keys, mouse_pos, mouse_buttons, bullets, particles):
        move = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w]
        )
        if move.length_squared() > 0:
            move.normalize_ip()
            self.velocity = self.velocity.lerp(move * self.speed, min(1, dt * 8))
        else:
            self.velocity *= 0.84 ** (dt * 60)

        self.pos += self.velocity * dt
        self.pos.x = clamp(self.pos.x, 45, WIDTH - 45)
        self.pos.y = clamp(self.pos.y, 55, HEIGHT - 45)

        mouse = pygame.Vector2(mouse_pos)
        aim = mouse - self.pos
        if aim.length_squared() > 4:
            self.angle = math.atan2(aim.y, aim.x)

        self.fire_timer -= dt
        self.dash_cooldown = max(0, self.dash_cooldown - dt)
        self.invuln = max(0, self.invuln - dt)
        self.overdrive = max(0, self.overdrive - dt)

        if mouse_buttons[0] and self.energy > 0 and self.fire_timer <= 0:
            self.shoot(bullets)
            self.energy -= 0.9 if self.overdrive <= 0 else 0.65

        if self.energy < self.max_energy:
            self.energy = min(self.max_energy, self.energy + 14 * dt)

        self.trail_timer -= dt
        if self.trail_timer <= 0 and self.velocity.length() > 80:
            self.trail_timer = 0.025
            back = pygame.Vector2(math.cos(self.angle + math.pi),
                                  math.sin(self.angle + math.pi))
            particles.append(Particle(
                self.pos.x + back.x * 16,
                self.pos.y + back.y * 16,
                CYAN,
                speed=45,
                life=0.35,
                size=4
            ))

    def shoot(self, bullets):
        self.fire_timer = 0.10 if self.overdrive > 0 else 0.17
        direction = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        bullets.append(Bullet(self.pos.x + direction.x * 24,
                              self.pos.y + direction.y * 24,
                              direction * 850))

    def dash(self, keys, particles):
        if self.dash_cooldown > 0 or self.energy < 22:
            return False
        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w]
        )
        if direction.length_squared() == 0:
            direction = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        else:
            direction.normalize_ip()

        self.pos += direction * 125
        self.pos.x = clamp(self.pos.x, 35, WIDTH - 35)
        self.pos.y = clamp(self.pos.y, 45, HEIGHT - 45)
        self.velocity = direction * 500
        self.energy -= 22
        self.dash_cooldown = 1.1
        self.invuln = 0.32

        for _ in range(24):
            particles.append(Particle(self.pos.x, self.pos.y, CYAN,
                                      speed=190, life=0.45, size=5))
        return True

    def damage(self, amount):
        if self.invuln > 0:
            return False
        if self.shield > 0:
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed
        if amount > 0:
            self.hp -= amount
        self.invuln = 0.55
        return True

    def draw(self, surface, camera):
        p = self.pos - camera
        if self.invuln > 0 and int(self.invuln * 20) % 2 == 0:
            return

        direction = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        side = pygame.Vector2(-direction.y, direction.x)

        nose = p + direction * 25
        left = p - direction * 16 + side * 15
        right = p - direction * 16 - side * 15
        rear = p - direction * 8

        glow_circle(surface, p, 28, CYAN, 55)
        pygame.draw.polygon(surface, WHITE, [nose, left, rear, right])
        pygame.draw.polygon(surface, CYAN, [nose, left, rear, right], width=3)

        cockpit = p + direction * 3
        pygame.draw.circle(surface, PURPLE, (int(cockpit.x), int(cockpit.y)), 7)
        pygame.draw.circle(surface, WHITE, (int(cockpit.x), int(cockpit.y)), 3)

        flame = p - direction * 18
        flame_len = 13 + random.randint(0, 8)
        pygame.draw.polygon(surface, YELLOW, [
            (flame.x, flame.y),
            (flame.x - side.x * 5 - direction.x * flame_len,
             flame.y - side.y * 5 - direction.y * flame_len),
            (flame.x + side.x * 5 - direction.x * flame_len,
             flame.y + side.y * 5 - direction.y * flame_len)
        ])


class Game:
    def __init__(self):
        self.state = MENU
        self.reset()
        self.stars = [Star() for _ in range(95)]
        self.high_score = 0
        self.camera = pygame.Vector2()
        self.shake = 0
        self.menu_time = 0

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.pickups = []
        self.particles = []
        self.score = 0
        self.combo = 1
        self.combo_timer = 0
        self.spawn_timer = 0.7
        self.pickup_timer = 7
        self.time_alive = 0
        self.wave = 1
        self.wave_banner = 2.5
        self.boss = None
        self.boss_spawned = False
        self.flash = 0
        self.message = ""
        self.message_timer = 0

    def start(self):
        self.reset()
        self.state = PLAYING

    def add_explosion(self, pos, color, amount=28, speed=220):
        for _ in range(amount):
            self.particles.append(
                Particle(pos[0], pos[1], color,
                         speed=random.uniform(speed * 0.5, speed),
                         life=random.uniform(0.35, 0.9),
                         size=random.uniform(2, 6))
            )
        self.shake = min(20, self.shake + amount * 0.18)

    def spawn_enemy(self):
        side = random.choice(("top", "bottom", "left", "right"))
        margin = 55
        if side == "top":
            x, y = random.uniform(0, WIDTH), -margin
        elif side == "bottom":
            x, y = random.uniform(0, WIDTH), HEIGHT + margin
        elif side == "left":
            x, y = -margin, random.uniform(0, HEIGHT)
        else:
            x, y = WIDTH + margin, random.uniform(0, HEIGHT)

        roll = random.random()
        if self.wave >= 5 and roll < 0.16:
            kind = "tank"
        elif roll < 0.55:
            kind = "hunter"
        else:
            kind = "drone"

        self.enemies.append(Enemy(x, y, kind, self.wave))

    def spawn_boss(self):
        self.boss = Boss(self.wave)
        self.boss_spawned = True
        self.message = "THE WARDEN HAS ARRIVED"
        self.message_timer = 3
        self.shake = 14
        for _ in range(65):
            self.particles.append(Particle(WIDTH / 2, 100, RED, 320, 1.1, 5))

    def update(self, dt):
        self.menu_time += dt
        for star in self.stars:
            star.update(dt, 150 if self.state == PLAYING else 40)

        if self.state != PLAYING:
            return

        self.time_alive += dt
        new_wave = 1 + int(self.time_alive // 18)
        if new_wave > self.wave:
            self.wave = new_wave
            self.wave_banner = 2.2
            self.combo = min(12, self.combo + 1)

        self.wave_banner = max(0, self.wave_banner - dt)
        self.message_timer = max(0, self.message_timer - dt)
        self.flash = max(0, self.flash - dt)
        self.shake *= 0.87 ** (dt * 60)

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()

        self.player.update(dt, keys, mouse_pos, mouse_buttons,
                           self.bullets, self.particles)

        # Spawn rhythm increases over time.
        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and self.boss is None:
            self.spawn_enemy()
            base = max(0.18, 0.85 - self.wave * 0.045)
            self.spawn_timer = random.uniform(base * 0.65, base * 1.15)

        self.pickup_timer -= dt
        if self.pickup_timer <= 0 and self.boss is None:
            self.pickups.append(Pickup(random.uniform(80, WIDTH - 80),
                                       random.uniform(100, HEIGHT - 80)))
            self.pickup_timer = random.uniform(8, 13)

        # Boss appears at wave 8.
        if self.wave >= 8 and not self.boss_spawned:
            self.spawn_boss()

        # Bullets
        self.bullets = [b for b in self.bullets if b.update(dt)]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.update(dt)]
        self.pickups = [p for p in self.pickups if p.update(dt)]

        # Enemies
        for enemy in self.enemies:
            enemy.update(dt, self.player.pos)

        # Bullet -> enemy collisions
        for bullet in self.bullets[:]:
            hit = False
            for enemy in self.enemies[:]:
                if bullet.pos.distance_to(enemy.pos) < bullet.radius + enemy.radius:
                    hit = True
                    dead = enemy.hit(1)
                    self.add_explosion(bullet.pos, CYAN, 4, 70)
                    if dead:
                        self.enemies.remove(enemy)
                        self.score += enemy.score * self.combo
                        self.combo = min(20, self.combo + 0.15)
                        self.combo_timer = 2.0
                        self.add_explosion(enemy.pos, enemy.color, 18, 190)
                    break
            if not hit and self.boss and bullet.pos.distance_to(self.boss.pos) < bullet.radius + self.boss.radius:
                hit = True
                dead = self.boss.hit(1)
                self.add_explosion(bullet.pos, CYAN, 4, 80)
                if dead:
                    self.score += 15000 * self.combo
                    self.add_explosion(self.boss.pos, RED, 130, 420)
                    self.state = VICTORY
                    self.high_score = max(self.high_score, int(self.score))
                    self.boss = None
            if hit and bullet in self.bullets:
                self.bullets.remove(bullet)

        # Enemy contact
        for enemy in self.enemies[:]:
            if enemy.pos.distance_to(self.player.pos) < enemy.radius + self.player.radius:
                if self.player.damage(12 if enemy.kind == "drone" else 18):
                    self.add_explosion(self.player.pos, RED, 12, 130)
                    self.flash = 0.12
                if enemy in self.enemies:
                    self.enemies.remove(enemy)

        # Enemy bullets
        for bullet in self.enemy_bullets[:]:
            if bullet.pos.distance_to(self.player.pos) < bullet.radius + self.player.radius:
                if self.player.damage(16):
                    self.add_explosion(self.player.pos, RED, 10, 120)
                    self.flash = 0.12
                self.enemy_bullets.remove(bullet)

        # Boss body collision
        if self.boss and self.boss.pos.distance_to(self.player.pos) < self.boss.radius + self.player.radius:
            self.player.damage(35)

        # Pickups
        for pickup in self.pickups[:]:
            if pickup.pos.distance_to(self.player.pos) < 30:
                self.pickups.remove(pickup)
                if pickup.kind == "energy":
                    self.player.energy = min(self.player.max_energy, self.player.energy + 45)
                    self.message = "ENERGY +45"
                elif pickup.kind == "shield":
                    self.player.shield = min(60, self.player.shield + 35)
                    self.message = "SHIELD ONLINE"
                else:
                    self.player.overdrive = 7
                    self.message = "OVERDRIVE // FIRE RATE UP"
                self.message_timer = 1.2
                self.add_explosion(pickup.pos, {
                    "energy": CYAN, "shield": GREEN, "overdrive": YELLOW
                }[pickup.kind], 16, 120)

        if self.combo_timer > 0:
            self.combo_timer -= dt
        else:
            self.combo = max(1, self.combo - dt * 0.8)

        if self.player.hp <= 0:
            self.state = GAME_OVER
            self.high_score = max(self.high_score, int(self.score))
            self.add_explosion(self.player.pos, RED, 100, 360)

       
        if self.shake > 0.5:
            self.camera.x = random.uniform(-self.shake, self.shake)
            self.camera.y = random.uniform(-self.shake, self.shake)
        else:
            self.camera.xy = (0, 0)

        # Particle update
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw_background(self):
        screen.fill(BLACK)

        # Subtle gradient bands
        for y in range(0, HEIGHT, 8):
            t = y / HEIGHT
            c = (int(5 + 8 * t), int(7 + 5 * t), int(18 + 15 * t))
            pygame.draw.rect(screen, c, (0, y, WIDTH, 8))

        for star in self.stars:
            star.draw(screen)

        # Neon grid / horizon
        horizon = HEIGHT * 0.62
        for i in range(12):
            y = horizon + i * i * 4.2
            if y < HEIGHT:
                pygame.draw.line(screen, (17, 28, 50), (0, y), (WIDTH, y), 1)

        for x in range(-600, WIDTH + 700, 80):
            pygame.draw.line(screen, (14, 25, 46),
                             (WIDTH / 2 + (x - WIDTH / 2) * 0.06, horizon),
                             (x, HEIGHT), 1)

        pygame.draw.line(screen, (45, 180, 220), (0, horizon), (WIDTH, horizon), 2)

    def draw_hud(self):
        # Top-left score
        draw_text(screen, f"SCORE  {int(self.score):08d}", FONT_MED, WHITE, (24, 18))
        draw_text(screen, f"WAVE {self.wave:02d}", FONT_SMALL, CYAN, (26, 52))
        if self.combo > 1.05:
            draw_text(screen, f"x{self.combo:.1f} COMBO", FONT_SMALL, YELLOW, (130, 52))

        # Player bars
        bx, by, bw = 24, HEIGHT - 65, 270
        pygame.draw.rect(screen, (22, 20, 35), (bx, by, bw, 12), border_radius=6)
        pygame.draw.rect(screen, RED, (bx, by, bw * clamp(self.player.hp / self.player.max_hp, 0, 1), 12), border_radius=6)
        draw_text(screen, "HULL", FONT_TINY, WHITE, (bx, by - 19))

        pygame.draw.rect(screen, (22, 20, 35), (bx, by + 25, bw, 8), border_radius=4)
        pygame.draw.rect(screen, CYAN, (bx, by + 25, bw * clamp(self.player.energy / self.player.max_energy, 0, 1), 8), border_radius=4)
        draw_text(screen, "ENERGY", FONT_TINY, CYAN, (bx, by + 38))

        if self.player.shield > 0:
            draw_text(screen, f"SHIELD {int(self.player.shield)}", FONT_TINY, GREEN, (315, HEIGHT - 58))

        if self.player.overdrive > 0:
            draw_text(screen, f"OVERDRIVE {self.player.overdrive:0.1f}s", FONT_SMALL, YELLOW,
                      (WIDTH - 24, HEIGHT - 52), center=False)

        # Controls
        draw_text(screen, "WASD MOVE   •   MOUSE AIM/FIRE   •   SPACE DASH   •   ESC PAUSE",
                  FONT_TINY, (150, 165, 190), (WIDTH - 24, HEIGHT - 20), center=False)

        if self.wave_banner > 0 and self.state == PLAYING:
            alpha = int(255 * min(1, self.wave_banner))
            layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            text = FONT_BIG.render(f"WAVE {self.wave}", True, (*CYAN, alpha))
            rect = text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 70))
            layer.blit(text, rect)
            screen.blit(layer, (0, 0))

        if self.message_timer > 0:
            draw_text(screen, self.message, FONT_MED, YELLOW,
                      (WIDTH / 2, HEIGHT - 92), center=True)

    def draw(self):
        self.draw_background()

        # World
        for pickup in self.pickups:
            pickup.draw(screen, self.camera)

        for bullet in self.bullets:
            bullet.draw(screen, self.camera)

        for bullet in self.enemy_bullets:
            bullet.draw(screen, self.camera)

        for enemy in self.enemies:
            enemy.draw(screen, self.camera)

        if self.boss:
            self.boss.draw(screen, self.camera)

        for particle in self.particles:
            particle.draw(screen, self.camera)

        if self.state in (PLAYING, PAUSED):
            self.player.draw(screen, self.camera)
            self.draw_hud()

        if self.state == MENU:
            self.draw_menu()
        elif self.state == PAUSED:
            self.draw_pause()
        elif self.state == GAME_OVER:
            self.draw_game_over()
        elif self.state == VICTORY:
            self.draw_victory()

        if self.flash > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 40, 80, int(150 * self.flash / 0.12)))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()

    def draw_menu(self):
        # Animated central logo
        pulse = 1 + math.sin(self.menu_time * 2.5) * 0.025
        title = FONT_HUGE.render("NEON", True, CYAN)
        drift = FONT_HUGE.render("DRIFT", True, PINK)

        title = pygame.transform.smoothscale(
            title, (int(title.get_width() * pulse), int(title.get_height() * pulse))
        )
        drift = pygame.transform.smoothscale(
            drift, (int(drift.get_width() * pulse), int(drift.get_height() * pulse))
        )

        screen.blit(title, title.get_rect(center=(WIDTH / 2, 180)))
        screen.blit(drift, drift.get_rect(center=(WIDTH / 2, 285)))

        draw_text(screen, "LAST LIGHT", FONT_MED, YELLOW,
                  (WIDTH / 2, 360), center=True)
        draw_text(screen, "SURVIVE THE VOID. BREAK THE WARDEN.",
                  FONT_SMALL, WHITE, (WIDTH / 2, 405), center=True)

        # Start button
        rect = pygame.Rect(WIDTH / 2 - 175, 455, 350, 68)
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        c = WHITE if hover else CYAN
        pygame.draw.rect(screen, (10, 20, 35), rect, border_radius=12)
        pygame.draw.rect(screen, c, rect, width=3, border_radius=12)
        draw_text(screen, "PRESS ENTER TO LAUNCH", FONT_MED, c,
                  rect.center, center=True)

        draw_text(screen, "WASD  •  MOUSE  •  SPACE",
                  FONT_SMALL, (130, 170, 195), (WIDTH / 2, 555), center=True)
        draw_text(screen, f"BEST SCORE  {self.high_score:08d}",
                  FONT_SMALL, YELLOW, (WIDTH / 2, 595), center=True)

        draw_text(screen, "A handcrafted arcade experience • No assets required",
                  FONT_TINY, (90, 105, 130), (WIDTH / 2, HEIGHT - 25), center=True)

    def draw_pause(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((2, 4, 12, 175))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "PAUSED", FONT_HUGE, WHITE, (WIDTH / 2, 260), center=True)
        draw_text(screen, "Press ESC to continue", FONT_MED, CYAN,
                  (WIDTH / 2, 365), center=True)
        draw_text(screen, "ENTER = restart", FONT_SMALL, (160, 180, 200),
                  (WIDTH / 2, 420), center=True)

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((25, 3, 12, 195))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "SYSTEM FAILURE", FONT_HUGE, RED, (WIDTH / 2, 220), center=True)
        draw_text(screen, f"SCORE  {int(self.score):08d}", FONT_BIG, WHITE,
                  (WIDTH / 2, 330), center=True)
        draw_text(screen, f"WAVE  {self.wave}", FONT_MED, CYAN,
                  (WIDTH / 2, 385), center=True)
        draw_text(screen, "ENTER  RESTART", FONT_MED, YELLOW,
                  (WIDTH / 2, 470), center=True)
        draw_text(screen, "ESC  MAIN MENU", FONT_SMALL, (170, 190, 215),
                  (WIDTH / 2, 520), center=True)

    def draw_victory(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 20, 18, 190))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "WARDEN // DESTROYED", FONT_BIG, GREEN,
                  (WIDTH / 2, 190), center=True)
        draw_text(screen, "THE LAST LIGHT SURVIVES", FONT_MED, WHITE,
                  (WIDTH / 2, 275), center=True)
        draw_text(screen, f"FINAL SCORE  {int(self.score):08d}",
                  FONT_BIG, YELLOW, (WIDTH / 2, 365), center=True)
        draw_text(screen, "ENTER  PLAY AGAIN", FONT_MED, CYAN,
                  (WIDTH / 2, 470), center=True)
        draw_text(screen, "ESC  MAIN MENU", FONT_SMALL, (170, 190, 215),
                  (WIDTH / 2, 520), center=True)


def main():
    game = Game()
    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.033)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.state == PLAYING:
                        game.state = PAUSED
                    elif game.state == PAUSED:
                        game.state = PLAYING
                    elif game.state in (GAME_OVER, VICTORY):
                        game.state = MENU

                elif event.key == pygame.K_RETURN:
                    if game.state in (MENU, GAME_OVER, VICTORY):
                        game.start()
                    elif game.state == PAUSED:
                        game.state = PLAYING

                elif event.key == pygame.K_SPACE and game.state == PLAYING:
                    keys = pygame.key.get_pressed()
                    game.player.dash(keys, game.particles)

        game.update(dt)
        game.draw()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
