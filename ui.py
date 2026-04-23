import pygame
import sys
import math
import os
import rules
import models

class UI:
    def __init__(self, GameState):
        pygame.init()
        pygame.mixer.init() # Khởi tạo hệ thống âm thanh
        
        # --- THIẾT LẬP CỬA SỔ & MÀU SẮC ---
        self.W, self.H = 800, 600
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Dots and Boxes - AI Project")
        self.clock = pygame.time.Clock()
        
        # Bảng màu
        self.DOT_COLOR = (255, 255, 255)      
        self.DOT_OUTLINE = (200, 190, 180)    
        self.P1_COLOR = (242, 92, 104)        
        self.P2_COLOR = (66, 191, 219)        
        self.LINE_EMPTY = (220, 210, 200)     
        self.LINE_FILLED = (100, 100, 100)    
        self.SELECT_COLOR = (255, 215, 0)     

        self.font_title = pygame.font.SysFont("Verdana", 45, bold=True)
        self.font_turn = pygame.font.SysFont("Verdana", 32, bold=True) 
        self.font_score = pygame.font.SysFont("Verdana", 24, bold=True)
        self.font_menu = pygame.font.SysFont("Verdana", 30)

        # --- TẢI TÀI NGUYÊN (ẢNH & ÂM THANH) ---
        self.bg_image = None
        
        # KHẮC PHỤC: Lấy đường dẫn tuyệt đối (Absolute Path) của thư mục chứa code
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        try:
            bg_path = os.path.join(base_dir, "assets", "images", "wood_bg.jpg")
            img = pygame.image.load(bg_path)
            self.bg_image = pygame.transform.scale(img, (self.W, self.H))
        except Exception:
            pass # Ẩn thông báo đi cho terminal gọn gàng khi bạn chưa thêm ảnh

        self.sound_enabled = True
        self.sounds = {}
        try:
            self.sounds['click'] = pygame.mixer.Sound(os.path.join(base_dir, "assets", "sounds", "click.wav"))
            self.sounds['capture'] = pygame.mixer.Sound(os.path.join(base_dir, "assets", "sounds", "capture.wav"))
            self.sounds['win'] = pygame.mixer.Sound(os.path.join(base_dir, "assets", "sounds", "win.wav"))
            print("--- ĐÃ TẢI ÂM THANH THÀNH CÔNG! ---")
        except Exception as e:
            print(f"!!! LỖI TẢI ÂM THANH: {e} !!!")
            print("=> GỢI Ý: Nếu lỗi trên ghi là 'Unrecognized audio format', nghĩa là file WAV của bạn là WAV GIẢ (do bạn tự đổi đuôi). Hãy xóa file đó đi, lên trang Convertio.co tải file MP3 lên để convert sang WAV chuẩn nhé!")

        # --- TRẠNG THÁI GAME & DỮ LIỆU ---
        self.app_state = 'MENU'
        self.GameState = GameState
        
        self.size = GameState.rows + 1 
        self.edge = 65 
        self.board_width = (self.size - 1) * self.edge 
        self.board_height = (self.size - 1) * self.edge
        self.margin_left = (self.W - self.board_width) // 2 
        self.margin_up = 130 
        
        self.selected_dot = None 
        # Danh sách lưu các hiệu ứng "+1" đang bay
        self.floating_texts = [] 

    def play_sound(self, sound_name):
        if self.sound_enabled and sound_name in self.sounds:
            self.sounds[sound_name].play()

    # ==========================================
    # HÀM HỖ TRỢ VẼ NỀN 
    # ==========================================
    def _draw_background(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
            # Vẽ một lớp sương mù trắng mỏng (alpha=100) đè lên ảnh gỗ để bàn cờ nổi bật hơn
            overlay = pygame.Surface((self.W, self.H))
            overlay.set_alpha(100)
            overlay.fill((255, 255, 255))
            self.screen.blit(overlay, (0, 0))
        else:
            top_color, bottom_color = (253, 246, 237), (225, 212, 198)
            for y in range(self.H):
                r = top_color[0] + (bottom_color[0] - top_color[0]) * y // self.H
                g = top_color[1] + (bottom_color[1] - top_color[1]) * y // self.H
                b = top_color[2] + (bottom_color[2] - top_color[2]) * y // self.H
                pygame.draw.line(self.screen, (r, g, b), (0, y), (self.W, y))

    # ==========================================
    # PHẦN 1: GIAO DIỆN MENU & SETTINGS
    # ==========================================
    def draw_button(self, text, y_pos, bg_color, text_color):
        btn_surf = self.font_menu.render(text, True, text_color)
        btn_rect = pygame.Rect(0, 0, 300, 60)
        btn_rect.center = (self.W // 2, y_pos)
        pygame.draw.rect(self.screen, bg_color, btn_rect, border_radius=15)
        text_rect = btn_surf.get_rect(center=btn_rect.center)
        self.screen.blit(btn_surf, text_rect)
        return btn_rect

    def render_menu(self):
        self._draw_background()
        title = self.font_title.render("Dots & Boxes", True, (70, 70, 70))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 80))

        self.btn_play = self.draw_button("Play Game", 250, self.P2_COLOR, (255, 255, 255))
        self.btn_settings = self.draw_button("Settings", 330, (150, 150, 150), (255, 255, 255))
        self.btn_quit = self.draw_button("Quit", 410, self.P1_COLOR, (255, 255, 255))

    def render_settings(self):
        self._draw_background()
        title = self.font_title.render("Settings", True, (70, 70, 70))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 80))
        
        # Nút bật/tắt âm thanh
        sound_text = "Âm thanh: BẬT" if self.sound_enabled else "Âm thanh: TẮT"
        sound_color = self.P2_COLOR if self.sound_enabled else self.LINE_FILLED
        self.btn_toggle_sound = self.draw_button(sound_text, 250, sound_color, (255, 255, 255))
        
        self.btn_back = self.draw_button("Back to Menu", 400, (150, 150, 150), (255, 255, 255))

    # ==========================================
    # PHẦN 2: GIAO DIỆN TRONG GAME
    # ==========================================
    # ... (Giữ nguyên _draw_header, _draw_lines_and_boxes, _draw_dots như bản cũ) ...
    def _draw_header(self):
        turn_text = "Lượt: Người 1" if self.GameState.current_player == 1 else "Lượt: Người 2"
        turn_color = self.P1_COLOR if self.GameState.current_player == 1 else self.P2_COLOR
        turn_surf = self.font_turn.render(turn_text, True, turn_color)
        self.screen.blit(turn_surf, (self.W // 2 - turn_surf.get_width() // 2, 25))

        p1_text = self.font_score.render(f"Người 1: {self.GameState.score_player1}", True, (80, 80, 80))
        self.screen.blit(p1_text, (65, 30))
        pygame.draw.circle(self.screen, self.P1_COLOR, (40, 45), 12) 

        p2_text = self.font_score.render(f"Người 2: {self.GameState.score_player2}", True, (80, 80, 80))
        p2_x = self.W - p2_text.get_width() - 30
        self.screen.blit(p2_text, (p2_x, 30))
        pygame.draw.circle(self.screen, self.P2_COLOR, (p2_x - 25, 45), 12)

    def _draw_lines_and_boxes(self):
        def draw_thick_line(color, start_pos, end_pos):
            pygame.draw.line(self.screen, color, start_pos, end_pos, 12)

        for i in range(self.GameState.rows + 1):
            for j in range(self.GameState.cols):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + (j + 1) * self.edge, self.margin_up + i * self.edge)
                color = self.LINE_FILLED if self.GameState.h_edges[i][j] else self.LINE_EMPTY
                draw_thick_line(color, start, end)

        for i in range(self.GameState.rows):
            for j in range(self.GameState.cols + 1):
                start = (self.margin_left + j * self.edge, self.margin_up + i * self.edge)
                end = (self.margin_left + j * self.edge, self.margin_up + (i + 1) * self.edge)
                color = self.LINE_FILLED if self.GameState.v_edges[i][j] else self.LINE_EMPTY
                draw_thick_line(color, start, end)

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
                    is_neighbor = (abs(i - r1) == 1 and j == c1) or (abs(j - c1) == 1 and i == r1)
                    if is_neighbor:
                        line_empty = False
                        if i == r1: 
                            if not self.GameState.h_edges[i][min(c1, j)]: line_empty = True
                        else:       
                            if not self.GameState.v_edges[min(r1, i)][j]: line_empty = True
                        if line_empty:
                            pygame.draw.circle(self.screen, current_color, (cx, cy), 16, 4) 
                pygame.draw.circle(self.screen, self.DOT_COLOR, (cx, cy), 10)

    def _draw_floating_texts(self):
        """Vẽ và cập nhật tọa độ cho hiệu ứng +1 bay lên"""
        for f in self.floating_texts[:]:
            f['y'] -= 1.5 # Tốc độ bay lên
            f['timer'] -= 1
            
            # Làm chữ mờ dần (Alpha fading)
            alpha = max(0, min(255, f['timer'] * 4)) 
            text_surf = self.font_turn.render(f['text'], True, f['color'])
            text_surf.set_alpha(alpha)
            self.screen.blit(text_surf, (f['x'], f['y']))
            
            if f['timer'] <= 0:
                self.floating_texts.remove(f)

    def render_game(self):
        self._draw_background() 
        self._draw_header()
        self._draw_lines_and_boxes()
        self._draw_dots()
        self._draw_floating_texts() # Vẽ hiệu ứng sau cùng để nằm trên cùng

    def render_game_over(self):
        self.render_game() 
        overlay = pygame.Surface((self.W, self.H))
        overlay.set_alpha(180) 
        overlay.fill((255, 255, 255))
        self.screen.blit(overlay, (0, 0))

        res = rules.get_winner(self.GameState)
        if res == 1: text, color = "NGƯỜI 1 THẮNG!", self.P1_COLOR
        elif res == 2: text, color = "NGƯỜI 2 THẮNG!", self.P2_COLOR
        else: text, color = "HÒA NHAU!", (100, 100, 100)
            
        win_surf = self.font_title.render(text, True, color)
        self.screen.blit(win_surf, (self.W // 2 - win_surf.get_width() // 2, self.H // 2 - 50))
        self.btn_back_menu = self.draw_button("Back to Menu", self.H // 2 + 50, (150, 150, 150), (255, 255, 255))

    # ==========================================
    # PHẦN 3: XỬ LÝ SỰ KIỆN CLICK 
    # ==========================================
    
    def handle_click(self, pos):
        if self.app_state == 'MENU':
            if self.btn_play.collidepoint(pos): 
                self.play_sound('click')
                
                # --- THÊM 4 DÒNG NÀY ĐỂ RESET GAME ---
                # Khởi tạo lại trạng thái game mới tinh dựa trên số hàng/cột cũ
                self.GameState = models.create_initial_state(self.GameState.rows, self.GameState.cols)
                self.selected_dot = None     # Xóa điểm đang chọn dở (nếu có)
                self.floating_texts.clear()  # Xóa các số +1 đang bay lơ lửng của ván trước
                # --------------------------------------
                
                self.app_state = 'GAME'
                
            elif self.btn_settings.collidepoint(pos): 
                self.play_sound('click')
                self.app_state = 'SETTINGS'
            elif self.btn_quit.collidepoint(pos):
                pygame.quit()
                sys.exit()
                
        elif self.app_state == 'SETTINGS':
            if self.btn_back.collidepoint(pos): 
                self.play_sound('click')
                self.app_state = 'MENU'
            elif self.btn_toggle_sound.collidepoint(pos):
                self.sound_enabled = not self.sound_enabled # Đảo trạng thái âm thanh
                self.play_sound('click')
                
        elif self.app_state == 'GAME_OVER':
            if self.btn_back_menu.collidepoint(pos):
                self.play_sound('click')
                self.app_state = 'MENU'
                
        elif self.app_state == 'GAME':
            x, y = pos
            hit_dot = None
            
            for i in range(self.size):
                for j in range(self.size):
                    cx = self.margin_left + j * self.edge
                    cy = self.margin_up + i * self.edge
                    if math.hypot(x - cx, y - cy) <= 18:
                        hit_dot = (i, j)
                        break
            
            if hit_dot:
                self.play_sound('click')
                if self.selected_dot is None:
                    self.selected_dot = hit_dot 
                elif self.selected_dot == hit_dot:
                    self.selected_dot = None 
                else:
                    r1, c1 = self.selected_dot
                    r2, c2 = hit_dot
                    dr, dc = abs(r2 - r1), abs(c2 - c1)
                    
                    if dr + dc == 1: 
                        if dr == 0: move = models.Move('H', r1, min(c1, c2))
                        else:       move = models.Move('V', min(r1, r2), c1)
                            
                        if rules.is_valid_move(self.GameState, move):
                            player_before_move = self.GameState.current_player
                            # Nhận undo_info từ apply_move để biết có ăn được ô nào không
                            undo_info = rules.apply_move(self.GameState, move)
                            
                            # Kiểm tra xem có ăn được ô nào không
                            if undo_info['completed_boxes']:
                                self.play_sound('capture')
                                color = self.P1_COLOR if player_before_move == 1 else self.P2_COLOR
                                
                                # Tạo hiệu ứng +1 cho từng ô ăn được
                                for box_r, box_c in undo_info['completed_boxes']:
                                    # Tính tọa độ giữa ô vuông
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
            if self.app_state == 'GAME' and self.GameState.moves_remaining == 0:
                self.play_sound('win') # Phát nhạc thắng
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