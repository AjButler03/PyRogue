import abc
import dungeon

# This file contains the class information for the Actor class and its children, the player and monster classes.

class player:
    
    # Player constructor
    def __init__(self):
        # player location
        self.r = 0
        self.c = 0
        # Player character's memory of the dungeon, as it appeared on sight.
        self.memmap = []
    
    # Initializes the player's position within the dungeon.
    # returns True on successful update, returns False otherwise.
    def init_pos(self, dungeon, r, c):
        if dungeon.valid_point(r, c) and dungeon.rmap[r][c] == 0:
            self.r = r
            self.c = c
            return True
        else:
            return False            