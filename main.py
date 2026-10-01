import pygame
import random
import os
import math

# ============================================================
# INITIALIZATION
# ============================================================

pygame.init()

# Audio dibuat optional agar game tetap bisa berjalan
# walaupun mixer/audio device bermasalah.
try:
    pygame.mixer.init()
    AUDIO_ENABLED = True
except pygame.error:
    AUDIO_ENABLED = False

WIDTH = 900
HEIGHT = 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GALAXY DEFENDER")
clock = pygame.time.Clock()


# ============================================================
# COLORS
# ============================================================

WHITE = (255, 255, 255)
BLACK = (5, 5, 20)
RED = (230, 50, 60)
GREEN = (50, 220, 100)
BLUE = (60, 160, 255)
CYAN = (50, 240, 255)
YELLOW = (255, 220, 50)
PURPLE = (180, 80, 255)
ORANGE = (255, 140, 40)


# ============================================================
# FONTS
# ============================================================

font_small = pygame.font.Font(None, 28)
font_medium = pygame.font.Font(None, 38)
font_big = pygame.font.Font(None, 72)
font_huge = pygame.font.Font(None, 100)


# ============================================================
# ASSET PATH
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")


def asset_path(filename):
    return os.path.join(ASSET_DIR, filename)


# ============================================================
# IMAGE LOADER
# ============================================================

def load_image(filename, size=None):

    path = asset_path(filename)

    if not os.path.exists(path):
        print(f"[INFO] Asset tidak ditemukan: {path}")
        return None

    try:
        img = pygame.image.load(path).convert_alpha()

        if size:
            img = pygame.transform.scale(img, size)

        return img

    except pygame.error as error:
        print(f"[WARNING] Gagal memuat image {filename}: {error}")
        return None


# ============================================================
# OPTIONAL SOUNDS
# ============================================================

fire_sound = None
explosion_sound = None

if AUDIO_ENABLED:

    try:

        fire_path = asset_path("fire.ogg")
        explosion_path = asset_path("explosion.ogg")

        if os.path.exists(fire_path):
            fire_sound = pygame.mixer.Sound(fire_path)

        if os.path.exists(explosion_path):
            explosion_sound = pygame.mixer.Sound(explosion_path)

    except pygame.error as error:

        print(f"[WARNING] Sound tidak dapat dimuat: {error}")


# ============================================================
# BACKGROUND
# ============================================================

background_image = load_image(
    "galaxy.jpg",
    (WIDTH, HEIGHT)
)

stars = []

for _ in range(150):

    stars.append([
        random.randint(0, WIDTH),
        random.randint(0, HEIGHT),
        random.randint(1, 3),
        random.randint(1, 3)
    ])


# ============================================================
# GAME IMAGES
# ============================================================

rocket_image = load_image(
    "rocket.png",
    (80, 90)
)

bullet_image = load_image(
    "bullet.png",
    (12, 28)
)

enemy_image = load_image(
    "ufo.png",
    (70, 55)
)

boss_image = load_image(
    "boss.png",
    (180, 120)
)

heart_image = load_image(
    "heart.png",
    (30, 30)
)


# ============================================================
# GAME VARIABLES
# ============================================================

score = 0
level = 1
lives = 3

level_kills = 0

level_targets = {
    1: 10,
    2: 20
}

MAX_LEVEL = 3

game_state = "MENU"


# ============================================================
# ENEMY SETTINGS
# ============================================================

enemy_count = 5
enemy_min_speed = 2
enemy_max_speed = 4


# ============================================================
# SHOOTING
# ============================================================

last_shot = 0
shoot_delay = 300


# ============================================================
# POWER UPS
# ============================================================

shield_active = False
shield_timer = 0

rapid_fire = False
rapid_timer = 0


# ============================================================
# BOSS
# ============================================================

boss = None
boss_max_health = 100
boss_direction = 1
boss_last_shot = 0


# ============================================================
# EFFECTS
# ============================================================

explosions = []

message_text = ""
message_timer = 0


# ============================================================
# HELPER
# ============================================================

