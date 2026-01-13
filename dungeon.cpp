#include "dungeon.h"

#include <endian.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <cmath>

#include "actor.h"
#include "darray.h"
#include "heap.h"
#include "utility.h"

// Globally storing array for rock hardness map
uint8_t rockMap[HEIGHT][WIDTH];

// Arrays for storing the distance from player
uint8_t walkingDist[HEIGHT][WIDTH];    // For standard enemies
uint8_t tunnelingDist[HEIGHT][WIDTH];  // For tunneling enemies

uint16_t roomc;  // room count
darray *rooms;   // dynamic array for rooms

uint16_t ustairc;  // up staircase count
darray *ustairs;   // store up stair locations
uint16_t dstairc;  // down staircase count
darray *dstairs;   // store down stair locations

// Maps for dungeon + actors + objects
terrain_t dmap[HEIGHT][WIDTH];
actor_c *amap[HEIGHT][WIDTH];
object_c *omap[HEIGHT][WIDTH];

// Allowing access to Player Character
player_c *player_character;
heap_t turnh;  // heap for keeping track of turns between monsters and PC

int pc_view_dist;

darray *monList;  // Dynamic array for monsters
uint16_t nummon;  // Number of monsters

// vector for listing objects
std::vector<object_c *> objList;
uint16_t numobj;

uint32_t score;

static void update_pc_mem();

// Comparator for point struct
static int32_t compare_point(const void *key, const void *with) {
    return ((point *)key)->cost - ((point *)with)->cost;
}

// comparator for actor (PC/Monsters) struct
static int32_t compare_actor_c(const void *key, const void *with) {
    int32_t tmp = ((actor_c *)key)->currTurn - ((actor_c *)with)->currTurn;
    if (tmp) {
        return tmp;  // no tie
    } else if (((actor_c *)key)->a > 255) {
        return -1;  // pc should have advantage
    } else if (((actor_c *)with)->a > 255) {
        return 1;  // pc should have advantage
    } else {
        return ((actor_c *)key)->speed -
               ((actor_c *)with)->speed;  // Tiebreaker
    }
}

// Gives a chance for something; exponentialy less likely the larger the itter
static int expChanceTime(int itter, double decayRate) {
    double probability = exp(-decayRate * itter);  // Exponential decay
    if ((double)rand() / RAND_MAX < probability) {
        return 1;  // yes
    } else {
        return 0;  // no
    }
}

// Chance used for PC dodging attacks. Larger n, more likely to dodge.
// will approach a maximum of only about 50% to make it fair.
static bool dodgeChance(uint32_t n) {
    int k = 40;  // tweakable; larger k means slower rise in probability
    double probability = 0.5 * static_cast<double>(n) / (n + k);
    double roll = static_cast<double>(rand()) / RAND_MAX;  // random [0.0, 1.0]
    return roll < probability;
}

// reduces a base damage by the given defense value; 0% at 1, ~100% at 600
static int defenseReduction(double baseValue, double scalingValue) {
    if (scalingValue <= 1)
        return static_cast<int>(std::ceil(baseValue));  // No reduction
    if (scalingValue >= 600) return 0;                  // Full reduction

    double reductionFraction =
        (scalingValue - 1) / (600 - 1);  // Scale between 0 and 1
    double reducedValue = baseValue * (1.0 - reductionFraction);

    return static_cast<int>(std::ceil(reducedValue));
}

// Determines if point (r, c) is within map boundry (inside immutable border)
// Does not determine if point is in rock or on floor.
int validPoint(uint16_t r, uint16_t c) {
    if (r < 1 || c < 1 || r > HEIGHT - 2 || c > WIDTH - 2) {
        // out of usable bounds
        return 0;
    } else {
        return 1;
    }
}

// Generates the rock hardness map
static void generate_RockMap() {
    int rlev, pass, i, j;    // loop control
    int r, c, r2, pc2, nc2;  // map coordinates
    // store the starting locale for each sector of rock hardness;
    // rock hardness from 0-3, followed by origin row and column
    int rockOrigin[ROCK_LEVELS]
                  [2];  // 2 hardcoded; pretty sure this is staying 2d

    // create outer edge as maximum hardness; immutable
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (i == 0 || i == HEIGHT - 1 || j == 0 || j == WIDTH - 1) {
                rockMap[i][j] = ROCK_LEVELS;
            } else {
                rockMap[i][j] =
                    0;  // just doing this for now; later it will be randomized
            }
        }
    }

    // create origin points for each rock hardness group
    for (int i = 1; i < (ROCK_LEVELS); i++) {
        r = (rand() % (HEIGHT - 4)) +
            2;  // randomize row between immutable edges
        c = (rand() % (WIDTH - 4)) +
            2;  // randomize column between immutable edges
        rockMap[r][c] = i % ROCK_LEVELS;
        rockOrigin[i][0] = r;
        rockOrigin[i][1] = c;
    }

    // gradually grow each rock type one character outward at a time
    // one type will not overwrite if another rock has already claimed a given
    // spot. outter loop is the passes that all rocks attempt to grow outward by
    // 1. inner loop is the rock types taking turns attempting to expand via
    // manhattan expansion
    for (pass = 1; pass <= WIDTH; pass++) {
        // itterate through rock types
        for (rlev = 1; rlev < (ROCK_LEVELS); rlev++) {
            // getting start point
            r = rockOrigin[rlev][0];
            c = rockOrigin[rlev][1];
            // now expand outward (via Manhattan expansion) to attempt to extend
            // rock's area i => distance from origin; r2 => new row coordinate;
            // c2 => new col coordinate
            for (i = 1; i <= pass; i++) {
                for (j = -i; j <= i; j++) {
                    // get new coordinates
                    r2 = r + j;
                    pc2 = c + (i - abs(j));  // positive column coordinate
                    nc2 = c - (i - abs(j));  // negative column coordinate
                    // check point on right (positive) side
                    if (r2 > 0 && r2 < HEIGHT - 1 && pc2 > 0 &&
                        pc2 < WIDTH - 1) {
                        if (!rockMap[r2][pc2]) {
                            rockMap[r2][pc2] = rlev % ROCK_LEVELS;
                        }
                    }
                    // check point on left (negative) side
                    if (r2 > 0 && r2 < HEIGHT - 1 && nc2 > 0 &&
                        nc2 < WIDTH - 1) {
                        if (!rockMap[r2][nc2]) {
                            rockMap[r2][nc2] = rlev % ROCK_LEVELS;
                        }
                    }
                }
            }
        }
    }
}

