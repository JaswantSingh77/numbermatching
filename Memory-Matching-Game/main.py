import math
import random
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pygame

# Number Match - BCA Lab Project
# Python 3.13 + Pygame 2.6.1. Run: py -3.13 main.py

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

W, H = 1100, 760
MIN_W, MIN_H = 850, 620
screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption("NUMBER MATCH - Memory Game")
clock = pygame.time.Clock()

BG = (15, 19, 33)
PANEL = (27, 35, 56)
LIGHT = (43, 54, 82)
WHITE = (240, 244, 255)
MUTED = (160, 173, 198)
BLUE = (102, 126, 234)
GREEN = (35, 125, 94)
PURPLE = (112, 83, 165)
GOLD = (245, 190, 75)
RED = (190, 70, 83)
LEVELS = {1: 5, 2: 7, 3: 10, 4: 12, 5: 15, 6: 18}
ROOT = Path(__file__).resolve().parent
DB_DIR = ROOT / "database"
DB_PATH = DB_DIR / "scores.db"
fonts = {}


def fnt(size, bold=False):
    key = (size, bold)
    if key not in fonts:
        fonts[key] = pygame.font.SysFont("segoeui", size, bold=bold)
    return fonts[key]


def text(s, size, color=WHITE, center=None, pos=None, bold=False):
    image = fnt(size, bold).render(str(s), True, color)
    rect = image.get_rect()
    if center is not None:
        rect.center = center
    elif pos is not None:
        rect.topleft = pos
    screen.blit(image, rect)


def box(rect, color=PANEL, radius=15, border=None):
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(screen, border, rect, 1, border_radius=radius)


def fmt(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02}:{seconds % 60:02}"


