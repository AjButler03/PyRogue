import random
import abc
import copy
from enum import Enum
import dungeon

# This file contains the class information for the Actor class and its children, the player and monster classes.


# This is the generic actor class to be used in the general turn loop.
class actor(abc.ABC):

    # Coordinate deltas for 8 surrounding points of a given point.
    # up_left, up, up_right, left, right, down_left, down, down_right, none
    _delta_r = [-1, -1, -1, 0, 0, 1, 1, 1, 0]
    _delta_c = [-1, 0, 1, -1, 1, -1, 0, 1, 0]

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
    def init_pos(
        self, dungeon: dungeon.dungeon, actor_map: list, r: int, c: int
    ) -> bool:
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

    # Returns the row, column coordinate of the actor, in that order.
    def get_pos(self):
        return self.r, self.c

    # Returns the current turn of the given actor.
    def get_currturn(self) -> int:
        return self.turn

    # Returns the speed (turn number increase per turn).
    def get_speed(self) -> int:
        return self.speed

    # Returns the character representation of the actor.
    def get_char(self) -> str:
        return self.char

    # Sets the current turn of the given actor.
    def set_currturn(self, turn: int):
        self.turn = turn

    # Returns True if the actor is alive, False otherwise.
    def is_alive(self):
        return self.alive

    # Declare this actor as dead.
    def kill(self):
        self.alive = False

    # Handles the turn for the actor.
    @abc.abstractmethod
    def handle_turn(self, dungeon: dungeon.dungeon, actor_map: list, player):
        pass

    # Returns the row, column coordinate of where the actor is attempting to move to.
    def target_pos(self, move):
        return self.r + self._delta_r[move.value], self.c + self._delta_c[move.value]


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
        # Init the player's speed (turn number increase per turn) to 10
        self.speed = 10
        # Define the player as alive
        self.alive = True
        self.char = "@"

    # Determines if the player can be at this position.
    def _valid_pos(self, dungeon: dungeon.dungeon, r: int, c: int) -> bool:
        if dungeon.valid_point(r, c) and dungeon.rmap[r][c] == 0:
            return True
        else:
            return False

    # Forces the player into this position. Does not check that position is 'valid'.
    def _force_pos_update(
        self, dungeon: dungeon.dungeon, actor_map: list, r: int, c: int
    ):
        actor_map[self.r][self.c] = None
        actor_map[r][c] = self
        self.r = r
        self.c = c

    # Turn handler for the player.
    def handle_turn(self, dungeon: dungeon.dungeon, actor_map: list, player):
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
            dmg = float("inf")
        else:
            dmg = 0
        actor_map[self.r][self.c] = None
        actor_map[new_r][new_c] = self
        self.r = new_r
        self.c = new_c
        dungeon.calc_dist_maps(new_r, new_c)

        # For combat dialog
        return a, dmg


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
        # Declaring a character to represent this monster in the dungeon
        # This is a temporary setup, as monsters will have custom definitions in the future
        if 0 <= attributes < 10:
            self.char = str(attributes)
        elif attributes == 10:
            self.char = "A"
        elif attributes == 11:
            self.char = "B"
        elif attributes == 12:
            self.char = "C"
        elif attributes == 13:
            self.char = "D"
        elif attributes == 14:
            self.char = "E"
        elif attributes == 15:
            self.char = "F"
        else:
            self.char = "!"

    # Returns True if the monster has the given attribute, False otherwise.
    def has_attribute(self, attr: int) -> bool:
        return (self.attributes & attr) != 0

    # Adds a given attribute to the monster.
    def add_attribute(self, attr: int):
        self.attributes |= attr

    # Determines if the monster can be at this position.
    def _valid_pos(self, dungeon: dungeon.dungeon, r: int, c: int):
        if dungeon.valid_point(r, c):
            if (
                dungeon.rmap[r][c] == 0
                or self.has_attribute(self._ATTR_TUNNEL_____)
                or self.has_attribute(self._ATTR_PASS_______)
            ):
                return True
        return False

    # Determines if the monster has a line of sight to the player; returns True if so, False otherwise.
    def _has_pc_los(self, dungeon: dungeon.dungeon, player: player) -> bool:
        dest_r, dest_c = player.get_pos()
        curr_r, curr_c = self.get_pos()
        diff_r = abs(dest_r - curr_r)
        diff_c = abs(dest_c - curr_c)
        step_dir_r = 0 if curr_r == dest_r else (1 if curr_r < dest_r else -1)
        step_dir_c = 0 if curr_c == dest_c else (1 if curr_c < dest_c else -1)
        error = diff_c - diff_r

        # Scan from the monster's position, moving towards the player's location.
        while True:
            # Check if there is rock in the way
            if dungeon.rmap[curr_r][curr_c] > 0:
                # Rock is in the way; no line of sight, so return False.
                return False

            # Check if scan has reached the player
            if curr_r == dest_r and curr_c == dest_c:
                # Reached the player; so line of sight established and return True.
                return True

            # Iterate towards the PC
            e2 = 2 * error
            if e2 > -diff_r:
                error -= diff_r
                curr_c += step_dir_c

            if e2 < diff_c:
                error += diff_c
                curr_r += step_dir_r

    # Calculates a straightline path to the player character.
    def _calc_straight_path(self, dungeon: dungeon.dungeon, player: player):
        # Note: this method ignores if the monster is a tunneler or not.
        dest_r, dest_c = self.get_pos()
        curr_r, curr_c = player.get_pos()
        diff_r = abs(dest_r - curr_r)
        diff_c = abs(dest_c - curr_c)
        step_dir_r = 0 if dest_r == curr_r else (1 if dest_r > curr_r else -1)
        step_dir_c = 0 if dest_c == curr_c else (1 if dest_c > curr_c else -1)
        error = diff_c - diff_r
        # dist is to give the path a useful weight to use when deciding where to go
        dist = 0
        # Init path to 'infinite' weight at every point; slow, but prevents multiple paths overlapping if LOS broken and regained
        self.path = [[float("inf")] * dungeon.width for _ in range(dungeon.height)]

        # Scan from the player's position, moving towards the monster's location.
        while True:
            # Update the path for distance from player
            self.path[curr_r][curr_c] = dist

            if curr_r == dest_r and curr_c == dest_c:
                # Reached the monster's position; stop here
                break

            # Iterate towards the monster
            e2 = 2 * error
            if e2 > -diff_r:
                error -= diff_r
                curr_c += step_dir_c

            if e2 < diff_c:
                error += diff_c
                curr_r += step_dir_r

            dist += 1

    # Handles an actor at a target location.
    def _handle_target_actor(
        self, dungeon: dungeon.dungeon, actor_map: list, dest_r: int, dest_c: int
    ) -> int:
        # First determine if the targeted actor is a monster or the player character.
        a = actor_map[dest_r][dest_c]
        if isinstance(a, player):
            # Attack player
            # For now, this is just an instant kill.
            a.kill()
            actor_map[dest_r][dest_c] = None
            # This will eventually return the damage dealt to the player character.
            return 100
        else:
            # displace monster (push them to another spot, or minimally swap places)
            delta_r = [-1, -1, -1, 0, 0, 1, 1, 1]
            delta_c = [-1, 0, 1, -1, 1, -1, 0, 1]

            # Attempt to randomly displace
            for _ in range(8):
                idx = random.randint(0, 7)
                new_r = dest_r + delta_r[idx]
                new_c = dest_c + delta_c[idx]
                if (
                    (dungeon.valid_point(new_r, new_c))
                    and (actor_map[new_r][new_c] != None)
                    and a._valid_pos(dungeon, new_r, new_c)
                ):
                    # New point works; move the monster to the new positions
                    # Move the targeted monster
                    actor_map[new_r][new_c] = a
                    a.r = new_r
                    a.c = new_c
                    # Move the targeting monster
                    actor_map[dest_r][dest_c] = self
                    self.r = dest_r
                    self.c = dest_c
                    # Done; return no damage dealt.
                    return 0

            # If make it to here, then random displacement failed; default to basic position swap.
            actor_map[self.r][self.c] = a
            a.r = self.r
            a.c = self.c
            actor_map[dest_r][dest_c] = self
            self.r = dest_r
            self.c = dest_c
            # Done; return no damage dealt.
            return 0

    # Handles moving monster, once target position found.
    def _move_handeler(
        self, dungeon: dungeon.dungeon, actor_map: list, new_r: int, new_c: int
    ):
        # Move the monster, handling whatever actor may be there
        a = actor_map[new_r][new_c]
        if a != None:
            # Call the handler for targeting another actor
            dmg = self._handle_target_actor(dungeon, actor_map, new_r, new_c)
        else:
            dmg = 0  # to have a return value
            # Check if there is rock in the way
            if dungeon.rmap[new_r][new_c] != 0:
                hardness = dungeon.rmap[new_r][new_c]
                if self.has_attribute(self._ATTR_TUNNEL_____):
                    # Bore rock
                    hardness = max(0, hardness - 86)
                    dungeon.rmap[new_r][new_c] = hardness
                if hardness < 1 or self.has_attribute(self._ATTR_PASS_______):
                    # Rock has been cleared and/or monster can pass through
                    dungeon.tmap[new_r][new_c] = dungeon.terrain.floor
                    # Update the actor map + position information
                    actor_map[self.r][self.c] = None
                    actor_map[new_r][new_c] = self
                    self.r = new_r
                    self.c = new_c
            else:
                # No actor, no rock in the way; so move into new location
                # Update the actor map + position information
                actor_map[self.r][self.c] = None
                actor_map[new_r][new_c] = self
                self.r = new_r
                self.c = new_c
        # Return actor + damage dealt for combat messages
        return a, dmg

    # Monster moves in a random direction.
    def _random_move(self, dungeon: dungeon.dungeon, actor_map: list):
        move = self._move(random.randint(0, 7))
        new_r, new_c = self.target_pos(move)
        # Check that new position is valid for the monster to be at
        # Repeat until this is the case
        while not self._valid_pos(dungeon, new_r, new_c):
            move = self._move(random.randint(0, 7))
            new_r, new_c = self.target_pos(move)
        a, dmg = self._move_handeler(dungeon, actor_map, new_r, new_c)
        # Return actor + damage dealt for combat messages
        return a, dmg

    # Monster moves based on its path.
    def _path_move(self, dungeon: dungeon.dungeon, actor_map: list):
        # Definine the min cost to be infinite to start
        min_cost = float("inf")
        minc_pt_idx = None
        # Find minimum cost point in surrounding 8
        for pt_idx in range(8):
            # Grabs the new point
            new_r, new_c = self.target_pos(self._move(pt_idx))
            if dungeon.valid_point(new_r, new_c):
                cost = self.path[new_r][new_c]
                if cost < min_cost:
                    # Better, so overwrite minimum cost point
                    min_cost = cost
                    minc_pt_idx = pt_idx

        # Error handeling; In theory, this shouldn't happen. My logic is broken somewhere such that this is an incredibly rare problem.
        if minc_pt_idx == None:
            # No min cost point was found; so don't move anywhere.
            minc_pt_idx = 8

        # Now attempt to move to that minimum cost point
        new_r, new_c = self.target_pos(self._move(minc_pt_idx))
        a, dmg = self._move_handeler(dungeon, actor_map, new_r, new_c)
        # Return actor + damage dealt for combat messages
        return a, dmg

    # Updates the monster's path, depending on the attributes that it has.
    # Returns True on a successful path update, False otherwise.
    def _update_path(self, dungeon: dungeon.dungeon, player: player) -> bool:
        # Check if monster is intelligent
        if self.has_attribute(self._ATTR_INTELLIGENT):
            # Check if monster is a telepath
            if self.has_attribute(self._ATTR_TELEPATHIC_):
                # Monster is intelligent and telepathic; thus, it should get a full distance map; not a copy.
                # Check if monster is a tunneling monster to determine which it should get.
                if self.has_attribute(self._ATTR_TUNNEL_____):
                    # Tunneler, get tunneling distance map.
                    self.path = dungeon.tunn_distmap
                    return True
                else:
                    # Not a tunneler, get walking distance map.
                    self.path = dungeon.walk_distmap
                    return True
            else:
                # Monster is intelligent, but not telepathic. Need to check for line of sight.
                if self._has_pc_los(dungeon, player):
                    # Has line of sight, so need to check which distance map monster should recieve a copy of.
                    # Also: Copy instead of direct assignment to emmulate 'memory' of last PC sighting.
                    if self.has_attribute(self._ATTR_TUNNEL_____):
                        self.path = copy.deepcopy(dungeon.tunn_distmap)
                        return True
                    else:
                        self.path = copy.deepcopy(dungeon.walk_distmap)
                        return True
        else:
            if self.has_attribute(self._ATTR_TELEPATHIC_):
                # Monster is telepathic, but not intelligent. Will need to calculate a straightline path.
                self._calc_straight_path(dungeon, player)
                return True
            else:
                # Monster is not telepathic, nor intelligent. Will need to check line of sight.
                if self._has_pc_los(dungeon, player):
                    self._calc_straight_path(dungeon, player)
                    return True
                # If there is not any line of sight, then no changes.
        return False

    # Turn handler for this monster.
    def handle_turn(self, dungeon: dungeon.dungeon, actor_map: list, player):
        # Update the monster's path.
        if self._update_path(dungeon, player):
            if self.has_attribute(self._ATTR_ERRATIC____) and random.randint(0, 1) > 0:
                # Erratic attribute triggered
                a, dmg = self._random_move(dungeon, actor_map)
            else:
                # Move based on path
                a, dmg = self._path_move(dungeon, actor_map)
        else:
            # Path update failure indicates that the monster should move randomly
            a, dmg = self._random_move(dungeon, actor_map)
        # Return actor + damage dealt for combat messages
        return a, dmg