// Attempts to insert a staircase at a given point in dungeon map
// returns 0 on success, 1 on fail
// up = '<'; down = '>'
static int insertStair(uint8_t r, uint8_t c, char dir) {
    staircase s;
    s.loc[0] = r;
    s.loc[1] = c;
    // validate that point given is valid and dir is a valid staircase char
    if (validPoint(r, c) && (dir == '<' || dir == '>')) {
        // check that point is either in room or in a corridor
        if (dmap[r][c] == floor_room || dmap[r][c] == floor_corridor) {
            // Place stair then store location data
            if (dir == '<') {
                dmap[r][c] = stair_up;
                darray_add(ustairs, &s);
            } else {
                dmap[r][c] = stair_down;
                darray_add(dstairs, &s);
            }
            return 0;
        }
    }
    return 1;
}

// Attempts to place a room at given row r, column c.
// Returns 0 if success, 1 if failure.
static int createRoom(room room) {
    int i, j;

    // Temporary maps
    terrain_t ttmpMap1[HEIGHT][WIDTH];
    uint8_t itmpMap2[HEIGHT][WIDTH];

    // check that spot is not already a room
    if (dmap[room.origin[0]][room.origin[1]]) {
        return 1;
    }
    // creating copy of maps to easily revert changes
    memcpy(ttmpMap1, dmap, sizeof(dmap));
    memcpy(itmpMap2, rockMap, sizeof(rockMap));

    // Attempt to create room point by point until reaching specified size
    for (i = room.origin[0]; i < room.origin[0] + room.size[0]; i++) {
        for (j = room.origin[1]; j < room.origin[1] + room.size[1]; j++) {
            if (!validPoint(i, j)) {
                // out of bounds; failure to build room at specified location
                return 1;
            } else if (ttmpMap1[i + 1][j] || ttmpMap1[i][j + 1] ||
                       ttmpMap1[room.origin[0] - 1][j] ||
                       ttmpMap1[i][room.origin[1] - 1]) {
                // room is either going to be adjacent to another room, or run
                // into another room
                return 1;
            } else {
                // claiming for room
                ttmpMap1[i][j] = floor_room;
                itmpMap2[i][j] = 0;
            }
        }
    }
    // Save room; dynamic array version
    darray_add(rooms, &room);

    memcpy(dmap, ttmpMap1, sizeof(ttmpMap1));
    memcpy(rockMap, itmpMap2, sizeof(itmpMap2));
    return 0;
}

// Draws a corridor between two points (c1, r1) -> (c2, r2)
// Utilizes Dijkstra's algorithm to follow rock hardness map
static void drawCorridorDijkstra(uint8_t r1, uint8_t c1, uint8_t r2,
                                 uint8_t c2) {
    heap_t h;
    uint8_t i, j;
    uint8_t sr, sc;
    uint8_t nr,
        nc;  // tmp for new row and new column when checking 8 adjacent points
    point parr[HEIGHT][WIDTH], *p;

    // initializing everything to 'infinite' cost
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            parr[i][j].loc[0] = i;
            parr[i][j].loc[1] = j;
            parr[i][j].cost = INT_MAX;
        }
    }

    // cost to get to point from point is zero
    parr[r1][c1].cost = 0;

    // initialize heap
    heap_init(&h, compare_point, NULL);
    // now add all points to heap
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (validPoint(i, j)) {
                parr[i][j].hn = heap_insert(&h, &parr[i][j]);
            } else {
                // point in immutable rock; does not get inserted into heap
                parr[i][j].hn = NULL;
            }
        }
    }

    // These are the coordinate deltas for 4 adjacent coordinates from a given
    // point
    int dr[] = {0, -1, 1, 0};  // delta row
    int dc[] = {-1, 0, 0, 1};  // delta column

    // now pop off heap until it is empty
    while ((p = (point *)heap_remove_min(&h))) {
        p->hn = NULL;

        // Check if we've reached desired point (c2, r2)
        if ((p->loc[0] == r2) && (p->loc[1] == c2)) {
            for (i = r2, j = c2; (i != r1) || (j != c1);
                 p = &parr[i][j], i = p->prev[0], j = p->prev[1]) {
                if (!dmap[i][j]) {
                    // this spot is not floor
                    dmap[i][j] = floor_corridor;  // label as corridor
                    rockMap[i][j] = 0;            // hardness 0
                }
            }
            heap_delete(&h);
        }

        // itterate through the coordinate deltas in dr and dc
        for (i = 0; i < 8; i++) {
            sr = p->loc[0];          // row for point pulled off heap
            sc = p->loc[1];          // col for point pulled off heap
            nr = p->loc[0] + dr[i];  // Row modified with delta
            nc = p->loc[1] + dc[i];  // Col modified with delta

            // This checks two things: a) p is not immutable and b) cost for new
            // point is lower via p
            if ((parr[nr][nc].hn) &&
                (parr[nr][nc].cost > p->cost + rockMap[sr][sc] + 1)) {
                parr[nr][nc].cost = p->cost + rockMap[sr][sc] +
                                    1;  // update cost in point struct  array
                parr[nr][nc].prev[0] = sr;  // update source row
                parr[nr][nc].prev[1] = sc;  // update source column
                heap_decrease_key_no_replace(
                    &h, parr[nr][nc].hn);  // update new points position in heap
            }
        }
    }

    // Destory the heap; should be done with it now
    heap_delete(&h);
}

