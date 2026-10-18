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
        self.life = random.uniform(0.3, 0.7)
        self.max_life = self.life

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self):
        if self.life > 0:
            alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
            surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color[:3], alpha), (2, 2), 2)
            screen.blit(surf, (int(self.x), int(self.y)))


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 15
        self.speed = 350
        self.health = 100
        self.max_health = 100
        self.dash_cooldown = 0
        self.shoot_cooldown = 0

    def update(self, dt):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt

        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt

    def dash(self):
        if self.dash_cooldown <= 0:
            self.dash_cooldown = 1.5

    def shoot(self, mouse_pos, bullets):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = 0.15
            angle = math.atan2(mouse_pos[1] - self.y, mouse_pos[0] - self.x)
            bullets.append(Bullet(self.x, self.y, angle))

    def draw(self, mouse_pos):
        angle = math.atan2(mouse_pos[1] - self.y, mouse_pos[0] - self.x)
        p1 = (self.x + math.cos(angle) * 20, self.y + math.sin(angle) * 20)
        p2 = (self.x + math.cos(angle + 2.5) * 12, self.y + math.sin(angle + 2.5) * 12)
        p3 = (self.x + math.cos(angle - 2.5) * 12, self.y + math.sin(angle - 2.5) * 12)
        pygame.draw.polygon(screen, HOT_PINK, [p1, p2, p3])


class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.speed = 700
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.radius = 4

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self):
        pygame.draw.circle(screen, VIOLET, (int(self.x), int(self.y)), self.radius)


class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 180
        self.radius = 12
        self.health = 30

    def update(self, dt, target_x, target_y):
        angle = math.atan2(target_y - self.y, target_x - self.x)
        self.x += math.cos(angle) * self.speed * dt
        self.y += math.sin(angle) * self.speed * dt

    def draw(self):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), self.radius)


class Pickup:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 8

    def draw(self):
        pygame.draw.circle(screen, GREEN, (int(self.x), int(self.y)), self.radius)


class Game:
    def __init__(self):
        self.state = "menu"
        self.score = 0
        self.highscore = load_highscore()
        self.wave = 1
        self.player = Player(WIDTH // 2, HEIGHT // 2)
        self.bullets = []
        self.enemies = []
        self.particles = []
        self.pickups = []
        self.message_timer = 0
        self.spawn_timer = 0

    def start(self):
        self.state = "playing"
        self.score = 0
        self.wave = 1
        self.player = Player(WIDTH // 2, HEIGHT // 2)
        self.bullets.clear()
        self.enemies.clear()
        self.particles.clear()
        self.pickups.clear()
        self.message_timer = 2.0

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt

        self.player.update(dt)

        self.spawn_timer += dt
        if self.spawn_timer > 1.5:
            self.spawn_timer = 0
            side = random.choice(["top", "bottom", "left", "right"])
            if side == "top":
                self.enemies.append(Enemy(random.randint(0, WIDTH), -20))
            elif side == "bottom":
                self.enemies.append(Enemy(random.randint(0, WIDTH), HEIGHT + 20))
            elif side == "left":
                self.enemies.append(Enemy(-20, random.randint(0, HEIGHT)))
            else:
                self.enemies.append(Enemy(WIDTH + 20, random.randint(0, HEIGHT)))

        for bullet in self.bullets[:]:
            bullet.update(dt)
            if not (0 <= bullet.x <= WIDTH and 0 <= bullet.y <= HEIGHT):
                self.bullets.remove(bullet)
                continue

            for enemy in self.enemies[:]:
                dist = math.hypot(bullet.x - enemy.x, bullet.y - enemy.y)
                if dist < bullet.radius + enemy.radius:
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    enemy.health -= 30
                    if enemy.health <= 0:
                        if enemy in self.enemies:
                            self.enemies.remove(enemy)
                        self.score += 100
                        if random.random() < 0.2:
                            self.pickups.append(Pickup(enemy.x, enemy.y))
                    break

        for enemy in self.enemies[:]:
            enemy.update(dt, self.player.x, self.player.y)
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist < enemy.radius + self.player.radius:
                self.player.health -= 25
                self.enemies.remove(enemy)
                if self.player.health <= 0:
                    self.state = "gameover"
                    if self.score > self.highscore:
                        self.highscore = self.score
                        save_highscore(self.highscore)

        for p in self.particles[:]:
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)

    def draw_hud(self):
        text(f"SCORE: {self.score}", FONT, WHITE, 20, 20)
        text(f"HP: {max(0, self.player.health)}", FONT, HOT_PINK, 20, 50)

    def draw(self):
        screen.fill(BG_COLOR)

        if self.state == "menu":
            text("NEON DRIFT", BIG_FONT, HOT_PINK, WIDTH // 2, HEIGHT // 2 - 60, True)
            text("LAST LIGHT", BIG_FONT, VIOLET, WIDTH // 2, HEIGHT // 2 + 10, True)
            text("PRESS ENTER TO START", FONT, WHITE, WIDTH // 2, HEIGHT // 2 + 90, True)

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
                text(f"WAVE {self.wave}", BIG_FONT, VIOLET, WIDTH // 2, HEIGHT // 2 - 40, True)

            if self.state == "paused":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((15, 7, 28, 210))
                screen.blit(overlay, (0, 0))
                text("PAUSED", BIG_FONT, HOT_PINK, WIDTH // 2, HEIGHT // 2, True)
                text("PRESS P TO RESUME", FONT, WHITE, WIDTH // 2, HEIGHT // 2 + 60, True)

            elif self.state == "gameover":
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((15, 7, 28, 220))
                screen.blit(overlay, (0, 0))
                text("SYSTEM FAILURE", BIG_FONT, HOT_PINK, WIDTH // 2, HEIGHT // 2 - 80, True)
                text(f"SCORE: {self.score}", FONT, WHITE, WIDTH // 2, HEIGHT // 2 - 15, True)
                text(f"BEST: {self.highscore}", FONT, VIOLET, WIDTH // 2, HEIGHT // 2 + 25, True)
                text("ENTER: RETRY   ESC: MENU", FONT, PINK, WIDTH // 2, HEIGHT // 2 + 90, True)

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

                elif event.key == pygame.K_SPACE and game.state == "playing":
                    game.player.dash()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and game.state == "playing":
                    game.player.shoot(pygame.mouse.get_pos(), game.bullets)

        if game.state == "playing":
            if pygame.mouse.get_pressed()[0]:
                game.player.shoot(pygame.mouse.get_pos(), game.bullets)
            game.update(dt)

        game.draw()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
