import random
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
        self.rmap = [[255] * self.width for _ in range(self.height)]
        # Declaring the terrain map for the dungeon
        self.tmap = [[self.terrain.debug] * self.width for _ in range(self.height)]
        
    def valid_point(self, r, c):
        # TODO
        return
        
    # Attempts to place a room into the dungeon terrain map
    def _place_room(self, room):
        # TODO
        # copy of the terrain map to easily revert changes if room cannot be placed
        tmap_copy = self.tmap.deepcopy()
        r = room.origin_r
        c = room.origin_c
        last_r = r + room.rsize_h
        last_c = c + room.rsize_w
        
        while (r <  last_r):
            while (c < last_c):
                return
                

    # Generates dungeon rock hardness map, necessary for Dijkstra path generation + NPC pathfinding
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
            
    def print_terrain(self):
        for r in range(self.height):
            for c in range(self.width):
                t_type = self.tmap[r][c]
                if (t_type == self.terrain.floor):
                    print(".", end="")
                elif (t_type == self.terrain.stair):
                    print("<", end="")
                elif (t_type == self.terrain.stdrock):
                    print(" ", end="")
                elif (t_type == self.terrain.immrock):
                    print("X", end="") # will want to be a proper border later
                else:
                    print("!", end="") # issue flag
            
            print("") # Newline for end of row
    
    # Generates a random dungeon
    def generate_dungeon(self):
        # TODO
        self._generate_rockmap()
        self._generate_terrain()
        return

def main():
    d = dungeon(21, 80)
    d.print_terrain()

if __name__ == "__main__":
    main()
