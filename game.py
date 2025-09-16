import pygame
import sys
import math
import os
import json
import string
import random  # sfx variants, selection, shake

# ================================
# INICIALIZACIÓN (fix lag audio)
# ================================
pygame.mixer.pre_init(22050, -16, 1, 512)  # 22.05 kHz, 16-bit, mono, buffer corto
pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

# --- Rutas/Assets ---
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# --- Player ---
PLAYER_SPEED = 6
PLAYER_SIZE = (50, 20)   # ancho, alto (colisiones / límites)
COLOR_BG_PLAY = (0, 60, 30)
COLOR_PLAYER  = (90, 200, 255)

# --- Bullets ---
BULLET_SPEED = -10      # negativo = hacia arriba (px/frame)
BULLET_SIZE  = (4, 12)
MAX_BULLETS  = 4
FIRE_COOLDOWN_MS = 250
COLOR_BULLET = (255, 255, 255)

# --- Power Ups (frecuencia/base) ---
POWERUP_EVERY_N_LEVELS = 2
MIN_FIRE_COOLDOWN_MS   = 90   # límite inferior de cooldown
MAX_BULLETS_CAP        = 6    # límite superior de balas simultáneas

# --- Power-up: Disparo múltiple ---
SHOT_COUNT_BASE = 1     # cantidad de balas por disparo al inicio
SHOT_COUNT_MAX  = 2     # tope (x2)
SHOT_SPREAD_PX  = 14    # separación horizontal entre las 2 balas

# --- Enemies / Dificultad base ---
ENEMY_COLS = 9
ENEMY_ROWS = 4
ENEMY_SIZE = (40, 24)
ENEMY_X_SPEED = 2.0         # velocidad base (px/frame)
ENEMY_X_STEP_RAMP = 0.25    # rampa por nivel
ENEMY_DROP = 18             # cuánto bajan al rebotar

# --- Disparos de enemigos normales ---
ENEMY_SHOOTERS_PER_LEVEL = 7      # cantidad habilitada a disparar por nivel
ENEMY_SHOOT_MIN_MS       = 1800   # intervalo mínimo entre disparos
ENEMY_SHOOT_MAX_MS       = 3200   # intervalo máximo entre disparos
ENEMY_BULLET_SPEED_NORM  = 6      # px/frame hacia abajo
COLOR_ENEMY_BULLET_NORM  = (255, 255, 120)

# --- FX ---
EXPLOSION_MS = 220  # duración de la explosión

# --- Daño del jugador (feedback) ---
HURT_SHAKE_MS  = 260
HURT_SHAKE_MAG = 6

# --- Sistema de juego ---
SCORE_PER_ENEMY   = 50
LEVEL_CLEAR_BONUS = 250
LIVES = 3
MAX_LIVES = 5

# Drop de vida enemigo
HEALTH_DROP_CHANCE = 0.06     # ~6% por enemigo eliminado
HEALTH_DROP_SPEED  = 3.5

# --- Menús / UI ---
COLOR_BG_MENU = (16, 16, 28)
COLOR_BG_OVER = (40, 6, 6)
COLOR_TEXT    = (240, 240, 240)
COLOR_SUBTEXT = (190, 190, 190)
COLOR_ACCENT  = (255, 220, 160)
TITLE = "Franco invader"
FONT_NAME = "Arial"

# --- Retro Pixel Art ---
PIXEL_SCALE = 3  # tamaño de cada "pixel" del sprite 8-bit

# --- Perfiles / Highscore ---
PROFILES_PATH = os.path.join(ASSETS_DIR, "profiles.json")  # guardamos dentro de assets
MAX_NAME_LEN  = 12

# --- Audio / assets ---
SFX_VOLUME   = 0.7
MUSIC_VOLUME = 0.5

# --- Boss ---
BOSS_EVERY_N_LEVELS = 5
BOSS_SIZE = (150, 84)        # área de colisión
BOSS_BASE_HP = 20
BOSS_HP_PER_CYCLE = 8
BOSS_X_SPEED = 2.0
BOSS_BOB_AMPLITUDE = 6
BOSS_BOB_SPEED = 0.02
BOSS_SHOOT_MIN_MS = 700
BOSS_SHOOT_MAX_MS = 1200
BOSS_BULLET_SPEED = 5
BOSS_KILL_BONUS = 500

COLOR_BOSS = (255, 90, 90)
COLOR_BOSS_BULLET = (255, 220, 160)

# --------------------------------

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Juego con Estados")
clock = pygame.time.Clock()

# ================================
# UTILIDADES DE DIBUJO (RETRO + TEXTO)
# ================================
def draw_shadow_text(screen, text, size, pos, color=COLOR_TEXT, shadow=(0,0,0)):
    font = pygame.font.SysFont(FONT_NAME, size)
    surf = font.render(text, True, color)
    shad = font.render(text, True, shadow)
    x, y = pos
    screen.blit(shad, (x+2, y+2))
    screen.blit(surf, (x, y))
    return surf.get_rect(topleft=pos)