def draw_text(text, font, color, x, y, center=False):

    surface = font.render(text, True, color)

    if center:
        rect = surface.get_rect(center=(x, y))
    else:
        rect = surface.get_rect(topleft=(x, y))

    screen.blit(surface, rect)


def create_explosion(x, y):

    explosions.append({
        "x": x,
        "y": y,
        "radius": 5,
        "timer": 20
    })

    if explosion_sound:
        explosion_sound.play()


def update_explosions():

    for explosion in explosions[:]:

        explosion["radius"] += 4
        explosion["timer"] -= 1

        if explosion["timer"] <= 0:
            explosions.remove(explosion)


def draw_explosions():

    for explosion in explosions:

        x = explosion["x"]
        y = explosion["y"]
        radius = explosion["radius"]

        pygame.draw.circle(
            screen,
            ORANGE,
            (x, y),
            radius,
            4
        )

        pygame.draw.circle(
            screen,
            YELLOW,
            (x, y),
            max(2, radius // 2)
        )


def show_message(text):

    global message_text
    global message_timer

    message_text = text
    message_timer = 120


# ============================================================
# PLAYER
# ============================================================

class Player(pygame.sprite.Sprite):

    def __init__(self):

        super().__init__()

        if rocket_image:

            self.image = rocket_image

        else:

            self.image = pygame.Surface(
                (80, 90),
                pygame.SRCALPHA
            )

            pygame.draw.polygon(
                self.image,
                CYAN,
                [
                    (40, 0),
                    (5, 80),
                    (40, 65),
                    (75, 80)
                ]
            )

            pygame.draw.circle(
                self.image,
                WHITE,
                (40, 35),
                10
            )

        self.rect = self.image.get_rect()

        self.rect.centerx = WIDTH // 2
        self.rect.bottom = HEIGHT - 25

        self.speed = 8

    def update(self):

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed

        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WIDTH, self.rect.right)

        # Auto fire ketika SPACE ditahan
        if keys[pygame.K_SPACE]:
            self.shoot()

    def shoot(self):

        global last_shot

        current_time = pygame.time.get_ticks()

        delay = 100 if rapid_fire else shoot_delay

        if current_time - last_shot < delay:
            return

        bullet = Bullet(
            self.rect.centerx,
            self.rect.top
        )

        bullets.add(bullet)

        last_shot = current_time

        if fire_sound:
            fire_sound.play()

    def draw(self):

        screen.blit(
            self.image,
            self.rect
        )

        if shield_active:

            pygame.draw.circle(
                screen,
                CYAN,
                self.rect.center,
                55,
                3
            )


# ============================================================
# BULLET
# ============================================================

class Bullet(pygame.sprite.Sprite):

    def __init__(self, x, y):

        super().__init__()

        if bullet_image:

            self.image = bullet_image

        else:

            self.image = pygame.Surface(
                (12, 28),
                pygame.SRCALPHA
            )

            pygame.draw.rect(
                self.image,
                CYAN,
                (3, 0, 6, 25)
            )

            pygame.draw.circle(
                self.image,
                WHITE,
                (6, 3),
                3
            )

        self.rect = self.image.get_rect(
            center=(x, y)
        )

        self.speed = -13

    def update(self):

        self.rect.y += self.speed

        if self.rect.bottom < 0:
            self.kill()


# ============================================================
# ENEMY
# ============================================================

class Enemy(pygame.sprite.Sprite):

    def __init__(self):

        super().__init__()

        if enemy_image:

            self.image = enemy_image

        else:

            self.image = pygame.Surface(
                (70, 55),
                pygame.SRCALPHA
            )

            pygame.draw.ellipse(
                self.image,
                PURPLE,
                (5, 15, 60, 30)
            )

            pygame.draw.ellipse(
                self.image,
                CYAN,
                (20, 5, 30, 30)
            )

            pygame.draw.circle(
                self.image,
                WHITE,
                (30, 20),
                5
            )

        self.rect = self.image.get_rect()

        self.respawn()

    def respawn(self):

        self.rect.x = random.randint(
            20,
            WIDTH - self.rect.width - 20
        )

        self.rect.y = random.randint(
            -500,
            -50
        )

        self.speed = random.randint(
            enemy_min_speed,
            enemy_max_speed
        )

        self.wave = random.uniform(
            0,
            math.pi * 2
        )

        self.wave_speed = random.uniform(
            0.02,
            0.05
        )

    def update(self):

        self.rect.y += self.speed

        self.wave += self.wave_speed

        self.rect.x += int(
            math.sin(self.wave) * 2
        )

        if self.rect.left < 0:
            self.rect.left = 0

        if self.rect.right > WIDTH:
            self.rect.right = WIDTH

        if self.rect.top > HEIGHT:

            damage_player()

            self.respawn()


