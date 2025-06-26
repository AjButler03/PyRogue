import tkinter as tk
from game import Pyrogue_Game

# This is the main executable for PyRogue. Running this file launches the game.


def main():
    # Initial screen size; arbitrary
    screen_h = 720
    screen_w = 1280

    # dungeon size and difficulty settings
    size = "small"
    diff = "normal"
    print("SIZE:", size, "DIFFICULTY:", diff)

    # Init dungeon
    map_h, map_w = dungeon_size[size]
    difficulty = difficulty_setting[diff]

    # Init tkinter window
    root = tk.Tk()
    root.configure(height=screen_h, width=1280)
    root.title("PyRogue")
    root.configure(bg='black')

    # Init game; includes tkinter event listeners
    Pyrogue_Game(root, screen_h, screen_w, map_h, map_w, difficulty)

    # Launch the tkinter loop, which activates game code through event listeners
    root.mainloop()


if __name__ == "__main__":
    main()