// Creates the PC actor, placing it into the dynamic array for actors.
static int create_PC(uint8_t r, uint8_t c) {
    if (player_character) {
        // update location
        player_character->loc[0] = r;
        player_character->loc[1] = c;
        player_character->currTurn = 0;
        // reset player memory
        memset(&player_character->mem_dungeon, rock_std,
               sizeof(player_character->mem_dungeon));
    } else {
        player_character = new player_c(r, c);
        pc_view_dist = 3;
    }
    // init values
    player_character->hn = heap_insert(&turnh, player_character);
    amap[r][c] = player_character;
    update_pc_mem();
    return 0;
}

// Generates dungeon with rooms, corridors, and staircases; Do not call before
// 'generate_RockMap'.
void generate_Dungeon() {
    // rooms cannot be overlapping or adjacent; must have 1 cell of non-room
    // between them (rock, corridor, whatever)
    int i, j;
    uint8_t r1, c1, r2, c2;  // row, col corrdinate
    uint8_t tmp;
    room room;
    roomc = ustairc = dstairc = 0;  // initialize room count to 0

    memset(dmap, debug,
           sizeof(dmap));  // ensure the dungeon map is empty to start
    generate_RockMap();    // create the dungeon's rockmap

    // destroy dynamic arrays if initialized
    if (rooms) {
        darray_destroy(rooms);
    }
    if (ustairs) {
        darray_destroy(ustairs);
    }
    if (dstairs) {
        darray_destroy(dstairs);
    }

    // initialize dynamic arrays
    darray_init(&rooms,
                sizeof(struct room));  // struct room simply because I didn't
                                       // want to rename local variable
    darray_init(&ustairs, sizeof(staircase));
    darray_init(&dstairs, sizeof(staircase));

    // initialize the turn heap
    heap_init(&turnh, compare_actor_c, NULL);

    // Generate rooms; minimally runs until there are the minimum number rooms,
    // then 25 chances at an additional room Each room after minimum is
    // exponentially less likely, so the total number won't exceed minimum by
    // much (in theory)
    for (i = 1; i < 25 || roomc < MIN_ROOMC;) {
        // generate random corrdinate
        room.origin[0] = rand() % (HEIGHT - 2) + 1;
        room.origin[1] = rand() % (WIDTH - 2) + 1;
        room.size[0] = rand() % ((HEIGHT - room.origin[0]) / 2) +
                       MIN_ROOM_HEIGHT;  // randomize room height
        room.size[1] = rand() % ((WIDTH - room.origin[1]) / 2) +
                       MIN_ROOM_WIDTH;  // randomize room width
        if (roomc < MIN_ROOMC) {
            // always attempt when less than 6 rooms
            if (!createRoom(room)) {
                roomc++;
            }
        } else if (expChanceTime(roomc, 0.5)) {
            // passed chanceTime; attempt to create room
            if (!createRoom(room)) {
                roomc++;
            }
            i++;
        }
    }

    // Connect rooms with corridors; picks random point in room 1 and room 2,
    // connects them directly. Corridors might overlapp with rooms (not
    // visually) or with other corridors.
    for (i = 0; i < roomc; i++) {
        // Point in room 1
        darray_at(rooms, i, &room);
        r1 = room.origin[0] + (rand() % (room.size[0] - 1));
        c1 = room.origin[1] + (rand() % (room.size[1] - 1));
        // Point in room 2
        if (i == (roomc - 1)) {
            // i at end of array; look at first entry
            darray_at(rooms, 0, &room);
            r2 = room.origin[0] + (rand() % (room.size[0] - 1));
            c2 = room.origin[1] + (rand() % (room.size[1] - 1));
        } else {
            // look at room after i
            darray_at(rooms, i + 1, &room);
            r2 = room.origin[0] + (rand() % (room.size[0] - 1));
            c2 = room.origin[1] + (rand() % (room.size[1] - 1));
        }

        if (validPoint(r1, c1) && validPoint(r2, c2)) {
            drawCorridorDijkstra(r1, c1, r2, c2);
        } else {
            printf("Path Issue: (%d, %d) to (%d, %d)\n", r1, c1, r2,
                   c2);  // debugging print; shouldn't ever come up
        }
    }

    // Now generate staircases; Guarantees one down, one up, with decreasing
    // chance for additional stairs. Attempts to place staircases at random
    // points until it has 100 failed attempts, or until both 1 up and 1 down
    // are placed.
    for (i = 0; i < 25 || ustairc < 1 || dstairc < 1; i++) {
        r1 = rand() % (HEIGHT - 2) + 1;
        c1 = rand() % (WIDTH - 2) + 1;
        if (ustairc < 1) {
            // we need an up staircase
            if (!insertStair(r1, c1, '<')) {
                ustairc++;
            }
        } else if (dstairc < 1) {
            // we need a down staircase
            if (!insertStair(r1, c1, '>')) {
                dstairc++;
            }
        } else if (expChanceTime(dstairc + ustairc, 0.6)) {
            tmp = rand() % 2;  // randomize stair direction
            if (tmp == 0) {
                if (!insertStair(r1, c1, '<')) {
                    ustairc++;
                }
            } else {
                if (!insertStair(r1, c1, '>')) {
                    dstairc++;
                }
            }
        }
    }

    // fill in remainder of dungeon with rock
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (i == 0 || i == HEIGHT - 1 || j == 0 || j == WIDTH - 1) {
                dmap[i][j] = rock_immutable;
            } else if (dmap[i][j] == debug) {
                dmap[i][j] = rock_std;
            }
        }
    }

    // randomly place player character; runs until valid spot found
    tmp = 0;
    while (!tmp) {
        r1 = rand() % (HEIGHT - 2) + 1;
        c1 = rand() % (WIDTH - 2) + 1;
        if (dmap[r1][c1] != rock_std && dmap[r1][c1] != rock_immutable) {
            create_PC(r1, c1);
            // create actor intance for PC; add to dynamic array
            tmp = 1;  // exit loop
        }
    }
}

