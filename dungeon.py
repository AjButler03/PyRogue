import random
import math
from enum import Enum
from utility import exp_chancetime

class dungeon:
    
    # Enum to dictate the terrain types of a dungeon
    class terrain(Enum):
        debug = 0
        floor = 1
        stair = 2
        stdrock = 3
        immrock = 4

    # Classes to store individual room and starcase information
    # Not strictly necessary atm, but will be helpful if I decide to create a saving/loading functionality
    class room:
        # Room Constructor
        def __init__(self, origin_r, origin_c, rsize_h, rsize_c):
            self.origin_r = origin_r
            self.origin_c = origin_c
            self.rsize_h = rsize_h
            self.rsize_c = rsize_c

    class staircase:
        # Staircase Constructor
        def __init__(self, origin_r, origin_c):
            self.origin_r = origin_r
            self.origin_c = origin_c

    # Dungeon Constructor
    def __init__(self, size_h, size_w):
        # Size of the dungeon
        self.height = size_h
        self.width = size_w
        # Counts of rooms / stairs
        self.roomc = 0
        self.stairc = 0
        # Declaring the rock hardness map; default max hardness of 255
        rmap = [[255] * self.width for _ in range(self.height)]
        # Declaring the terrain map for the dungeon
        tmap = [[self.terrain.debug] * self.width for _ in range(self.height)]

    # Generates rock hardness map, necessary for Dijkstra path generation + NPC pathfinding
    def _generate_rockmap(self):
        # TODO
        # This needs to generate the rockmap, preferably making it somewhat smoothish
        return

    # Generates the dungeon rooms, cooridors, and staircases (terrain)
    # Cannot be called before generating the rockmap
    def _generate_terrain(self):
        # Creating rooms; at least 1
        while (self.roomc < 1) or (exp_chancetime(self.roomc)):
            new_room = self.room(
                (random.random() % self.height),
                (random.random() % self.width),
                (random.random() % (self.height / 2)),
                (random.random() % (self.width / 2)),
            )

    def generate_dungeon(self):
        # TODO
        return

def main():
    d = dungeon(21, 80)

if __name__ == "__main__":
    main()
