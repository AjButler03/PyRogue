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

    # Handles the turn for the actor.
    @abc.abstractmethod
    def handle_turn(self, dungeon, actor_map):
        pass

    # Returns True if the actor is alive, False otherwise.
    @abc.abstractmethod
    def is_alive(self):
        pass

    # Declare this actor as dead.
    @abc.abstractmethod
    def kill(self):
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
        # Define the player as alive
        self.alive = True

    # Initializes the player's position within the dungeon.
    # Returns True on successful placement, False otherwise.
    def init_pos(self, dungeon, actor_map, r, c):
        if (
            dungeon.valid_point(r, c)
            and dungeon.rmap[r][c] == 0
            and actor_map[r][c] == None
        ):
            self.r = r
            self.c = c
            actor_map[r][c] = self
            return True
        else:
            return False

    # Turn handler for the player.
    def handle_turn(self, dungeon, actor_map):
        # TODO
        return

    # Returns True if the player is alive, False otherwise.
    def is_alive(self):
        return self.alive

    # Declares the player as dead.
    def kill(self):
        self.alive = False


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
        # Declare the monster as initially alive
        self.alive = True

    def init_pos(self, dungeon, actor_map, r, c):
        if (
            dungeon.valid_point(r, c)
            and dungeon.rmap[r][c] == 0
            and actor_map[r][c] == None
        ):
            self.r = r
            self.c = c
            actor_map[r][c] = self
            return True
        else:
            return False

    # Turn handler for this monster.
    def handle_turn(self, dungeon, actor_map):
        # TODO
        return

    # Returns True if this monster is alive, False otherwise.
    def is_alive(self):
        return self.alive

    # Declares this monster as dead.
    def kill(self):
        self.alive = False