def init_db():
    DB_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS results(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL, level INTEGER NOT NULL, score INTEGER NOT NULL,
            moves INTEGER NOT NULL, seconds REAL NOT NULL, played_at TEXT NOT NULL)""")


def save_result(player, level, score, moves, seconds):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO results(player,level,score,moves,seconds,played_at) VALUES(?,?,?,?,?,?)",
                (player, level, score, moves, seconds, datetime.now().isoformat(timespec="seconds")))
    except sqlite3.Error as exc:
        print("Database save error:", exc)


def leaderboard():
    try:
        with sqlite3.connect(DB_PATH) as db:
            return db.execute(
                "SELECT player,level,score,moves,seconds FROM results "
                "ORDER BY score DESC, seconds ASC LIMIT 10").fetchall()
    except sqlite3.Error as exc:
        print("Database read error:", exc)
        return []


class Game:
    def __init__(self, player):
        self.player = player or "Player"
        self.level = 1
        self.total_score = 0
        self.new_level()

    def new_level(self):
        pairs = LEVELS[self.level]
        self.numbers = list(range(1, pairs + 1)) * 2
        random.shuffle(self.numbers)
        self.matched = set()
        self.opened = []
        self.moves = 0
        self.score = 0
        self.started = time.monotonic()
        self.elapsed = 0
        self.done = False
        self.hide_at = 0
        self.hint_until = 0
        self.message = "Find the matching numbers!"
        self.message_until = time.monotonic() + 2

    def say(self, message, duration=1.6):
        self.message = message
        self.message_until = time.monotonic() + duration

    def pick(self, index):
        now = time.monotonic()
        if self.done or now < self.hide_at or now < self.hint_until:
            return
        if index in self.matched or index in self.opened:
            return
        self.opened.append(index)
        if len(self.opened) == 2:
            self.moves += 1
            a, b = self.opened
            if self.numbers[a] == self.numbers[b]:
                self.matched.update((a, b))
                self.score += 100
                self.total_score += 100
                self.opened.clear()
                self.say("Correct match! +100", 1.2)
                if len(self.matched) == len(self.numbers):
                    self.finish()
            else:
                self.score = max(0, self.score - 5)
                self.total_score = max(0, self.total_score - 5)
                self.hide_at = now + 0.8
                self.say("Not a match!", 0.8)

    def update(self):
        now = time.monotonic()
        if len(self.opened) == 2 and now >= self.hide_at:
            self.opened.clear()
        if now >= self.hint_until:
            self.hint_until = 0

    def hint(self):
        now = time.monotonic()
        if self.done or len(self.opened) == 2 or self.hint_until > now:
            self.say("Finish your current move first.")
        elif self.score < 20:
            self.say("You need 20 points to use a hint.")
        else:
            self.score -= 20
            self.total_score = max(0, self.total_score - 20)
            self.hint_until = now + 1.2
            self.say("Hint: all unmatched numbers are shown briefly.", 1.2)

    def finish(self):
        self.elapsed = time.monotonic() - self.started
        self.done = True
        bonus = max(0, 300 - int(self.elapsed)) + max(0, 200 - max(0, self.moves - len(self.numbers)//2)*5)
        self.score += bonus
        self.total_score += bonus
        save_result(self.player, self.level, self.score, self.moves, self.elapsed)
        self.say(f"Level complete! Bonus +{bonus}", 4)


def tile_rects(count):
    sw, sh = screen.get_size()
    cols = 5 if count <= 10 else 7 if count <= 14 else 6
    rows = math.ceil(count / cols)
    gap = 11
    area_top, area_bottom = 210, sh - 115
    area_h = area_bottom - area_top
    tw = min(105, (sw - 90 - gap * (cols - 1)) // cols)
    th = min(82, (area_h - gap * (rows - 1)) // rows)
    tw = max(48, min(tw, th + 12))
    th = max(48, min(th, tw - 12))
    start_x = (sw - (cols * tw + (cols - 1) * gap)) // 2
    total_h = rows * th + (rows - 1) * gap
    start_y = area_top + max(0, (area_h - total_h) // 2)
    return [pygame.Rect(start_x + (i % cols)*(tw+gap),
                        start_y + (i // cols)*(th+gap), tw, th)
            for i in range(count)]


class App:
    def __init__(self):
        init_db()
        self.state = "menu"
        self.player = "Player"
        self.edit_name = False
        self.game = None
        self.sound = True
        self.buttons = {}

    def button(self, key, label, rect, color=BLUE, size=18):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        c = tuple(min(255, x + 20) for x in color) if hover else color
        box(rect, c, 11)
        text(label, size, WHITE, center=rect.center, bold=True)
        self.buttons[key] = rect

    def header(self, title, subtitle=""):
        sw, _ = screen.get_size()
        text(title, 34, WHITE, center=(sw//2, 55), bold=True)
        if subtitle:
            text(subtitle, 15, MUTED, center=(sw//2, 91))

    def draw_menu(self):
        screen.fill(BG)
        self.header("NUMBER MATCH", "A little challenge for your memory")
        sw, sh = screen.get_size()
        r = pygame.Rect(sw//2-235, 135, 470, min(535, sh-165))
        box(r)
        text("Match identical numbers", 21, WHITE, center=(sw//2, 180), bold=True)
        text("Player name (click the field to edit)", 14, MUTED, center=(sw//2, 225))
        nr = pygame.Rect(sw//2-155, 244, 310, 45)
        box(nr, LIGHT, 9, BLUE if self.edit_name else None)
        text(self.player + ("|" if self.edit_name else ""), 18, WHITE, center=nr.center)
        self.buttons["name"] = nr
        y = 315
        for key, label, color in [
            ("start", "START GAME", BLUE), ("instructions", "INSTRUCTIONS", LIGHT),
            ("leaderboard", "LEADERBOARD", LIGHT), ("settings", "SETTINGS", LIGHT)]:
            self.button(key, label, pygame.Rect(sw//2-145, y, 290, 47), color)
            y += 60
        text("Python 3.13  •  Pygame  •  SQLite", 13, MUTED, center=(sw//2, sh-25))

    def draw_game(self):
        g = self.game
        screen.fill(BG)
        sw, sh = screen.get_size()
        self.header("NUMBER MATCH", f"LEVEL {g.level}  •  {LEVELS[g.level]} PAIRS")
        stat_rect = pygame.Rect(25, 112, sw-50, 75)
        box(stat_rect)
        stats = [("SCORE", g.total_score), ("MOVES", g.moves),
                 ("TIME", fmt(time.monotonic()-g.started) if not g.done else fmt(g.elapsed)),
                 ("MATCHED", f"{len(g.matched)//2}/{LEVELS[g.level]}"),
                 ("PLAYER", g.player[:12])]
        slot = (sw-80)//len(stats)
        for i, (label, value) in enumerate(stats):
            x = 40 + i*slot
            text(label, 12, MUTED, center=(x+slot//2, 135), bold=True)
            text(value, 18, WHITE, center=(x+slot//2, 162), bold=True)

        now = time.monotonic()
        rects = tile_rects(len(g.numbers))
        for i, r in enumerate(rects):
            matched = i in g.matched
            revealed = i in g.opened
            hinted = g.hint_until > now and not matched
            color = GREEN if matched else PURPLE if hinted else (LIGHT if revealed else (54,67,101))
            box(r, color, 12, (85,102,145))
            if matched or revealed or hinted:
                text(g.numbers[i], max(22, r.height//2), WHITE, center=r.center, bold=True)
            else:
                text("?", max(22, r.height//2), MUTED, center=r.center, bold=True)

        by = sh-68
        self.button("hint", "USE HINT (-20)", pygame.Rect(30, by, 175, 43), PURPLE, 15)
        self.button("restart", "RESTART LEVEL", pygame.Rect(220, by, 175, 43), LIGHT, 15)
        self.button("menu", "MAIN MENU", pygame.Rect(sw-205, by, 175, 43), LIGHT, 15)
        if now < g.message_until:
            text(g.message, 15, GOLD, center=(sw//2, sh-95), bold=True)
        if g.done:
            self.draw_complete()

    def draw_complete(self):
        sw, sh = screen.get_size()
        shade = pygame.Surface((sw, sh), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 185))
        screen.blit(shade, (0, 0))
        r = pygame.Rect(sw//2-220, sh//2-175, 440, 350)
        box(r)
        final = self.game.level == 6
        text("YOU WON!" if final else "LEVEL COMPLETE!", 27, GOLD,
             center=(sw//2, r.y+45), bold=True)
        text(f"Level: {self.game.level}", 18, WHITE, center=(sw//2, r.y+100))
        text(f"Score: {self.game.score}", 18, WHITE, center=(sw//2, r.y+137))
        text(f"Moves: {self.game.moves}", 18, WHITE, center=(sw//2, r.y+174))
        text(f"Time: {fmt(self.game.elapsed)}", 18, WHITE, center=(sw//2, r.y+211))
        if final:
            self.button("again", "PLAY AGAIN", pygame.Rect(sw//2-105, r.y+265, 210, 45))
        else:
            self.button("next", "NEXT LEVEL", pygame.Rect(sw//2-105, r.y+265, 210, 45))

    def draw_instructions(self):
        screen.fill(BG)
        sw, sh = screen.get_size()
        self.header("HOW TO PLAY")
        r = pygame.Rect(sw//2-365, 135, 730, 455)
        box(r)
        lines = [
            "1. Enter your name on the main menu.",
            "2. Reveal two tiles by clicking them.",
            "3. Match identical numbers; matched tiles stay visible.",
            "4. Different numbers hide again after a short delay.",
            "5. Each correct match gives 100 points.",
            "6. Each incorrect match deducts 5 points.",
            "7. A hint reveals unmatched numbers briefly and costs 20 points.",
            "8. Complete all pairs to move to the next level.",
            "",
            "Levels contain 5, 7, 10, 12, 15 and 18 pairs.",
            "Press R to restart a level. Press ESC to return to menu."
        ]
        for i, line in enumerate(lines):
            text(line, 17, WHITE, pos=(r.x+35, r.y+35+i*34))
        self.button("back", "BACK", pygame.Rect(sw//2-85, sh-85, 170, 44), LIGHT)

    def draw_leaderboard(self):
        screen.fill(BG)
        sw, sh = screen.get_size()
        self.header("LEADERBOARD", "Top saved results on this computer")
        r = pygame.Rect(sw//2-410, 130, 820, 475)
        box(r)
        heads = [("PLAYER", r.x+30), ("LEVEL", r.x+310), ("SCORE", r.x+415),
                 ("MOVES", r.x+535), ("TIME", r.x+655)]
        for label, x in heads:
            text(label, 14, GOLD, pos=(x, r.y+25), bold=True)
        rows = leaderboard()
        if not rows:
            text("No saved scores yet. Complete a level first.", 17, MUTED,
                 center=(sw//2, r.y+110))
        for i, row in enumerate(rows):
            player, level, score, moves, seconds = row
            y = r.y+65+i*34
            for value, x in [(player[:18], r.x+30), (level, r.x+325),
                             (score, r.x+420), (moves, r.x+545), (fmt(seconds), r.x+660)]:
                text(value, 15, WHITE if i < 3 else MUTED, pos=(x, y))
        self.button("back", "BACK", pygame.Rect(sw//2-85, sh-85, 170, 44), LIGHT)

    def draw_settings(self):
        screen.fill(BG)
        sw, sh = screen.get_size()
        self.header("SETTINGS")
        r = pygame.Rect(sw//2-230, 180, 460, 300)
        box(r)
        self.button("sound", f"SOUND: {'ON' if self.sound else 'OFF'}",
                    pygame.Rect(sw//2-140, 255, 280, 55), LIGHT)
        text("Scores are stored locally in database/scores.db", 14, MUTED,
             center=(sw//2, 360))
        self.button("back", "BACK", pygame.Rect(sw//2-85, 415, 170, 44), LIGHT)

    def draw(self):
        self.buttons = {}
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "game":
            self.draw_game()
        elif self.state == "instructions":
            self.draw_instructions()
        elif self.state == "leaderboard":
            self.draw_leaderboard()
        elif self.state == "settings":
            self.draw_settings()
        pygame.display.flip()

    def click(self, pos):
        if self.state == "game" and self.game and not self.game.done:
            for i, r in enumerate(tile_rects(len(self.game.numbers))):
                if r.collidepoint(pos):
                    self.game.pick(i)
                    return
        key = next((k for k, r in self.buttons.items() if r.collidepoint(pos)), None)
        if key == "name":
            self.edit_name = True
        elif key == "start":
            self.game = Game(self.player.strip() or "Player")
            self.state = "game"
            self.edit_name = False
        elif key == "instructions":
            self.state = "instructions"
        elif key == "leaderboard":
            self.state = "leaderboard"
        elif key == "settings":
            self.state = "settings"
        elif key == "back":
            self.state = "menu"
        elif key == "sound":
            self.sound = not self.sound
        elif key == "hint" and self.game:
            self.game.hint()
        elif key == "restart" and self.game:
            self.game.new_level()
        elif key == "menu":
            self.state = "menu"
        elif key == "next" and self.game and self.game.level < 6:
            self.game.level += 1
            self.game.new_level()
        elif key == "again":
            self.game = Game(self.player.strip() or "Player")

    def event(self, e):
        global screen
        if e.type == pygame.QUIT:
            return False
        if e.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((max(MIN_W, e.w), max(MIN_H, e.h)), pygame.RESIZABLE)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click(e.pos)
        elif e.type == pygame.KEYDOWN:
            if self.state == "menu" and self.edit_name:
                if e.key == pygame.K_RETURN:
                    self.edit_name = False
                elif e.key == pygame.K_BACKSPACE:
                    self.player = self.player[:-1]
                elif e.unicode.isprintable() and len(self.player) < 22:
                    self.player += e.unicode
            elif e.key == pygame.K_ESCAPE:
                if self.state == "menu":
                    return False
                self.state = "menu"
            elif self.state == "game" and self.game:
                if e.key == pygame.K_r and not self.game.done:
                    self.game.new_level()
                elif e.key == pygame.K_RETURN and self.game.done and self.game.level < 6:
                    self.game.level += 1
                    self.game.new_level()
        return True

    def run(self):
        running = True
        while running:
            for e in pygame.event.get():
                running = self.event(e)
                if not running:
                    break
            if self.state == "game" and self.game:
                self.game.update()
            self.draw()
            clock.tick(60)
        pygame.quit()


if __name__ == "__main__":
    App().run()
