import pygame
import random
import math
import asyncio

pygame.init()

WIDTH, HEIGHT = 1000, 700
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("NEON DRIFT // LAST LIGHT")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 22)
BG_COLOR = (15, 7, 28)
HOT_PINK = (255, 45, 149)
WHITE = (248, 238, 255)

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 15
        self.speed = 350

    def update(self, dt):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

    def draw(self, mouse_pos):
        angle = math.atan2(mouse_pos[1] - self.y, mouse_pos[0] - self.x)
        p1 = (self.x + math.cos(angle) * 20, self.y + math.sin(angle) * 20)
        p2 = (self.x + math.cos(angle + 2.5) * 12, self.y + math.sin(angle + 2.5) * 12)
        p3 = (self.x + math.cos(angle - 2.5) * 12, self.y + math.sin(angle - 2.5) * 12)
        pygame.draw.polygon(screen, HOT_PINK, [p1, p2, p3])

async def main():
    player = Player(WIDTH // 2, HEIGHT // 2)
    running = True
    
    while running:
        dt = min(clock.tick(FPS) / 1000, 0.035)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        player.update(dt)

        screen.fill(BG_COLOR)
        player.draw(pygame.mouse.get_pos())
        
        img = FONT.render("NEON DRIFT RUNNING SUCCESSFULLY!", True, WHITE)
        screen.blit(img, (50, 50))

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()

asyncio.run(main())
