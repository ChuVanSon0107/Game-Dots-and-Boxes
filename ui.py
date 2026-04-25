import pygame
import sys
import math
import os
import rules
import models

class UI:
    def __init__(self, GameState):
        pygame.init()
        pygame.mixer.init() 
        
        # --- THIẾT LẬP CỬA SỔ & MÀU SẮC ---
        self.W, self.H = 800, 600
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Dots and Boxes - AI Project")
        self.clock = pygame.time.Clock()
        
        # Bảng màu
        self.DOT_COLOR = (255, 255, 255)      
        self.DOT_OUTLINE = (200, 190, 180)    
        self.P1_COLOR = (45, 212, 235)        # Xanh Cyan (Người)
        self.P2_COLOR = (255, 65, 84)         # Đỏ (Máy)
        self.LINE_EMPTY = (220, 210, 200)     
        self.LINE_FILLED = (100, 100, 100)    
        self.SELECT_COLOR = (255, 215, 0)     

        self.font_title = pygame.font.SysFont("Verdana", 45, bold=True)
        self.font_turn = pygame.font.SysFont("Verdana", 32, bold=True) 
        self.font_score = pygame.font.SysFont("Verdana", 28, bold=True) 
        self.font_menu = pygame.font.SysFont("Verdana", 30)
        self.font_text = pygame.font.SysFont("Verdana", 20)

        # --- TẢI TÀI NGUYÊN ---
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

        # --- TRẠNG THÁI GAME & DỮ LIỆU ---
        self.app_state = 'MENU'
        self.previous_state = 'MENU' 
        self.show_tutorial = False 
        
        self.GameState = GameState
        
        self.size = GameState.rows + 1 
        self.edge = 65 
        self.board_width = (self.size - 1) * self.edge 
        self.board_height = (self.size - 1) * self.edge
        self.margin_left = (self.W - self.board_width) // 2 
        self.margin_up = 160 
        
        self.selected_dot = None 
        self.floating_texts = [] 
        self.history_undo_info = []

        # Timers cho Animation khuôn mặt
        self.p1_shake_timer = 0
        self.p2_shake_timer = 0

    def play_sound(self, sound_name):
        if self.sound_enabled and sound_name in self.sounds:
            self.sounds[sound_name].play()

    # ==========================================
    # HỆ THỐNG VẼ GIAO DIỆN CHUNG
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
        pygame.draw.rect(self.screen, (160, 150, 140), shadow_rect, border_radius=radius)
        pygame.draw.rect(self.screen, current_color, display_rect, border_radius=radius)
        
        btn_surf = self.font_menu.render(text, True, text_color)
        text_rect = btn_surf.get_rect(center=display_rect.center)
        self.screen.blit(btn_surf, text_rect)
        
        return base_rect

    def _draw_background(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
            overlay = pygame.Surface((self.W, self.H))
            overlay.set_alpha(120)
            overlay.fill((255, 255, 255))
            self.screen.blit(overlay, (0, 0))
        else:
            top_color, bottom_color = (220, 240, 245), (250, 240, 230)
            for y in range(self.H):
                r = top_color[0] + (bottom_color[0] - top_color[0]) * y // self.H
                g = top_color[1] + (bottom_color[1] - top_color[1]) * y // self.H
                b = top_color[2] + (bottom_color[2] - top_color[2]) * y // self.H
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

    # ==========================================
    # CỬA SỔ HƯỚNG DẪN (TUTORIAL MODAL)
    # ==========================================
    def _draw_tutorial_modal(self):
        if not self.show_tutorial: return
        
        overlay = pygame.Surface((self.W, self.H))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        modal_rect = pygame.Rect(0, 0, 520, 350)
        modal_rect.center = (self.W // 2, self.H // 2)
        pygame.draw.rect(self.screen, (255, 255, 255), modal_rect, border_radius=20)
        pygame.draw.rect(self.screen, self.P1_COLOR, modal_rect, width=4, border_radius=20)
        
        title = self.font_turn.render("HOW TO PLAY", True, (50, 50, 50))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, modal_rect.y + 20))
        
        instructions = [
            "1. Click to connect 2 adjacent dots.",
            "2. The player who completes a box (4 sides)",
            "   gets 1 point and an EXTRA TURN.",
            "3. The game ends when the board is full.",
            "4. The player with the most points wins!"
        ]
        
        y_offset = modal_rect.y + 90
        for line in instructions:
            text_surf = self.font_text.render(line, True, (80, 80, 80))
            self.screen.blit(text_surf, (modal_rect.x + 40, y_offset))
            y_offset += 35
            
        self.btn_close_tutorial = self._draw_enhanced_button("Got it!", self.W // 2, modal_rect.bottom - 40, 200, 50, self.P2_COLOR, (255, 255, 255))

    # ==========================================
    # PHẦN 1: MENU
    # ==========================================
    def render_menu(self):
        self._draw_background()
        title = self.font_title.render("Dots & Boxes", True, (70, 70, 70))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 80))

        self.btn_play = self._draw_enhanced_button("Play Game", self.W // 2, 220, 300, 60, self.P1_COLOR, (255, 255, 255))
        self.btn_settings = self._draw_enhanced_button("Settings", self.W // 2, 300, 300, 60, (150, 150, 150), (255, 255, 255))
        self.btn_tutorial = self._draw_enhanced_button("Tutorial", self.W // 2, 380, 300, 60, self.P2_COLOR, (255, 255, 255))
        self.btn_quit = self._draw_enhanced_button("Quit", self.W // 2, 460, 300, 60, (100, 100, 100), (255, 255, 255))
        
        self._draw_tutorial_modal()

    def render_settings(self):
        self._draw_background()
        title = self.font_title.render("Settings", True, (70, 70, 70))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 80))
        
        sound_text = "Sound: ON" if self.sound_enabled else "Sound: OFF"
        sound_color = self.P1_COLOR if self.sound_enabled else self.LINE_FILLED
        
        self.btn_toggle_sound = self._draw_enhanced_button(sound_text, self.W // 2, 250, 300, 60, sound_color, (255, 255, 255))
        self.btn_back = self._draw_enhanced_button("Back", self.W // 2, 400, 300, 60, (150, 150, 150), (255, 255, 255))

    # ==========================================
    # PHẦN 2: HEADER IN-GAME (VẼ AVATAR)
    # ==========================================
    def _draw_avatar(self, x, y, color, is_bot, timer):
        offset_y = 0
        if timer > 0:
            offset_y = math.sin(timer * 0.8) * 8 
            
        y += offset_y
        
        pygame.draw.circle(self.screen, color, (x, y), 35)
        
        if not is_bot:
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y - 5), 10, 3)
            pygame.draw.arc(self.screen, (255, 255, 255), (x - 18, y - 5, 36, 40), 0, math.pi, 3)
            pygame.draw.line(self.screen, (255, 255, 255), (x - 18, y + 15), (x + 18, y + 15), 3) 
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), (x - 15, y - 10, 30, 22), 3, border_radius=4)
            pygame.draw.circle(self.screen, (255, 255, 255), (x - 6, y - 2), 3) 
            pygame.draw.circle(self.screen, (255, 255, 255), (x + 6, y - 2), 3) 
            pygame.draw.line(self.screen, (255, 255, 255), (x - 6, y + 6), (x + 6, y + 6), 2) 
            pygame.draw.line(self.screen, (255, 255, 255), (x, y - 10), (x, y - 18), 2) 
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y - 18), 3) 

    def _draw_header(self):
        turn_text = "Turn: P1 (You)" if self.GameState.current_player == 1 else "Turn: P2 (Bot)"
        turn_color = self.P1_COLOR if self.GameState.current_player == 1 else self.P2_COLOR
        turn_surf = self.font_turn.render(turn_text, True, turn_color)
        self.screen.blit(turn_surf, (self.W // 2 - turn_surf.get_width() // 2, 40))

        # === PLAYER 1 ===
        p1_x, p1_y = 80, 50
        self._draw_avatar(p1_x, p1_y, self.P1_COLOR, False, self.p1_shake_timer)
        
        score1_x = p1_x + 50
        pygame.draw.circle(self.screen, (255, 255, 255), (score1_x, p1_y), 28)
        pygame.draw.circle(self.screen, (200, 200, 200), (score1_x, p1_y), 28, 1) 
        score1_surf = self.font_score.render(str(self.GameState.score_player1), True, self.P1_COLOR)
        self.screen.blit(score1_surf, (score1_x - score1_surf.get_width()//2, p1_y - score1_surf.get_height()//2))
        
        if self.GameState.current_player == 1:
            pygame.draw.line(self.screen, self.P1_COLOR, (p1_x - 30, p1_y + 45), (p1_x + 30, p1_y + 45), 4)

        # === PLAYER 2 ===
        p2_x, p2_y = self.W - 80, 50
        self._draw_avatar(p2_x, p2_y, self.P2_COLOR, True, self.p2_shake_timer)
        
        score2_x = p2_x - 50
        pygame.draw.circle(self.screen, (255, 255, 255), (score2_x, p2_y), 28)
        pygame.draw.circle(self.screen, (200, 200, 200), (score2_x, p2_y), 28, 1)
        score2_surf = self.font_score.render(str(self.GameState.score_player2), True, self.P2_COLOR)
        self.screen.blit(score2_surf, (score2_x - score2_surf.get_width()//2, p2_y - score2_surf.get_height()//2))

        if self.GameState.current_player == 2:
            pygame.draw.line(self.screen, self.P2_COLOR, (p2_x - 30, p2_y + 45), (p2_x + 30, p2_y + 45), 4)

    # ==========================================
    # CÁC HÀM VẼ IN-GAME CÒN LẠI
    # ==========================================
    def _draw_lines_and_boxes(self):
        for i in range(self.GameState.rows + 1):
            for j in range(self.GameState.cols):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + (j + 1) * self.edge, self.margin_up + i * self.edge)
                color = self.LINE_FILLED if self.GameState.h_edges[i][j] else self.LINE_EMPTY
                pygame.draw.line(self.screen, color, start, end, 12)

        for i in range(self.GameState.rows):
            for j in range(self.GameState.cols + 1):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + j * self.edge, self.margin_up + (i + 1) * self.edge)
                color = self.LINE_FILLED if self.GameState.v_edges[i][j] else self.LINE_EMPTY
                pygame.draw.line(self.screen, color, start, end, 12)

        for i in range(self.GameState.rows):
            for j in range(self.GameState.cols):
                owner = self.GameState.boxes[i][j]
                if owner != 0:
                    color = self.P1_COLOR if owner == 1 else self.P2_COLOR
                    rect = (self.margin_left + j * self.edge + 6, self.margin_up + i * self.edge + 6, self.edge - 12, self.edge - 12)
                    pygame.draw.rect(self.screen, color, rect, border_radius=8)

    def _draw_dots(self):
        current_color = self.P1_COLOR if self.GameState.current_player == 1 else self.P2_COLOR
        for i in range(self.size):
            for j in range(self.size):
                cx, cy = self.margin_left + j * self.edge, self.margin_up + i * self.edge
                pygame.draw.circle(self.screen, self.DOT_OUTLINE, (cx, cy), 14)
                if self.selected_dot == (i, j):
                    pygame.draw.circle(self.screen, current_color, (cx, cy), 18)
                elif self.selected_dot is not None:
                    r1, c1 = self.selected_dot
                    if (abs(i - r1) == 1 and j == c1) or (abs(j - c1) == 1 and i == r1):
                        empty = False
                        if i == r1 and not self.GameState.h_edges[i][min(c1, j)]: empty = True
                        elif j == c1 and not self.GameState.v_edges[min(r1, i)][j]: empty = True
                        if empty: pygame.draw.circle(self.screen, current_color, (cx, cy), 16, 4) 
                pygame.draw.circle(self.screen, self.DOT_COLOR, (cx, cy), 10)

    def _draw_floating_texts(self):
        for f in self.floating_texts[:]:
            f['y'] -= 1.5 
            f['timer'] -= 1
            alpha = max(0, min(255, f['timer'] * 4)) 
            text_surf = self.font_turn.render(f['text'], True, f['color'])
            text_surf.set_alpha(alpha)
            self.screen.blit(text_surf, (f['x'], f['y']))
            if f['timer'] <= 0: self.floating_texts.remove(f)

    def _draw_in_game_buttons(self):
        button_y = self.H - 50
        self.btn_in_game_help = self._draw_enhanced_button("?", 40, button_y, 50, 50, self.P1_COLOR, (255, 255, 255))
        self.btn_undo = self._draw_enhanced_button("Undo", 160, button_y, 140, 50, (255, 165, 0), (255, 255, 255))
        self.btn_in_game_settings = self._draw_enhanced_button("Settings", self.W // 2 + 20, button_y, 140, 50, (150, 150, 150), (255, 255, 255))
        self.btn_in_game_exit = self._draw_enhanced_button("Exit", self.W - 100, button_y, 140, 50, (100, 100, 100), (255, 255, 255))

    def render_game(self):
        self._draw_background() 
        self._draw_header()
        self._draw_lines_and_boxes()
        self._draw_dots()
        self._draw_floating_texts() 
        self._draw_in_game_buttons()
        self._draw_tutorial_modal() 

    def render_game_over(self):
        self.render_game() 
        if not self.show_tutorial:
            overlay = pygame.Surface((self.W, self.H))
            overlay.set_alpha(180) 
            overlay.fill((255, 255, 255))
            self.screen.blit(overlay, (0, 0))

            res = rules.get_winner(self.GameState)
            if res == 1: text, color = "PLAYER 1 WINS!", self.P1_COLOR
            elif res == 2: text, color = "PLAYER 2 WINS!", self.P2_COLOR
            else: text, color = "IT'S A TIE!", (100, 100, 100)
                
            win_surf = self.font_title.render(text, True, color)
            self.screen.blit(win_surf, (self.W // 2 - win_surf.get_width() // 2, self.H // 2 - 50))
            self.btn_back_menu = self._draw_enhanced_button("Back to Menu", self.W // 2, self.H // 2 + 50, 300, 60, (150, 150, 150), (255, 255, 255))

    # ==========================================
    # PHẦN 3: XỬ LÝ SỰ KIỆN CLICK 
    # ==========================================
    def handle_click(self, pos):
        if self.show_tutorial:
            if self.btn_close_tutorial.collidepoint(pos):
                self.play_sound('click')
                self.show_tutorial = False
            return 

        if self.app_state == 'MENU':
            if self.btn_play.collidepoint(pos): 
                self.play_sound('click')
                self.GameState = models.create_initial_state(self.GameState.rows, self.GameState.cols)
                self.selected_dot = None     
                self.floating_texts.clear()  
                self.history_undo_info.clear() 
                self.app_state = 'GAME'
                
            elif self.btn_tutorial.collidepoint(pos):
                self.play_sound('click')
                self.show_tutorial = True
            elif self.btn_settings.collidepoint(pos): 
                self.play_sound('click')
                self.previous_state = 'MENU' 
                self.app_state = 'SETTINGS'
            elif self.btn_quit.collidepoint(pos):
                pygame.quit()
                sys.exit()
                
        elif self.app_state == 'SETTINGS':
            if self.btn_back.collidepoint(pos): 
                self.play_sound('click')
                self.app_state = self.previous_state 
            elif self.btn_toggle_sound.collidepoint(pos):
                self.sound_enabled = not self.sound_enabled 
                self.play_sound('click')
                
        elif self.app_state == 'GAME_OVER':
            if self.btn_back_menu.collidepoint(pos):
                self.play_sound('click')
                self.app_state = 'MENU'
                
        elif self.app_state == 'GAME':
            x, y = pos
            
            if self.btn_in_game_exit.collidepoint(pos):
                self.play_sound('click')
                self.app_state = 'MENU'
                return
            elif self.btn_in_game_settings.collidepoint(pos):
                self.play_sound('click')
                self.previous_state = 'GAME' 
                self.app_state = 'SETTINGS'
                return
            elif self.btn_in_game_help.collidepoint(pos):
                self.play_sound('click')
                self.show_tutorial = True
                return
            elif self.btn_undo.collidepoint(pos):
                self.play_sound('click')
                if len(self.GameState.last_move) > 0:
                    last_m = self.GameState.last_move[-1]
                    last_info = self.history_undo_info.pop()
                    rules.undo_move(self.GameState, last_m, last_info)
                    self.selected_dot = None
                    self.floating_texts.clear()
                return

            hit_dot = None
            for i in range(self.size):
                for j in range(self.size):
                    cx, cy = self.margin_left + j * self.edge, self.margin_up + i * self.edge
                    if math.hypot(x - cx, y - cy) <= 18:
                        hit_dot = (i, j)
                        break
            
            if hit_dot:
                self.play_sound('click')
                if self.selected_dot is None: self.selected_dot = hit_dot 
                elif self.selected_dot == hit_dot: self.selected_dot = None 
                else:
                    r1, c1 = self.selected_dot
                    r2, c2 = hit_dot
                    dr, dc = abs(r2 - r1), abs(c2 - c1)
                    
                    if dr + dc == 1: 
                        if dr == 0: move = models.Move('H', r1, min(c1, c2))
                        else:       move = models.Move('V', min(r1, r2), c1)
                            
                        if rules.is_valid_move(self.GameState, move):
                            player_before = self.GameState.current_player
                            
                            undo_info = rules.apply_move(self.GameState, move)
                            self.history_undo_info.append(undo_info) 
                            
                            if undo_info['completed_boxes']:
                                self.play_sound('capture')
                                color = self.P1_COLOR if player_before == 1 else self.P2_COLOR
                                
                                if player_before == 1:
                                    self.p1_shake_timer = 20 
                                else:
                                    self.p2_shake_timer = 20
                                
                                for box_r, box_c in undo_info['completed_boxes']:
                                    fx = self.margin_left + box_c * self.edge + self.edge // 2 - 15
                                    fy = self.margin_up + box_r * self.edge + self.edge // 2 - 15
                                    self.floating_texts.append({'x': fx, 'y': fy, 'text': '+1', 'color': color, 'timer': 60})
                                    
                        self.selected_dot = None 
                    else:
                        self.selected_dot = hit_dot 

    # ==========================================
    # PHẦN 4: VÒNG LẶP CHÍNH
    # ==========================================
    def run_game(self):
        while True:
            if self.p1_shake_timer > 0: self.p1_shake_timer -= 1
            if self.p2_shake_timer > 0: self.p2_shake_timer -= 1

            if self.app_state == 'GAME' and self.GameState.moves_remaining == 0:
                self.play_sound('win') 
                self.app_state = 'GAME_OVER'
                
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            if self.app_state == 'MENU': self.render_menu()
            elif self.app_state == 'SETTINGS': self.render_settings()
            elif self.app_state == 'GAME': self.render_game()
            elif self.app_state == 'GAME_OVER': self.render_game_over()

            pygame.display.flip()
            self.clock.tick(60)