// Using Dijkstra's algorithm, find the shortest distance to the player
// character from every other point on the map (rooms, corridors, and
// non-immutable rock) This is essentially reverse-engineered from Jeremy
// Sheaffer's Dijkstra path generation.
void calc_tunneldist() {
    heap_t h;
    uint8_t i, j;
    uint8_t nr,
        nc;  // tmp for new row and new column when checking 8 adjacent points
    point parr[HEIGHT][WIDTH], *p;

    // start location is wherever the player character is
    uint8_t sr = player_character->loc[0];
    uint8_t sc = player_character->loc[1];

    // initializing everything to 'infinite' cost
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            parr[i][j].loc[0] = i;
            parr[i][j].loc[1] = j;
            parr[i][j].cost = UINT8_MAX;
            tunnelingDist[i][j] = UINT8_MAX;
        }
    }

    // Cost to get to PC from PC is 0
    parr[sr][sc].cost = 0;
    tunnelingDist[sr][sc] = 0;
    // initialize heap
    heap_init(&h, compare_point, NULL);
    // now add all points to heap
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (validPoint(i, j)) {
                parr[i][j].hn = heap_insert(&h, &parr[i][j]);
            } else {
                // point in immutable rock; does not get inserted into heap
                parr[i][j].hn = NULL;
            }
        }
    }

    // These are the coordinate deltas for 8 surrounding coordinates from a
    // given point
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};  // delta row
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};  // delta column

    // now pop off heap until it is empty
    while ((p = (point *)heap_remove_min(&h))) {
        p->hn = NULL;

        // itterate through the coordinate deltas in dr and dc
        for (i = 0; i < 8; i++) {
            sr = p->loc[0];          // row for point pulled off heap
            sc = p->loc[1];          // col for point pulled off heap
            nr = p->loc[0] + dr[i];  // Row modified with delta
            nc = p->loc[1] + dc[i];  // Col modified with delta

            // This checks two things: a) p is not immutable and b) cost for new
            // point is lower via p
            if ((parr[nr][nc].hn) &&
                (parr[nr][nc].cost > p->cost + (rockMap[sr][sc] / 85) + 1)) {
                parr[nr][nc].cost = p->cost + (rockMap[sr][sc] / 85) +
                                    1;  // update cost in point struct array
                tunnelingDist[nr][nc] =
                    parr[nr][nc].cost;      // update cost in normal int array
                parr[nr][nc].prev[0] = sr;  // update source row
                parr[nr][nc].prev[1] = sc;  // update source column
                heap_decrease_key_no_replace(
                    &h, parr[nr][nc].hn);  // update new points position in heap
            }
        }
    }
    heap_delete(&h);
}

// Using a simplified version of Dijkstra's algorithm, find the shortest
// distance to the player character from every other point in the walkable
// dungeon (rooms and corridors only).
void calc_walkdist() {
    int i;
    heap_t h;
    point parr[HEIGHT][WIDTH], *p;
    uint8_t r, c;
    const uint8_t STEP_COST = 1;  // Cost to step on a walkable tile

    // Get the player's starting position
    uint8_t start_r = player_character->loc[0];
    uint8_t start_c = player_character->loc[1];

    // Initialize distance arrays
    for (r = 0; r < HEIGHT; r++) {
        for (c = 0; c < WIDTH; c++) {
            parr[r][c].loc[0] = r;
            parr[r][c].loc[1] = c;
            parr[r][c].cost = UINT8_MAX;
            walkingDist[r][c] = UINT8_MAX;
        }
    }

    // Set cost to reach player location as 0
    parr[start_r][start_c].cost = 0;
    walkingDist[start_r][start_c] = 0;

    // Initialize heap with comparison function
    heap_init(&h, compare_point, NULL);

    // Add all walkable points (hardness == 0) to the heap
    for (r = 0; r < HEIGHT; r++) {
        for (c = 0; c < WIDTH; c++) {
            if (validPoint(r, c) && rockMap[r][c] == 0) {
                parr[r][c].hn = heap_insert(&h, &parr[r][c]);
            } else {
                parr[r][c].hn = NULL;
            }
        }
    }

    // Deltas for 8-directional movement
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};

    // Process the heap until all reachable points are settled
    while ((p = (point *)heap_remove_min(&h))) {
        p->hn = NULL;

        uint8_t cur_r = p->loc[0];
        uint8_t cur_c = p->loc[1];

        for (i = 0; i < 8; i++) {
            uint8_t new_r = cur_r + dr[i];
            uint8_t new_c = cur_c + dc[i];

            // Bounds and walkability check
            if (validPoint(new_r, new_c) && rockMap[new_r][new_c] == 0 &&
                parr[new_r][new_c].hn &&
                parr[new_r][new_c].cost > p->cost + STEP_COST) {
                parr[new_r][new_c].cost = p->cost + STEP_COST;
                walkingDist[new_r][new_c] = parr[new_r][new_c].cost;
                parr[new_r][new_c].prev[0] = cur_r;
                parr[new_r][new_c].prev[1] = cur_c;
                heap_decrease_key_no_replace(&h, parr[new_r][new_c].hn);
            }
        }
    }

    heap_delete(&h);
}

// boolean check to see if given point has a direct line of sight to the PC.
static int check_PC_los(uint8_t r1, uint8_t c1) {
    uint8_t pcpos[] = {player_character->loc[0], player_character->loc[1]};
    int dc = abs(pcpos[1] - c1);
    int dr = abs(pcpos[0] - r1);
    int sc = (c1 < pcpos[1]) ? 1 : -1;  // Step direction for column
    int sr = (r1 < pcpos[0]) ? 1 : -1;  // Step direction for row
    int err = dc - dr;

    while (1) {
        // check if obstacle in way
        if (dmap[r1][c1] == rock_immutable || dmap[r1][c1] == rock_std ||
            dmap[r1][c1] == debug) {
            return 0;  // No line of sight
        }

        if (r1 == pcpos[0] && c1 == pcpos[1]) {
            return 1;  // there is line of sight
        }

        int e2 = 2 * err;
        if (e2 > -dr) {
            err -= dr;
            c1 += sc;
        }
        if (e2 < dc) {
            err += dc;
            r1 += sr;
        }
    }
}

