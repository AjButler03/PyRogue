import tkinter as tk
from game import Pyrogue_Game

# This is the main executable for PyRogue. Running this file launches the game.

# Pre-defined dungeon sizes
dungeon_size = {
    'tiny' : (10, 20),
    'small': (20, 40),
    'medium': (30, 60),
    'large': (40, 80),
    'enormous': (50, 90)
}

# Pre-defined difficulty settings
difficulty_setting = {
    'trivial': 0.10,
    'easy': 0.25,
    'normal': 0.75,
    'hard': 1.25,
    'very_hard': 1.75,
    'legendary': 2.5
}


def main():
    screen_h = 720
    screen_w = 1280
    map_h, map_w = dungeon_size['medium']
    difficulty = difficulty_setting['normal']
    root = tk.Tk()
    root.title("PyRogue")
    Pyrogue_Game(root, screen_h, screen_w, map_h, map_w, difficulty)
    root.mainloop()


if __name__ == "__main__":
    main()
