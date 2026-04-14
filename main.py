import pygame
import sys
import models
import ui

init_state = models.create_initial_state(6, 6) # Create initial game state with n rows and n columns

game_ui = ui.UI(init_state) # Initialize UI with the game state
game_ui.render_board() # Render the initial board
game_ui.run_game() # Start the game loop to handle events and update the display