// Creates path from actor m to player character, drawing a straight line.
static void calc_straightpath(monster_c *m) {
    uint8_t pcpos[] = {player_character->loc[0], player_character->loc[1]};
    uint8_t r1 = m->loc[0];
    uint8_t c1 = m->loc[1];
    int dc = abs(pcpos[1] - c1);
    int dr = abs(pcpos[0] - r1);
    int sc = (c1 < pcpos[1]) ? 1 : -1;  // Step direction for column
    int sr = (r1 < pcpos[0]) ? 1 : -1;  // Step direction for row
    int err = dc - dr;
    uint32_t dist = 1;  // for giving weight to path

    memset(m->mem_path, 0xFF,
           sizeof(m->mem_path));  // Set all values to INT_MAX using memset

    while (1) {
        m->mem_path[r1][c1] = UINT8_MAX - dist;

        if (r1 == pcpos[0] && c1 == pcpos[1])
            break;  // Stop when reaching the endpoint

        int e2 = 2 * err;
        if (e2 > -dr) {
            err -= dr;
            c1 += sc;
        }
        if (e2 < dc) {
            err += dc;
            r1 += sr;
        }
        dist++;
    }
}

// Generates specified number of monsters; if given zero, uses defualt value.
void generate_Monsters(uint16_t count) {
    uint32_t i, desc_idx;
    uint8_t r, c;
    monster_c *m;
    mdesc_c *mdesc;

    // destroy monList if already existing
    if (monList && nummon) {
        // manually delete monsters; darray will not do this
        for (i = 0; i < nummon; i++) {
            darray_at(monList, i, &m);
            delete (m);
        }
        darray_destroy(monList);
    }

    darray_init(&monList, sizeof(monster_c *));  // init monList

    if (!count) {
        nummon = DEFAULT_NUMMON;
    } else {
        nummon = count;
    }

    for (i = 0; i < nummon;) {
        r = rand() % (HEIGHT - 2) + 1;
        c = rand() % (WIDTH - 2) + 1;
        if (dmap[r][c] != rock_std && dmap[r][c] != rock_immutable &&
            amap[r][c] == NULL) {
            // select random monster type
            desc_idx = rand() % num_monster_types;
            // desc_idx = 21;
            mdesc = monster_types[desc_idx];
            // if unique, needs both eligibility requirements. Otherwise we
            // don't care.
            if ((mdesc->gen_eligible[0] && mdesc->gen_eligible[1]) ||
                !(is_uniq(mdesc->abil))) {
                // rarity check
                if (((uint32_t)(rand() % 100) + 1) >= mdesc->rrty) {
                    mdesc->gen_eligible[0] = false;  // set as already present
                    m = new monster_c(r, c, mdesc);
                    m->hn = heap_insert(&turnh, m);
                    darray_add(monList, &m);
                    amap[r][c] = m;
                    i++;
                }
            }
        }
    }
}

// Generates at least MIN_OBJECTS objects in dungeon.
void generate_Objects() {
    uint32_t i, desc_idx;
    uint8_t r, c;
    object_c *o;
    odesc_c *odesc;

    // empty objList if not empty
    if (!(objList.empty()) && numobj) {
        // manually delete objects
        for (i = 0; i < numobj; i++) {
            o = objList[i];
            omap[o->loc[0]][o->loc[1]] = NULL;
            delete (o);
        }
        objList.clear();
    }
    numobj = 0;  // reset the number of objects

    // hardcode 15 objects/dungeon for now; might be randomish later
    for (i = 0; i < 15;) {
        r = rand() % (HEIGHT - 2) + 1;
        c = rand() % (WIDTH - 2) + 1;
        if (dmap[r][c] != rock_std && dmap[r][c] != rock_immutable &&
            amap[r][c] == NULL) {
            // select random monster type
            desc_idx = rand() % num_object_types;
            odesc = object_types[desc_idx];
            // if artifact, needs both eligibility requirements. Otherwise we
            // don't care.
            if ((odesc->gen_eligible[0] && odesc->gen_eligible[1]) ||
                !(odesc->art)) {
                // rarity check
                if (((uint32_t)(rand() % 100) + 1) >= odesc->rrty) {
                    odesc->gen_eligible[0] = false;  // set as already present
                    o = new object_c(r, c, odesc);
                    objList.push_back(o);
                    omap[r][c] = o;
                    numobj++;
                    i++;
                }
            }
        }
    }
}

