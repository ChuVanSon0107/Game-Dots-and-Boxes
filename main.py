import pygame
import sys
import models
import ui
# Giá trị mặc định cho kích thước bàn cờ (số ô vuông)
board_size = 3
init_state = models.create_initial_state(board_size, board_size) # Create initial game state with n rows and n columns

game_ui = ui.UI(init_state) # Initialize UI with the game state
game_ui.run_game() # Start the game loop to handle events and update the display

