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
    def init_pos(self, dungeon: dungeon.dungeon, actor_map: list, r: int, c: int):
        pass

    # Returns the row, column coordinate of the actor, in that order.
    @abc.abstractmethod
    def get_pos(self):
        pass

    # Returns the current turn of the given actor.
    @abc.abstractmethod
    def get_currturn(self) -> int:
        pass

    # Sets the current turn of the given actor.
    @abc.abstractmethod
    def set_currturn(self, turn: int):
        pass

    # Returns True if the actor is alive, False otherwise.
    @abc.abstractmethod
    def is_alive(self):
        pass

    # Declare this actor as dead.
    @abc.abstractmethod
    def kill(self):
        pass

    # Handles the turn for the actor.
    @abc.abstractmethod
    def handle_turn(self, dungeon: dungeon.dungeon, actor_map: list):
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
        # Init the player's turn to zero
        self.turn = 0
        # Define the player as alive
        self.alive = True

    # Determines if the player can be at this position.
    def _valid_pos(self, dungeon: dungeon.dungeon, r: int, c: int) -> bool:
        if dungeon.valid_point(r, c) and dungeon.rmap[r][c] == 0:
            return True
        else:
            return False

    # Initializes the player's position within the dungeon.
    # Returns True on successful placement, False otherwise.
    def init_pos(self, dungeon: dungeon.dungeon, actor_map: list, r: int, c: int):
        if self._valid_pos(dungeon, r, c) and actor_map[r][c] == None:
            self.r = r
            self.c = c
            actor_map[r][c] = self
            return True
        else:
            return False

    # Returns the row, column coordinate of the player, in that order.
    def get_pos(self):
        return self.r, self.c

    # Returns the current turn of the player.
    def get_currturn(self) -> int:
        return self.turn

    # Sets the current turn of the monster.
    def set_currturn(self, turn: int):
        self.turn = turn

    # Returns True if the player is alive, False otherwise.
    def is_alive(self) -> bool:
        return self.alive

    # Declares the player as dead.
    def kill(self):
        self.alive = False

    # Turn handler for the player.
    def handle_turn(self, dungeon: dungeon.dungeon, actor_map: list):
        # For now, the player just moves randomly.
        move = self._move(random.randint(0, 7))
        new_r, new_c = self.target_pos(move)
        # Check that new position is valid for the PC to be at
        # Repeat until this is the case
        while not self._valid_pos(dungeon, new_r, new_c):
            move = self._move(random.randint(0, 7))
            new_r, new_c = self.target_pos(move)
        # Move the PC, removing whatever monster may be there
        a = actor_map[new_r][new_c]
        if not a == None:
            # Mark actor as dead
            a.kill()
        actor_map[self.r][self.c] = None
        actor_map[new_r][new_c] = self
        self.r = new_r
        self.c = new_c
        return


# This is the class for monsters and their turn/movement methods.
class monster(actor):
    # A monster can have any number of attributes. I will be indicating these using a bit field.
    # For v03, only the first 4 will be fully implemented. The others will come later, if I decide to do them at all.
    _ATTR_INTELLIGENT = 0b0000_0000_0000_0001  # Bit 1 (0000 0000 0000 0001)
    _ATTR_TELEPATHIC_ = 0b0000_0000_0000_0010  # Bit 2 (0000 0000 0000 0010)
    _ATTR_TUNNEL_____ = 0b0000_0000_0000_0100  # Bit 3 (0000 0000 0000 0100)
    _ATTR_ERRATIC____ = 0b0000_0000_0000_1000  # Bit 4 (0000 0000 0000 1000)
    _ATTR_PASS_______ = 0b0000_0000_0001_0000  # Bit 5 (0000 0000 0001 0000)
    _ATTR_PICKUP_____ = 0b0000_0000_0010_0000  # Bit 6 (0000 0000 0010 0000)
    _ATTR_DESTROY____ = 0b0000_0000_0100_0000  # Bit 7 (0000 0000 0100 0000)
    _ATTR_UNIQ_______ = 0b0000_0000_1000_0000  # Bit 8 (0000 0000 1000 0000)
    _ATTR_BOSS_______ = 0b0000_0001_0000_0000  # Bit 9 (0000 0001 0000 0000)

    # Monster constructor
    def __init__(self, attributes: int, speed: int):
        # Declare fields for location
        self.r = 0
        self.c = 0
        # Monster's 'path'; this is a distance map of the dungeon to determine where to move next
        self.path = []
        # Speed modifier; lower is better
        self.speed = speed
        # bitfield to indicate what sort of attributes that the monster has
        self.attributes = attributes
        # Set the monsters current turn to zero
        self.turn = 0
        # Declare the monster as initially alive
        self.alive = True

    # Returns True if the monster has the given attribute, False otherwise.
    def has_attribute(self, attr: int) -> bool:
        return (self.attributes & attr) != 0

    # Adds a given attribute to the monster.
    def add_attribute(self, attr: int):
        self.attributes |= attr

    # Determines if the monster can be at this position.
    def _valid_pos(self, dungeon: dungeon.dungeon, r: int, c: int):
        if dungeon.valid_point(r, c) and dungeon.rmap[r][c] == 0:
            return True
        else:
            return False

    def init_pos(self, dungeon: dungeon.dungeon, actor_map: list, r: int, c: int) -> bool:
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

    # Updates the monster's path, depending on the attributes that it has
    def _update_path(self, dungeon):
        pass

    # Returns the current turn of the monster.
    def get_currturn(self) -> int:
        return self.turn

    # Sets the current turn of the monster.
    def set_currturn(self, turn: int):
        self.turn = turn

    # Returns True if this monster is alive, False otherwise.
    def is_alive(self):
        return self.alive

    # Declares this monster as dead.
    def kill(self):
        self.alive = False

    # Turn handler for this monster.
    def handle_turn(self, dungeon: dungeon.dungeon, actor_map: list):
        # For now, the player just moves randomly.
        move = self._move(random.randint(0, 7))
        new_r, new_c = self.target_pos(move)
        # Check that new position is valid for the PC to be at
        # Repeat until this is the case
        while not self._valid_pos(dungeon, new_r, new_c):
            move = self._move(random.randint(0, 7))
            new_r, new_c = self.target_pos(move)
        # Move the PC, removing whatever monster may be there
        a = actor_map[new_r][new_c]
        if not a == None and isinstance(a, player):
            # Mark player as dead and remove from the actor map
            a.kill()
            actor_map[new_r][new_c] = None
        elif a == None:
            # Have monster move only if there isn't another monster there
            # Eventually I want this to displace the monster that exists there, if thats the case
            actor_map[self.r][self.c] = None
            actor_map[new_r][new_c] = self
            self.r = new_r
            self.c = new_c