// attempts to move an actor to given spot. Also handles attacking.
// If given point is rock, the actor will either drill or do nothing.
// If given point has an actor, and PC->Monster or Monster->PC, then targeted
// actor will be attacked. Monster->Monster will lead to pushing target away.
uint8_t actormove(uint8_t r, uint8_t c, actor_c *actor) {
    int tmp;
    actor_c *a2;
    int damage;
    // check if point is valid, and not the existing location for the actor
    if (validPoint(r, c) && !(r == actor->loc[0] && c == actor->loc[1])) {
        // check if actor present in target position
        if (amap[r][c]) {
            a2 = amap[r][c];
            // now check if given actor is PC or Monster
            if (is_pc(actor->a)) {
                // PC->Monster attack; roll through PC's weapons
                damage = 0;
                // rolling all damage die (if item present)
                if (player_character->weapon) {
                    damage += player_character->weapon->damage.roll();
                }
                if (player_character->offhand) {
                    damage += player_character->offhand->damage.roll();
                }
                if (player_character->ranged) {
                    damage += player_character->ranged->damage.roll();
                }
                if (player_character->armor) {
                    damage += player_character->armor->damage.roll();
                }
                if (player_character->helmet) {
                    damage += player_character->helmet->damage.roll();
                }
                if (player_character->cloak) {
                    damage += player_character->cloak->damage.roll();
                }
                if (player_character->gloves) {
                    damage += player_character->gloves->damage.roll();
                }
                if (player_character->boots) {
                    damage += player_character->boots->damage.roll();
                }
                if (player_character->light) {
                    damage += player_character->light->damage.roll();
                }
                if (player_character->ring1) {
                    damage += player_character->ring1->damage.roll();
                }
                if (player_character->ring2) {
                    damage += player_character->ring2->damage.roll();
                }

                if (damage > 0) {
                    a2->hp -= damage;
                } else {
                    a2->hp -= actor->dam.roll();  // fisticuffs
                }
                if (a2->hp <= 0) {
                    // currTurn, speed zero to move to front of heap
                    a2->currTurn = 0;
                    a2->speed = 0;
                    // reorder heap
                    heap_decrease_key_no_replace(&turnh, a2->hn);
                    if (is_uniq(a2->a)) {
                        // if unique type, then mark as ungeneratable.
                        ((monster_c *)a2)->mdesc->gen_eligible[1] = false;
                    }
                    amap[r][c] = NULL;  // remove from visible map
                }
                return 0;
            } else if (is_pc(a2->a)) {
                // Monster->PC attack
                // roll for dodge chance; if unsuccessful dodge, deal damage
                if (!dodgeChance(player_character->dodge)) {
                    // deal damage after player_character's defense reduction
                    a2->hp -= actor->dam.roll() /
                              ((player_character->defense / 10) + 1);
                    a2->hp -= defenseReduction(actor->dam.roll(),
                                               player_character->defense);
                }
                if (a2->hp <= 0) {
                    // currTurn, speed zero to move to front of heap
                    a2->currTurn = 0;
                    a2->speed = 0;
                    // reorder heap
                    heap_decrease_key_no_replace(&turnh, a2->hn);
                    amap[r][c] = NULL;  // remove from visible map
                }
                return 0;
            } else {
                // Monster->Monster
                // This should displace a2 into a neighboring cell
                // Or if no neighboring cell is available, swap actor and a2
                int dr[] = {-1, -1, -1, 0, 0, 0, 1, 1, 1};  // delta row
                int dc[] = {-1, 0, 1, -1, 0, 1, -1, 0, 1};  // delta column
                int new_r, new_c;
                int i = 0;

                // attempt to randomly displace into neighboring cell
                for (i = 0; i < 8; i++) {
                    // attempt random point
                    new_r = a2->loc[0] + dr[rand() % 9];
                    new_c = a2->loc[1] + dc[rand() % 9];
                    if (validPoint(new_r, new_c) && !amap[new_r][new_c] &&
                        dmap[r][c] != rock_std &&
                        dmap[r][c] != rock_immutable && dmap[r][c] != debug) {
                        // move a2 into new point
                        amap[new_r][new_c] = a2;
                        a2->loc[0] = (uint8_t)new_r;
                        a2->loc[1] = (uint8_t)new_c;
                        // place actor where a2 was
                        amap[actor->loc[0]][actor->loc[1]] = NULL;
                        amap[r][c] = actor;
                        actor->loc[0] = r;
                        actor->loc[1] = c;
                        return 0;  // return with success
                    }
                }
                // if here, did not find valid position to push a2 into
                // just swap actor and a2's positions
                new_r = actor->loc[0];
                new_c = actor->loc[1];
                actor->loc[0] = r;
                actor->loc[1] = c;
                amap[r][c] = actor;
                amap[new_r][new_c] = a2;
                a2->loc[0] = new_r;
                a2->loc[1] = new_c;
                return 0;  // return with success
            }
        } else if ((dmap[r][c] == rock_std) && is_tunneler(actor->a)) {
            // Tunneler; attempting to drill
            tmp = rockMap[r][c] - 85;
            if (tmp < 0) {
                // update map with new corridor spot
                rockMap[r][c] = 0;
                dmap[r][c] = floor_corridor;
                // move
                amap[actor->loc[0]][actor->loc[1]] = NULL;
                actor->loc[0] = r;
                actor->loc[1] = c;
                amap[r][c] = actor;
                return 0;
            } else {
                rockMap[r][c] = tmp;
                return 0;
            }
        } else if (dmap[r][c] != rock_std && dmap[r][c] != rock_immutable &&
                   dmap[r][c] != debug) {
            // regular movement; attempt to move
            amap[actor->loc[0]][actor->loc[1]] = NULL;
            actor->loc[0] = r;
            actor->loc[1] = c;
            amap[r][c] = actor;
            return 0;
        }
    }
    return 1;  // failure to move
}

// teleports actor to location as if it were attempting to move there
uint8_t actorteleport(uint8_t r, uint8_t c, actor_c *actor) {
    // check if point is valid, and not the existing location for the actor
    if (validPoint(r, c) && !(r == actor->loc[0] && c == actor->loc[1])) {
        if (dmap[r][c] != rock_immutable && dmap[r][c] != debug) {
            if (amap[r][c]) {
                // INSTAKILL
                amap[r][c]->hp = 0;  // deaded
                amap[r][c]->speed = 0;
                amap[r][c]->currTurn = 0;
                heap_decrease_key_no_replace(&turnh,
                                             amap[r][c]->hn);  // reorder heap
                amap[r][c] = NULL;
            }
            // move
            amap[actor->loc[0]][actor->loc[1]] = NULL;
            actor->loc[0] = r;
            actor->loc[1] = c;
            amap[r][c] = actor;
            update_pc_mem();
            return 0;
        }
    }
    return 1;
}

// random movement for monster m
static void randomMove(monster_c *m) {
    // 03/05/2025; I watched the sunrise while writing this bit. Pain.
    int di, tmp;
    // deltas for 8 surrounding points
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};  // delta row
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};  // delta column
    tmp = 1;

    // go until it's a valid spot; shouldn't run too many times
    while (tmp) {
        di = rand() % 8;
        tmp = actormove(m->loc[0] + dr[di], m->loc[1] + dc[di], m);
    }
}

