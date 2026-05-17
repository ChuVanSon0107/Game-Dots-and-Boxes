import pygame
import sys
import math
import os
import random
import threading
import copy
import rules
import models
import ai

class UI:
    def __init__(self, GameState):
        pygame.init()
        pygame.mixer.init() 
        
        # --- WINDOW & DISPLAY SETUP ---
        self.W, self.H = 1000, 800
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

        # --- AI BOT STATE ---
        self.ai_player = 2              # AI là Player 2
        self.ai_delay_ms = 300          # Delay trước khi AI đi (ms) – để người chơi thấy
        self.ai_thinking = False        # AI đang "suy nghĩ"?
        self.ai_think_start = 0         # Thời điểm bắt đầu thinking
        self.ai_move_pending = None     # Nước đi AI đã tính xong, chờ apply
        self.ai_thread = None           # Background thread cho AI computation
        
        # THUẬT TOÁN AUTO-SCALING & CENTERING BÀN CỜ
        header_space = 145 
        footer_space = 90  
        
        avail_w = self.W - 120  
        avail_h = self.H - header_space - footer_space
        
        edge_w = avail_w // self.GameState.cols
        edge_h = avail_h // self.GameState.rows
        self.edge = min(65, edge_w, edge_h) # Đảm bảo ô vuông không to quá 65px
        
        self.board_width = self.GameState.cols * self.edge 
        self.board_height = self.GameState.rows * self.edge
        
        # Tự động căn giữa 2 bên lề
        self.margin_left = (self.W - self.board_width) // 2 
        self.margin_up = header_space + (avail_h - self.board_height) // 2
        
        # Co giãn bán kính hạt chấm và độ dày nét vẽ tương ứng mật độ (Đã tăng nhỉnh hơn)
        self.line_thick = max(5, int(self.edge * 0.18))  # Tăng độ dày đường kẻ
        self.dot_r_out = max(7, int(self.edge * 0.22))   # Tăng viền ngoài của chấm
        self.dot_r_in = max(4, int(self.edge * 0.14))    # Tăng lõi trắng của chấm
        self.click_r = max(16, int(self.edge * 0.50))    # Tăng vùng nhận diện click cho dễ bấm
        
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
        self.anim_tick = 0

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
    # BACKGROUND ENGINE - UPGRADED
    # ==========================================

    def _draw_background(self):
        t = self.themes[self.current_theme_idx]
        theme_name = t['name']
        tick = getattr(self, 'anim_tick', 0)  # fallback nếu chưa thêm anim_tick

        # ============================================================
        # THEME 1: CLASSIC WOOD – Buổi sáng đồng quê, cây cỏ hoa lá
        # ============================================================
        if theme_name == 'Classic Wood':
            # -- Sky gradient: xanh nhạt trên, vàng cam phía chân trời --
            sky_top    = (160, 210, 245)
            sky_mid    = (255, 220, 160)
            sky_ground = (140, 185, 100)
            horizon_y  = int(self.H * 0.62)

            for y in range(horizon_y):
                ratio = y / horizon_y
                r = int(sky_top[0] + (sky_mid[0] - sky_top[0]) * ratio)
                g = int(sky_top[1] + (sky_mid[1] - sky_top[1]) * ratio)
                b = int(sky_top[2] + (sky_mid[2] - sky_top[2]) * ratio)
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

            # -- Đất / bãi cỏ --
            for y in range(horizon_y, self.H):
                ratio = (y - horizon_y) / (self.H - horizon_y)
                r = int(sky_ground[0] * (1 - ratio * 0.3))
                g = int(sky_ground[1] * (1 - ratio * 0.2))
                b = int(sky_ground[2] * (1 - ratio * 0.4))
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

            # -- Mặt trời ấm áp --
            sun_x, sun_y = 90, 75
            for ring in range(5, 0, -1):
                alpha_surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                pygame.draw.circle(alpha_surf, (255, 230, 100, 18 * ring), (sun_x, sun_y), 30 + ring * 12)
                self.screen.blit(alpha_surf, (0, 0))
            pygame.draw.circle(self.screen, (255, 240, 80), (sun_x, sun_y), 32)
            pygame.draw.circle(self.screen, (255, 255, 200), (sun_x, sun_y), 22)

            # Tia sáng mặt trời xoay theo tick
            for i in range(8):
                angle = math.radians(i * 45 + tick * 0.3)
                x1 = sun_x + int(math.cos(angle) * 38)
                y1 = sun_y + int(math.sin(angle) * 38)
                x2 = sun_x + int(math.cos(angle) * 55)
                y2 = sun_y + int(math.sin(angle) * 55)
                pygame.draw.line(self.screen, (255, 220, 80), (x1, y1), (x2, y2), 3)

            # -- Mây trắng bồng bềnh (di chuyển chậm) --
            cloud_data = [(120, 80, 1.0), (350, 55, 0.7), (580, 95, 0.9), (710, 60, 0.6)]
            for cx, cy, sc in cloud_data:
                # offset di chuyển từng mây với tốc độ khác nhau
                ox = int((tick * 0.18 * sc) % (self.W + 200)) - 100
                for dx, dy, r in [(0, 0, 26), (28, -10, 22), (-28, -8, 20), (52, 2, 18), (-50, 4, 16)]:
                    pygame.draw.circle(self.screen, (255, 255, 255), (cx + ox + dx, cy + dy), int(r * sc))

            # -- Dãy cây xa xăm (silhouette) --
            tree_xs = list(range(0, self.W + 40, 28))
            for tx in tree_xs:
                h_tree = 45 + int(math.sin(tx * 0.07) * 15)
                ty = horizon_y - h_tree
                col = (60 + int(math.sin(tx * 0.05) * 15), 130 + int(math.sin(tx * 0.04) * 20), 60)
                pygame.draw.polygon(self.screen, col,
                    [(tx, horizon_y), (tx + 14, horizon_y), (tx + 7, ty)])

            # -- Hàng cỏ cao phía trước --
            for gx in range(0, self.W, 9):
                gy = self.H - random.randint(20, 45) if not hasattr(self, '_grass_h') else self.H - self._grass_cache[gx // 9 % len(self._grass_cache)]
                sway = math.sin(tick * 0.04 + gx * 0.15) * 4
                col = (50 + int(math.sin(gx * 0.1) * 20), 140 + int(math.sin(gx * 0.08) * 30), 50)
                pygame.draw.line(self.screen, col,
                    (gx, self.H), (gx + int(sway), self.H - 30), 2)

            # -- Hoa đồng nội phía trước --
            flower_spots = [80, 180, 310, 430, 560, 680, 760]
            for fx in flower_spots:
                fy = self.H - 32
                stem_sway = math.sin(tick * 0.05 + fx * 0.1) * 3
                # thân
                pygame.draw.line(self.screen, (60, 130, 50),
                    (fx, fy), (fx + int(stem_sway), fy - 22), 3)
                # cánh hoa
                petal_colors = [(255, 120, 170), (255, 200, 80), (180, 130, 255)]
                pc = petal_colors[fx % len(petal_colors)]
                head_x = fx + int(stem_sway)
                head_y = fy - 22
                for angle in range(0, 360, 60):
                    px = head_x + int(math.cos(math.radians(angle + tick * 0.5)) * 7)
                    py = head_y + int(math.sin(math.radians(angle + tick * 0.5)) * 7)
                    pygame.draw.circle(self.screen, pc, (px, py), 5)
                pygame.draw.circle(self.screen, (255, 240, 60), (head_x, head_y), 5)

            # -- Lá rơi (cải tiến: hình ellipse xoay, màu sắc) --
            leaf_colors = [(180, 220, 90), (220, 190, 70), (240, 150, 60), (160, 200, 80)]
            for i, leaf in enumerate(self.leaves):
                lc = leaf_colors[i % len(leaf_colors)]
                lx, ly = int(leaf[0]), int(leaf[1])
                angle = (tick * 2 + i * 17) % 360
                # Vẽ hình lá đơn giản bằng ellipse
                leaf_surf = pygame.Surface((16, 10), pygame.SRCALPHA)
                pygame.draw.ellipse(leaf_surf, (*lc, 200), (0, 0, 16, 10))
                rotated = pygame.transform.rotate(leaf_surf, angle)
                self.screen.blit(rotated, (lx - 8, ly - 5))
                leaf[1] += 0.7
                leaf[0] += math.sin(leaf[1] * 0.04 + i) * 1.2
                if leaf[1] > self.H:
                    leaf[1] = -10
                    leaf[0] = random.randint(0, self.W)

        # ============================================================
        # THEME 2: DARK NIGHT – Đêm huyền bí, thiên hà, trăng sáng
        # ============================================================
        elif theme_name == 'Dark Night':
            # -- Sky gradient: đen tuyệt vời xuống tím sâu --
            sky_top = (5, 5, 18)
            sky_bot = (25, 12, 45)
            for y in range(self.H):
                ratio = y / self.H
                r = int(sky_top[0] + (sky_bot[0] - sky_top[0]) * ratio)
                g = int(sky_top[1] + (sky_bot[1] - sky_top[1]) * ratio)
                b = int(sky_top[2] + (sky_bot[2] - sky_top[2]) * ratio)
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

            # -- Dải Ngân Hà mờ ảo (nhiều chấm nhỏ mờ tạo thành vệt) --
            if not hasattr(self, '_milky_way'):
                self._milky_way = [
                    (random.randint(0, self.W),
                     random.randint(0, int(self.H * 0.55)),
                     random.randint(1, 2),
                     random.randint(60, 150))
                    for _ in range(180)
                ]
            for mx, my, mr, ma in self._milky_way:
                mw_surf = pygame.Surface((mr*2+2, mr*2+2), pygame.SRCALPHA)
                pygame.draw.circle(mw_surf, (200, 180, 255, ma), (mr+1, mr+1), mr)
                self.screen.blit(mw_surf, (mx - mr, my - mr))

            # -- Sao nhấp nháy (twinkle) --
            for i, (sx, sy, sr) in enumerate(self.stars):
                # Nhấp nháy: alpha dao động theo sin
                twinkle = int(180 + math.sin(tick * 0.07 + i * 0.9) * 75)
                star_surf = pygame.Surface((sr*4, sr*4), pygame.SRCALPHA)
                # Glow mờ xung quanh
                pygame.draw.circle(star_surf, (255, 255, 200, twinkle // 4), (sr*2, sr*2), sr*2)
                # Lõi sao
                pygame.draw.circle(star_surf, (255, 255, 230, twinkle), (sr*2, sr*2), sr)
                self.screen.blit(star_surf, (sx - sr*2, sy - sr*2))

            # -- Vài ngôi sao bắn qua (shooting star) --
            if not hasattr(self, '_shooting_stars'):
                self._shooting_stars = [
                    [random.randint(0, self.W), random.randint(0, int(self.H * 0.4)),
                     random.uniform(4, 8), random.randint(0, 300)]
                    for _ in range(3)
                ]
            for ss in self._shooting_stars:
                ss[3] -= 1
                if ss[3] <= 0:
                    ss[0] = random.randint(100, self.W)
                    ss[1] = random.randint(10, int(self.H * 0.3))
                    ss[3] = random.randint(180, 420)
                trail_len = 45
                tx_end = ss[0] - int(ss[2] * 5)
                ty_end = ss[1] + int(ss[2] * 3)
                for tl in range(trail_len, 0, -5):
                    alpha = int(255 * tl / trail_len)
                    prog = tl / trail_len
                    tx = int(ss[0] - ss[2] * prog * 5)
                    ty = int(ss[1] + ss[2] * prog * 3)
                    ss_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(ss_surf, (255, 255, 255, alpha), (2, 2), 2)
                    self.screen.blit(ss_surf, (tx, ty))

            # -- Mặt Trăng rằm sáng rực --
            moon_x, moon_y = self.W - 110, 100
            moon_r = 50
            # Ánh hào quang phát sáng (nhiều vòng mờ dần)
            for glow in range(6, 0, -1):
                g_surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                pygame.draw.circle(g_surf, (255, 255, 200, 12 * glow), (moon_x, moon_y), moon_r + glow * 14)
                self.screen.blit(g_surf, (0, 0))
            # Thân trăng
            pygame.draw.circle(self.screen, (255, 248, 200), (moon_x, moon_y), moon_r)
            pygame.draw.circle(self.screen, (255, 255, 230), (moon_x, moon_y), moon_r - 8)
            # Kết cấu bề mặt (crater nhỏ)
            craters = [(-14, -10, 7), (12, 8, 5), (-5, 18, 4), (18, -18, 6), (-20, 12, 4)]
            for cx, cy, cr in craters:
                pygame.draw.circle(self.screen, (235, 228, 180), (moon_x + cx, moon_y + cy), cr)
                pygame.draw.circle(self.screen, (200, 195, 150), (moon_x + cx, moon_y + cy), cr, 1)

            # -- Đường chân trời: Cityscape tối --
            building_data = [
                (0, 100, 30), (35, 140, 45), (85, 90, 35), (125, 120, 40),
                (170, 80, 28), (200, 110, 55), (260, 95, 38), (300, 130, 42),
                (345, 85, 30), (380, 115, 50), (435, 100, 35), (470, 75, 28),
                (500, 125, 45), (550, 90, 38), (595, 140, 55), (655, 80, 30),
                (690, 110, 42), (735, 95, 35), (770, 130, 50),
            ]
            ground_y = self.H - 55
            for bx, bh, bw in building_data:
                # Tòa nhà tối
                pygame.draw.rect(self.screen, (18, 20, 35),
                    (bx, ground_y - bh, bw, bh))
                # Cửa sổ phát sáng vàng/trắng ngẫu nhiên
                for wy in range(ground_y - bh + 6, ground_y - 8, 14):
                    for wx in range(bx + 4, bx + bw - 4, 10):
                        seed = (bx * 7 + wx * 13 + wy * 3) % 100
                        if seed > 45:
                            wc = (255, 220, 100) if seed > 70 else (180, 210, 255)
                            pygame.draw.rect(self.screen, wc, (wx, wy, 6, 8))
            # Mặt đất
            pygame.draw.rect(self.screen, (12, 14, 25), (0, ground_y, self.W, self.H - ground_y))
            # Phản chiếu trên mặt đất
            reflect_surf = pygame.Surface((self.W, 18), pygame.SRCALPHA)
            pygame.draw.rect(reflect_surf, (255, 248, 200, 25), (self.W - 200, 0, 200, 18))
            self.screen.blit(reflect_surf, (0, ground_y))

        # ============================================================
        # THEME 3: SNOW WHITE – Mùa đông, núi tuyết, người tuyết, bão tuyết
        # ============================================================
        elif theme_name == 'Snow White':
            # -- Sky gradient: xanh nhạt trên, trắng xám đục phía dưới (trời흐림) --
            sky_top = (170, 200, 230)
            sky_bot = (220, 235, 248)
            for y in range(self.H):
                ratio = y / self.H
                r = int(sky_top[0] + (sky_bot[0] - sky_top[0]) * ratio)
                g = int(sky_top[1] + (sky_bot[1] - sky_top[1]) * ratio)
                b = int(sky_top[2] + (sky_bot[2] - sky_top[2]) * ratio)
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

            # -- Đám mây nặng nề mang tuyết --
            cloud_data = [(90, 45, 1.2), (280, 30, 1.0), (480, 55, 0.9), (680, 35, 1.1)]
            for cx, cy, sc in cloud_data:
                drift = int((tick * 0.1 * sc) % (self.W + 200)) - 100
                base_col = (200, 210, 225)
                for dx, dy, r in [(0, 0, 38), (40, -14, 32), (-40, -12, 28), (70, 4, 24), (-68, 6, 22), (20, -30, 26)]:
                    pygame.draw.circle(self.screen, base_col, (cx + drift + dx, cy + dy), int(r * sc))

            # -- Dãy núi tuyết nhiều lớp (xa -> gần, sáng dần) --
            mountain_layers = [
                # (list_of_peaks, color)
                ([(0,self.H),(150,self.H-220),(320,self.H-180),(490,self.H-260),(650,self.H-200),(800,self.H-170),(800,self.H)], (170,185,210)),
                ([(0,self.H),(100,self.H-160),(260,self.H-200),(420,self.H-155),(580,self.H-210),(740,self.H-160),(800,self.H)], (190,205,225)),
                ([(0,self.H),(-50,self.H-130),(120,self.H-170),(300,self.H-120),(480,self.H-175),(660,self.H-140),(850,self.H-110),(800,self.H)], (210,222,238)),
            ]
            for pts, col in mountain_layers:
                pygame.draw.polygon(self.screen, col, pts)
                # Mũ tuyết trên đỉnh núi
                snow_col = (240, 248, 255)
                for i in range(1, len(pts) - 2):
                    px, py = pts[i]
                    if py < self.H - 100:
                        snow_pts = [(px - 25, py + 35), (px, py - 10), (px + 25, py + 35)]
                        pygame.draw.polygon(self.screen, snow_col, snow_pts)

            # -- Mặt đất tuyết trắng gợn sóng --
            ground_y = self.H - 70
            snow_ground = []
            for gx in range(0, self.W + 10, 10):
                gy = ground_y + int(math.sin(gx * 0.03 + tick * 0.01) * 6)
                snow_ground.append((gx, gy))
            snow_ground += [(self.W, self.H), (0, self.H)]
            pygame.draw.polygon(self.screen, (240, 248, 255), snow_ground)
            # Viền tuyết nhẹ (bóng đổ mờ)
            pygame.draw.polygon(self.screen, (210, 225, 245), snow_ground, 3)

            # -- Cây thông phủ tuyết --
            pine_xs = [60, 190, 590, 730]
            for px_tree in pine_xs:
                py_base = ground_y
                trunk_col = (100, 70, 50)
                # Thân
                pygame.draw.rect(self.screen, trunk_col, (px_tree - 5, py_base - 18, 10, 20))
                # 3 lớp cành (từ dưới lên)
                for layer, (lw, lh, ly_off) in enumerate([(54, 28, -18), (44, 24, -42), (30, 20, -62)]):
                    pine_col = (50 + layer * 15, 100 + layer * 10, 60 + layer * 10)
                    pts = [(px_tree - lw//2, py_base + ly_off + lh),
                           (px_tree, py_base + ly_off),
                           (px_tree + lw//2, py_base + ly_off + lh)]
                    pygame.draw.polygon(self.screen, pine_col, pts)
                    # Tuyết trên cành
                    snow_pts = [(px_tree - lw//2 + 4, py_base + ly_off + lh - 4),
                                (px_tree, py_base + ly_off + 4),
                                (px_tree + lw//2 - 4, py_base + ly_off + lh - 4)]
                    snow_surf = pygame.Surface((lw + 10, lh + 10), pygame.SRCALPHA)
                    pygame.draw.polygon(self.screen, (240, 248, 255), snow_pts)

            # -- Người tuyết dễ thương (cải tiến) --
            sx, sy = 680, ground_y - 5
            # Bóng
            pygame.draw.ellipse(self.screen, (200, 215, 235), (sx - 42, sy - 8, 84, 16))
            # Thân dưới
            pygame.draw.circle(self.screen, (245, 252, 255), (sx, sy - 38), 38)
            pygame.draw.circle(self.screen, (230, 240, 255), (sx, sy - 38), 38, 2)
            # Thân giữa
            pygame.draw.circle(self.screen, (248, 254, 255), (sx, sy - 88), 28)
            pygame.draw.circle(self.screen, (220, 235, 250), (sx, sy - 88), 28, 2)
            # Đầu
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy - 128), 22)
            pygame.draw.circle(self.screen, (215, 230, 248), (sx, sy - 128), 22, 2)
            # Mắt
            pygame.draw.circle(self.screen, (30, 30, 30), (sx - 8, sy - 134), 4)
            pygame.draw.circle(self.screen, (30, 30, 30), (sx + 8, sy - 134), 4)
            pygame.draw.circle(self.screen, (255, 255, 255), (sx - 7, sy - 135), 2)
            pygame.draw.circle(self.screen, (255, 255, 255), (sx + 9, sy - 135), 2)
            # Mũi cà rốt
            pygame.draw.polygon(self.screen, (255, 120, 20),
                [(sx, sy - 128), (sx - 3, sy - 125), (sx - 20, sy - 127), (sx - 3, sy - 130)])
            # Miệng cười (chấm)
            for mi in range(-3, 4, 2):
                pygame.draw.circle(self.screen, (40, 40, 40), (sx + mi * 3, sy - 118 + abs(mi)), 2)
            # Nút cúc áo
            for btn_y in [sy - 82, sy - 70, sy - 58]:
                pygame.draw.circle(self.screen, (80, 80, 100), (sx, btn_y), 3)
            # Tay (cành cây)
            pygame.draw.line(self.screen, (100, 70, 50), (sx - 28, sy - 90), (sx - 58, sy - 75), 4)
            pygame.draw.line(self.screen, (100, 70, 50), (sx - 58, sy - 75), (sx - 70, sy - 62), 3)
            pygame.draw.line(self.screen, (100, 70, 50), (sx - 58, sy - 75), (sx - 68, sy - 85), 3)
            pygame.draw.line(self.screen, (100, 70, 50), (sx + 28, sy - 90), (sx + 58, sy - 75), 4)
            pygame.draw.line(self.screen, (100, 70, 50), (sx + 58, sy - 75), (sx + 70, sy - 62), 3)
            pygame.draw.line(self.screen, (100, 70, 50), (sx + 58, sy - 75), (sx + 68, sy - 85), 3)
            # Mũ
            pygame.draw.rect(self.screen, (30, 30, 30), (sx - 28, sy - 152, 56, 8), border_radius=3)
            pygame.draw.rect(self.screen, (30, 30, 30), (sx - 18, sy - 174, 36, 26), border_radius=4)
            # Khăn quàng
            scarf_col = (220, 50, 60)
            scarf_surf = pygame.Surface((60, 12), pygame.SRCALPHA)
            pygame.draw.rect(scarf_surf, (*scarf_col, 220), (0, 0, 60, 12), border_radius=4)
            self.screen.blit(scarf_surf, (sx - 30, sy - 112))
            pygame.draw.rect(self.screen, scarf_col, (sx - 22, sy - 108, 10, 18), border_radius=3)

            # -- Bông tuyết rơi (cải tiến: hình bông 6 cánh) --
            for i, snow in enumerate(self.snowflakes):
                sx2, sy2 = int(snow[0]), int(snow[1])
                sr2 = int(snow[2])
                # Bông tuyết nhỏ vẽ bằng đường thẳng chéo
                sn_surf = pygame.Surface((sr2*6+2, sr2*6+2), pygame.SRCALPHA)
                scx, scy = sr2*3+1, sr2*3+1
                alpha_snow = 220
                for angle in range(0, 180, 60):
                    rad = math.radians(angle)
                    ex = int(math.cos(rad) * sr2 * 3)
                    ey = int(math.sin(rad) * sr2 * 3)
                    pygame.draw.line(sn_surf, (255, 255, 255, alpha_snow),
                        (scx - ex, scy - ey), (scx + ex, scy + ey), max(1, sr2 - 1))
                self.screen.blit(sn_surf, (sx2 - sr2*3, sy2 - sr2*3))

                snow[1] += snow[3] * 0.8
                snow[0] += math.sin(snow[1] * 0.02 + i) * 1.2
                if snow[1] > self.H:
                    snow[1] = -10
                    snow[0] = random.randint(0, self.W)

        else:
            # Fallback gradient đơn giản
            top_c, bot_c = t['bg_top'], t['bg_bot']
            for y in range(self.H):
                r = top_c[0] + (bot_c[0] - top_c[0]) * y // self.H
                g = top_c[1] + (bot_c[1] - top_c[1]) * y // self.H
                b = top_c[2] + (bot_c[2] - top_c[2]) * y // self.H
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

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
        if self.ai_thinking:
            turn_txt = "Bot is thinking..."
            turn_c = self.P2_COLOR
            # Hiệu ứng nhấp nháy cho text "thinking"
            alpha = int(180 + math.sin(self.anim_tick * 0.15) * 75)
            turn_s = self.font_turn.render(turn_txt, True, turn_c)
            turn_s.set_alpha(alpha)
        else:
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
            pad = int(self.edge * 0.4) # Bóng nền co giãn theo cạnh
            bg_r = pygame.Rect(self.margin_left - pad, self.margin_up - pad, 
                               self.board_width + pad*2, self.board_height + pad*2)
            pygame.draw.rect(self.screen, t['board_bg'], bg_r, border_radius=20)

        for i in range(self.GameState.rows + 1):
            for j in range(self.GameState.cols):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + (j + 1) * self.edge, self.margin_up + i * self.edge)
                c = self.LINE_FILLED if self.GameState.h_edges[i][j] else self.LINE_EMPTY
                pygame.draw.line(self.screen, c, start, end, self.line_thick)

        for i in range(self.GameState.rows):
            for j in range(self.GameState.cols + 1):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + j * self.edge, self.margin_up + (i + 1) * self.edge)
                c = self.LINE_FILLED if self.GameState.v_edges[i][j] else self.LINE_EMPTY
                pygame.draw.line(self.screen, c, start, end, self.line_thick)

        for i in range(self.GameState.rows):
            for j in range(self.GameState.cols):
                owner = self.GameState.boxes[i][j]
                if owner != 0:
                    c = self.P1_COLOR if owner == 1 else self.P2_COLOR
                    pad_box = max(2, int(self.edge * 0.15))
                    rect_size = self.edge - pad_box * 2
                    r = (self.margin_left + j * self.edge + pad_box, self.margin_up + i * self.edge + pad_box, rect_size, rect_size)
                    pygame.draw.rect(self.screen, c, r, border_radius=max(2, int(self.edge * 0.1)))

    def _draw_dots(self):
        cur_c = self.P1_COLOR if self.GameState.current_player == 1 else self.P2_COLOR
        for i in range(self.GameState.rows + 1):
            for j in range(self.GameState.cols + 1):
                cx, cy = self.margin_left + j * self.edge, self.margin_up + i * self.edge
                pygame.draw.circle(self.screen, self.DOT_OUTLINE, (cx, cy), self.dot_r_out)
                if self.selected_dot == (i, j):
                    pygame.draw.circle(self.screen, cur_c, (cx, cy), self.dot_r_out + 3)
                elif self.selected_dot is not None:
                    r1, c1 = self.selected_dot
                    if (abs(i-r1)==1 and j==c1) or (abs(j-c1)==1 and i==r1):
                        empty = False
                        if i==r1 and not self.GameState.h_edges[i][min(c1,j)]: empty = True
                        elif j==c1 and not self.GameState.v_edges[min(r1,i)][j]: empty = True
                        if empty: pygame.draw.circle(self.screen, cur_c, (cx, cy), self.dot_r_out + 2, 3) 
                pygame.draw.circle(self.screen, self.DOT_COLOR, (cx, cy), self.dot_r_in)

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
            # Nếu AI đang thinking → không cho click gì cả
            if self.ai_thinking or self.GameState.current_player == self.ai_player:
                # Chỉ cho phép exit, settings, help
                if self.btn_in_game_exit.collidepoint(pos): 
                    self.play_sound('click'); self.ai_thinking = False; self.ai_move_pending = None; self.app_state = 'MENU'
                elif self.btn_in_game_settings.collidepoint(pos): 
                    self.play_sound('click'); self.previous_state = 'GAME'; self.app_state = 'SETTINGS'
                elif self.btn_in_game_help.collidepoint(pos): 
                    self.play_sound('click'); self.show_tutorial = True
                return

            if self.btn_in_game_exit.collidepoint(pos): self.play_sound('click'); self.app_state = 'MENU'; return
            elif self.btn_in_game_settings.collidepoint(pos): self.play_sound('click'); self.previous_state = 'GAME'; self.app_state = 'SETTINGS'; return
            elif self.btn_in_game_help.collidepoint(pos): self.play_sound('click'); self.show_tutorial = True; return
            elif self.btn_undo.collidepoint(pos):
                self.play_sound('click')
                # Undo: hoàn tác cho đến khi quay về lượt Player 1
                # (undo cả nước AI lẫn nước người chơi trước đó)
                while len(self.history_undo_info) > 0:
                    last_m = self.GameState.last_move[-1]
                    last_i = self.history_undo_info.pop()
                    was_player = last_i['previous_player']
                    rules.undo_move(self.GameState, last_m, last_i)
                    # Dừng khi đã undo xong 1 nước của Player 1 (người chơi)
                    if was_player != self.ai_player:
                        break
                self.selected_dot = None; self.floating_texts.clear()
                self.ai_thinking = False; self.ai_move_pending = None
                return

            hit_dot = None
            for i in range(self.GameState.rows + 1):
                for j in range(self.GameState.cols + 1):
                    cx, cy = self.margin_left + j * self.edge, self.margin_up + i * self.edge
                    # Sử dụng bán kính click động
                    if math.hypot(pos[0] - cx, pos[1] - cy) <= self.click_r: 
                        hit_dot = (i, j)
                        break
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
                            self._apply_move_with_effects(move)
                        self.selected_dot = None 
                    else: self.selected_dot = hit_dot 

    def _apply_move_with_effects(self, move):
        """
        Apply một nước đi và kích hoạt hiệu ứng (âm thanh, animation).
        Dùng chung cho cả Player và AI.
        """
        player_b = self.GameState.current_player
        info = rules.apply_move(self.GameState, move)
        self.history_undo_info.append(info)
        if info['completed_boxes']:
            self.play_sound('capture')
            color = self.P1_COLOR if player_b == 1 else self.P2_COLOR
            if player_b == 1:
                self.p1_shake_timer = 20
            else:
                self.p2_shake_timer = 20
            for box_r, box_c in info['completed_boxes']:
                fx = self.margin_left + box_c * self.edge + self.edge // 2 - 15
                fy = self.margin_up + box_r * self.edge + self.edge // 2 - 15
                self.floating_texts.append({'x': fx, 'y': fy, 'text': '+1', 'color': color, 'timer': 60})

    def _ai_compute_worker(self, state_copy, ai_player):
        """
        Worker function chạy trên background thread.
        Tính nước đi tốt nhất trên bản sao state (thread-safe).
        """
        try:
            best_move = ai.get_best_move(state_copy, ai_player=ai_player)
            self.ai_move_pending = best_move
        except Exception as e:
            print(f"AI error: {e}")
            # Fallback: chọn nước đi đầu tiên
            legal = ai.get_legal_moves(state_copy)
            self.ai_move_pending = legal[0] if legal else None

    def _handle_ai_turn(self):
        """
        Xử lý lượt AI trong game loop (non-blocking).
        Chạy AI trên background thread để UI vẫn responsive.
        """
        if self.app_state != 'GAME':
            return
        if self.GameState.moves_remaining == 0:
            return
        if self.GameState.current_player != self.ai_player:
            # Reset AI state khi không phải lượt AI
            self.ai_thinking = False
            self.ai_move_pending = None
            self.ai_thread = None
            return

        now = pygame.time.get_ticks()

        # Bước 1: Bắt đầu thinking – khởi chạy background thread
        if not self.ai_thinking:
            self.ai_thinking = True
            self.ai_think_start = now
            self.ai_move_pending = None

            # Tạo deep copy của state để thread-safe
            state_copy = copy.deepcopy(self.GameState)
            self.ai_thread = threading.Thread(
                target=self._ai_compute_worker,
                args=(state_copy, self.ai_player),
                daemon=True
            )
            self.ai_thread.start()
            return

        # Bước 2: Chờ thread tính xong
        if self.ai_thread is not None and self.ai_thread.is_alive():
            # Thread vẫn đang chạy → UI vẫn render bình thường
            return

        # Bước 3: Thread đã xong → chờ delay để người chơi thấy
        if self.ai_move_pending is not None:
            elapsed = now - self.ai_think_start
            # Đảm bảo ít nhất ai_delay_ms trước khi apply
            if elapsed < self.ai_delay_ms:
                return

            # Thực hiện nước đi
            self.play_sound('click')
            self._apply_move_with_effects(self.ai_move_pending)

            # Reset AI state
            self.ai_thinking = False
            self.ai_move_pending = None
            self.ai_thread = None
        else:
            # Trường hợp lỗi: không tìm được nước đi
            self.ai_thinking = False
            self.ai_thread = None

    def run_game(self):
        while True:
            self.anim_tick += 1
            if self.p1_shake_timer > 0: self.p1_shake_timer -= 1
            if self.p2_shake_timer > 0: self.p2_shake_timer -= 1
            if self.app_state == 'GAME' and self.GameState.moves_remaining == 0:
                self.play_sound('win'); self.app_state = 'GAME_OVER'
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: self.handle_click(event.pos)

            # --- AI turn handling ---
            self._handle_ai_turn()

            if self.app_state == 'MENU': self.render_menu()
            elif self.app_state == 'SETTINGS': self.render_settings()
            elif self.app_state == 'GAME': self.render_game()
            elif self.app_state == 'GAME_OVER': self.render_game_over()
            pygame.display.flip(); self.clock.tick(60)