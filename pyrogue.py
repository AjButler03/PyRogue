import tkinter as tk
from menu_main import Menu_Main


# This is the main executable for PyRogue. Running this file launches the game.


def main():
    # Initial screen size; arbitrary
    screen_h = 720
    screen_w = 1280

    # Init tkinter window
    root = tk.Tk()
    root.title("PyRogue")
    root.configure(bg="black")

    # Init the main menu; this will handle settings changes as well as launching / ending individual games
    menu = Menu_Main(root, screen_h, screen_w)

    # Launch the tkinter loop, which will start the main menu's code
    root.mainloop()


if __name__ == "__main__":
    main()