# ============================================================
# POWER UP
# ============================================================

class PowerUp(pygame.sprite.Sprite):

    def __init__(self, x, y, power_type):

        super().__init__()

        self.power_type = power_type

        self.image = pygame.Surface(
            (40, 40),
            pygame.SRCALPHA
        )

        if power_type == "shield":

            pygame.draw.circle(
                self.image,
                CYAN,
                (20, 20),
                18,
                3
            )

            pygame.draw.circle(
                self.image,
                WHITE,
                (20, 20),
                7
            )

        elif power_type == "rapid":

            pygame.draw.polygon(
                self.image,
                YELLOW,
                [
                    (23, 0),
                    (5, 22),
                    (18, 22),
                    (12, 40),
                    (35, 15),
                    (22, 15)
                ]
            )

        self.rect = self.image.get_rect(
            center=(x, y)
        )

        self.speed = 3

    def update(self):

        self.rect.y += self.speed

        if self.rect.top > HEIGHT:
            self.kill()


# ============================================================
# BOSS
# ============================================================

class Boss(pygame.sprite.Sprite):

    def __init__(self):

        super().__init__()

        if boss_image:

            self.image = boss_image

        else:

            self.image = pygame.Surface(
                (180, 120),
                pygame.SRCALPHA
            )

            pygame.draw.ellipse(
                self.image,
                RED,
                (10, 35, 160, 60)
            )

            pygame.draw.ellipse(
                self.image,
                PURPLE,
                (50, 10, 80, 60)
            )

            pygame.draw.circle(
                self.image,
                CYAN,
                (90, 45),
                15
            )

            pygame.draw.circle(
                self.image,
                WHITE,
                (90, 45),
                7
            )

        self.rect = self.image.get_rect()

        self.rect.centerx = WIDTH // 2
        self.rect.y = 40

        self.speed = 4

        self.health = boss_max_health

    def update(self):

        global boss_direction
        global boss_last_shot

        self.rect.x += self.speed * boss_direction

        if self.rect.left <= 0:
            boss_direction = 1

        if self.rect.right >= WIDTH:
            boss_direction = -1

        current_time = pygame.time.get_ticks()

        if current_time - boss_last_shot >= 1000:

            boss_bullet = BossBullet(
                self.rect.centerx,
                self.rect.bottom
            )

            boss_bullets.add(boss_bullet)

            boss_last_shot = current_time

    def draw_health(self):

        bar_width = 500
        bar_height = 20

        x = WIDTH // 2 - bar_width // 2
        y = 15

        pygame.draw.rect(
            screen,
            RED,
            (x, y, bar_width, bar_height)
        )

        health_ratio = max(
            0,
            self.health / boss_max_health
        )

        health_width = int(
            bar_width * health_ratio
        )

        pygame.draw.rect(
            screen,
            GREEN,
            (
                x,
                y,
                health_width,
                bar_height
            )
        )

        pygame.draw.rect(
            screen,
            WHITE,
            (
                x,
                y,
                bar_width,
                bar_height
            ),
            2
        )

        draw_text(
            "BOSS",
            font_small,
            WHITE,
            WIDTH // 2,
            47,
            center=True
        )


# ============================================================
# BOSS BULLET
# ============================================================