def draw_centered_text(screen, text, size, y, color=COLOR_TEXT, shadow=(0,0,0)):
    font = pygame.font.SysFont(FONT_NAME, size)
    surf = font.render(text, True, color)
    shad = font.render(text, True, shadow)
    rect = surf.get_rect(center=(WIDTH//2, y))
    screen.blit(shad, (rect.x+2, rect.y+2))
    screen.blit(surf, rect)
    return rect

def draw_pixel_sprite(screen, pattern, x, y, color, scale=PIXEL_SCALE):
    """pattern: lista de strings con '1' = pixel activo, '0' = vacío."""
    for r, row in enumerate(pattern):
        for c, ch in enumerate(row):
            if ch == "1":
                pygame.draw.rect(
                    screen, color,
                    pygame.Rect(x + c*scale, y + r*scale, scale, scale)
                )

# ================================
# FONDO: STARFIELD (parallax)
# ================================
class Starfield:
    def __init__(self, layers=((60, 1), (40, 2), (20, 3))):
        self.layers = []
        for count, speed in layers:
            stars = []
            for _ in range(count):
                x = random.randint(0, WIDTH - 1)
                y = random.randint(0, HEIGHT - 1)
                stars.append([x, y])
            self.layers.append({"stars": stars, "speed": speed})

    def update(self):
        for layer in self.layers:
            for p in layer["stars"]:
                p[1] += layer["speed"]
                if p[1] >= HEIGHT:
                    p[0] = random.randint(0, WIDTH - 1)
                    p[1] = 0

    def draw(self, screen):
        for i, layer in enumerate(self.layers):
            col = (140 - i * 25, 200 - i * 25, 150 - i * 25)
            size = 2 if i == 0 else 1
            for x, y in layer["stars"]:
                screen.fill(col, (x, y, size, size))

# ================================
# OVERLAY: CRT scanlines
# ================================
def build_crt_overlay():
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 2):
        pygame.draw.line(surf, (0, 0, 0, 28), (0, y), (WIDTH, y))
    vign = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(vign, (0, 0, 0, 60), (0, 0, WIDTH, HEIGHT), width=12)
    surf.blit(vign, (0, 0))
    return surf

# ================================
# PERFILES: carga/guardado JSON
# ================================
class ProfileManager:
    def __init__(self, path=PROFILES_PATH):
        self.path = path
        self.data = {"profiles": [], "last_active": None}
        self.load()
        if not self.data["profiles"]:
            self.create_profile("Guest")
            self.set_active("Guest")

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            else:
                self.save()
        except Exception:
            self.data = {"profiles": [], "last_active": None}
            self.save()

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def profiles(self):
        return [p["name"] for p in self.data["profiles"]]

    def get_active(self):
        name = self.data.get("last_active")
        for p in self.data["profiles"]:
            if p["name"] == name:
                return p
        return None

    def set_active(self, name):
        if name in self.profiles():
            self.data["last_active"] = name
            self.save()
            return True
        return False

    def create_profile(self, name):
        name = name.strip()[:MAX_NAME_LEN]
        if (not name) or (name in self.profiles()):
            return False
        self.data["profiles"].append({"name": name, "high_score": 0})
        self.data["last_active"] = name
        self.save()
        return True

    def update_high_score(self, score):
        p = self.get_active()
        if not p:
            return False
        if score > p.get("high_score", 0):
            p["high_score"] = score
            self.save()
            return True
        return False

# ================================
# PATRONES 8-BIT
# ================================
PLAYER_PATTERN = [
    "000010000",
    "000111000",
    "001111100",
    "011111110",
    "111111111",
    "001001100",
    "010000010",
]

ALIEN_PATTERNS = [
    [  # tipo 0
        "0011100",
        "0100010",
        "1011101",
        "1111111",
        "1011101",
        "0100010",
        "0011100",
    ],
    [  # tipo 1
        "0011100",
        "0111110",
        "1100011",
        "1110111",
        "1100011",
        "0111110",
        "0011100",
    ],
    [  # tipo 2
        "0001000",
        "0011100",
        "0111110",
        "1111111",
        "0100010",
        "0011100",
        "0001000",
    ],
]

BOSS_PATTERN = [
    "000001111111100000",
    "000111111111111000",
    "011111001100111110",
    "111110111111011111",
    "111111111111111111",
    "011111011110111110",
    "001110111111011100",
    "000100011110001000",
    "000000001100000000",
]

# Iconos 8-bit (power-ups)
ICON_LIGHTNING = [
    "0000100",
    "0001100",
    "0011000",
    "0110000",
    "1111111",
    "0001100",
    "0011000",
    "0110000",
]
ICON_TWIN = [
    "010010",
    "111111",
    "111111",
    "010010",
    "010010",
    "111111",
    "111111",
    "010010",
]
ICON_DOUBLE = [
    "01100110",
    "01100110",
    "11111111",
    "01100110",
    "01100110",
    "11111111",
    "01100110",
    "01100110",
]

# Corazón (vida) 8-bit
HEART_PATTERN = [
    "01100110",
    "11111111",
    "11111111",
    "11111111",
    "01111110",
    "00111100",
    "00011000",
    "00000000",
]

# ================================
# ESTADOS
# ================================
class State:
    def __init__(self, game): self.game = game
    def handle_events(self, events): pass
    def update(self): pass
    def render(self, screen): pass

class MenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.mode = "main"      # "main" | "new_profile"
        self.name_buffer = ""
        self.bg = Starfield()

    def handle_events(self, events):
        if self.mode == "main":
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.game.change_state(PlayState(self.game))
                    elif event.key == pygame.K_TAB:
                        names = self.game.profiles.profiles()
                        if names:
                            cur = self.game.profiles.get_active()["name"]
                            idx = (names.index(cur) + 1) % len(names)
                            self.game.profiles.set_active(names[idx])
                    elif event.key == pygame.K_n:
                        self.mode = "new_profile"
                        self.name_buffer = ""
                    elif event.key == pygame.K_m:
                        if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                        else: self.game.play_music_loop()
                    elif event.key == pygame.K_c:
                        self.game.crt_on = not self.game.crt_on
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
        else:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.name_buffer.strip():
                            self.game.profiles.create_profile(self.name_buffer)
                        self.mode = "main"
                    elif event.key == pygame.K_BACKSPACE:
                        self.name_buffer = self.name_buffer[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        self.mode = "main"
                    else:
                        ch = event.unicode
                        if ch and ch in (string.ascii_letters + string.digits + "_- "):
                            if len(self.name_buffer) < MAX_NAME_LEN:
                                self.name_buffer += ch

    def render(self, screen):
        screen.fill(COLOR_BG_MENU)
        self.bg.update(); self.bg.draw(screen)
        draw_centered_text(screen, TITLE, 48, 140, COLOR_ACCENT)
        active = self.game.profiles.get_active()
        best = active.get("high_score", 0) if active else 0
        pname = active["name"] if active else "Guest"

        if self.mode == "main":
            draw_centered_text(screen, f"Perfil: {pname}  (TAB para cambiar)", 22, 230, COLOR_TEXT)
            draw_centered_text(screen, f"High Score: {best}", 22, 260, COLOR_SUBTEXT)
            draw_centered_text(screen, "ESPACIO: Jugar   |   N: Nuevo Perfil   |   M: Música   |   C: CRT   |   ESC: Salir", 22, 330, COLOR_TEXT)
        else:
            draw_centered_text(screen, "Nuevo Perfil", 32, 230, COLOR_TEXT)
            draw_centered_text(screen, f"Nombre (ENTER confirma): {self.name_buffer}", 22, 270, COLOR_SUBTEXT)

        if getattr(self.game, "crt_on", False):
            screen.blit(self.game.crt_overlay, (0, 0))

class GameOverState(State):
    def __init__(self, game, final_score):
        super().__init__(game)
        self.final_score = final_score
        # sonido de game over
        self.game.play_gameover()
        self.new_record = self.game.profiles.update_high_score(final_score)
        self.bg = Starfield()

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.game.change_state(MenuState(self.game))
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

    def render(self, screen):
        screen.fill(COLOR_BG_OVER)
        self.bg.update(); self.bg.draw(screen)
        draw_centered_text(screen, "GAME OVER", 48, 180, COLOR_TEXT)
        draw_centered_text(screen, f"Puntaje: {self.final_score}", 28, 240, COLOR_ACCENT)
        active = self.game.profiles.get_active()
        best = active.get("high_score", 0) if active else 0
        if self.new_record:
            draw_centered_text(screen, f"¡Nuevo récord para {active['name']}!", 24, 280, (255, 240, 120))
        else:
            draw_centered_text(screen, f"Récord ({active['name']}): {best}", 24, 280, COLOR_SUBTEXT)
        draw_centered_text(screen, "R: volver al Menú   |   ESC: salir", 22, 340, COLOR_TEXT)
        if getattr(self.game, "crt_on", False):
            screen.blit(self.game.crt_overlay, (0, 0))

class PauseState(State):
    def __init__(self, game, play_state):
        super().__init__(game)
        self.play_state = play_state
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.game.play_pause_out()
                    self.game.change_state(self.play_state)
                elif event.key == pygame.K_r:
                    self.game.change_state(PlayState(self.game))
                elif event.key == pygame.K_m:
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                    else: self.game.play_music_loop()
                elif event.key == pygame.K_ESCAPE:
                    self.game.change_state(GameOverState(self.game, self.play_state.score))
    def update(self): pass
    def render(self, screen):
        self.play_state.render(screen)
        overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(150); overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        draw_centered_text(screen, "PAUSA", 48, HEIGHT//2 - 40, COLOR_TEXT)
        draw_centered_text(screen, "P: reanudar  |  R: reiniciar  |  M: música  |  ESC: terminar", 22, HEIGHT//2 + 10, COLOR_SUBTEXT)

class PowerUpChoiceState(State):
    """
    Pantalla de elección de power-up (cada 2 niveles):
    0) Cadencia   1) Balas +1   2) Disparo x2
    """
    def __init__(self, game, play_state):
        super().__init__(game)
        self.play_state = play_state
        self.selection = 0
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 150))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selection = (self.selection - 1) % 3
                    self.game.play_select()
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selection = (self.selection + 1) % 3
                    self.game.play_select()
                elif event.key == pygame.K_1:
                    self.selection = 0; self.apply_and_continue()
                elif event.key == pygame.K_2:
                    self.selection = 1; self.apply_and_continue()
                elif event.key == pygame.K_3:
                    self.selection = 2; self.apply_and_continue()
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.apply_and_continue()
                elif event.key == pygame.K_ESCAPE:
                    self.apply_and_continue()

    def apply_and_continue(self):
        self.game.play_confirm()
        if self.selection == 0:
            new_cd = int(self.play_state.fire_cooldown_ms * 0.85)
            self.play_state.fire_cooldown_ms = max(MIN_FIRE_COOLDOWN_MS, new_cd)
        elif self.selection == 1:
            self.play_state.max_bullets = min(MAX_BULLETS_CAP, self.play_state.max_bullets + 1)
        else:
            self.play_state.shot_count = min(SHOT_COUNT_MAX, 2)
        self.play_state._setup_level()
        self.game.change_state(self.play_state)

    def update(self): pass

    def _draw_card(self, screen, rect, title, pattern, selected):
        pygame.draw.rect(screen, (30, 30, 30), rect, border_radius=16)
        pygame.draw.rect(screen, (90, 90, 90), rect, width=2, border_radius=16)
        if selected:
            pygame.draw.rect(screen, COLOR_ACCENT, rect, width=4, border_radius=16)
        font = pygame.font.SysFont(FONT_NAME, 24)
        tt = font.render(title, True, COLOR_TEXT)
        screen.blit(tt, (rect.x + (rect.w - tt.get_width()) // 2, rect.y + 14))
        icon_w = len(pattern[0]) * PIXEL_SCALE
        icon_h = len(pattern) * PIXEL_SCALE
        ix = rect.x + (rect.w - icon_w) // 2
        iy = rect.y + (rect.h - icon_h) // 2 + 6
        draw_pixel_sprite(screen, pattern, ix, iy, COLOR_ACCENT, PIXEL_SCALE)
        tip = pygame.font.SysFont(FONT_NAME, 18).render("ENTER para elegir", True, COLOR_SUBTEXT)
        screen.blit(tip, (rect.x + (rect.w - tip.get_width()) // 2, rect.bottom - 28))

    def render(self, screen):
        self.play_state.render(screen)
        screen.blit(self.overlay, (0, 0))
        draw_centered_text(screen, "¡Elegí tu mejora!", 38, 140, COLOR_TEXT)
        card_w, card_h = 240, 240
        gap = 20
        total_w = 3*card_w + 2*gap
        start_x = WIDTH//2 - total_w//2
        y_cards = HEIGHT//2 - card_h//2
        rects = [
            pygame.Rect(start_x + 0*(card_w+gap), y_cards, card_w, card_h),
            pygame.Rect(start_x + 1*(card_w+gap), y_cards, card_w, card_h),
            pygame.Rect(start_x + 2*(card_w+gap), y_cards, card_w, card_h),
        ]
        self._draw_card(screen, rects[0], "Cadencia", ICON_LIGHTNING, self.selection == 0)
        self._draw_card(screen, rects[1], "Balas +1", ICON_TWIN,      self.selection == 1)
        self._draw_card(screen, rects[2], "Disparo x2", ICON_DOUBLE,  self.selection == 2)
        draw_centered_text(screen, "←/→ para elegir • 1/2/3 o ENTER para confirmar", 20, HEIGHT - 40, COLOR_SUBTEXT)

# ================================
# UTILIDAD: TIMER (cooldowns)
# ================================
class Timer:
    def __init__(self): self._last = 0
    def ready(self, now_ms: int, cooldown_ms: int) -> bool:
        if now_ms - self._last >= cooldown_ms:
            self._last = now_ms
            return True
        return False

# ================================
# ENTIDADES: PLAYER / BULLET / FX
# ================================
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, PLAYER_SIZE[0], PLAYER_SIZE[1])
        self.rect.centerx = x
        self.rect.y = y
        self.speed = PLAYER_SPEED
        self._hurt_until = 0
        self._shake_mag  = HURT_SHAKE_MAG

    def hurt(self, ms=HURT_SHAKE_MS, mag=HURT_SHAKE_MAG):
        self._hurt_until = pygame.time.get_ticks() + ms
        self._shake_mag  = mag

    def update(self):
        keys = pygame.key.get_pressed()
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  dx -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += self.speed
        self.rect.x += dx
        if self.rect.left  < 10:             self.rect.left  = 10
        if self.rect.right > WIDTH - 10:     self.rect.right = WIDTH - 10

    def draw(self, screen):
        sprite_w = len(PLAYER_PATTERN[0]) * PIXEL_SCALE
        sprite_h = len(PLAYER_PATTERN) * PIXEL_SCALE
        x = self.rect.centerx - sprite_w // 2
        y = self.rect.centery - sprite_h // 2
        now = pygame.time.get_ticks()
        hurt = now < self._hurt_until
        if hurt:
            x += random.randint(-self._shake_mag, self._shake_mag)
            y += random.randint(-self._shake_mag, self._shake_mag)
        # parpadeo cada ~40ms (omitimos dibujar en frames pares)
        if hurt and ((now // 40) % 2 == 0):
            return
        color = (255, 255, 255) if hurt else COLOR_PLAYER
        draw_pixel_sprite(screen, PLAYER_PATTERN, x, y, color, PIXEL_SCALE)

class Bullet:
    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, BULLET_SIZE[0], BULLET_SIZE[1])
        self.rect.centerx = x
        self.rect.bottom  = y
        self.speed = BULLET_SPEED
        self.alive = True
        self.trail = []
        self._trail_accum = 0
    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.alive = False
            return
        self._trail_accum += 1
        if self._trail_accum % 2 == 0:
            self.trail.append([self.rect.centerx, self.rect.y + BULLET_SIZE[1] // 2, 180])
        for t in self.trail:
            t[2] -= 24
        self.trail = [t for t in self.trail if t[2] > 0]
    def draw(self, screen):
        for x, y, a in self.trail:
            s = pygame.Surface((3, 3), pygame.SRCALPHA)
            s.fill((255, 255, 255, max(0, min(255, a))))
            screen.blit(s, (x - 1, y - 1))
        pygame.draw.rect(screen, COLOR_BULLET, self.rect, border_radius=2)

class Explosion:
    def __init__(self, x, y, duration_ms=EXPLOSION_MS):
        self.x, self.y = x, y
        self.start = pygame.time.get_ticks()
        self.duration = duration_ms
        self.alive = True
    def update(self):
        if pygame.time.get_ticks() - self.start >= self.duration:
            self.alive = False
    def draw(self, screen):
        t = (pygame.time.get_ticks() - self.start) / max(1, self.duration)
        t = min(max(t, 0), 1)
        radius = int(4 + 18 * t)
        alpha  = int(255 * (1 - t))
        # ✅ fix: tamaño (w,h) correcto
        surf = pygame.Surface((radius*2 + 2, radius*2 + 2), pygame.SRCALPHA)
        color = (255, 220, 160, alpha)
        pygame.draw.circle(surf, color, (radius+1, radius+1), radius)
        screen.blit(surf, (self.x - radius - 1, self.y - radius - 1))

# ================================
# PICKUP DE VIDA
# ================================
class HealthPickup:
    def __init__(self, x, y, speed=HEALTH_DROP_SPEED):
        self.w = len(HEART_PATTERN[0]) * PIXEL_SCALE
        self.h = len(HEART_PATTERN) * PIXEL_SCALE
        self.rect = pygame.Rect(0, 0, self.w, self.h)
        self.rect.centerx = x
        self.rect.top = y
        self.speed = speed
        self.alive = True
        self._blink_until = pygame.time.get_ticks() + 180
    def update(self):
        self.rect.y += self.speed
        if self.rect.top > HEIGHT:
            self.alive = False
    def draw(self, screen):
        now = pygame.time.get_ticks()
        blink = now < self._blink_until and ((now // 80) % 2 == 0)
        color = (255, 100, 120) if blink else (255, 60, 90)
        draw_pixel_sprite(screen, HEART_PATTERN, self.rect.x, self.rect.y, color, PIXEL_SCALE)

# ================================
# ENEMY BULLET
# ================================
class EnemyBullet:
    def __init__(self, x, y, speed=5, color=COLOR_BOSS_BULLET):
        self.rect = pygame.Rect(0, 0, 4, 12)
        self.rect.centerx = x
        self.rect.top = y
        self.speed = speed
        self.alive = True
        self.color = color
    def update(self):
        self.rect.y += self.speed
        if self.rect.top > HEIGHT:
            self.alive = False
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=2)

# ================================
# STRATEGY movimiento enemigos
# ================================
class EnemyMovementStrategy:
    def step(self, grid): raise NotImplementedError

class HorizontalBounceStrategy(EnemyMovementStrategy):
    def step(self, grid):
        alive = grid._alive()
        if not alive: return
        now = pygame.time.get_ticks()
        for e in alive:
            e.rect.x += grid.direction * grid.x_speed
            e.update_anim(now)
        grid._recalc_bounds()
        grid.maybe_bounce(now, extra_margin=0)

class ZigZagBounceStrategy(EnemyMovementStrategy):
    def __init__(self, amplitude=2, speed_add=0.0):
        self.amplitude = amplitude
        self.speed_add = speed_add
    def step(self, grid):
        alive = grid._alive()
        if not alive: return
        now = pygame.time.get_ticks()
        for idx, e in enumerate(alive):
            phase = (now // 16 + idx) * 0.2
            e.rect.x += grid.direction * (grid.x_speed + self.speed_add) + int(self.amplitude * math.sin(phase))
            e.update_anim(now)
        grid._recalc_bounds()
        grid.maybe_bounce(now, extra_margin=self.amplitude + 1)

# ================================
# ENEMIGOS: sprite + grid
# ================================
ENEMY_PALETTE = [
    (255,120,120), (255,180,120), (120,220,120), (120,170,255), (220,120,220)
]

class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, ENEMY_SIZE[0], ENEMY_SIZE[1])
        self.alive = True
        self.variant = 0
        idx = ((x // 40) + (y // 24)) % len(ALIEN_PATTERNS)
        self.pattern = ALIEN_PATTERNS[idx]
        self.color   = ENEMY_PALETTE[((x // 40) + (y // 24)) % len(ENEMY_PALETTE)]
        self.can_shoot = False
        self._next_shot_at = 1_000_000_000
    def update_anim(self, now_ms):
        self.variant = (now_ms // 250) % 2
    def draw(self, screen):
        base = self.color
        col = (min(255, base[0]+20), min(255, base[1]+20), min(255, base[2]+20)) if self.variant else base
        sprite_w = len(self.pattern[0]) * PIXEL_SCALE
        sprite_h = len(self.pattern) * PIXEL_SCALE
        x = self.rect.centerx - sprite_w // 2
        y = self.rect.centery - sprite_h // 2
        draw_pixel_sprite(screen, self.pattern, x, y, col, PIXEL_SCALE)

class EnemyGrid:
    def __init__(self, rows=ENEMY_ROWS, x_speed=ENEMY_X_SPEED, strategy=None):
        self.rows = rows
        self.cols = ENEMY_COLS
        self.x_speed = x_speed
        self.drop = ENEMY_DROP
        self.direction = 1
        self.enemies = []
        self.bounds = pygame.Rect(0, 0, 0, 0)
        self.movement_strategy = strategy or HorizontalBounceStrategy()
        self.last_bounce = 0
        self.bounce_cooldown_ms = 400
        self._shoot_min_ms = ENEMY_SHOOT_MIN_MS
        self._shoot_max_ms = ENEMY_SHOOT_MAX_MS
        self._build_grid()
    def _build_grid(self):
        margin_x, margin_y = 60, 80
        gap_x, gap_y = 20, 18
        self.enemies.clear()
        for r in range(self.rows):
            for c in range(self.cols):
                x = margin_x + c * (ENEMY_SIZE[0] + gap_x)
                y = margin_y + r * (ENEMY_SIZE[1] + gap_y)
                self.enemies.append(Enemy(x, y))
        self._recalc_bounds()
    def _recalc_bounds(self):
        rects = [e.rect for e in self.enemies if e.alive]
        if not rects:
            self.bounds = pygame.Rect(0, 0, 0, 0); return
        b = rects[0].copy()
        for r in rects[1:]: b.union_ip(r)
        self.bounds = b
    def _alive(self):
        return [e for e in self.enemies if e.alive]
    def maybe_bounce(self, now, extra_margin=0):
        if now - self.last_bounce < self.bounce_cooldown_ms:
            return
        if self.bounds.left < 20 + extra_margin or self.bounds.right > WIDTH - 20 - extra_margin:
            self.direction *= -1
            for e in self._alive():
                e.rect.y += self.drop
            self._recalc_bounds()
            self.last_bounce = now
    # shooters y disparos
    def assign_shooters(self, level: int):
        alive_idxs = [i for i, e in enumerate(self.enemies) if e.alive]
        k = min(ENEMY_SHOOTERS_PER_LEVEL, len(alive_idxs))
        chosen = random.sample(alive_idxs, k) if k > 0 else []
        rate = max(0.7, 1.0 - 0.03 * (level - 1))
        min_ms = int(ENEMY_SHOOT_MIN_MS * rate)
        max_ms = int(ENEMY_SHOOT_MAX_MS * rate)
        now = pygame.time.get_ticks()
        for idx in chosen:
            e = self.enemies[idx]
            e.can_shoot = True
            e._next_shot_at = now + random.randint(min_ms, max_ms)
        self._shoot_min_ms = min_ms
        self._shoot_max_ms = max_ms
    def collect_shots(self):
        now = pygame.time.get_ticks()
        out = []
        for e in self.enemies:
            if not (e.alive and e.can_shoot): continue
            if now >= e._next_shot_at:
                cx = e.rect.centerx
                y  = e.rect.bottom
                out.append(EnemyBullet(cx, y, speed=ENEMY_BULLET_SPEED_NORM, color=COLOR_ENEMY_BULLET_NORM))
                e._next_shot_at = now + random.randint(self._shoot_min_ms, self._shoot_max_ms)
        return out
    def update(self):
        self.movement_strategy.step(self)
    def draw(self, screen):
        for e in self.enemies:
            if e.alive: e.draw(screen)
    def any_reached_bottom(self):
        return any(e.alive and e.rect.bottom >= HEIGHT - 80 for e in self.enemies)
    def alive_count(self):
        return sum(1 for e in self.enemies if e.alive)

# ================================
# ENTIDAD: BOSS
# ================================
class Boss:
    def __init__(self, hp, x_speed=BOSS_X_SPEED):
        self.rect = pygame.Rect(WIDTH // 2 - BOSS_SIZE[0] // 2, 80, BOSS_SIZE[0], BOSS_SIZE[1])
        self.max_hp = hp
        self.hp = hp
        self.x_speed = x_speed
        self.direction = 1
        self.alive = True
        self._next_shot_at = pygame.time.get_ticks() + random.randint(BOSS_SHOOT_MIN_MS, BOSS_SHOOT_MAX_MS)
        self._draw_y_offset = 0
        self._hurt_until = 0
    def update(self):
        now = pygame.time.get_ticks()
        self.rect.x += self.direction * self.x_speed
        if self.rect.left < 20 or self.rect.right > WIDTH - 20:
            self.direction *= -1
            self.rect.x += self.direction * self.x_speed
        self._draw_y_offset = int(BOSS_BOB_AMPLITUDE * math.sin(now * BOSS_BOB_SPEED))
    def try_shoot(self):
        now = pygame.time.get_ticks()
        if now >= self._next_shot_at:
            self._next_shot_at = now + random.randint(BOSS_SHOOT_MIN_MS, BOSS_SHOOT_MAX_MS)
            cx = self.rect.centerx; y = self.rect.bottom
            return [EnemyBullet(cx, y, speed=BOSS_BULLET_SPEED, color=COLOR_BOSS_BULLET),
                    EnemyBullet(cx - 20, y, speed=BOSS_BULLET_SPEED, color=COLOR_BOSS_BULLET),
                    EnemyBullet(cx + 20, y, speed=BOSS_BULLET_SPEED, color=COLOR_BOSS_BULLET)]
        return []
    def take_damage(self, dmg=1):
        self.hp -= dmg
        self._hurt_until = pygame.time.get_ticks() + 120  # flash
        if self.hp <= 0:
            self.alive = False
    def draw(self, screen):
        sprite_w = len(BOSS_PATTERN[0]) * PIXEL_SCALE
        sprite_h = len(BOSS_PATTERN) * PIXEL_SCALE
        x = self.rect.centerx - sprite_w // 2
        y = self.rect.y + (self.rect.height // 2 - sprite_h // 2) + self._draw_y_offset
        now = pygame.time.get_ticks()
        col = (255, 255, 255) if now < self._hurt_until else COLOR_BOSS
        draw_pixel_sprite(screen, BOSS_PATTERN, x, y, col, PIXEL_SCALE)
    def draw_healthbar(self, screen):
        bar_w, bar_h = 300, 12
        x = WIDTH // 2 - bar_w // 2; y = 50
        pygame.draw.rect(screen, (60, 60, 60), (x, y, bar_w, bar_h), border_radius=4)
        pct = max(0.0, self.hp / max(1, self.max_hp))
        pygame.draw.rect(screen, (255, 80, 80), (x, y, int(bar_w * pct), bar_h), border_radius=4)
        pygame.draw.rect(screen, (0, 0, 0), (x, y, bar_w, bar_h), width=2, border_radius=4)

# ================================
# FACTORY
# ================================
class EntityFactory:
    def create_bullet(self, x, y): return Bullet(x, y)
    def create_explosion(self, x, y): return Explosion(x, y)
    def create_enemy_bullet(self, x, y, speed, color): return EnemyBullet(x, y, speed, color)
    def create_health_pickup(self, x, y): return HealthPickup(x, y)
    def create_enemy_grid(self, level: int) -> 'EnemyGrid':
        rows = min(ENEMY_ROWS + (level // 2), 6)
        speed = ENEMY_X_SPEED + (level - 1) * max(0.15, ENEMY_X_STEP_RAMP * 0.6)
        if level >= 3:
            amp = 2 if level < 5 else 3
            strategy = ZigZagBounceStrategy(amplitude=amp)
        else:
            strategy = HorizontalBounceStrategy()
        grid = EnemyGrid(rows=rows, x_speed=speed, strategy=strategy)
        grid.drop = max(12, ENEMY_DROP - max(0, level-1))
        grid.assign_shooters(level)
        return grid
    def create_boss(self, level: int) -> 'Boss':
        cycles = max(1, level // BOSS_EVERY_N_LEVELS)
        hp = BOSS_BASE_HP + (cycles - 1) * BOSS_HP_PER_CYCLE
        x_speed = BOSS_X_SPEED + 0.2 * (cycles - 1)
        return Boss(hp=hp, x_speed=x_speed)

# ================================
# PLAY STATE
# ================================
class PlayState(State):
    def __init__(self, game):
        super().__init__(game)
        self.game.play_music_loop()
        self.player = Player(WIDTH // 2, HEIGHT - 60)
        self.bullets = []
        self.fire_timer = Timer()
        self.explosions = []
        self.bg = Starfield(layers=((80, 1), (50, 2), (25, 3)))
        self.health_pickups = []

        # Stats arma (power-ups)
        self.fire_cooldown_ms = FIRE_COOLDOWN_MS
        self.max_bullets      = MAX_BULLETS
        self.shot_count       = SHOT_COUNT_BASE

        self.level = 1
        self.factory = EntityFactory()
        self.enemy_grid = None
        self.enemy_bullets = []
        self.boss = None
        self.score = 0
        self.lives = LIVES
        self._setup_level()

    def _setup_level(self):
        self.enemy_bullets.clear()
        self.explosions.clear()
        self.health_pickups.clear()
        if self.level % BOSS_EVERY_N_LEVELS == 0:
            self.boss = self.factory.create_boss(self.level)
            self.enemy_grid = None
            self.game.play_boss_warn()
        else:
            self.boss = None
            self.enemy_grid = self.factory.create_enemy_grid(self.level)

    def _level_up_with_powerup(self, bonus):
        self.score += bonus
        self.game.play_levelup()
        just_finished = self.level
        self.level += 1
        if just_finished % POWERUP_EVERY_N_LEVELS == 0:
            self.game.change_state(PowerUpChoiceState(self.game, self))
        else:
            self._setup_level()

    def _on_player_hit(self, damage=1):
        self.player.hurt()
        self.game.play_hurt()
        self.lives -= damage
        if self.lives <= 0:
            self.game.change_state(GameOverState(self.game, self.score))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.change_state(GameOverState(self.game, self.score))
                elif event.key == pygame.K_p:
                    self.game.play_pause_in()
                    self.game.change_state(PauseState(self.game, self))
                elif event.key == pygame.K_m:
                    if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                    else: self.game.play_music_loop()
                elif event.key == pygame.K_c:
                    self.game.crt_on = not self.game.crt_on

    def shoot(self):
        now = pygame.time.get_ticks()
        if (len(self.bullets) + self.shot_count) <= self.max_bullets and \
           self.fire_timer.ready(now, self.fire_cooldown_ms):

            cx = self.player.rect.centerx
            y  = self.player.rect.top

            if self.shot_count == 1:
                self.bullets.append(self.factory.create_bullet(cx, y))
            else:
                offs = [-SHOT_SPREAD_PX // 2, SHOT_SPREAD_PX // 2]
                for off in offs:
                    self.bullets.append(self.factory.create_bullet(cx + off, y))

            self.game.play_shoot()

    def update(self):
        self.player.update()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.shoot()

        # balas propias
        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.alive]

        # pickups de vida
        for hp in self.health_pickups: hp.update()
        for hp in list(self.health_pickups):
            if hp.alive and hp.rect.colliderect(self.player.rect):
                if self.lives < MAX_LIVES:
                    self.lives = min(MAX_LIVES, self.lives + 1)
                    self.game.play_powerup()
                hp.alive = False
        self.health_pickups = [hp for hp in self.health_pickups if hp.alive]

        if self.boss:
            # --- MODO BOSS ---
            self.boss.update()
            new_shots = self.boss.try_shoot()
            if new_shots:
                self.enemy_bullets.extend(new_shots)
                self.game.play_enemy_shoot()

            for eb in self.enemy_bullets: eb.update()
            self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

            for eb in self.enemy_bullets:
                if eb.alive and eb.rect.colliderect(self.player.rect):
                    eb.alive = False
                    self._on_player_hit(1)

            for b in self.bullets:
                if not b.alive: continue
                if self.boss.alive and b.rect.colliderect(self.boss.rect):
                    b.alive = False
                    self.boss.take_damage(1)
                    self.explosions.append(self.factory.create_explosion(b.rect.centerx, b.rect.centery))
                    self.game.play_hit()

            if not self.boss.alive:
                self._level_up_with_powerup(BOSS_KILL_BONUS)

        else:
            # --- MODO NORMAL (grilla) ---
            self.enemy_grid.update()

            # disparos ocasionales
            new_eb = self.enemy_grid.collect_shots()
            if new_eb:
                self.enemy_bullets.extend(new_eb)
                self.game.play_enemy_shoot()

            for eb in self.enemy_bullets: eb.update()
            self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

            for eb in self.enemy_bullets:
                if eb.alive and eb.rect.colliderect(self.player.rect):
                    eb.alive = False
                    self._on_player_hit(1)

            # colisiones bala–enemigo
            for b in self.bullets:
                if not b.alive: continue
                for e in self.enemy_grid.enemies:
                    if e.alive and b.rect.colliderect(e.rect):
                        e.alive = False
                        b.alive = False
                        self.explosions.append(self.factory.create_explosion(e.rect.centerx, e.rect.centery))
                        self.score += SCORE_PER_ENEMY
                        self.game.play_hit()

                        # chance de dropear vida
                        if self.lives < MAX_LIVES and random.random() < HEALTH_DROP_CHANCE:
                            self.health_pickups.append(self.factory.create_health_pickup(e.rect.centerx, e.rect.centery))

                        break

            if self.enemy_grid.any_reached_bottom():
                self._on_player_hit(1)
                for e in self.enemy_grid.enemies:
                    e.rect.y -= ENEMY_DROP * 2

            if self.enemy_grid.alive_count() == 0:
                self._level_up_with_powerup(LEVEL_CLEAR_BONUS)

        # explosiones
        for ex in self.explosions: ex.update()
        self.explosions = [ex for ex in self.explosions if ex.alive]

    def render(self, screen):
        screen.fill(COLOR_BG_PLAY)
        self.bg.update(); self.bg.draw(screen)

        # HUD panel
        hud_h = 52 if not self.boss else 72
        panel = pygame.Surface((WIDTH, hud_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 110), (8, 8, WIDTH - 16, hud_h - 16), border_radius=16)
        screen.blit(panel, (0, 0))

        self.player.draw(screen)
        if self.boss: self.boss.draw(screen)
        else: self.enemy_grid.draw(screen)

        for b in self.bullets: b.draw(screen)
        for ex in self.explosions: ex.draw(screen)
        for eb in self.enemy_bullets: eb.draw(screen)
        for hp in self.health_pickups: hp.draw(screen)

        # HUD
        font = pygame.font.SysFont(FONT_NAME, 24)
        active = self.game.profiles.get_active()
        best = active.get("high_score", 0) if active else 0
        pname = active["name"] if active else "Guest"
        hud = font.render(f"{pname}  |  Score: {self.score}   Lives: {self.lives}/{MAX_LIVES}   Level: {self.level}   Best: {best}", True, COLOR_TEXT)
        screen.blit(hud, (10, 10))

        if self.boss:
            font_small = pygame.font.SysFont(FONT_NAME, 20)
            boss_txt = font_small.render("BOSS LEVEL", True, COLOR_ACCENT)
            screen.blit(boss_txt, (10, 40))
            self.boss.draw_healthbar(screen)

        font_small = pygame.font.SysFont(FONT_NAME, 18)
        info = font_small.render(
            f"Bullets cap: {self.max_bullets}  |  Cooldown: {self.fire_cooldown_ms} ms  |  Shot: x{self.shot_count}",
            True, COLOR_SUBTEXT
        )
        screen.blit(info, (10, 36 if not self.boss else 60))

        if getattr(self.game, "crt_on", False):
            screen.blit(self.game.crt_overlay, (0, 0))

# ================================
# CLASE GAME (loop, audio, perfiles)
# ================================
class Game:
    def __init__(self):
        self.profiles = ProfileManager()

        # AUDIO
        self.snd_shoots = []
        self.snd_hit    = None
        self.snd_hurt   = None
        self.snd_power  = None
        self.snd_enemy_shoot = None
        self.snd_levelup = None
        self.snd_boss_warn = None
        self.snd_pause_in  = None
        self.snd_pause_out = None
        self.snd_select = None
        self.snd_confirm = None
        self.snd_gameover = None
        self.music_ok   = False

        self._shoot_rr = 0
        self.ch_pool_shoot = []
        self.ch_hit  = None
        self.ch_hurt = None
        self.ch_ui   = None
        self.ch_enemy = None

        def resolve_path(filename):
            """Busca en assets/ y assets/sonidos/."""
            p1 = os.path.join(ASSETS_DIR, filename)
            p2 = os.path.join(ASSETS_DIR, "sonidos", filename)
            if os.path.exists(p1): return p1
            if os.path.exists(p2): return p2
            return None

        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            self.ch_pool_shoot = [pygame.mixer.Channel(i) for i in range(4)]
            self.ch_hit  = pygame.mixer.Channel(10)
            self.ch_hurt = pygame.mixer.Channel(11)
            self.ch_ui   = pygame.mixer.Channel(12)
            self.ch_enemy= pygame.mixer.Channel(13)

            # --- Player shots (múltiples candidatos) ---
            shoot_candidates = ["shoot.wav", "shoot1.wav", "shoot2.wav", "laser.wav"]
            for name in shoot_candidates:
                path = resolve_path(name)
                if path:
                    try:
                        s = pygame.mixer.Sound(path)
                        s.set_volume(SFX_VOLUME)
                        self.snd_shoots.append(s)
                    except Exception:
                        pass

            # --- Efectos varios ---
            def load_one(fname):
                p = resolve_path(fname)
                if not p: return None
                try:
                    s = pygame.mixer.Sound(p)
                    s.set_volume(SFX_VOLUME)
                    return s
                except Exception:
                    return None

            self.snd_hit        = load_one("hit.wav")
            self.snd_hurt       = load_one("hurt.wav")
            self.snd_power      = load_one("powerup.wav")
            self.snd_enemy_shoot= load_one("enemy_shoot.wav")
            self.snd_levelup    = load_one("levelup.wav")
            self.snd_boss_warn  = load_one("boss_warn.wav")
            self.snd_pause_in   = load_one("pause_in.wav")
            self.snd_pause_out  = load_one("pause_out.wav")
            self.snd_select     = load_one("select.wav")
            self.snd_confirm    = load_one("confirm.wav")
            self.snd_gameover   = load_one("gameover.wav")

            # Música
            mpath = resolve_path("bgm.mp3") or resolve_path("bgm.wav")
            if mpath:
                try:
                    pygame.mixer.music.load(mpath)
                    pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    self.music_ok = True
                except Exception:
                    self.music_ok = False

        except Exception:
            self.snd_shoots = []
            self.snd_hit = self.snd_hurt = self.snd_power = None
            self.snd_enemy_shoot = self.snd_levelup = self.snd_boss_warn = None
            self.snd_pause_in = self.snd_pause_out = None
            self.snd_select = self.snd_confirm = self.snd_gameover = None
            self.music_ok = False
            self.ch_pool_shoot = []
            self.ch_hit = self.ch_hurt = self.ch_ui = self.ch_enemy = None
            self._shoot_rr = 0

        self.crt_overlay = build_crt_overlay()
        self.crt_on = True
        self.state = MenuState(self)

    # ==== SFX helpers ====
    def play_shoot(self):
        if not self.snd_shoots or not self.ch_pool_shoot: return
        ch = self.ch_pool_shoot[self._shoot_rr]
        self._shoot_rr = (self._shoot_rr + 1) % len(self.ch_pool_shoot)
        ch.play(random.choice(self.snd_shoots))
    def play_hit(self):
        if self.snd_hit and self.ch_hit: self.ch_hit.play(self.snd_hit)
    def play_hurt(self):
        if self.snd_hurt and self.ch_hurt: self.ch_hurt.play(self.snd_hurt)
    def play_powerup(self):
        if self.snd_power and self.ch_ui: self.ch_ui.play(self.snd_power)
    def play_enemy_shoot(self):
        if self.snd_enemy_shoot and self.ch_enemy: self.ch_enemy.play(self.snd_enemy_shoot)
    def play_levelup(self):
        if self.snd_levelup and self.ch_ui: self.ch_ui.play(self.snd_levelup)
    def play_boss_warn(self):
        if self.snd_boss_warn and self.ch_ui: self.ch_ui.play(self.snd_boss_warn)
    def play_pause_in(self):
        if self.snd_pause_in and self.ch_ui: self.ch_ui.play(self.snd_pause_in)
    def play_pause_out(self):
        if self.snd_pause_out and self.ch_ui: self.ch_ui.play(self.snd_pause_out)
    def play_select(self):
        if self.snd_select and self.ch_ui: self.ch_ui.play(self.snd_select)
    def play_confirm(self):
        if self.snd_confirm and self.ch_ui: self.ch_ui.play(self.snd_confirm)
    def play_gameover(self):
        if self.snd_gameover and self.ch_ui: self.ch_ui.play(self.snd_gameover)

    def change_state(self, new_state): self.state = new_state
    def play_music_loop(self):
        if self.music_ok and not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)

    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT: running = False
            self.state.handle_events(events)
            self.state.update()
            self.state.render(screen)
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()
        sys.exit()

# ================================
# PUNTO DE ENTRADA
# ================================
if __name__ == "__main__":
    Game().run()
