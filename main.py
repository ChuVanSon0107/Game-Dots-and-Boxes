import pygame
import sys
import models
import ui

init_state = models.create_initial_state(6, 6) # Create initial game state with n rows and n columns

ui.run_game(init_state)