// Monster makes 1 move based on their path.
static void pathMove(monster_c *m) {
    int i, new_r, new_c;
    uint8_t tmp;
    // minimum cost point in surrounding 8
    uint8_t minp[] = {m->loc[0], m->loc[1]};
    uint8_t min_c = UINT8_MAX;  // associated cost for point
    // deltas for 8 surrounding points
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};  // delta row
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};  // delta column

    // finding minimum cost delta
    for (i = 0; i < 8; i++) {
        new_r = m->loc[0] + dr[i];
        new_c = m->loc[1] + dc[i];

        if (validPoint(new_r, new_c)) {
            tmp = m->mem_path[new_r][new_c];
            if (tmp < min_c) {
                min_c = tmp;
                minp[0] = new_r;
                minp[1] = new_c;
            }
        }
    }

    // attempt move
    actormove((uint8_t)minp[0], (uint8_t)minp[1], m);
}

// Turn handling for given monster
void monster_Turn(monster_c *m) {
    uint8_t erraticChance = rand() % 2;

    // first check for erratic behavior
    if (erraticChance && is_erratic(m->a)) {
        randomMove(m);  // monster is behaving erratically
        return;
    } else {
        // monster is not erratic or behaving erratically
        if (is_intelligent(m->a)) {
            if (is_telepath(m->a)) {
                // monster is a telepath; update their distance map
                if (is_tunneler(m->a)) {
                    // intelligent, telepathic, tunneling
                    memcpy(&m->mem_path, tunnelingDist, sizeof(tunnelingDist));
                } else {
                    // intelligent and telepathic
                    memcpy(&m->mem_path, walkingDist, sizeof(walkingDist));
                }
            } else {
                // non-telepathic; check for line of sight to PC
                // will update, but will not forget
                if (check_PC_los(m->loc[0], m->loc[1])) {
                    // update path based on tunneling ability
                    if (is_tunneler(m->a)) {
                        // intelligent and tunneling
                        memcpy(&m->mem_path, tunnelingDist,
                               sizeof(tunnelingDist));
                    } else {
                        // intelligent
                        calc_straightpath(m);
                    }
                }
            }
        } else {
            if (is_telepath(m->a)) {
                // telepathic; they know where PC is, but are dumb and will just
                // go in a straight line.
                calc_straightpath(m);
            } else if (check_PC_los(m->loc[0], m->loc[1])) {
                calc_straightpath(m);
            } else {
                randomMove(m);
                return;
            }
        }
    }
    // double check that path is initialized before moving based on it
    if (m->mem_path[0][0]) {
        pathMove(m);
    } else {
        randomMove(m);
    }
}

// updates the PC's memory of the dungeon for their current point in said
// dungeon.
static void update_pc_mem() {
    int i, j;
    // Loop through all points within pc_view_dist * pc_view_dist around PC
    for (i = player_character->loc[0] - pc_view_dist;
         i <= player_character->loc[0] + pc_view_dist; i++) {
        for (j = player_character->loc[1] - pc_view_dist;
             j <= player_character->loc[1] + pc_view_dist; j++) {
            // make sure the point is a valid one
            if (validPoint(i, j)) {
                player_character->mem_dungeon[i][j] =
                    dmap[i][j];  // update memory of dungeon
            }
        }
    }
}

// attempts to move the PC one cell, based on specified move.
uint8_t pc_move(a_move m) {
    /*
     * Yes, this returns 1 on success. Non-standard, but I handle user input in
     * a somewhat clunky way, which utilises the the return value here.
     * It is what it is.
     */
    // upleft, up, upright, left, none,right, downleft, down, downright
    int dr[] = {-1, -1, -1, 0, 0, 0, 1, 1, 1};  // delta row
    int dc[] = {-1, 0, 1, -1, 0, 1, -1, 0, 1};  // delta column
    int np[] = {player_character->loc[0] + dr[m],
                player_character->loc[1] + dc[m]};
    uint8_t failure = 0;

    // attempt move
    failure = actormove(np[0], np[1], player_character);
    update_pc_mem();  // update PC's idea of the dungeon
    if (!failure) {
        score++;
        return 1;  // report success
    } else {
        return 0;  // report failure
    }
}

// Writes the generated dungeon to file in binary, big-endian order.
int saveDungeonToFile(char filepath[]) {
    int i, j;
    room r;
    staircase s;
    int data;  // store data converted to big-endian
    FILE *f;
    char ftm[] = "RLG327-S2025";

    f = fopen(filepath, "wb");
    if (f == NULL) {
        perror("Save Failed");  // printing error on fopen;
        return 1;               // fopen had an oopsies
    }
    // write filetype marker (ftm) to begin file
    data = fwrite(&ftm, sizeof(char), 12, f);
    // For simplicity (and my sanity) I'm only going to check succes this one
    // time
    if (!data) {
        perror("Save Failed");
        return 1;
    }

    // File version info; this is just 0 I guess
    data = 0;
    data = htobe32(data);
    // endian-ness shouldn't matter with 0
    fwrite(&data, sizeof(data), 1, f);

    // Writing file size, given count of rooms and staircases
    data = 1708 + (roomc * 4) + (ustairc * 2) + (dstairc * 2);
    data = htobe32(data);
    fwrite(&data, sizeof(uint32_t), 1, f);

    // Writing the coordinates of the player character
    data = player_character->loc[1];
    fwrite(&data, sizeof(char), 1, f);
    data = player_character->loc[0];
    fwrite(&data, sizeof(char), 1, f);

    // Writing rock hardness map to file
    // Given that I'm writing one byte at a time, endian-ness is irrelevent here
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            data = rockMap[i][j];
            fwrite(&data, sizeof(uint8_t), 1, f);
        }
    }

    // Write the number of rooms to file
    data = htobe16(roomc);
    fwrite(&data, sizeof(uint16_t), 1, f);

    // Write room information to file (4 byte each)
    for (int i = 0; i < roomc; i++) {
        // grabbing information for ith room
        darray_at(rooms, i, &r);
        // Write its respective info
        fwrite(&r.origin[1], sizeof(uint8_t), 1, f);  // write origin col
        fwrite(&r.origin[0], sizeof(uint8_t), 1, f);  // write origin row
        fwrite(&r.size[1], sizeof(uint8_t), 1, f);    // write width of room
        fwrite(&r.size[0], sizeof(uint8_t), 1, f);    // write height of room
    }

    // Write number of upward staircases (2 byte)
    data = htobe16(ustairc);
    fwrite(&data, sizeof(uint16_t), 1, f);

    // Write info on upward staircases (pairs of 1 byte)
    for (i = 0; i < ustairc; i++) {
        // re-using variables from rooms; getting coordinates
        darray_at(ustairs, i, &s);
        // Writing coordinates to file
        fwrite(&s.loc[1], sizeof(uint8_t), 1, f);
        fwrite(&s.loc[0], sizeof(uint8_t), 1, f);
    }

    // write number of downward staircases (2 byte)
    data = htobe16(dstairc);
    fwrite(&data, sizeof(uint16_t), 1, f);

    // write info on downward staircases (pairs of 1 byte)
    for (i = 0; i < dstairc; i++) {
        // re-using variables from rooms; getting coordinates
        darray_at(dstairs, i, &s);
        // Writing coordinates to file
        fwrite(&s.loc[1], sizeof(uint8_t), 1, f);
        fwrite(&s.loc[0], sizeof(uint8_t), 1, f);
    }

    // That's all, folks (shoutout loony toons)
    fclose(f);
    return 0;
}

