#ifndef DUNGEON_H
#define DUNGEON_H

#include "darray.h"
#include "heap.h"
#include "stdint.h"

// rock hardness levels; 0 reserved for rooms/corridors, highest reserved for
// outer boundary
#define ROCK_LEVELS 255  // default 255
// Minimum room size
#define MIN_ROOM_HEIGHT 3  // default 3
#define MIN_ROOM_WIDTH 4   // default 4
#define MIN_ROOMC 6        // default 6
// Default monster count
#define DEFAULT_NUMMON 10  // default 10
#define MIN_OBJECTS 10     // default 10

// Forward referencing this; declared in utility.h
class actor_c;
class monster_c;

typedef enum {
    up_left,
    up,
    up_right,
    left,
    none,
    right,
    down_left,
    down,
    down_right
} a_move;

int validPoint(uint16_t r, uint16_t c);
void generate_Dungeon();                 // generates dungeon
void calc_tunneldist();                  // Dijkstra for tunneling
void calc_walkdist();                    // Dijkstra for walking
void generate_Monsters(uint16_t count);  // generate monsters in dungeon
void generate_Objects();                 // generate objects in dungeon
void monster_Turn(monster_c *m);         // Monster turn to move
uint8_t actorteleport(uint8_t r, uint8_t c, actor_c *actor);
uint8_t pc_move(a_move m);                 // PC turn to move
int saveDungeonToFile(char filepath[]);    // write dungeon to file
int loadDungeonFromFile(char filepath[]);  // read dungeon from file

#endif