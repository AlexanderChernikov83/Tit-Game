import math
import random
import sys
import pygame

# ----------------- НАСТРОЙКИ -----------------
WIDTH, HEIGHT = 800, 600
FPS = 60

ROUND_TIME = 60          # секунд
MAX_MISSES = 999         # можно ограничить, напр. 30

SPAWN_START_MS = 900     # стартовый интервал появления мишеней (мс)
SPAWN_MIN_MS = 350       # минимальный интервал спавна (ограничение)
LEVEL_STEP_SCORE = 10    # каждые N очков повышаем сложность

BG_COLOR = (20, 24, 28)
HUD_COLOR = (173, 216, 230)  # светло-синий
CROSSHAIR_COLOR = (240, 240, 240)

# Событие таймера спавна
SPAWN_EVENT = pygame.USEREVENT + 1

# ----------------- ПОДГОТОВКА -----------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Тир — Pygame")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 24, bold=True)
big_font = pygame.font.SysFont("arial", 42, bold=True)
pygame.mouse.set_visible(False)  # свой прицел — системный спрячем


# ----------------- ВСПОМОГАТЕЛЬНОЕ -----------------
def clamp(v, a, b):
    return max(a, min(b, v))


def draw_crosshair(surf, pos, size=16, thickness=2):
    x, y = pos
    pygame.draw.line(surf, CROSSHAIR_COLOR, (x - size, y), (x + size, y), thickness)
    pygame.draw.line(surf, CROSSHAIR_COLOR, (x, y - size), (x, y + size), thickness)
    pygame.draw.circle(surf, CROSSHAIR_COLOR, (x, y), 3, 1)


# ----------------- КЛАСС МИШЕНИ -----------------
class Target(pygame.sprite.Sprite):
    def __init__(self, speed_scale=1.0):
        super().__init__()
        # случайный размер (чем больше — тем легче попасть)
        self.radius = random.randint(14, 28)
        # позиция так, чтобы не заспавниться частично за краем
        self.x = random.randint(self.radius, WIDTH - self.radius)
        self.y = random.randint(self.radius, HEIGHT - self.radius)

        # скорость и направление
        angle = random.uniform(0, math.tau)
        base_speed = random.uniform(1.2, 2.7) * speed_scale
        self.vx = math.cos(angle) * base_speed
        self.vy = math.sin(angle) * base_speed

        # цвет — чуть рандома
        base = random.choice([(255, 90, 90), (255, 190, 60), (60, 200, 255), (120, 255, 120)])
        self.color = base

        # вспышка при попадании
        self.hit_flash = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy

        # отскок от краёв
        if self.x - self.radius <= 0 or self.x + self.radius >= WIDTH:
            self.vx *= -1
            self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        if self.y - self.radius <= 0 or self.y + self.radius >= HEIGHT:
            self.vy *= -1
            self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

        if self.hit_flash > 0:
            self.hit_flash -= 1

    def draw(self, surf):
        # внешнее кольцо
        pygame.draw.circle(surf, (0, 0, 0), (int(self.x), int(self.y)), self.radius + 2)
        # основа
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        # белая точка-центр
        pygame.draw.circle(surf, (245, 245, 245), (int(self.x), int(self.y)), max(3, self.radius // 4))
        # вспышка
        if self.hit_flash > 0:
            alpha = int(255 * (self.hit_flash / 8))
            flash_surface = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(
                flash_surface,
                (255, 255, 255, alpha),
                (self.radius * 2, self.radius * 2),
                self.radius + 6,
                4
            )
            surf.blit(flash_surface, (int(self.x) - self.radius * 2, int(self.y) - self.radius * 2))

    def is_hit(self, pos):
        px, py = pos
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= self.radius ** 2


# ----------------- ИГРОВОЙ ЦИКЛ -----------------
def run_game():
    # состояние
    targets = []
    score = 0
    shots = 0
    hits = 0
    level = 1

    spawn_interval = SPAWN_START_MS
    speed_scale = 1.0

    pygame.time.set_timer(SPAWN_EVENT, spawn_interval)
    start_ticks = pygame.time.get_ticks()
    game_over = False

    while True:
        dt = clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        # --------- события ---------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # управление на экране Game Over
            if game_over and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return  # рестарт
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            if not game_over:
                if event.type == SPAWN_EVENT:
                    # спавним 1–2 мишени в зависимости от уровня
                    count = 1 if level < 3 else 2
                    for _ in range(count):
                        targets.append(Target(speed_scale=speed_scale))

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    shots += 1
                    hit_any = False
                    # проверяем попадание по ближайшей сверху
                    for t in reversed(targets):
                        if t.is_hit(mouse_pos):
                            hits += 1
                            score += 1
                            t.hit_flash = 8
                            targets.remove(t)
                            hit_any = True
                            break
                    if not hit_any:
                        # промах — можно считать как отдельную метрику
                        pass

        # --------- логика ---------
        if not game_over:
            # время
            elapsed_sec = (pygame.time.get_ticks() - start_ticks) / 1000
            time_left = max(0, ROUND_TIME - int(elapsed_sec))
            if time_left == 0:
                game_over = True

            # апдейт мишеней
            for t in targets:
                t.update()

            # повышение уровня каждые LEVEL_STEP_SCORE очков
            new_level = score // LEVEL_STEP_SCORE + 1
            if new_level > level:
                level = new_level
                # ускоряем спавн и скорость
                spawn_interval = max(SPAWN_MIN_MS, int(spawn_interval * 0.87))
                pygame.time.set_timer(SPAWN_EVENT, spawn_interval)
                speed_scale *= 1.08

        # --------- рендер ---------
        screen.fill(BG_COLOR)

        # рисуем мишени
        for t in targets:
            t.draw(screen)

        # HUD
        acc = (hits / shots * 100) if shots > 0 else 0.0
        hud_text = f"Очки: {score}   Уровень: {level}   Время: {max(0, ROUND_TIME - (pygame.time.get_ticks() - start_ticks)//1000)}   Точность: {acc:.0f}%"
        hud_surf = font.render(hud_text, True, HUD_COLOR)
        screen.blit(hud_surf, (10, 10))

        # прицел
        draw_crosshair(screen, mouse_pos, size=16, thickness=2)

        # экран окончания
        if game_over:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 140))
            screen.blit(shade, (0, 0))

            title = big_font.render("🎯 Игра окончена!", True, HUD_COLOR)
            stats = font.render(f"Очки: {score}   Выстрелов: {shots}   Попаданий: {hits}   Точность: {acc:.1f}%", True, HUD_COLOR)
            hint = font.render("Нажми R — рестарт, ESC — выход", True, HUD_COLOR)

            screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 80))
            screen.blit(stats, (WIDTH//2 - stats.get_width()//2, HEIGHT//2 - 30))
            screen.blit(hint,  (WIDTH//2 - hint.get_width()//2,  HEIGHT//2 + 15))

        pygame.display.flip()


# ----------------- ЗАПУСК -----------------
if __name__ == "__main__":
    while True:
        run_game()
