
import pygame
import random
import math
import json
import asyncio

pygame.init()

# WINDOW
WIDTH, HEIGHT = 1000, 700
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("NEON DRIFT // LAST LIGHT")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 22)
BIG_FONT = pygame.font.SysFont("consolas", 52, bold=True)

# PURPLE DREAM COLORS
BG_COLOR = (15, 7, 28)
GRID_COLOR = (42, 22, 65)
PANEL_COLOR = (29, 14, 48)
BLACK = (5, 3, 15)
WHITE = (248, 238, 255)
PURPLE = (138, 43, 226)
VIOLET = (186, 85, 255)
PINK = (255, 105, 180)
HOT_PINK = (255, 45, 149)
RED = (255, 75, 110)
GREEN = (130, 255, 190)
YELLOW = (255, 190, 240)
CYAN = VIOLET

SAVE_FILE = "neon_highscore.json"


def text(message, font, color, x, y, center=False):
    image = font.render(str(message), True, color)
    rect = image.get_rect()

    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)

    screen.blit(image, rect)


def load_highscore():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            return json.load(file).get("score", 0)
    except (OSError, ValueError, TypeError):
        return 0


def save_highscore(score):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as file:
            json.dump({"score": score}, file)
    except (OSError, TypeError):
        pass


class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.random() * math.tau
        speed = random.uniform(40, 220)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.2, 0.65)
        self.max_life = self.life

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self):
        if self.life > 0:
            radius = max(1, int(4 * self.life / self.max_life))
            pygame.draw.circle(
                screen, self.color,
                (int(self.x), int(self.y)), radius
            )


class Bullet:
    def __init__(self, x, y, angle, speed, color, damage=1):
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.damage = damage
        self.radius = 5
        self.life = 1.8

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self):
        pygame.draw.circle(
            screen, self.color,
            (int(self.x), int(self.y)), self.radius + 2
        )
        pygame.draw.circle(
            screen, WHITE,
            (int(self.x), int(self.y)), 2
        )

    def dead(self):
        return (
            self.life <= 0
            or self.x < -30 or self.x > WIDTH + 30
            or self.y < -30 or self.y > HEIGHT + 30
        )


class Player:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT / 2
        self.radius = 14
        self.speed = 270
        self.hp = 100
        self.max_hp = 100
        self.fire_timer = 0
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.invulnerable = 0
        self.rapid_timer = 0
        self.shield_timer = 0
        self.weapon_level = 1

    def update(self, dt, keys, particles):
        dx = (
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        )
        dy = (
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP])
        )

        length = math.hypot(dx, dy)
        if length:
            dx /= length
            dy /= length

        speed = self.speed * (2.7 if self.dash_timer > 0 else 1)
        self.x += dx * speed * dt
        self.y += dy * speed * dt

        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

        self.fire_timer = max(0, self.fire_timer - dt)
        self.dash_timer = max(0, self.dash_timer - dt)
        self.dash_cooldown = max(0, self.dash_cooldown - dt)
        self.invulnerable = max(0, self.invulnerable - dt)
        self.rapid_timer = max(0, self.rapid_timer - dt)
        self.shield_timer = max(0, self.shield_timer - dt)

        if self.dash_timer > 0 and random.random() < 0.8:
            particles.append(Particle(self.x, self.y, HOT_PINK))

    def dash(self):
        if self.dash_cooldown <= 0:
            self.dash_timer = 0.18
            self.dash_cooldown = 1.5
            self.invulnerable = max(self.invulnerable, 0.25)

    def shoot(self, target, bullets):
        if self.fire_timer > 0:
            return

        angle = math.atan2(target[1] - self.y, target[0] - self.x)
        self.fire_timer = 0.09 if self.rapid_timer > 0 else 0.2

        if self.weapon_level >= 3:
            angles = [angle - 0.2, angle, angle + 0.2]
        elif self.weapon_level == 2:
            angles = [angle - 0.1, angle + 0.1]
        else:
            angles = [angle]

        for shot_angle in angles:
            bullets.append(
                Bullet(self.x, self.y, shot_angle, 620, HOT_PINK)
            )

    def damage(self, amount):
        if self.invulnerable > 0:
            return

        if self.shield_timer > 0:
            self.shield_timer = max(0, self.shield_timer - 1)
            self.invulnerable = 0.25
            return

        self.hp -= amount
        self.invulnerable = 0.75

    def draw(self, target):
        if self.invulnerable > 0:
            if int(pygame.time.get_ticks() / 80) % 2:
                return

        angle = math.atan2(target[1] - self.y, target[0] - self.x)
        points = []

        for radius, offset in [
            (24, 0), (15, 2.5), (10, math.pi), (15, -2.5)
        ]:
            a = angle + offset
            points.append((
                int(self.x + math.cos(a) * radius),
                int(self.y + math.sin(a) * radius)
            ))

        pygame.draw.polygon(screen, VIOLET, points, 3)
        pygame.draw.circle(
            screen, WHITE, (int(self.x), int(self.y)), 4
        )

        if self.shield_timer > 0:
            pygame.draw.circle(
                screen, PINK,
                (int(self.x), int(self.y)), 28, 2
            )


