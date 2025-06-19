import tkinter as tk
from game import pyrogue_game

# This is the main executable for PyRogue. Running this file launches the game.


def main():
    screen_h = 720
    screen_w = 1280
    map_h = 30
    map_w = 60
    # Easy: 0.25, normal: 0.75, hard = 1.25
    difficulty = 0.25
    root = tk.Tk()
    root.title("PyRogue")
    game = pyrogue_game(root, screen_h, screen_w, map_h, map_w, difficulty)
    root.mainloop()


if __name__ == "__main__":
    main()
