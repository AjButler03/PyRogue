#ifndef UTILITY_H
#define UTILITY_H

#include <vector>

#include "darray.h"
#include "heap.h"

/*
 * This header is to store things that are used in several files, and declaring
 * them in one spot. I assume that this is a technically very ugly solution, but
 * I am of the mindset that if it works, it works.
 */

// Map size
#define HEIGHT 21  // default 21
#define WIDTH 80   // default 80

// forward reference these for use
class actor_c;
class player_c;
class object_c;

// Struct for heap used in Dijkstra's alg
typedef struct point {
    heap_node_t *hn;  // pointer to the heap node of 'this' instance of point
    uint8_t loc[2];   // row, column of point
    uint32_t cost;    // weight
    uint8_t prev[2];  // prev point in path
} point;

// Struct to keep dynamic array of staircases
typedef struct staircase {
    uint8_t loc[2];  // row, column that staircase is at
} staircase;

// Struct to keep dynamic array of rooms + their associated info
typedef struct room {
    uint8_t origin[2];  // Origin coordinate
    uint8_t size[2];    // Room size
} room;

// defining possible terrain types in dungeon
typedef enum {
    debug,
    floor_room,
    floor_corridor,
    rock_std,
    rock_immutable,
    stair_up,
    stair_down
} terrain_t;

// Maps for dungeon + actors + objects; making widely available
extern terrain_t dmap[HEIGHT][WIDTH];
extern actor_c *amap[HEIGHT][WIDTH];
extern object_c *omap[HEIGHT][WIDTH];

// Arrays for storing the distance from player
extern uint8_t walkingDist[HEIGHT][WIDTH];    // For standard enemies
extern uint8_t tunnelingDist[HEIGHT][WIDTH];  // For tunneling enemies

// Allowing access to Player Character
extern player_c *player_character;
extern heap_t turnh;  // heap for keeping track of turns between monsters and PC

// dynamic array for listing monsters
extern darray *monList;
extern uint16_t nummon;

// dynamic array for listing objects
extern std::vector<object_c *> objList;
extern uint16_t numobj;

extern uint32_t score;

#endif