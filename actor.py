import abc
import dungeon

# This file contains the class information for the Actor class and its children, the player and monster classes.

# This is the generic actor class to be used in the general turn loop.
class actor(abc.ABC):
    # This method is to initialize the position of the actor within the dungeon, verifying the location as valid.
    # Returns True on successful placement, False otherwise.
    @abc.abstractmethod
    def init_pos(self, dungeon, actor_map, r, c):
        pass
    
# This is the class for the player character and its turn/movement methods.
class player(actor):
    
    # Player constructor
    def __init__(self):
        # Declare fields for location
        self.r = 0
        self.c = 0
        # Player character's memory of the dungeon, as it appeared on sight.
        self.memmap = []
    
    # Initializes the player's position within the dungeon.
    # Returns True on successful placement, False otherwise.
    def init_pos(self, dungeon, actor_map, r, c):
        if dungeon.valid_point(r, c) and dungeon.rmap[r][c] == 0 and actor_map[r][c] == None:
            self.r = r
            self.c = c
            actor_map[r][c] = self
            return True
        else:
            return False
        
# This is the class for monsters and their turn/movement methods.        
class monster(actor):
    
    # Monster constructor
    def __init__(self, attributes):
        # Declare fields for location
        self.r = 0
        self.c = 0
        # Monster's 'path'; this is a distance map of the dungeon to determine where to move next
        self.path = []
        # bitfield to indicate what sort of attributes that the monster has
        self.attributes = attributes