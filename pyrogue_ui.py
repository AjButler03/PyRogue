import tkinter as tk
from dungeon import dungeon

# This file handles the tkinker user interface for the the game. Consequently, it also handles much of the high-level game logic.

TILE_SIZE = 16

class dungeon_ui:
    def __init__(self, root, dungeon: dungeon):
        self.canvas = tk.Canvas(root, width = 1280, height=720, bg='black')
        self.canvas.pack()
        self.dungeon = dungeon
        self.render_dungeon()
        
    def render_dungeon(self):
        for row, line in enumerate(self.dungeon.tmap):
            for col, char in enumerate(line):
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                terrain = self.dungeon.tmap[row][col]
                if terrain == dungeon.terrain.floor:
                    char = "."
                elif terrain == dungeon.terrain.stair:
                    char  = ">"
                elif terrain == dungeon.terrain.stdrock:
                    char = " "
                elif terrain == dungeon.terrain.immrock:
                    char = "X"
                else:
                    char = "!"
                self.canvas.create_rectangle(x, y, x + TILE_SIZE, y + TILE_SIZE, fill='black', outline='')
                self.canvas.create_text(x + TILE_SIZE // 2, y + TILE_SIZE // 2, text=char, fill = 'white', font=('Consolas', 12))
                