class BossBullet(pygame.sprite.Sprite):

    def __init__(self, x, y):

        super().__init__()

        self.image = pygame.Surface(
            (15, 30),
            pygame.SRCALPHA
        )

        pygame.draw.circle(
            self.image,
            RED,
            (7, 15),
            8
        )

        pygame.draw.circle(
            self.image,
            YELLOW,
            (7, 15),
            4
        )

        self.rect = self.image.get_rect(
            center=(x, y)
        )

        self.speed = 8

    def update(self):

        self.rect.y += self.speed

        if self.rect.top > HEIGHT:
            self.kill()


# ============================================================
# SPRITE GROUPS
# ============================================================

player = Player()

bullets = pygame.sprite.Group()
enemies = pygame.sprite.Group()
powerups = pygame.sprite.Group()
boss_bullets = pygame.sprite.Group()


# ============================================================
# STATE
# ============================================================

def change_state(new_state):

    global game_state

    game_state = new_state


# ============================================================
# DAMAGE PLAYER
# ============================================================

def damage_player():

    global lives
    global shield_active

    if shield_active:
        return

    lives -= 1

    show_message("-1 LIFE!")

    if lives <= 0:
        change_state("GAMEOVER")


# ============================================================
# CREATE ENEMIES
# ============================================================

def create_enemies():

    enemies.empty()

    for _ in range(enemy_count):

        enemies.add(
            Enemy()
        )


# ============================================================
# START LEVEL
# ============================================================

def start_level():

    global enemy_count
    global enemy_min_speed
    global enemy_max_speed
    global boss
    global level_kills
    global boss_direction
    global boss_last_shot

    level_kills = 0

    bullets.empty()
    enemies.empty()
    powerups.empty()
    boss_bullets.empty()

    boss = None

    boss_direction = 1
    boss_last_shot = pygame.time.get_ticks()

    player.rect.centerx = WIDTH // 2
    player.rect.bottom = HEIGHT - 25

    if level == 1:

        enemy_count = 5
        enemy_min_speed = 2
        enemy_max_speed = 4

        create_enemies()

        show_message("LEVEL 1")

    elif level == 2:

        enemy_count = 8
        enemy_min_speed = 3
        enemy_max_speed = 6

        create_enemies()

        show_message("LEVEL 2 - DANGER!")

    elif level == 3:

        boss = Boss()

        show_message("FINAL BOSS!")


# ============================================================
# NEXT LEVEL
# ============================================================

def next_level():

    global level

    level += 1

    if level > MAX_LEVEL:

        change_state("WIN")

    else:

        start_level()


# ============================================================
# RESET GAME
# ============================================================

def reset_game():

    global score
    global lives
    global level
    global shield_active
    global shield_timer
    global rapid_fire
    global rapid_timer
    global boss
    global last_shot
    global message_timer
    global explosions

    score = 0
    lives = 3
    level = 1

    shield_active = False
    shield_timer = 0

    rapid_fire = False
    rapid_timer = 0

    boss = None

    last_shot = 0
    message_timer = 0

    explosions.clear()

    start_level()

    change_state("PLAYING")


# ============================================================
# BACKGROUND
# ============================================================

def draw_background():

    if background_image:

        screen.blit(
            background_image,
            (0, 0)
        )

    else:

        screen.fill(BLACK)

        for star in stars:

            pygame.draw.circle(
                screen,
                WHITE,
                (star[0], star[1]),
                star[2]
            )

            star[1] += star[3]

            if star[1] > HEIGHT:

                star[0] = random.randint(
                    0,
                    WIDTH
                )

                star[1] = 0


# ============================================================
# HUD
# ============================================================

def draw_hud():

    draw_text(
        f"SCORE: {score}",
        font_medium,
        WHITE,
        20,
        15
    )

    if level < 3:

        target = level_targets[level]

        draw_text(
            f"UFO: {level_kills}/{target}",
            font_small,
            YELLOW,
            20,
            55
        )

    draw_text(
        f"LEVEL: {level}",
        font_medium,
        WHITE,
        WIDTH - 160,
        15
    )

    for i in range(lives):

        if heart_image:

            screen.blit(
                heart_image,
                (
                    20 + i * 38,
                    HEIGHT - 45
                )
            )

        else:

            draw_text(
                "♥",
                font_medium,
                RED,
                20 + i * 38,
                HEIGHT - 50
            )

    if shield_active:

        seconds = max(
            0,
            shield_timer // FPS
        )

        draw_text(
            f"SHIELD: {seconds}s",
            font_small,
            CYAN,
            WIDTH - 150,
            HEIGHT - 35
        )

    if rapid_fire:

        seconds = max(
            0,
            rapid_timer // FPS
        )

        draw_text(
            f"RAPID: {seconds}s",
            font_small,
            YELLOW,
            WIDTH - 150,
            HEIGHT - 60
        )


