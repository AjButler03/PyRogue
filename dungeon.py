import random
import math
from enum import Enum
from utility import exp_chancetime

class dungeon:
    # Types to dictate the terrain types of a dungeon
    class terrain(Enum):
        debug = 0
        floor = 1
        stair = 2
        stdrock = 3
        immrock = 4
    
    # Class to store individual room information
    class room:
        # Room Constructor
        def __init__(self, origin_r, origin_c, rsize_h, rsize_c):
            self.origin_r = origin_r
            self.origin_c = origin_c
            self.rsize_h = rsize_h
            self.rsize_c = rsize_c
    
    # Dungeon Constructor
    def __init__(self, size_h, size_w):
        # Size of the dungeon
        self.height = size_h
        self.width = size_w
        # Counts of rooms / stairs
        self.roomc = 0
        self.stairc = 0
        # Declaring the terrain map for the dungeon
        tmap = [[self.terrain.debug] * self.width for _ in range(self.height)]
        
    def generate_terrain(self):
        while (self.roomc < 7) or (exp_chancetime(self.roomc)):
            new_room = self.room.__init__(new_room, (random.random() % self.height), (random.random() % self.width), (random.random() % (self.height / 2)), (random.random() % (self.width / 2)), )
            
        
def main():
    d = dungeon.__init__(d, 21, 80)
    
if __name__ == "__main__":
    main()