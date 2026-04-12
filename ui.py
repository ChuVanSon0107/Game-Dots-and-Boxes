import pygame
import sys
import models

def run_game(init_state):
    """
    Khởi tạo game Dots and Boxes.
    Hiển thị giao diện và xử lý sự kiện người chơi.
    Tuấn Khanh 12/4/2026
    """
    pygame.init() # Init pygame
    W, H = 800, 600 # Screen setup
    edge = 36 # Spacing between grid points
    size = init_state['rows'] + 1 # size x size grid of dots, which creates a (size-1) x (size-1) grid of boxes
    board_size = (size - 1) * edge # Total board width/height
    margin_left = (W - board_size) // 2 # Center board horizontally
    margin_up = 300 # Top margin for scoreboard space
    turn_player = 1 # 1 for player 1, 2 for player 2
    scores = {
        'p1': init_state['score_player1'],
        'p2': init_state['score_player2']
    }
    moves_remaining = init_state['moves_remaining'] # Initialize moves remaining from game state


    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Catch the Falling Blocks")

    WHT, BLU, RED, BLK = (255, 255, 255), (0, 200, 255), (255, 0, 0), (0, 0, 0) # Colors

    # Clock and font
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)

    # Draw dots and boxes board 7x7
    # Create arrays for horizontal and vertical lines
    # Making lines capable to toggle between empty and filled states
    # If filled, if turn player is 0 fill red, else fill blue (theses cannot be changed until the game is restarted)

    h_lines = init_state['h_edges'] 
    v_lines = init_state['v_edges'] 
    boxes = init_state['boxes']
    def draw_board():
        screen.fill(WHT) # Clear screen
        
        # Draw scoreboard at the top
        player1_text = font.render(f"Player 1 (Red): {scores['p1']}", True, RED)
        player2_text = font.render(f"Player 2 (Cyan): {scores['p2']}", True, BLU)
        screen.blit(player1_text, (50, 30))
        screen.blit(player2_text, (W - 250, 30))
        
        # Draw horizontal lines
        for i in range(size):
            for j in range(size - 1):
                if h_lines[i][j]: # If line is filled
                    color = RED if h_lines[i][j] == 1 else BLU # Color based on current player
                    pygame.draw.line(screen, color, (margin_left + j * edge, margin_up + i * edge), (margin_left + (j + 1) * edge, margin_up + i * edge), 5)
                else:
                    pygame.draw.line(screen, WHT, (margin_left + j * edge, margin_up + i * edge), (margin_left + (j + 1) * edge, margin_up + i * edge), 5) # Clear line
        # Draw vertical lines
        for i in range(size - 1):
            for j in range(size):
                if v_lines[i][j]: # If line is filled
                    color = RED if v_lines[i][j] == 1 else BLU # Color based on current player
                    pygame.draw.line(screen, color, (margin_left + j * edge, margin_up + i * edge), (margin_left + j * edge, margin_up + (i + 1) * edge), 5)
                else:
                    pygame.draw.line(screen, WHT, (margin_left + j * edge, margin_up + i * edge), (margin_left + j * edge, margin_up + (i + 1) * edge), 5) # Clear line
        # Draw boxes
        for i in range(size - 1):
            for j in range(size - 1):
                if boxes[i][j]: # If box is completed
                    color = RED if boxes[i][j] == 1 else BLU # Color based on current player
                    pygame.draw.rect(screen, color, (margin_left + j * edge + 5, margin_up + i * edge + 5, edge - 10, edge - 10)) # Fill box
                else:
                    pygame.draw.rect(screen, WHT, (margin_left + j * edge + 5, margin_up + i * edge + 5, edge - 10, edge - 10)) # Clear box
        # Draw dots
        for i in range(size):
            for j in range(size):
                pygame.draw.circle(screen, BLK, (margin_left + j * edge, margin_up + i * edge), 5)

    # Function to check for boxes[i][j] completion after a line is toggled with designated i and j
    def check_box_completion(i, j):
        completed = False
        if i >= 0 and i < size - 1 and j >= 0 and j < size - 1: # Check box to the right and down
            if boxes[i][j]: # If box is already completed, return False
                return False
            if h_lines[i][j] and h_lines[i + 1][j] and v_lines[i][j] and v_lines[i][j + 1]:
                boxes[i][j] = turn_player # Mark box as completed by current player
                if turn_player == 1:
                    scores['p1'] += 1
                else:
                    scores['p2'] += 1
                completed = True
        return completed
    
    # Display results when the game is finished
    def display_winner():
        if scores['p1'] > scores['p2']:
            winner_text = font.render("Player 1 wins!", True, RED)
        elif scores['p2'] > scores['p1']:
            winner_text = font.render("Player 2 wins!", True, BLU)
        else:
            winner_text = font.render("It's a tie!", True, BLK)
        screen.blit(winner_text, (W // 2 - winner_text.get_width() // 2, 100))
        pygame.display.flip()
        pygame.time.wait(3000) # Wait for 3 seconds before closing the game

    while True:
        if moves_remaining == 0: # If no moves remaining, determine winner
            display_winner()
            pygame.quit()
            sys.exit()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                res = False # Flag to check if a box was completed
                moved = False # Flag to check if a line was toggled
                # Check for horizontal line click
                for i in range(size):
                    for j in range(size - 1):
                        if margin_left + j * edge < x < margin_left + (j + 1) * edge and margin_up + i * edge - 5 < y < margin_up + i * edge + 5:
                            if (h_lines[i][j] != 0): # If line is already filled, ignore click
                                break
                            moved = True
                            h_lines[i][j] = turn_player # Toggle line state base on player's turn
                            # Get the 2 boxes that could be completed by this line
                            if check_box_completion(i - 1, j): # Check box above
                                res = True
                            if check_box_completion(i, j): # Check box below
                                res = True
                            break # Break to prevent multiple line toggles on a single click
                # Check for vertical line click
                for i in range(size - 1):
                    for j in range(size):
                        if margin_left + j * edge - 5 < x < margin_left + j * edge + 5 and margin_up + i * edge < y < margin_up + (i + 1) * edge:
                            if (v_lines[i][j] != 0): # If line is already filled, ignore click
                                break
                            moved = True
                            v_lines[i][j] = turn_player # Toggle line state base on player's turn
                            # Get the 2 boxes that could be completed by this line
                            if check_box_completion(i, j - 1): # Check box to the left
                                res = True
                            if check_box_completion(i, j): # Check box to the right
                                res = True
                            break # Break to prevent multiple line toggles on a single click
                # If no box was completed, switch turn
                if moved:
                    moves_remaining -= 1
                    if not res: # If no box was completed, switch turn
                        turn_player = 3 - turn_player
        # If no moves remaining, display winner
        draw_board()
        pygame.display.flip()
        clock.tick(60)