// Reads a dungeon from binary file; populates dungeon.c fields accordingly.
int loadDungeonFromFile(char filepath[]) {
    int i, j;
    room r;
    staircase s;
    char filemarker[13];  // store filemarker at start of file; if valid, it's
                          // 13 char
    int data;             // store read byte(s)
    FILE *f;
    f = fopen(filepath, "rb");
    if (f == NULL) {
        perror("Load Failed");  // printing error on fopen; for testing purposes
        return 1;               // fopen had an oopsies
    }

    // Initialize my dynamic arrays
    darray_init(&rooms, sizeof(room));
    darray_init(&ustairs, sizeof(staircase));
    darray_init(&dstairs, sizeof(staircase));

    // initialize the turn heap
    heap_init(&turnh, compare_actor_c, NULL);

    // Attempt to read filetype header; really just testing that write worked
    // Will only check that read was successful this one time; not worth doing
    // over and over
    data = fread(&filemarker, sizeof(char), 13, f);
    if (!data) {
        perror("Load Failed");
        return 1;
    } else {
        // validate that the filetype header matches
        // yay input validation
        if (strcmp(filemarker, "RLG327-S2025")) {
            printf("filetype header missmatch... ");
            return 1;
        }
    }

    // Read file version; really just skipping 4 bytes here, b/c idk why it's
    // there Note: we read an extra byte to get null byte in file header. Hence,
    // only reading 3 here.
    fread(&data, sizeof(char), 3, f);

    // Read the file size; not sure what exactly I'd want this for at the moment
    fread(&data, 4 * sizeof(char), 1, f);
    data = be32toh(data);
    // printf("File size: %d\n", data);

    // Read player character position (pair of bytes)
    fread(&data, sizeof(char), 1, f);
    i = data;
    fread(&data, sizeof(char), 1, f);
    j = data;
    // placing PC in dungeon
    create_PC(j, i);

    // Read rock hardness map (1 byte per position; 1680 total)
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            fread(&data, sizeof(uint8_t), 1, f);
            rockMap[i][j] = data;
        }
    }

    // Read number of rooms (2 bytes)
    fread(&data, sizeof(uint16_t), 1, f);
    roomc = be16toh(data);

    // Read room information; 4 bytes total for each room
    for (i = 0; i < roomc; i++) {
        // reading room location and size
        fread(&r.origin[1], sizeof(uint8_t), 1, f);
        fread(&r.origin[0], sizeof(uint8_t), 1, f);
        fread(&r.size[1], sizeof(uint8_t), 1, f);
        fread(&r.size[0], sizeof(uint8_t), 1, f);
        // attempting to create room
        createRoom(r);
    }

    // Small intermission from reading; Populate corridors based on
    // zero-hardness My staircase placement method depends on seeing corridor
    // characters to work, So this needs to be done before continuing
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (!dmap[i][j] && !rockMap[i][j]) {
                dmap[i][j] = floor_corridor;
            }
        }
    }

    // Read number of up stair cases; 2 bytes
    fread(&data, sizeof(uint16_t), 1, f);
    ustairc = be16toh(data);

    // Read location of up stair cases; pair of bytes each
    for (i = 0; i < ustairc; i++) {
        fread(&s.loc[1], sizeof(uint8_t), 1, f);
        fread(&s.loc[0], sizeof(uint8_t), 1, f);
        insertStair(s.loc[0], s.loc[1], '<');
    }

    // Read number of down stair cases; 2 bytes
    fread(&data, sizeof(uint16_t), 1, f);
    dstairc = be16toh(data);

    // Read location of down stair cases; pair of bytes each
    for (i = 0; i < dstairc; i++) {
        fread(&s.loc[1], sizeof(uint8_t), 1, f);
        fread(&s.loc[0], sizeof(uint8_t), 1, f);
        insertStair(s.loc[0], s.loc[1], '>');
    }

    // populate remaining dungeon with rock
    // fill in remainder of dungeon with rock
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (i == 0 || i == HEIGHT - 1 || j == 0 || j == WIDTH - 1) {
                dmap[i][j] = rock_immutable;
            } else if (!dmap[i][j]) {
                dmap[i][j] = rock_std;
            }
        }
    }
    update_pc_mem();  // make sure PC's memory is up to date

    // And we're done (yay!)
    fclose(f);
    return 0;
}