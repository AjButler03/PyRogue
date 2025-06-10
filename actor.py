import random
import abc
from enum import Enum
import dungeon

# This file contains the class information for the Actor class and its children, the player and monster classes.


# This is the generic actor class to be used in the general turn loop.
class actor(abc.ABC):

    # Enum to define moves, whose values correspond to the move's idx in the coordinate deltas
    class _move(Enum):
        up_left = 0
        up = 1
        up_right = 2
        left = 3
        right = 4
        down_left = 5
        down = 6
        down_right = 7
        none = 8

    # This method is to initialize the position of the actor within the dungeon, verifying the location as valid.
    # Returns True on successful placement, False otherwise.
    @abc.abstractmethod
    def init_pos(self, dungeon, actor_map, r, c):
        pass

    # Returns the row, column coordinate of the actor, in that order.
    @abc.abstractmethod
    def get_pos(self):
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

    # Returns the row, column coordinate of where the actor is attempting to move to.
    def target_pos(self, move):
        # Coordinate deltas for 8 surrounding points
        # up_left, up, up_right, left, right, down_left, down, down_right
        delta_r = [-1, -1, -1, 0, 0, 1, 1, 1]
        delta_c = [-1, 0, 1, -1, 1, -1, 0, 1]
        return self.r + delta_r[move.value], self.c + delta_c[move.value]


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
    
    # Determines if the player can be at this position.
    def _valid_pos(self, dungeon, r, c):
        if dungeon.valid_point(r, c) and dungeon.rmap[r][c] == 0:
            return True
        else:
            return False

    # Initializes the player's position within the dungeon.
    # Returns True on successful placement, False otherwise.
    def init_pos(self, dungeon, actor_map, r, c):
        if (
            self._valid_pos(dungeon, r, c)
            and actor_map[r][c] == None
        ):
            self.r = r
            self.c = c
            actor_map[r][c] = self
            return True
        else:
            return False

    # Returns the row, column coordinate of the player, in that order.
    def get_pos(self):
        return self.r, self.c

    # Turn handler for the player.
    def handle_turn(self, dungeon, actor_map):
        # For now, the player just moves randomly.
        move = self._move(random.randint(0, 7))
        new_r, new_c = self.target_pos(move)
        # Check that new position is valid for the PC to be at
        # Repeat until this is the case
        while not self._valid_pos(dungeon, new_r, new_c):
            move = self._move(random.randint(0, 7))
            new_r, new_c = self.target_pos(move)
        # Move the PC, removing whatever monster may be there
        actor_map[self.r][self.c] = None
        actor_map[new_r][new_c] = self
        self.r = new_r
        self.c = new_c
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

    # Returns the row, column coordinate of the player, in that order.
    def get_pos(self):
        return self.r, self.c

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