# ============================================================
# MENU
# ============================================================

def draw_menu():

    draw_background()

    draw_text(
        "GALAXY",
        font_huge,
        CYAN,
        WIDTH // 2,
        130,
        center=True
    )

    draw_text(
        "DEFENDER",
        font_huge,
        WHITE,
        WIDTH // 2,
        220,
        center=True
    )

    draw_text(
        "PRESS ENTER TO START",
        font_medium,
        YELLOW,
        WIDTH // 2,
        340,
        center=True
    )

    draw_text(
        "A / D or ARROW KEYS = MOVE",
        font_small,
        WHITE,
        WIDTH // 2,
        400,
        center=True
    )

    draw_text(
        "SPACE = SHOOT",
        font_small,
        WHITE,
        WIDTH // 2,
        430,
        center=True
    )

    draw_text(
        "ESC = EXIT",
        font_small,
        WHITE,
        WIDTH // 2,
        460,
        center=True
    )


# ============================================================
# GAME OVER
# ============================================================

def draw_gameover():

    draw_background()

    draw_text(
        "GAME OVER",
        font_huge,
        RED,
        WIDTH // 2,
        180,
        center=True
    )

    draw_text(
        f"FINAL SCORE: {score}",
        font_medium,
        WHITE,
        WIDTH // 2,
        280,
        center=True
    )

    draw_text(
        "PRESS R TO RESTART",
        font_medium,
        YELLOW,
        WIDTH // 2,
        360,
        center=True
    )

    draw_text(
        "PRESS ESC TO EXIT",
        font_small,
        WHITE,
        WIDTH // 2,
        410,
        center=True
    )


# ============================================================
# WIN
# ============================================================

def draw_win():

    draw_background()

    draw_text(
        "YOU WIN!",
        font_huge,
        GREEN,
        WIDTH // 2,
        160,
        center=True
    )

    draw_text(
        "GALAXY SAVED!",
        font_big,
        CYAN,
        WIDTH // 2,
        260,
        center=True
    )

    draw_text(
        f"FINAL SCORE: {score}",
        font_medium,
        WHITE,
        WIDTH // 2,
        340,
        center=True
    )

    draw_text(
        "PRESS R TO PLAY AGAIN",
        font_medium,
        YELLOW,
        WIDTH // 2,
        410,
        center=True
    )


# ============================================================
# POWER UP
# ============================================================

def update_powerups():

    global shield_active
    global shield_timer
    global rapid_fire
    global rapid_timer

    powerups.update()

    collected = pygame.sprite.spritecollide(
        player,
        powerups,
        True
    )

    for power in collected:

        if power.power_type == "shield":

            shield_active = True
            shield_timer = FPS * 8

            show_message(
                "SHIELD ACTIVATED!"
            )

        elif power.power_type == "rapid":

            rapid_fire = True
            rapid_timer = FPS * 7

            show_message(
                "RAPID FIRE!"
            )


# ============================================================
# TIMERS
# ============================================================

def update_timers():

    global shield_active
    global shield_timer
    global rapid_fire
    global rapid_timer
    global message_timer

    if shield_active:

        shield_timer -= 1

        if shield_timer <= 0:

            shield_timer = 0
            shield_active = False

    if rapid_fire:

        rapid_timer -= 1

        if rapid_timer <= 0:

            rapid_timer = 0
            rapid_fire = False

    if message_timer > 0:

        message_timer -= 1


# ============================================================
# POWER UP SPAWN
# ============================================================

def maybe_spawn_powerup(x, y):

    if random.randint(1, 100) > 15:
        return

    power = PowerUp(
        x,
        y,
        random.choice([
            "shield",
            "rapid"
        ])
    )

    powerups.add(power)


