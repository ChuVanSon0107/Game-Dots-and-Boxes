import pygame
import sys
import math
import os
import random
import rules
import models

class UI:
    def __init__(self, GameState):
        pygame.init()
        pygame.mixer.init() 
        
        # --- WINDOW & DISPLAY SETUP ---
        self.W, self.H = 800, 600
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Dots and Boxes - AI Project")
        self.clock = pygame.time.Clock()
        
        # ==========================================
        # THEME ENGINE (UI COLORS)
        # ==========================================
        self.themes = [
            {
                'name': 'Classic Wood',
                'use_bg_image': True,
                'bg_top': (220, 240, 245), 'bg_bot': (250, 240, 230),
                'board_bg': None, 
                'text_main': (70, 70, 70), 'text_score': (80, 80, 80),
                'p1': (45, 212, 235), 'p2': (255, 65, 84), 
                'dot_core': (255, 255, 255), 'dot_out': (200, 190, 180),
                'line_empty': (220, 210, 200), 'line_fill': (100, 100, 100)
            },
            {
                'name': 'Dark Night',
                'use_bg_image': False,
                'bg_top': (20, 25, 35), 'bg_bot': (10, 15, 20), # Nền trời đêm tối hơn
                'board_bg': (30, 30, 35), 
                'text_main': (230, 230, 230), 'text_score': (200, 200, 200),
                'p1': (255, 180, 0), 'p2': (0, 200, 255), 
                'dot_core': (60, 60, 65), 'dot_out': (255, 180, 0),
                'line_empty': (50, 50, 55), 'line_fill': (200, 200, 200)
            },
            {
                'name': 'Snow White',
                'use_bg_image': False,
                'bg_top': (200, 220, 240), 'bg_bot': (230, 240, 250), # Nền trời mùa đông
                'board_bg': (255, 255, 255), 
                'text_main': (50, 50, 50), 'text_score': (100, 100, 100),
                'p1': (230, 50, 70), 'p2': (50, 100, 230), 
                'dot_core': (255, 255, 255), 'dot_out': (200, 200, 200),
                'line_empty': (235, 235, 235), 'line_fill': (80, 80, 80)
            }
        ]
        self.current_theme_idx = 0
        self.apply_theme()

        self.font_title = pygame.font.SysFont("Verdana", 45, bold=True)
        self.font_turn = pygame.font.SysFont("Verdana", 32, bold=True) 
        self.font_score = pygame.font.SysFont("Verdana", 28, bold=True) 
        self.font_menu = pygame.font.SysFont("Verdana", 30, bold=True)
        self.font_text = pygame.font.SysFont("Verdana", 20)

        # --- ASSETS LOADING ---
        self.bg_image = None
        base_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            bg_path = os.path.join(base_dir, "assets", "images", "wood_bg.jpg")
            img = pygame.image.load(bg_path)
            self.bg_image = pygame.transform.scale(img, (self.W, self.H))
        except Exception:
            pass 

        self.sound_enabled = True
        self.sounds = {}
        try:
            self.sounds['click'] = pygame.mixer.Sound(os.path.join(base_dir, "assets", "sounds", "click.wav"))
            self.sounds['capture'] = pygame.mixer.Sound(os.path.join(base_dir, "assets", "sounds", "capture.wav"))
            self.sounds['win'] = pygame.mixer.Sound(os.path.join(base_dir, "assets", "sounds", "win.wav"))
        except Exception:
            pass

        # --- GAME STATE & FLAGS ---
        self.app_state = 'MENU'
        self.previous_state = 'MENU' 
        self.show_tutorial = False 
        
        self.GameState = GameState
        self.size = GameState.rows + 1 
        self.edge = 65 
        self.board_width = (self.size - 1) * self.edge 
        self.board_height = (self.size - 1) * self.edge
        self.margin_left = (self.W - self.board_width) // 2 
        self.margin_up = 165 
        
        self.selected_dot = None 
        self.floating_texts = [] 
        self.history_undo_info = []

        self.p1_shake_timer = 0
        self.p2_shake_timer = 0

        # --- TẠO SẴN DỮ LIỆU PARTICLE CHO CÁC THEME ---
        # 1. Dark Night: Tạo 60 vì sao (x, y, radius)
        self.stars = [(random.randint(0, self.W), random.randint(0, self.H), random.randint(1, 3)) for _ in range(60)]
        # 2. Snow White: Tạo 80 bông tuyết (x, y, radius, speed)
        self.snowflakes = [[random.randint(0, self.W), random.randint(0, self.H), random.uniform(2, 4), random.uniform(1, 2.5)] for _ in range(80)]
        # 3. Classic Wood: Tạo 30 chiếc lá rơi (x, y)
        self.leaves = [[random.randint(0, self.W), random.randint(0, self.H)] for _ in range(30)]

    def apply_theme(self):
        t = self.themes[self.current_theme_idx]
        self.P1_COLOR = t['p1']
        self.P2_COLOR = t['p2']
        self.DOT_COLOR = t['dot_core']
        self.DOT_OUTLINE = t['dot_out']
        self.LINE_EMPTY = t['line_empty']
        self.LINE_FILLED = t['line_fill']
        self.TEXT_MAIN = t['text_main']
        self.TEXT_SCORE = t['text_score']

    def play_sound(self, sound_name):
        if self.sound_enabled and sound_name in self.sounds:
            self.sounds[sound_name].play()

    # ==========================================
    # UI COMPONENT ENGINE
    # ==========================================
    def _draw_enhanced_button(self, text, x_center, y_center, width, height, bg_color, text_color):
        mouse_pos = pygame.mouse.get_pos()
        radius = 15
        base_rect = pygame.Rect(0, 0, width, height)
        base_rect.center = (x_center, y_center)
        
        is_hovered = base_rect.collidepoint(mouse_pos) and not self.show_tutorial
        display_rect = base_rect.copy()
        current_color = bg_color
        shadow_offset = 5 
        
        if is_hovered:
            display_rect.y -= 4
            shadow_offset += 4 
            current_color = (min(255, bg_color[0] + 35), min(255, bg_color[1] + 35), min(255, bg_color[2] + 35))
            
        shadow_rect = display_rect.copy()
        shadow_rect.y += shadow_offset 
        s_color = (20, 20, 20) if self.current_theme_idx == 1 else (160, 150, 140)
        pygame.draw.rect(self.screen, s_color, shadow_rect, border_radius=radius)
        pygame.draw.rect(self.screen, current_color, display_rect, border_radius=radius)
        
        btn_surf = self.font_menu.render(text, True, text_color)
        text_rect = btn_surf.get_rect(center=display_rect.center)
        self.screen.blit(btn_surf, text_rect)
        return base_rect

    def _draw_setting_selector(self, label, value_text, y_pos):
        label_surf = self.font_turn.render(label, True, self.TEXT_MAIN)
        self.screen.blit(label_surf, (self.W // 2 - label_surf.get_width() // 2, y_pos - 45))

        box_w, box_h = 340, 56
        box_rect = pygame.Rect(0, 0, box_w, box_h)
        box_rect.center = (self.W // 2, y_pos + 15)
        
        shadow_rect = box_rect.copy()
        shadow_rect.y += 4
        s_color = (20, 20, 20) if self.current_theme_idx == 1 else (160, 150, 140)
        pygame.draw.rect(self.screen, s_color, shadow_rect, border_radius=15)
        pygame.draw.rect(self.screen, (255, 255, 255), box_rect, border_radius=15)

        val_surf = self.font_turn.render(value_text, True, (50, 50, 50))
        self.screen.blit(val_surf, (self.W // 2 - val_surf.get_width() // 2, y_pos + 15 - val_surf.get_height() // 2))

        cyan_color = (0, 190, 200) 
        l_btn = self._draw_enhanced_button("<", self.W // 2 - box_w // 2 + 10, y_pos + 15, 55, 55, cyan_color, (255, 255, 255))
        r_btn = self._draw_enhanced_button(">", self.W // 2 + box_w // 2 - 10, y_pos + 15, 55, 55, cyan_color, (255, 255, 255))
        return l_btn, r_btn

    # ==========================================
    # HỆ THỐNG VẼ BACKGROUND THEO THEME MỚI CỰC CHẤT
    # ==========================================
    def _draw_background(self):
        t = self.themes[self.current_theme_idx]
        theme_name = t['name']

        # 1. Vẽ phông nền cơ bản (Gradient hoặc Ảnh)
        if t['use_bg_image'] and self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
            overlay = pygame.Surface((self.W, self.H))
            overlay.set_alpha(150)
            overlay.fill((255, 255, 255))
            self.screen.blit(overlay, (0, 0))
        else:
            top_c, bot_c = t['bg_top'], t['bg_bot']
            for y in range(self.H):
                r = top_c[0] + (bot_c[0] - top_c[0]) * y // self.H
                g = top_c[1] + (bot_c[1] - top_c[1]) * y // self.H
                b = top_c[2] + (bot_c[2] - top_c[2]) * y // self.H
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

        # 2. VẼ CHI TIẾT ĐỒ HỌA TRANG TRÍ DỰA VÀO THEME HIỆN TẠI
        if theme_name == 'Classic Wood':
            # Vẽ Bãi cỏ mờ ở phía dưới
            pygame.draw.rect(self.screen, (130, 180, 110), (0, self.H - 50, self.W, 50))
            
            # Vẽ một vài khóm hoa
            for fx in [100, 250, 450, 600, 750]:
                # Thân cây
                pygame.draw.line(self.screen, (90, 150, 70), (fx, self.H - 50), (fx, self.H - 70), 4)
                # Cánh hoa màu hồng
                for dx, dy in [(-6, -4), (6, -4), (0, -10), (0, 2)]:
                    pygame.draw.circle(self.screen, (255, 150, 180), (fx + dx, self.H - 70 + dy), 6)
                # Nhụy hoa màu vàng
                pygame.draw.circle(self.screen, (255, 220, 50), (fx, self.H - 70), 5)
                
            # Hiệu ứng Lá rơi đung đưa
            for leaf in self.leaves:
                pygame.draw.ellipse(self.screen, (150, 200, 100), (leaf[0], int(leaf[1]), 12, 8))
                leaf[1] += 0.8 # Tốc độ rơi
                leaf[0] += math.sin(leaf[1] * 0.05) * 1.5 # Đung đưa ngang
                if leaf[1] > self.H: # Chạm đáy thì rớt lại từ trên đỉnh
                    leaf[1] = -10
                    leaf[0] = random.randint(0, self.W)

        elif theme_name == 'Dark Night':
            # Vẽ các vì sao rải rác
            for star in self.stars:
                pygame.draw.circle(self.screen, (255, 255, 220), (star[0], star[1]), star[2])
                
            # Vẽ Mặt trăng sáng rực ở góc trên bên phải
            pygame.draw.circle(self.screen, (255, 255, 200), (self.W - 100, 100), 45)
            pygame.draw.circle(self.screen, (255, 255, 230), (self.W - 100, 100), 35)

        elif theme_name == 'Snow White':
            # Vẽ 3 ngọn núi tuyết nhấp nhô phía sau bàn cờ
            pygame.draw.polygon(self.screen, (200, 210, 225), [(0, self.H), (200, self.H - 250), (450, self.H)])
            pygame.draw.polygon(self.screen, (180, 190, 205), [(250, self.H), (500, self.H - 300), (800, self.H)])
            pygame.draw.polygon(self.screen, (220, 230, 240), [(-50, self.H), (100, self.H - 150), (300, self.H)])
            
            # Vẽ Người tuyết dễ thương bên góc phải
            sx, sy = 700, self.H - 30
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), 40)       # Đáy
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy - 55), 30)  # Thân
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy - 100), 20) # Đầu
            
            pygame.draw.circle(self.screen, (0, 0, 0), (sx - 7, sy - 105), 3)    # Mắt trái
            pygame.draw.circle(self.screen, (0, 0, 0), (sx + 7, sy - 105), 3)    # Mắt phải
            pygame.draw.polygon(self.screen, (255, 140, 0), [(sx, sy - 100), (sx, sy - 95), (sx - 20, sy - 97)]) # Mũi cà rốt
            
            # Hiệu ứng Tuyết rơi
            for snow in self.snowflakes:
                pygame.draw.circle(self.screen, (255, 255, 255), (int(snow[0]), int(snow[1])), int(snow[2]))
                snow[1] += snow[3] # Tốc độ rơi
                snow[0] += math.sin(snow[1] * 0.02) * 0.8 # Lắc lư theo gió
                if snow[1] > self.H:
                    snow[1] = -10
                    snow[0] = random.randint(0, self.W)

    # ==========================================
    # MODAL WINDOWS (TUTORIAL & GAME OVER)
    # ==========================================
    def _draw_tutorial_modal(self):
        if not self.show_tutorial: return
        overlay = pygame.Surface((self.W, self.H))
        overlay.set_alpha(150); overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        modal_rect = pygame.Rect(0, 0, 520, 350)
        modal_rect.center = (self.W // 2, self.H // 2)
        pygame.draw.rect(self.screen, (255, 255, 255), modal_rect, border_radius=20)
        pygame.draw.rect(self.screen, self.P1_COLOR, modal_rect, width=4, border_radius=20)
        
        title = self.font_turn.render("HOW TO PLAY", True, (50, 50, 50))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, modal_rect.y + 20))
        
        instr = [
            "1. Connect 2 adjacent dots.",
            "2. Complete a box (4 sides) to get 1 point.",
            "3. Completing a box gives you an EXTRA TURN.",
            "4. Game ends when the board is full.",
            "5. The player with most points wins!"
        ]
        y_off = modal_rect.y + 90
        for line in instr:
            text_surf = self.font_text.render(line, True, (80, 80, 80))
            self.screen.blit(text_surf, (modal_rect.x + 40, y_off))
            y_off += 35
            
        self.btn_close_tutorial = self._draw_enhanced_button("Got it!", self.W // 2, modal_rect.bottom - 40, 200, 50, self.P2_COLOR, (255, 255, 255))

    def render_game_over(self):
        self.render_game() 
        if not self.show_tutorial:
            overlay = pygame.Surface((self.W, self.H))
            overlay.set_alpha(180) 
            overlay.fill((0, 0, 0) if self.current_theme_idx == 1 else (255, 255, 255))
            self.screen.blit(overlay, (0, 0))

            modal_rect = pygame.Rect(0, 0, 420, 400)
            modal_rect.center = (self.W // 2, self.H // 2)
            
            shadow_rect = modal_rect.copy()
            shadow_rect.y += 8
            s_color = (20, 20, 20) if self.current_theme_idx == 1 else (150, 150, 150)
            pygame.draw.rect(self.screen, s_color, shadow_rect, border_radius=25)
            
            m_bg = (40, 45, 50) if self.current_theme_idx == 1 else (255, 255, 255)
            pygame.draw.rect(self.screen, m_bg, modal_rect, border_radius=25)

            res = rules.get_winner(self.GameState)
            if res == 1:
                title, win_c, detail = "VICTORY!", self.P1_COLOR, "You won the game!"
            elif res == 2:
                title, win_c, detail = "DEFEAT!", self.P2_COLOR, "Bot won the game!"
            else:
                title, win_c, detail = "DRAW!", self.TEXT_MAIN, "It's a tie game!"
                
            pygame.draw.rect(self.screen, win_c, modal_rect, width=5, border_radius=25)

            t_surf = self.font_title.render(title, True, win_c)
            self.screen.blit(t_surf, (self.W // 2 - t_surf.get_width() // 2, modal_rect.y + 35))

            score = f"{self.GameState.score_player1} - {self.GameState.score_player2}"
            s_surf = self.font_title.render(score, True, self.TEXT_MAIN)
            self.screen.blit(s_surf, (self.W // 2 - s_surf.get_width() // 2, modal_rect.y + 105))

            d_surf = self.font_text.render(detail, True, self.TEXT_SCORE)
            self.screen.blit(d_surf, (self.W // 2 - d_surf.get_width() // 2, modal_rect.y + 175))

            btn_c = win_c if res != 0 else self.P1_COLOR
            self.btn_play_again = self._draw_enhanced_button("Play Again", self.W // 2, modal_rect.bottom - 120, 280, 55, btn_c, (255, 255, 255))
            self.btn_back_menu = self._draw_enhanced_button("Main Menu", self.W // 2, modal_rect.bottom - 50, 280, 55, (150, 150, 150), (255, 255, 255))

    # ==========================================
    # GAME RENDERERS
    # ==========================================
    def render_menu(self):
        self._draw_background()
        title = self.font_title.render("Dots & Boxes", True, self.TEXT_MAIN)
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 80))

        self.btn_play = self._draw_enhanced_button("Play Game", self.W // 2, 220, 300, 60, self.P1_COLOR, (255, 255, 255))
        self.btn_settings = self._draw_enhanced_button("Settings", self.W // 2, 300, 300, 60, (150, 150, 150), (255, 255, 255))
        self.btn_tutorial = self._draw_enhanced_button("Tutorial", self.W // 2, 380, 300, 60, self.P2_COLOR, (255, 255, 255))
        self.btn_quit = self._draw_enhanced_button("Quit", self.W // 2, 460, 300, 60, (100, 100, 100), (255, 255, 255))
        self._draw_tutorial_modal()

    def render_settings(self):
        self._draw_background()
        title = self.font_title.render("Settings", True, self.TEXT_MAIN)
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 60))
        
        sound_val = "ON" if self.sound_enabled else "OFF"
        self.btn_sound_l, self.btn_sound_r = self._draw_setting_selector("Sound", sound_val, 190)
        
        theme_val = self.themes[self.current_theme_idx]['name']
        self.btn_theme_l, self.btn_theme_r = self._draw_setting_selector("Theme", theme_val, 330)
        
        self.btn_back = self._draw_enhanced_button("Back", self.W // 2, 470, 300, 60, (150, 150, 150), (255, 255, 255))

    def _draw_avatar(self, x, y, color, is_bot, timer):
        off_y = math.sin(timer * 0.8) * 8 if timer > 0 else 0
        y += off_y
        pygame.draw.circle(self.screen, color, (x, y), 35)
        if not is_bot: 
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y - 5), 10, 3)
            pygame.draw.arc(self.screen, (255, 255, 255), (x - 18, y - 5, 36, 40), 0, math.pi, 3)
            pygame.draw.line(self.screen, (255, 255, 255), (x - 18, y + 15), (x + 18, y + 15), 3) 
        else: 
            pygame.draw.rect(self.screen, (255, 255, 255), (x - 15, y - 10, 30, 22), 3, border_radius=4)
            pygame.draw.circle(self.screen, (255, 255, 255), (x - 6, y - 2), 3) 
            pygame.draw.circle(self.screen, (255, 255, 255), (x + 6, y - 2), 3) 
            pygame.draw.line(self.screen, (255, 255, 255), (x, y - 10), (x, y - 18), 2) 
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y - 18), 3) 

    def _draw_header(self):
        turn_txt = "Turn: P1 (You)" if self.GameState.current_player == 1 else "Turn: P2 (Bot)"
        turn_c = self.P1_COLOR if self.GameState.current_player == 1 else self.P2_COLOR
        turn_s = self.font_turn.render(turn_txt, True, turn_c)
        self.screen.blit(turn_s, (self.W // 2 - turn_s.get_width() // 2, 40))

        # P1 Header
        p1_x, p1_y = 80, 50
        self._draw_avatar(p1_x, p1_y, self.P1_COLOR, False, self.p1_shake_timer)
        s1_x = p1_x + 55
        pygame.draw.circle(self.screen, (255, 255, 255), (s1_x, p1_y), 28)
        pygame.draw.circle(self.screen, (200, 200, 200), (s1_x, p1_y), 28, 1) 
        sc1 = self.font_score.render(str(self.GameState.score_player1), True, self.P1_COLOR)
        self.screen.blit(sc1, (s1_x - sc1.get_width()//2, p1_y - sc1.get_height()//2))
        if self.GameState.current_player == 1:
            pygame.draw.line(self.screen, self.P1_COLOR, (p1_x - 30, p1_y + 45), (p1_x + 30, p1_y + 45), 4)

        # P2 Header
        p2_x, p2_y = self.W - 80, 50
        self._draw_avatar(p2_x, p2_y, self.P2_COLOR, True, self.p2_shake_timer)
        s2_x = p2_x - 55
        pygame.draw.circle(self.screen, (255, 255, 255), (s2_x, p2_y), 28)
        pygame.draw.circle(self.screen, (200, 200, 200), (s2_x, p2_y), 28, 1)
        sc2 = self.font_score.render(str(self.GameState.score_player2), True, self.P2_COLOR)
        self.screen.blit(sc2, (s2_x - sc2.get_width()//2, p2_y - sc2.get_height()//2))
        if self.GameState.current_player == 2:
            pygame.draw.line(self.screen, self.P2_COLOR, (p2_x - 30, p2_y + 45), (p2_x + 30, p2_y + 45), 4)

    def _draw_lines_and_boxes(self):
        t = self.themes[self.current_theme_idx]
        if t['board_bg']:
            pad = 40
            bg_r = pygame.Rect(self.margin_left - pad, self.margin_up - pad, 
                               self.board_width + pad*2, self.board_height + pad*2)
            pygame.draw.rect(self.screen, t['board_bg'], bg_r, border_radius=20)

        for i in range(self.GameState.rows + 1):
            for j in range(self.GameState.cols):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + (j + 1) * self.edge, self.margin_up + i * self.edge)
                c = self.LINE_FILLED if self.GameState.h_edges[i][j] else self.LINE_EMPTY
                pygame.draw.line(self.screen, c, start, end, 12)

        for i in range(self.GameState.rows):
            for j in range(self.GameState.cols + 1):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + j * self.edge, self.margin_up + (i + 1) * self.edge)
                c = self.LINE_FILLED if self.GameState.v_edges[i][j] else self.LINE_EMPTY
                pygame.draw.line(self.screen, c, start, end, 12)

        for i in range(self.GameState.rows):
            for j in range(self.GameState.cols):
                owner = self.GameState.boxes[i][j]
                if owner != 0:
                    c = self.P1_COLOR if owner == 1 else self.P2_COLOR
                    r = (self.margin_left + j * self.edge + 6, self.margin_up + i * self.edge + 6, self.edge - 12, self.edge - 12)
                    pygame.draw.rect(self.screen, c, r, border_radius=8)

    def _draw_dots(self):
        cur_c = self.P1_COLOR if self.GameState.current_player == 1 else self.P2_COLOR
        for i in range(self.size):
            for j in range(self.size):
                cx, cy = self.margin_left + j * self.edge, self.margin_up + i * self.edge
                pygame.draw.circle(self.screen, self.DOT_OUTLINE, (cx, cy), 15)
                if self.selected_dot == (i, j):
                    pygame.draw.circle(self.screen, cur_c, (cx, cy), 18)
                elif self.selected_dot is not None:
                    r1, c1 = self.selected_dot
                    if (abs(i-r1)==1 and j==c1) or (abs(j-c1)==1 and i==r1):
                        empty = False
                        if i==r1 and not self.GameState.h_edges[i][min(c1,j)]: empty = True
                        elif j==c1 and not self.GameState.v_edges[min(r1,i)][j]: empty = True
                        if empty: pygame.draw.circle(self.screen, cur_c, (cx, cy), 17, 4) 
                pygame.draw.circle(self.screen, self.DOT_COLOR, (cx, cy), 11)

    def _draw_floating_texts(self):
        for f in self.floating_texts[:]:
            f['y'] -= 1.5; f['timer'] -= 1
            alpha = max(0, min(255, f['timer'] * 4)) 
            text_s = self.font_turn.render(f['text'], True, f['color'])
            text_s.set_alpha(alpha)
            self.screen.blit(text_s, (f['x'], f['y']))
            if f['timer'] <= 0: self.floating_texts.remove(f)

    def _draw_in_game_buttons(self):
        y = self.H - 50
        self.btn_in_game_help = self._draw_enhanced_button("?", 40, y, 50, 50, self.P1_COLOR, (255, 255, 255))
        self.btn_undo = self._draw_enhanced_button("Undo", 160, y, 140, 50, (255, 165, 0), (255, 255, 255))
        self.btn_in_game_settings = self._draw_enhanced_button("Settings", self.W // 2 + 20, y, 140, 50, (150, 150, 150), (255, 255, 255))
        self.btn_in_game_exit = self._draw_enhanced_button("Exit", self.W - 100, y, 140, 50, (100, 100, 100), (255, 255, 255))

    def render_game(self):
        self._draw_background(); self._draw_header(); self._draw_lines_and_boxes()
        self._draw_dots(); self._draw_floating_texts(); self._draw_in_game_buttons()
        self._draw_tutorial_modal()

    # ==========================================
    # INPUT HANDLING
    # ==========================================
    def handle_click(self, pos):
        if self.show_tutorial:
            if self.btn_close_tutorial.collidepoint(pos): self.play_sound('click'); self.show_tutorial = False
            return 

        if self.app_state == 'MENU':
            if self.btn_play.collidepoint(pos): 
                self.play_sound('click'); self.GameState = models.create_initial_state(self.GameState.rows, self.GameState.cols)
                self.selected_dot = None; self.floating_texts.clear(); self.history_undo_info.clear(); self.app_state = 'GAME'
            elif self.btn_tutorial.collidepoint(pos): self.play_sound('click'); self.show_tutorial = True
            elif self.btn_settings.collidepoint(pos): self.play_sound('click'); self.previous_state = 'MENU'; self.app_state = 'SETTINGS'
            elif self.btn_quit.collidepoint(pos): pygame.quit(); sys.exit()
                
        elif self.app_state == 'SETTINGS':
            if self.btn_back.collidepoint(pos): self.play_sound('click'); self.app_state = self.previous_state 
            elif self.btn_sound_l.collidepoint(pos) or self.btn_sound_r.collidepoint(pos):
                self.sound_enabled = not self.sound_enabled; self.play_sound('click')
            elif self.btn_theme_l.collidepoint(pos): self.play_sound('click'); self.current_theme_idx = (self.current_theme_idx - 1) % len(self.themes); self.apply_theme()
            elif self.btn_theme_r.collidepoint(pos): self.play_sound('click'); self.current_theme_idx = (self.current_theme_idx + 1) % len(self.themes); self.apply_theme()
                
        elif self.app_state == 'GAME_OVER':
            if self.btn_back_menu.collidepoint(pos): self.play_sound('click'); self.app_state = 'MENU'
            elif self.btn_play_again.collidepoint(pos):
                self.play_sound('click'); self.GameState = models.create_initial_state(self.GameState.rows, self.GameState.cols)
                self.selected_dot = None; self.floating_texts.clear(); self.history_undo_info.clear(); self.app_state = 'GAME'
                
        elif self.app_state == 'GAME':
            if self.btn_in_game_exit.collidepoint(pos): self.play_sound('click'); self.app_state = 'MENU'; return
            elif self.btn_in_game_settings.collidepoint(pos): self.play_sound('click'); self.previous_state = 'GAME'; self.app_state = 'SETTINGS'; return
            elif self.btn_in_game_help.collidepoint(pos): self.play_sound('click'); self.show_tutorial = True; return
            elif self.btn_undo.collidepoint(pos):
                self.play_sound('click')
                if len(self.GameState.last_move) > 0:
                    last_m = self.GameState.last_move[-1]; last_i = self.history_undo_info.pop()
                    rules.undo_move(self.GameState, last_m, last_i)
                    self.selected_dot = None; self.floating_texts.clear()
                return

            hit_dot = None
            for i in range(self.size):
                for j in range(self.size):
                    cx, cy = self.margin_left + j * self.edge, self.margin_up + i * self.edge
                    if math.hypot(pos[0] - cx, pos[1] - cy) <= 18: hit_dot = (i, j); break
            
            if hit_dot:
                self.play_sound('click')
                if self.selected_dot is None: self.selected_dot = hit_dot 
                elif self.selected_dot == hit_dot: self.selected_dot = None 
                else:
                    r1, c1 = self.selected_dot; r2, c2 = hit_dot
                    dr, dc = abs(r2 - r1), abs(c2 - c1)
                    if dr + dc == 1: 
                        if dr == 0: move = models.Move('H', r1, min(c1, c2))
                        else:       move = models.Move('V', min(r1, r2), c1)
                        if rules.is_valid_move(self.GameState, move):
                            player_b = self.GameState.current_player
                            info = rules.apply_move(self.GameState, move)
                            self.history_undo_info.append(info) 
                            if info['completed_boxes']:
                                self.play_sound('capture'); color = self.P1_COLOR if player_b == 1 else self.P2_COLOR
                                if player_b == 1: self.p1_shake_timer = 20 
                                else: self.p2_shake_timer = 20
                                for box_r, box_c in info['completed_boxes']:
                                    fx = self.margin_left + box_c * self.edge + self.edge // 2 - 15
                                    fy = self.margin_up + box_r * self.edge + self.edge // 2 - 15
                                    self.floating_texts.append({'x': fx, 'y': fy, 'text': '+1', 'color': color, 'timer': 60})
                        self.selected_dot = None 
                    else: self.selected_dot = hit_dot 

    def run_game(self):
        while True:
            if self.p1_shake_timer > 0: self.p1_shake_timer -= 1
            if self.p2_shake_timer > 0: self.p2_shake_timer -= 1
            if self.app_state == 'GAME' and self.GameState.moves_remaining == 0:
                self.play_sound('win'); self.app_state = 'GAME_OVER'
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: self.handle_click(event.pos)

            if self.app_state == 'MENU': self.render_menu()
            elif self.app_state == 'SETTINGS': self.render_settings()
            elif self.app_state == 'GAME': self.render_game()
            elif self.app_state == 'GAME_OVER': self.render_game_over()
            pygame.display.flip(); self.clock.tick(60)