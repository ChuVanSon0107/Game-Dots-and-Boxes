import pygame
import sys
import rules
import models
# Tuấn Khanh 21/4/2026
# Các hàm thuộc lớp UI:
# __init__: Khởi tạo giao diện, thiết lập các thuộc tính cần thiết từ GameState
# render_board: Vẽ lại bàn cờ dựa trên trạng thái hiện tại
# display_winner: Hiển thị người chiến thắng khi trò chơi kết thúc
# handle_move: Xử lý sự kiện click chuột, xác định đường nào được chọn và cập nhật trạng thái
# run_game: Vòng lặp chính của trò chơi, xử lý sự kiện và cập nhật giao diện liên tục

class UI:
    def __init__(self, GameState):
        self.W, self.H = 800, 600 # Screen setup
        self.WHT, self.BLU, self.RED, self.BLK = (255, 255, 255), (0, 200, 255), (255, 0, 0), (0, 0, 0) # Colors

        pygame.init() # Init pygame
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Dots and Boxes")

        # Clock and self.font
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)

        # Các thuộc tính cần khởi tạo:
        # self.size, self.edge, board_size, self.boxes, edges_count self.margin_left, self.margin_up,
        # current_player, score_player1, score_player2, moves_remaining, last_move (chưa có)
        self.GameState = GameState
        self.size = GameState.rows + 1 # self.size x self.size grid of dots, which creates a (self.size-1) x (self.size-1) grid of self.boxes
        self.edge = 56 # Spacing between grid points
        self.board_size = (self.size - 1) * self.edge # Total board width/height
        self.h_edges = GameState.h_edges
        self.v_edges = GameState.v_edges
        self.boxes = GameState.boxes
        self.edges_count = GameState.edges_count
        self.margin_left = (self.W - self.board_size) // 2 # Left margin for centering the board
        self.margin_up = 200 # Top margin for scoreboard space
        self.current_player = 1 # 1 for player 1, 2 for player 2
        self.score_player1 = GameState.score_player1
        self.score_player2 = GameState.score_player2
        self.moves_remaining = GameState.moves_remaining

    def render_board(self):

        self.screen.fill((255,255,255)) # Clear screen
        
        # Draw scoreboard at the top
        player1_text = self.font.render(f"Player 1 (Red): {self.score_player1}", True, self.RED)
        player2_text = self.font.render(f"Player 2 (Cyan): {self.score_player2}", True, self.BLU)
        self.screen.blit(player1_text, (50, 30))
        self.screen.blit(player2_text, (self.W - 250, 30))

        # Draw horizontal lines
        for i in range(self.size):
            for j in range(self.size - 1):
                if self.h_edges[i][j]: # If line is filled
                    color = self.RED if self.h_edges[i][j] == 1 else self.BLU # Color based on current player
                    pygame.draw.line(self.screen, color, (self.margin_left + j * self.edge, self.margin_up + i * self.edge), (self.margin_left + (j + 1) * self.edge, self.margin_up + i * self.edge), 5)
                else:
                    pygame.draw.line(self.screen, self.WHT, (self.margin_left + j * self.edge, self.margin_up + i * self.edge), (self.margin_left + (j + 1) * self.edge, self.margin_up + i * self.edge), 5) # Clear line
        # Draw vertical lines
        for i in range(self.size - 1):
            for j in range(self.size):
                if self.v_edges[i][j]: # If line is filled
                    color = self.RED if self.v_edges[i][j] == 1 else self.BLU # Color based on current player
                    pygame.draw.line(self.screen, color, (self.margin_left + j * self.edge, self.margin_up + i * self.edge), (self.margin_left + j * self.edge, self.margin_up + (i + 1) * self.edge), 5)
                else:
                    pygame.draw.line(self.screen, self.WHT, (self.margin_left + j * self.edge, self.margin_up + i * self.edge), (self.margin_left + j * self.edge, self.margin_up + (i + 1) * self.edge), 5) # Clear line
        # Draw self.boxes
        for i in range(self.size - 1):
            for j in range(self.size - 1):
                if self.boxes[i][j]: # If box is completed
                    color = self.RED if self.boxes[i][j] == 1 else self.BLU # Color based on current player
                    pygame.draw.rect(self.screen, color, (self.margin_left + j * self.edge + 5, self.margin_up + i * self.edge + 5, self.edge - 10, self.edge - 10)) # Fill box
                else:
                    pygame.draw.rect(self.screen, self.WHT, (self.margin_left + j * self.edge + 5, self.margin_up + i * self.edge + 5, self.edge - 10, self.edge - 10)) # Clear box
        # Draw dots
        for i in range(self.size):
            for j in range(self.size):
                pygame.draw.circle(self.screen, self.BLK, (self.margin_left + j * self.edge, self.margin_up + i * self.edge), 5)

    def display_winner(self):
        res = rules.get_winner(self.GameState)
        if res == 1:
            winner_text = self.font.render("Player 1 wins!", True, self.RED)
        elif res == 2:
            winner_text = self.font.render("Player 2 wins!", True, self.BLU)
        else:
            winner_text = self.font.render("It's a tie!", True, self.BLK)
        self.screen.blit(winner_text, (self.W // 2 - winner_text.get_width() // 2, 100))
        pygame.display.flip()
        pygame.time.wait(3000) # Wait for 3 seconds before closing the game

    def human_input_to_move(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            clicked = False # Flag to check if a line click was completed
            dot_radius = 8  # Exclusion zone around dots to prevent accidental corner clicks
            
            # Check for horizontal line click
            for i in range(self.size):
                for j in range(self.size - 1):
                    left_x = self.margin_left + j * self.edge
                    right_x = self.margin_left + (j + 1) * self.edge
                    line_y = self.margin_up + i * self.edge
                    
                    # Check if click is on the line and NOT on the corner dots
                    x_in_range = left_x + dot_radius < x < right_x - dot_radius
                    y_in_range = line_y - 5 < y < line_y + 5
                    
                    if x_in_range and y_in_range:
                        if (self.h_edges[i][j] == 0): # If line is already filled, ignore click
                            move = rules.Move('H', i, j) # Create Move object for rules processing
                            rules.apply_move(self.GameState, move) # Apply move to update GameState and UI
            
            # Check for vertical line click
            if not clicked:
                for i in range(self.size - 1):
                    for j in range(self.size):
                        line_x = self.margin_left + j * self.edge
                        top_y = self.margin_up + i * self.edge
                        bottom_y = self.margin_up + (i + 1) * self.edge
                        
                        # Check if click is on the line and NOT on the corner dots
                        x_in_range = line_x - 5 < x < line_x + 5
                        y_in_range = top_y + dot_radius < y < bottom_y - dot_radius
                        
                        if x_in_range and y_in_range:
                            if (self.v_edges[i][j] == 0): # If line is already filled, ignore click
                                move = models.Move('V', i, j) # Create Move object for rules processing
                                rules.apply_move(self.GameState, move) # Apply move to update GameState and UI
    
    def run_game(self):
        """
        Khởi tạo game Dots and Boxes.
        Hiển thị giao diện và xử lý sự kiện người chơi.
        Tuấn Khanh 12/4/2026
        """

        # Main game loop
        while True:
            if self.moves_remaining == 0: # If no moves remaining, determine winner
                self.display_winner()
                pygame.quit()
                sys.exit()
            for event in pygame.event.get():
                self.human_input_to_move(event)
            self.render_board()
            pygame.display.flip()
            self.clock.tick(60)