# ============================================================
# ENEMY COLLISIONS
# ============================================================

def handle_enemy_collisions():

    global score
    global level_kills

    collisions = pygame.sprite.groupcollide(
        enemies,
        bullets,
        True,
        True
    )

    for enemy in collisions:

        score += 10
        level_kills += 1

        create_explosion(
            enemy.rect.centerx,
            enemy.rect.centery
        )

        maybe_spawn_powerup(
            enemy.rect.centerx,
            enemy.rect.centery
        )

        # Spawn pengganti hanya jika target level
        # belum tercapai.
        if level_kills < level_targets.get(
            level,
            float("inf")
        ):

            enemies.add(
                Enemy()
            )

    if level < 3:

        target = level_targets[level]

        if level_kills >= target:

            next_level()


# ============================================================
# PLAYER VS ENEMY
# ============================================================

def handle_player_enemy_collision():

    hit = pygame.sprite.spritecollide(
        player,
        enemies,
        True
    )

    if not hit:
        return

    for enemy in hit:

        create_explosion(
            enemy.rect.centerx,
            enemy.rect.centery
        )

    if not shield_active:

        damage_player()


# ============================================================
# BOSS COLLISION
# ============================================================

def handle_boss_collision():

    global score
    global boss

    if boss is None:
        return

    hits = pygame.sprite.spritecollide(
        boss,
        bullets,
        True
    )

    for bullet in hits:

        boss.health -= 5

        create_explosion(
            bullet.rect.centerx,
            bullet.rect.centery
        )

        if boss.health <= 0:

            score += 500

            create_explosion(
                boss.rect.centerx,
                boss.rect.centery
            )

            boss.kill()
            boss = None

            boss_bullets.empty()

            change_state("WIN")

            return


# ============================================================
# BOSS BULLETS
# ============================================================

def handle_boss_bullets():

    hits = pygame.sprite.spritecollide(
        player,
        boss_bullets,
        True
    )

    if not hits:
        return

    # Shield menyerap serangan
    if shield_active:
        create_explosion(
            player.rect.centerx,
            player.rect.centery
        )
        return

    damage_player()

    create_explosion(
        player.rect.centerx,
        player.rect.centery
    )


# ============================================================
# GAME UPDATE
# ============================================================

def update_game():

    player.update()

    bullets.update()
    enemies.update()
    boss_bullets.update()

    if boss:
        boss.update()

    update_powerups()
    update_timers()
    update_explosions()

    handle_enemy_collisions()

    # Jangan lanjutkan collision jika level sudah berubah
    if game_state != "PLAYING":
        return

    handle_player_enemy_collision()

    if game_state != "PLAYING":
        return

    handle_boss_collision()

    if game_state != "PLAYING":
        return

    handle_boss_bullets()


# ============================================================
# DRAW GAME
# ============================================================

def draw_game():

    draw_background()

    bullets.draw(screen)
    enemies.draw(screen)
    powerups.draw(screen)
    boss_bullets.draw(screen)

    if boss:

        screen.blit(
            boss.image,
            boss.rect
        )

        boss.draw_health()

    player.draw()

    draw_explosions()

    draw_hud()

    if message_timer > 0:

        draw_text(
            message_text,
            font_big,
            YELLOW,
            WIDTH // 2,
            HEIGHT // 2,
            center=True
        )


# ============================================================
# MAIN LOOP
# ============================================================

running = True

while running:

    clock.tick(FPS)

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                running = False

            elif game_state == "MENU":

                if event.key == pygame.K_RETURN:

                    reset_game()

            elif game_state == "GAMEOVER":

                if event.key == pygame.K_r:

                    reset_game()

            elif game_state == "WIN":

                if event.key == pygame.K_r:

                    reset_game()

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    if game_state == "MENU":

        draw_menu()

    elif game_state == "PLAYING":

        update_game()
        draw_game()

    elif game_state == "GAMEOVER":

        draw_gameover()

    elif game_state == "WIN":

        draw_win()

    pygame.display.flip()


pygame.quit()