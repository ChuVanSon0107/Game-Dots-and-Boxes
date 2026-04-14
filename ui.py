import pygame
import sys
# Tuấn Khanh 14/4/2026
# Các hàm thuộc lớp UI:
# __init__: Khởi tạo giao diện, thiết lập các thuộc tính cần thiết từ state
# render_board: Vẽ lại bàn cờ dựa trên trạng thái hiện tại
# check_box_completion: Kiểm tra xem việc đặt một đường có hoàn thành một ô vuông nào không, cập nhật điểm số nếu có
# display_winner: Hiển thị người chiến thắng khi trò chơi kết thúc
# handle_click: Xử lý sự kiện click chuột, xác định đường nào được chọn và cập nhật trạng thái
# run_game: Vòng lặp chính của trò chơi, xử lý sự kiện và cập nhật giao diện liên tục

class UI:
    def __init__(self, state):
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
        self.size = state['rows'] + 1 # self.size x self.size grid of dots, which creates a (self.size-1) x (self.size-1) grid of self.boxes
        self.edge = 56 # Spacing between grid points
        self.board_size = (self.size - 1) * self.edge # Total board width/height
        self.h_edges = state['h_edges']
        self.v_edges = state['v_edges']
        self.boxes = state['boxes']
        self.edges_count = state['edges_count']
        self.margin_left = (self.W - self.board_size) // 2 # Left margin for centering the board
        self.margin_up = 200 # Top margin for scoreboard space
        self.current_player = 1 # 1 for player 1, 2 for player 2
        self.score_player1 = state['score_player1']
        self.score_player2 = state['score_player2']
        self.moves_remaining = state['moves_remaining']

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

    def check_box_completion(self, i, j):
        completed = False
        if i < 0 or j < 0 or i >= self.size - 1 or j >= self.size - 1: # If out of bounds, return False
            return False
        self.edges_count[i][j] += 1 # Increment edge count for this box
        if self.edges_count[i][j] == 4: # If all 4 edges
            self.boxes[i][j] = self.current_player # Mark box as completed by current player
            if self.current_player == 1:
                self.score_player1 += 1
            else:
                self.score_player2 += 1
            completed = True
        return completed

    def display_winner(self):
        if self.score_player1 > self.score_player2:
            winner_text = self.font.render("Player 1 wins!", True, self.RED)
        elif self.score_player2 > self.score_player1:
            winner_text = self.font.render("Player 2 wins!", True, self.BLU)
        else:
            winner_text = self.font.render("It's a tie!", True, self.BLK)
        self.screen.blit(winner_text, (self.W // 2 - winner_text.get_width() // 2, 100))
        pygame.display.flip()
        pygame.time.wait(3000) # Wait for 3 seconds before closing the game

    def handle_click(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            res = False # Flag to check if a box was completed
            moved = False # Flag to check if a line was toggled
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
                        if (self.h_edges[i][j] != 0): # If line is already filled, ignore click
                            break
                        moved = True
                        self.h_edges[i][j] = self.current_player # Toggle line state base on player's turn
                        if self.check_box_completion(i - 1, j): # Check box above
                            res = True
                        if self.check_box_completion(i, j): # Check box below
                            res = True
                        break # Break to prevent multiple line toggles on a single click
            
            # Check for vertical line click
            if not res:
                for i in range(self.size - 1):
                    for j in range(self.size):
                        line_x = self.margin_left + j * self.edge
                        top_y = self.margin_up + i * self.edge
                        bottom_y = self.margin_up + (i + 1) * self.edge
                        
                        # Check if click is on the line and NOT on the corner dots
                        x_in_range = line_x - 5 < x < line_x + 5
                        y_in_range = top_y + dot_radius < y < bottom_y - dot_radius
                        
                        if x_in_range and y_in_range:
                            if (self.v_edges[i][j] != 0): # If line is already filled, ignore click
                                break
                            moved = True
                            self.v_edges[i][j] = self.current_player # Toggle line state base on player's turn
                            # Get the 2 self.boxes that could be completed by this line
                            if self.check_box_completion(i, j - 1): # Check box to the left
                                res = True
                            if self.check_box_completion(i, j): # Check box to the right
                                res = True
            # If no box was completed, switch turn
            if moved:
                self.moves_remaining -= 1
                if not res: # If no box was completed, switch turn
                    self.current_player = 3 - self.current_player

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
                self.handle_click(event)
            self.render_board()
            pygame.display.flip()
            self.clock.tick(60)