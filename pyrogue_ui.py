import tkinter as tk
from dungeon import dungeon

# This file handles the tkinker user interface for the the game. Consequently, it also handles much of the high-level game logic.
class dungeon_ui:
    def __init__(self, root, dungeon: dungeon):
        self.root = root
        self.canvas = tk.Canvas(root, width=1280, height=720, bg='black')
        self.canvas.pack(fill = tk.BOTH, expand = True)
        self.dungeon = dungeon
        
        self.resize_id = None
        self.resize_event = None
        
        self.root.bind("<Configure>", self.on_resize)
    
    def on_resize(self, event):
        # Save the event for redrawing
        self.resize_event = event
        
        # Cancel any pending redraw
        if self.resize_id:
            self.root.after_cancel(self.resize_id)
            
        # schedule a redraw for 50ms from now
        self.resize_id = self.root.after(100, self._redraw)

    def _redraw(self):
        if self.resize_event == None:
            return
        
        event = self.resize_event
        self.canvas.delete("all")
        self.render_dungeon(event.width, event.height)
    
    def render_dungeon(self, width, height):
        max_tile_width = width // self.dungeon.width
        max_tile_height = height // (self.dungeon.height + 3)
        tile_size = min(max_tile_width, max_tile_height)
        
        # For properly centering the dungeon
        x_offset = (width - tile_size * self.dungeon.width) // 2
        y_offset = tile_size * 2
        
        for row, line in enumerate(self.dungeon.tmap):
            for col, char in enumerate(line):
                x = col * tile_size + x_offset
                y = row * tile_size + y_offset
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
                self.canvas.create_rectangle(x, y, x + tile_size, y + tile_size, fill='black', outline='')
                self.canvas.create_text(x + tile_size // 2, y + tile_size // 2, text=char, fill = 'white', font=('Consolas', int(tile_size / 1.5)))
                