class Enemy:
    TYPES = {
        "hunter": (RED, 95, 2, 13),
        "runner": (PINK, 175, 1, 9),
        "tank": (VIOLET, 48, 6, 21),
    }

    def __init__(self, wave):
        self.kind = random.choices(
            ["hunter", "runner", "tank"],
            weights=[55, 30, min(25, 5 + wave * 2)]
        )[0]

        self.color, base_speed, base_hp, self.radius = self.TYPES[self.kind]
        self.speed = base_speed + min(wave * 2, 65)
        self.hp = base_hp + wave // 4
        self.max_hp = self.hp
        self.damage_value = 10

        side = random.randrange(4)
        if side == 0:
            self.x, self.y = random.randrange(WIDTH), -25
        elif side == 1:
            self.x, self.y = WIDTH + 25, random.randrange(HEIGHT)
        elif side == 2:
            self.x, self.y = random.randrange(WIDTH), HEIGHT + 25
        else:
            self.x, self.y = -25, random.randrange(HEIGHT)

    def update(self, dt, player):
        dx = player.x - self.x
        dy = player.y - self.y
        distance = max(1, math.hypot(dx, dy))
        self.x += dx / distance * self.speed * dt
        self.y += dy / distance * self.speed * dt

    def draw(self):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(screen, self.color, (x, y), self.radius, 2)
        pygame.draw.circle(screen, self.color, (x, y), 4)

        if self.hp < self.max_hp:
            width = self.radius * 2
            pygame.draw.rect(
                screen, RED,
                (x - width // 2, y - self.radius - 8, width, 4)
            )
            pygame.draw.rect(
                screen, GREEN,
                (
                    x - width // 2, y - self.radius - 8,
                    int(width * max(0, self.hp) / self.max_hp), 4
                )
            )


class Pickup:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.kind = random.choice(["heal", "rapid", "shield", "weapon"])
        self.life = 9

    def update(self, dt):
        self.life -= dt

    def apply(self, player):
        if self.kind == "heal":
            player.hp = min(player.max_hp, player.hp + 25)
        elif self.kind == "rapid":
            player.rapid_timer = 7
        elif self.kind == "shield":
            player.shield_timer = 6
        elif self.kind == "weapon":
            player.weapon_level = min(3, player.weapon_level + 1)

    def draw(self):
        colors = {
            "heal": GREEN, "rapid": YELLOW,
            "shield": VIOLET, "weapon": PINK
        }
        symbols = {
            "heal": "+", "rapid": "R", "shield": "S", "weapon": "W"
        }
        color = colors[self.kind]
        pygame.draw.circle(
            screen, color, (int(self.x), int(self.y)), 12, 2
        )
        text(
            symbols[self.kind], FONT, color,
            int(self.x), int(self.y) - 10, True
        )


class Game:
    def __init__(self):
        self.highscore = load_highscore()
        self.state = "menu"
        self.reset()

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.pickups = []
        self.particles = []
        self.score = 0
        self.wave = 1
        self.kills = 0
        self.spawn_timer = 0
        self.message_timer = 2.5

    def start(self):
        self.reset()
        self.state = "playing"

    def explode(self, x, y, color, amount=15):
        for _ in range(amount):
            self.particles.append(Particle(x, y, color))

    def update(self, dt):
        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.particles)
        self.message_timer = max(0, self.message_timer - dt)
        self.spawn_timer -= dt

        if self.spawn_timer <= 0:
            self.spawn_timer = max(0.25, 1 - self.wave * 0.04)
            if len(self.enemies) < 5 + self.wave * 2:
                self.enemies.append(Enemy(self.wave))

        for enemy in self.enemies[:]:
            enemy.update(dt, self.player)

            distance = math.hypot(
                enemy.x - self.player.x, enemy.y - self.player.y
            )
            if distance < enemy.radius + self.player.radius:
                old_hp = self.player.hp
                self.player.damage(enemy.damage_value)
                if self.player.hp < old_hp:
                    self.explode(self.player.x, self.player.y, RED, 8)
                enemy.hp = 0

            if enemy.hp <= 0:
                self.enemies.remove(enemy)
                self.score += 10
                self.kills += 1
                self.explode(enemy.x, enemy.y, enemy.color, 10)
                if random.random() < 0.15:
                    self.pickups.append(Pickup(enemy.x, enemy.y))

        for bullet in self.bullets[:]:
            bullet.update(dt)
            hit = False

            for enemy in self.enemies:
                if math.hypot(
                    bullet.x - enemy.x, bullet.y - enemy.y
                ) < enemy.radius + bullet.radius:
                    enemy.hp -= bullet.damage
                    self.explode(bullet.x, bullet.y, enemy.color, 3)
                    hit = True
                    break

            if hit or bullet.dead():
                if bullet in self.bullets:
                    self.bullets.remove(bullet)

        for bullet in self.enemy_bullets[:]:
            bullet.update(dt)
            if bullet.dead():
                self.enemy_bullets.remove(bullet)

        for pickup in self.pickups[:]:
            pickup.update(dt)
            if math.hypot(
                pickup.x - self.player.x, pickup.y - self.player.y
            ) < 28:
                pickup.apply(self.player)
                self.pickups.remove(pickup)
            elif pickup.life <= 0:
                self.pickups.remove(pickup)

        for particle in self.particles[:]:
            particle.update(dt)
            if particle.life <= 0:
                self.particles.remove(particle)

        if self.kills >= self.wave * 12:
            self.wave += 1
            self.kills = 0
            self.message_timer = 2

        if self.player.hp <= 0:
            self.state = "gameover"
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)

    def draw_background(self):
        screen.fill(BG_COLOR)
        offset = (pygame.time.get_ticks() // 40) % 40

        for x in range(0, WIDTH, 40):
            pygame.draw.line(
                screen, GRID_COLOR, (x, 0), (x, HEIGHT)
            )

        for y in range(-40, HEIGHT + 40, 40):
            pygame.draw.line(
                screen, GRID_COLOR,
                (0, y + offset), (WIDTH, y + offset)
            )

        time_value = pygame.time.get_ticks() * 0.02
        for i in range(55):
            x = int((i * 173 + time_value * (i % 3 + 1)) % WIDTH)
            y = (i * 97) % HEIGHT
            screen.set_at((x, y), VIOLET)

    def draw_hud(self):
        text(f"HP {max(0, self.player.hp)}", FONT, PINK, 25, 18)
        text(f"SCORE {self.score}", FONT, VIOLET, 20, 50)
        text(f"BEST {self.highscore}", FONT, PURPLE, 20, 78)
        text(f"WAVE {self.wave}", FONT, PINK, WIDTH - 150, 20)
        text(f"KILLS {self.kills}", FONT, WHITE, WIDTH - 150, 50)

        dash_text = (
            "DASH READY" if self.player.dash_cooldown <= 0
            else f"DASH {self.player.dash_cooldown:.1f}s"
        )
        dash_color = (
            PINK if self.player.dash_cooldown <= 0 else VIOLET
        )
        text(dash_text, FONT, dash_color, WIDTH - 150, 80)

        if self.player.rapid_timer > 0:
            text(
                f"RAPID FIRE {self.player.rapid_timer:.1f}",
                FONT, HOT_PINK, WIDTH // 2, 20, True
            )

    def draw(self):
        self.draw_background()

        if self.state == "menu":
            # Decorative neon rings
            t = pygame.time.get_ticks() * 0.001
            for radius in (80, 110, 140):
                r = int(radius + math.sin(t * 2) * 4)
                pygame.draw.circle(
                    screen, GRID_COLOR, (WIDTH // 2, 205), r, 1
                )

            text(
                "NEON DRIFT", BIG_FONT, VIOLET,
                WIDTH // 2, 190, True
            )
            text(
                "// LAST LIGHT", FONT, HOT_PINK,
                WIDTH // 2, 245, True
            )
            text(
                "SURVIVE THE NEON NIGHT",
                FONT, WHITE, WIDTH // 2, 320, True
            )
            text(
                "WASD / ARROWS - MOVE",
                FONT, PINK, WIDTH // 2, 380, True
            )
            text(
                "MOUSE - AIM AND FIRE",
                FONT, PINK, WIDTH // 2, 420, True
            )
            text(
                "SPACE - DASH",
                FONT, PINK, WIDTH // 2, 460, True
            )

            pulse = (math.sin(pygame.time.get_ticks() * 0.006) + 1) / 2
            start_color = (
                255,
                int(45 + pulse * 70),
                int(149 + pulse * 60)
            )
            text(
                "PRESS ENTER TO START",
                FONT, start_color, WIDTH // 2, 530, True
            )
            text(
                f"BEST SCORE: {self.highscore}",
                FONT, VIOLET, WIDTH // 2, 580, True
            )

        else:
            for particle in self.particles:
                particle.draw()
            for pickup in self.pickups:
                pickup.draw()
            for bullet in self.bullets:
                bullet.draw()
            for enemy in self.enemies:
                enemy.draw()

            self.player.draw(pygame.mouse.get_pos())
            self.draw_hud()

            if self.message_timer > 0 and self.state == "playing":
                text(
                    f"WAVE {self.wave}", BIG_FONT, VIOLET,
                    WIDTH // 2, HEIGHT // 2 - 40, True
                )

            if self.state == "paused":
                overlay = pygame.Surface(
                    (WIDTH, HEIGHT), pygame.SRCALPHA
                )
                overlay.fill((15, 7, 28, 210))
                screen.blit(overlay, (0, 0))
                text(
                    "PAUSED", BIG_FONT, HOT_PINK,
                    WIDTH // 2, HEIGHT // 2, True
                )
                text(
                    "PRESS P TO RESUME",
                    FONT, WHITE, WIDTH // 2, HEIGHT // 2 + 60, True
                )

            elif self.state == "gameover":
                overlay = pygame.Surface(
                    (WIDTH, HEIGHT), pygame.SRCALPHA
                )
                overlay.fill((15, 7, 28, 220))
                screen.blit(overlay, (0, 0))
                text(
                    "SYSTEM FAILURE", BIG_FONT, HOT_PINK,
                    WIDTH // 2, HEIGHT // 2 - 80, True
                )
                text(
                    f"SCORE: {self.score}", FONT, WHITE,
                    WIDTH // 2, HEIGHT // 2 - 15, True
                )
                text(
                    f"BEST: {self.highscore}", FONT, VIOLET,
                    WIDTH // 2, HEIGHT // 2 + 25, True
                )
                text(
                    "ENTER: RETRY   ESC: MENU",
                    FONT, PINK, WIDTH // 2, HEIGHT // 2 + 90, True
                )

        pygame.display.flip()


async def main():
    game = Game()
    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000, 0.035)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.state == "playing":
                        game.state = "paused"
                    elif game.state in ("paused", "gameover"):
                        game.state = "menu"
                    else:
                        running = False

                elif event.key == pygame.K_RETURN:
                    if game.state in ("menu", "gameover"):
                        game.start()

                elif event.key == pygame.K_p:
                    if game.state == "playing":
                        game.state = "paused"
                    elif game.state == "paused":
                        game.state = "playing"

                elif (
                    event.key == pygame.K_SPACE
                    and game.state == "playing"
                ):
                    game.player.dash()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and game.state == "playing":
                    game.player.shoot(
                        pygame.mouse.get_pos(), game.bullets
                    )

        if game.state == "playing":
            if pygame.mouse.get_pressed()[0]:
                game.player.shoot(
                    pygame.mouse.get_pos(), game.bullets
                )
            game.update(dt)

        game.draw()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

