import random
import copy
from utility import PriorityQueue
from enum import Enum
from utility import exp_chancetime
from collections import deque

# This file is to handle all functions that deal with the dungeon itself.

min_room_h = 3
min_room_w = 4
max_rock_hardness = 255

class dungeon:

    # Enum to dictate the terrain types of a dungeon
    class terrain(Enum):
        debug = 0
        floor = 1
        stair = 2
        stdrock = 3
        immrock = 4

    # Classes to store individual room information
    class room:
        # Room Constructor
        def __init__(self, origin_r, origin_c, rsize_h, rsize_w):
            self.origin_r = origin_r
            self.origin_c = origin_c
            self.rsize_h = rsize_h
            self.rsize_w = rsize_w

    # Class to store individual staircase information
    class staircase:
        # Staircase Constructor
        def __init__(self, r, c):
            self.r = r
            self.c = c
            # True = up, False = down; Here in case I decide to make that matter
            self.direction = True

    # Simple class to queue different points in Dijkstra's algorithm
    class dpoint:
        def __init__(self, r, c, w):
            self.r = r
            self.c = c
            self.w = w
            self.prev = None

        def __lt__(self, other):
            return self.w < other.w

        def __eq__(self, other):
            return (self.r, self.c) == (other.r, other.c)

        def __hash__(self):
            return hash((self.r, self.c))

    # Dungeon Constructor
    def __init__(self, size_h, size_w):
        # Size of the dungeon
        self.height = size_h
        self.width = size_w
        # Counts of rooms / stairs
        self.roomc = 0
        self.room_list = []
        self.stairc = 0
        self.stair_list = []
                                
        # Declaring the rock hardness map (used in terrain generation, pathfinding calculations)
        self.rmap = [[0] * self.width for _ in range(self.height)]
        # Declaring the terrain map for the dungeon
        self.tmap = [[self.terrain.debug] * self.width for _ in range(self.height)]
        # Declare walking and tunneling distance maps used in monster pathfinding
        self.walk_distmap = [[float('inf')] * self.width for _ in range(self.height)]
        self.tunn_distmap = [[float('inf')] * self.width for _ in range(self.height)]

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

    # Attempts to place a staircase
    def _place_stair(self, staircase):
        if (
            self.valid_point(staircase.r, staircase.c)
            and self.tmap[staircase.r][staircase.c] == self.terrain.floor
        ):
            self.tmap[staircase.r][staircase.c] = self.terrain.stair
            return True
        else:
            return False

    # Generates dungeon rock hardness map, necessary for Dijkstra path generation + NPC pathfinding
    def _generate_rockmap(self):
        # Step 1: Initialize immutable outer border to 255
        for r in range(self.height):
            for c in range(self.width):
                if r == 0 or c == 0 or r == self.height - 1 or c == self.width - 1:
                    self.rmap[r][c] = max_rock_hardness
                else:
                    self.rmap[r][c] = 0  # Explicitly clear previous runs if any

        # Step 2: Generate one random origin for each rock hardness level (1–254, 0 reserved for floor & 255 is immutable rock)
        rock_origins = [
            (random.randint(1, self.height - 2), random.randint(1, self.width - 2))
            for _ in range(max_rock_hardness - 1)
        ]

        # Step 3: BFS propagation from each origin with decaying hardness
        for rlev in range(1, max_rock_hardness):
            origin_r, origin_c = rock_origins[rlev - 1]
            queue = deque()
            queue.append((origin_r, origin_c, rlev))

            while queue:
                r, c, hardness = queue.popleft()

                # Skip out-of-bounds or immutable
                if not (1 <= r < self.height - 1 and 1 <= c < self.width - 1):
                    continue

                # If this cell is unset or the new hardness is higher (stronger rock), update
                if self.rmap[r][c] == 0 or hardness > self.rmap[r][c]:
                    self.rmap[r][c] = hardness

                    # Spread to neighbors with decayed hardness (min = 1)
                    if hardness > 1:
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            queue.append((r + dr, c + dc, hardness - 1))

    # Creates a corridor between point 1 and point 2
    # Utilizing dijkstra's algoritm over the rockmap
    def _dijkstra_corridor(self, r1, c1, r2, c2):
        pq = PriorityQueue()
        visited = set()
        pmap = {}

        # Initialize starting point
        start = self.dpoint(r1, c1, 0)
        pq.push(start, 0)
        pmap[(r1, c1)] = start

        # 4 Surrounding points in cardinal directions
        delta_r = [0, -1, 1, 0]
        delta_c = [-1, 0, 0, 1]

        # Repeatedly pop points until queue is empty
        while len(pq) > 0:
            _, curr = pq.pop()

            # Check if point has already been visited; ignore if so
            if (curr.r, curr.c) in visited:
                continue
            visited.add((curr.r, curr.c))

            if curr.r == r2 and curr.c == c2:
                # Reached destination; trace back path
                p = curr
                while p and (p.r != r1 or p.c != c1):
                    if self.tmap[p.r][p.c] == self.terrain.debug:
                        self.tmap[p.r][p.c] = self.terrain.floor
                        self.rmap[p.r][p.c] = 0
                    p = p.prev
                return

            # Itterate through surrounding points of curr
            for dr, dc in zip(delta_r, delta_c):
                nr, nc = curr.r + dr, curr.c + dc
                # Check that point is valid and unvisited; otherwise ignore
                if not self.valid_point(nr, nc) or (nr, nc) in visited:
                    continue

                cost = self.rmap[nr][nc] + 1
                new_dist = curr.w + cost
                neighbor = pmap.get((nr, nc))

                # Evaluate neighbor point
                if neighbor is None:
                    # Ungenerated in pmap, so creating and pushing to queue
                    neighbor = self.dpoint(nr, nc, new_dist)
                    neighbor.prev = curr
                    pmap[(nr, nc)] = neighbor
                    pq.push(neighbor, new_dist)
                elif new_dist < neighbor.w:
                    # Neighbor weight is better through curr, so update and decrease key
                    neighbor.w = new_dist
                    neighbor.prev = curr
                    pq.decrease_key(neighbor, new_dist)

    # Generates the dungeon rooms, cooridors, and staircases (terrain)
    # Cannot be called before generating the rockmap
    def _generate_terrain(self):
        # Creating rooms; at least 1
        attemptc = 0  # To keep track of the number of room placement attempts
        attempt_limit = max(self.width, self.height) * 10
        # print(attempt_limit, "attempt limit on room placement")
        min_roomc = max(1, attempt_limit // 100)  # arbitrary; at least a few
        # print(min_roomc, "Minimum rooms")
        # Attempts either self.width or self.height times, whichever is smaller
        while (self.roomc < min_roomc) or (attemptc < attempt_limit):
            new_room = self.room(
                (random.randint(1, self.height - 1)),
                (random.randint(1, self.width - 1)),
                (random.randint(min_room_h, self.height // 2)),
                (random.randint(min_room_w, self.width // 2)),
            )
            if self.roomc <= min_roomc:
                if self._place_room(new_room):
                    self.roomc += 1
                    self.room_list.append(new_room)
            elif exp_chancetime(self.roomc - min_roomc + 1):
                if self._place_room(new_room):
                    self.roomc += 1
                    self.room_list.append(new_room)
            attemptc += 1
        # print(attemptc, "Room placement attempts made")
        # print(len(self.room_list), "Rooms successfully placed")

        # Now create corridors between rooms
        for i in range(len(self.room_list)):
            room1 = self.room_list[i]
            if i == (self.roomc - 1):
                # i at end of array; grab first entry
                room2 = self.room_list[0]
            else:
                room2 = self.room_list[i + 1]

            r1 = random.randint(room1.origin_r, room1.origin_r + room1.rsize_h - 1)
            c1 = random.randint(room1.origin_c, room1.origin_c + room1.rsize_w - 1)
            r2 = random.randint(room2.origin_r, room2.origin_r + room2.rsize_h - 1)
            c2 = random.randint(room2.origin_c, room2.origin_c + room2.rsize_w - 1)
            self._dijkstra_corridor(r1, c1, r2, c2)

        # Create staircases in dungeon
        attempt_limit = self.roomc * 4
        min_stairc = max(1, self.roomc // 2)
        attemptc = 0
        while (self.stairc < min_stairc) or (attemptc < attempt_limit):
            stair = self.staircase(
                random.randint(1, self.height - 1), random.randint(1, self.width - 1)
            )
            if self.stairc <= min_stairc:
                if self._place_stair(stair):
                    self.stairc += 1
            elif exp_chancetime(self.stairc - min_stairc + 1):
                if self._place_stair(stair):
                    self.stairc += 1
            # self.stairc += 1 # Remove line when staircase placement is actually implemented
            attemptc += 1

        # Fill in remaining terrain as rock
        for r in range(self.height):
            for c in range(self.width):
                if self.valid_point(r, c):
                    if self.tmap[r][c] == self.terrain.debug:
                        self.tmap[r][c] = self.terrain.stdrock
                else:
                    self.tmap[r][c] = self.terrain.immrock

    # Calculates distance from point via walking using Dijkstra's algorithm.
    def _calc_walk_distmap(self, r, c):
        pq = PriorityQueue()
        visited = set()
        pmap = {}

        # Initialize starting point
        start = self.dpoint(r, c, 0)
        self.walk_distmap[r][c] = 0
        pq.push(start, 0)
        pmap[(r, c)] = start

        # All 8 surrounding points, including diagonal
        delta_r = [-1, -1, -1, 0, 0, 1, 1, 1]
        delta_c = [-1, 0, 1, -1, 1, -1, 0, 1]

        # Repeatedly pop points until queue is empty
        while len(pq) > 0:
            _, curr = pq.pop()

            # Check if point has already been visited; ignore if so
            if ((curr.r, curr.c) in visited) or self.rmap[curr.r][curr.c] != 0:
                continue
            visited.add((curr.r, curr.c))

            # Itterate through surrounding points of curr
            for dr, dc in zip(delta_r, delta_c):
                nr, nc = curr.r + dr, curr.c + dc
                # Check that point is valid and unvisited; otherwise ignore
                if (
                    not self.valid_point(nr, nc)
                    or (nr, nc) in visited
                    or self.rmap[nr][nc] != 0
                ):
                    continue

                new_dist = curr.w + 1
                neighbor = pmap.get((nr, nc))

                # Evaluate neighbor point
                if neighbor is None:
                    # Ungenerated in pmap, so creating and pushing to queue
                    neighbor = self.dpoint(nr, nc, new_dist)
                    neighbor.prev = curr
                    pmap[(nr, nc)] = neighbor
                    self.walk_distmap[nr][nc] = new_dist
                    pq.push(neighbor, new_dist)
                elif new_dist < neighbor.w:
                    # Neighbor weight is better through curr, so update and decrease key
                    neighbor.w = new_dist
                    self.walk_distmap[nr][nc] = new_dist
                    neighbor.prev = curr
                    pq.decrease_key(neighbor, new_dist)

    # Calculates distance from point via any movement using Dijkstra's algorithm.
    def _calc_tunn_distmap(self, r, c):
        pq = PriorityQueue()
        visited = set()
        pmap = {}

        # Initialize starting point
        start = self.dpoint(r, c, 0)
        self.tunn_distmap[r][c] = 0
        pq.push(start, 0)
        pmap[(r, c)] = start

        # All 8 surrounding points, including diagonal
        delta_r = [-1, -1, -1, 0, 0, 1, 1, 1]
        delta_c = [-1, 0, 1, -1, 1, -1, 0, 1]

        # Repeatedly pop points until queue is empty
        while len(pq) > 0:
            _, curr = pq.pop()

            # Check if point has already been visited; ignore if so
            if ((curr.r, curr.c) in visited):
                continue
            visited.add((curr.r, curr.c))

            # Itterate through surrounding points of curr
            for dr, dc in zip(delta_r, delta_c):
                nr, nc = curr.r + dr, curr.c + dc
                # Check that point is valid and unvisited; otherwise ignore
                if (
                    not self.valid_point(nr, nc)
                    or (nr, nc) in visited
                ):
                    continue
                
                # 85 will be the amount that a tunneling monster can 'drill' per turn; i.e., the amount it can reduce hardness
                new_dist = curr.w + (self.rmap[nr][nc] // 85) + 1
                neighbor = pmap.get((nr, nc))

                # Evaluate neighbor point
                if neighbor is None:
                    # Ungenerated in pmap, so creating and pushing to queue
                    neighbor = self.dpoint(nr, nc, new_dist)
                    neighbor.prev = curr
                    pmap[(nr, nc)] = neighbor
                    self.tunn_distmap[nr][nc] = new_dist
                    pq.push(neighbor, new_dist)
                elif new_dist < neighbor.w:
                    # Neighbor weight is better through curr, so update and decrease key
                    neighbor.w = new_dist
                    self.tunn_distmap[nr][nc] = new_dist
                    neighbor.prev = curr
                    pq.decrease_key(neighbor, new_dist)

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
                if self.rmap[r][c] == 0:
                    print(" ", end="")
                elif self.rmap[r][c] == max_rock_hardness:
                    print("X", end="")
                else:
                    print(self.rmap[r][c] % 10, end="")

            print("")  # Newline for end of row

    # Method to show walking distance map in console
    def print_walk_distmap(self):
        for r in range(self.height):
            for c in range(self.width):
                if self.walk_distmap[r][c] == 0:
                    print('\033[94m@\033[0m', end="")
                elif self.rmap[r][c] == max_rock_hardness:
                    print("X", end="")
                elif (self.walk_distmap[r][c] == float('inf')):
                    print(" ", end="")
                else:
                    print(self.walk_distmap[r][c] % 10, end="")

            print("")  # Newline for end of row

    # Method to show tunneling distance map in console
    def print_tunn_distmap(self):
        for r in range(self.height):
            for c in range(self.width):
                if self.tunn_distmap[r][c] == 0:
                    print('\033[94m@\033[0m', end="")
                elif self.rmap[r][c] == max_rock_hardness:
                    print("X", end="")
                elif (self.tunn_distmap[r][c] == float('inf')):
                    print(" ", end="")
                else:
                    print(self.tunn_distmap[r][c] % 10, end="")

            print("")  # Newline for end of row

    # Calculates the distance maps from specified point
    def calc_dist_maps(self, r, c):
        self._calc_walk_distmap(r, c)
        self._calc_tunn_distmap(r, c)

    # Generates a random dungeon
    def generate_dungeon(self):
        self._generate_rockmap()
        self._generate_terrain()
        return