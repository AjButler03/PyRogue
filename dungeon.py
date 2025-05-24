import random
import copy
import math
from enum import Enum
from utility import exp_chancetime

min_room_h = 3
min_room_w = 4


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
        def __init__(self, origin_r, origin_c, rsize_h, rsize_w):
            self.origin_r = origin_r
            self.origin_c = origin_c
            self.rsize_h = rsize_h
            self.rsize_w = rsize_w

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
        self.rmap = [[0] * self.width for _ in range(self.height)]
        # Declaring the terrain map for the dungeon
        self.tmap = [[self.terrain.debug] * self.width for _ in range(self.height)]

    # Boolean function; checks if point is within immutable outer border of dungeon
    def valid_point(self, r, c):
        if (r < 1) or (c < 1) or (r > self.height - 2) or (c > self.width - 2):
            return False
        else:
            return True

    # Attempts to place a room into the dungeon terrain map
    def _place_room(self, room):
        r = room.origin_r
        c = room.origin_c
        last_r = r + room.rsize_h
        last_c = c + room.rsize_w

        if self.tmap[r][c] == self.terrain.floor:
            # Room origin conflicts with another room
            return False

        # copy of the terrain & rock maps to easily revert changes if room cannot be placed
        rmap_copy = copy.deepcopy(self.rmap)
        tmap_copy = copy.deepcopy(self.tmap)

        while r < last_r:
            c = room.origin_c
            while c < last_c:
                if not self.valid_point(r, c):
                    # Out of bounds
                    return False
                elif (
                    tmap_copy[r + 1][c] == self.terrain.floor
                    or tmap_copy[r][c + 1] == self.terrain.floor
                    or tmap_copy[room.origin_r - 1][c] == self.terrain.floor
                    or tmap_copy[r][room.origin_c - 1] == self.terrain.floor
                ):
                    # Room is either going to be adjacent to another room, or run into another room
                    return False
                else:
                    # Claim as room cell on dungeon maps
                    tmap_copy[r][c] = self.terrain.floor
                    rmap_copy[r][c] = 0
                c += 1
            r += 1

        # No issue occured; Update master copy of maps and return success
        self.rmap = copy.deepcopy(rmap_copy)
        self.tmap = copy.deepcopy(tmap_copy)
        return True

    # Generates dungeon rock hardness map, necessary for Dijkstra path generation + NPC pathfinding
    def _generate_rockmap(self):
        # This can probably be optimized later. Hop to it, later me.
        # Storing the origin points for rock hardness levels
        rock_origin = [[0, 0] for _ in range(255)]

        # Marking immutable border
        r = 0
        while r < self.height:
            c = 0
            while c < self.width:
                if (
                    (r == 0)
                    or (c == 0)
                    or (r == self.height - 1)
                    or (c == self.width - 1)
                ):
                    self.rmap[r][c] = 255
                c += 1
            r += 1

        # Create origin points for every rock level
        rocklevel = 0
        while rocklevel < 255:
            rock_origin[rocklevel][0] = random.randint(2, self.height - 3)
            rock_origin[rocklevel][1] = random.randint(2, self.width - 3)
            rocklevel += 1

        # Now gradually expand each rock level outward one by one
        expansion_pass = 0
        num_passes = max(self.width, self.height)
        while expansion_pass < num_passes:
            rlev = 1
            while rlev < 255:
                r = rock_origin[rlev][0]
                c = rock_origin[rlev][1]

                # Now do Manhattan expansion
                i = 1
                while i <= expansion_pass:
                    j = -i
                    while j <= i:
                        r2 = r + j
                        pc2 = c + (i - abs(j))  # positive column coordinate
                        nc2 = c - (i - abs(j))  # negative column coordinate

                        # check point on right (positive) side
                        if (
                            r2 > 0
                            and r2 < self.height - 1
                            and pc2 > 0
                            and pc2 < self.width - 1
                        ):
                            if self.rmap[r2][pc2] == 0:
                                self.rmap[r2][pc2] = rlev

                        # check point on left (negative) side
                        if (
                            r2 > 0
                            and r2 < self.height - 1
                            and nc2 > 0
                            and nc2 < self.width - 1
                        ):
                            if self.rmap[r2][nc2] == 0:
                                self.rmap[r2][nc2] = rlev
                        j += 1
                    i += 1
                rlev += 1
            expansion_pass += 1

    # Generates the dungeon rooms, cooridors, and staircases (terrain)
    # Cannot be called before generating the rockmap
    def _generate_terrain(self):
        # Creating rooms; at least 1
        attemptc = 0  # To keep track of the number of room placement attempts
        attempt_limit = min(self.width, self.height)
        min_roomc = attempt_limit // 3
        # Right now it's just hardcoded to attempt 25 times (at least one success), but that could be changed later.
        while (self.roomc < min_roomc) or (attemptc < attempt_limit):
            new_room = self.room(
                (random.randint(1, self.height - 1)),
                (random.randint(1, self.width - 1)),
                (random.randint(min_room_h, self.height // 2)),
                (random.randint(min_room_w, self.width // 2)),
            )
            if self.roomc < min_roomc:
                if self._place_room(new_room):
                    self.roomc += 1
            elif exp_chancetime(self.roomc - min_roomc + 1):
                if self._place_room(new_room):
                    self.roomc += 1
            attemptc += 1

    # Method to show terrain in console
    def print_terrain(self):
        for r in range(self.height):
            for c in range(self.width):
                t_type = self.tmap[r][c]
                if t_type == self.terrain.floor:
                    print(".", end="")
                elif t_type == self.terrain.stair:
                    print("<", end="")
                elif t_type == self.terrain.stdrock:
                    print(" ", end="")
                elif t_type == self.terrain.immrock:
                    print("X", end="")  # will want to be a proper border later
                else:
                    print("!", end="")  # issue flag

            print("")  # Newline for end of row

    # Method to show rock hardness map in console
    def print_rockmap(self):
        for r in range(self.height):
            for c in range(self.width):
                print(self.rmap[r][c] % 10, end="")

            print("")  # Newline for end of row

    # Generates a random dungeon
    def generate_dungeon(self):
        self._generate_rockmap()
        self._generate_terrain()
        return


def main():
    d = dungeon(20, 80)
    d.generate_dungeon()
    d.print_terrain()
    d.print_rockmap()


if __name__ == "__main__":
    main()
