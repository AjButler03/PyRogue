#ifndef ACTOR_H
#define ACTOR_H

#include <string>
#include <vector>

#include "dice.h"
#include "utility.h"

// bitfield for monster attributes; 16 bits available
#define ATT_INTELLIGENT 0b0000000000000001  // bit 1  (0000 0000 0000 0001)
#define ATT_TELEPATHIC 0b0000000000000010   // bit 2  (0000 0000 0000 0010)
#define ATT_TUNNEL 0b0000000000000100       // bit 3  (0000 0000 0000 0100)
#define ATT_ERRATIC 0b0000000000001000      // bit 4  (0000 0000 0000 1000)
#define ATT_PASS 0b0000000000010000         // bit 5  (0000 0000 0001 0000)
#define ATT_PICKUP 0b0000000000100000       // bit 6  (0000 0000 0010 0000)
#define ATT_DESTROY 0b0000000001000000      // bit 7  (0000 0000 0100 0000)
#define ATT_UNIQ 0b0000000010000000         // bit 8  (0000 0000 1000 0000)
#define ATT_BOSS 0b0000000100000000         // bit 9  (0000 0001 0000 0000)
#define ATT_PC 0b1000000000000000           // bit 16 (1000 0000 0000 0000)

// bitwise operators to 'add' attributes
#define make_intelligent(a) ((a) |= ATT_INTELLIGENT)
#define make_telepath(a) ((a) |= ATT_TELEPATHIC)
#define make_tunneler(a) ((a) |= ATT_TUNNEL)
#define make_erratic(a) ((a) |= ATT_ERRATIC)
#define make_pass(a) ((a) |= ATT_PASS)
#define make_pickup(a) ((a) |= ATT_PICKUP)
#define make_destroy(a) ((a) |= ATT_DESTROY)
#define make_uniq(a) ((a) |= ATT_UNIQ)
#define make_boss(a) ((a) |= ATT_BOSS)
#define make_pc(a) ((a) |= ATT_PC)

// bitwise true/false check the attributes
#define is_intelligent(a) ((a) & ATT_INTELLIGENT)
#define is_telepath(a) ((a) & ATT_TELEPATHIC)
#define is_tunneler(a) ((a) & ATT_TUNNEL)
#define is_erratic(a) ((a) & ATT_ERRATIC)
#define is_pass(a) ((a) & ATT_PASS)
#define is_pickup(a) ((a) & ATT_PICKUP)
#define is_destroy(a) ((a) & ATT_DESTROY)
#define is_uniq(a) ((a) & ATT_UNIQ)
#define is_boss(a) ((a) & ATT_BOSS)
#define is_pc(a) ((a) & ATT_PC)

// distance that the PC can see in the dungeon.
extern int pc_view_dist;

// Forward referencing these
class mdesc_c;
class odesc_c;

// These store the monster & object types after parsing desc files
// really ugly solution to sharing where its needed
// these are defined officially in parsedesc.cpp
extern std::vector<mdesc_c *> monster_types;
extern std::vector<odesc_c *> object_types;
extern uint32_t num_monster_types;
extern uint32_t num_object_types;

typedef enum object_type {
    objtype_no_type,
    objtype_WEAPON,
    objtype_OFFHAND,
    objtype_RANGED,
    objtype_LIGHT,
    objtype_ARMOR,
    objtype_HELMET,
    objtype_CLOAK,
    objtype_GLOVES,
    objtype_BOOTS,
    objtype_AMULET,
    objtype_RING,
    objtype_SCROLL,
    objtype_BOOK,
    objtype_FLASK,
    objtype_GOLD,
    objtype_AMMUNITION,
    objtype_FOOD,
    objtype_WAND,
    objtype_CONTAINER
} object_type_t;

// storing description of monster types
class mdesc_c {
   public:
    std::string name;
    std::string desc;
    uint8_t desc_line_c;
    uint32_t color;
    uint16_t abil;
    bool boss;  // this is a separate bool b/c I'm lazy
    dice speed;
    dice hp;
    dice dam;
    char symb;
    uint32_t rrty;
    // this next field is purely for unique monster tracking
    // (false/true) 0 => (in/notin dungeon), 1 => (dead/notdead)
    bool gen_eligible[2];

    mdesc_c();
    ~mdesc_c() {};
};

class odesc_c {
   public:
    std::string name, desc;
    uint8_t desc_line_c;
    uint32_t color;
    object_type_t type;
    dice hit, damage, dodge, defense, weight, speed, attribute, value;
    bool art;
    uint32_t rrty;
    // this next field is purely for artifact tracking
    // (false/true) 0 => (in/notin dungeon), 1 => (destroyed/notdestroyed)
    bool gen_eligible[2];
    char symb;

    odesc_c();
    ~odesc_c() {};
};

class object_c {
    public:
     uint8_t loc[2];
     uint32_t hit, dodge, defense, weight, speed, attribute, value, rrty;
     bool art;
     dice damage;
     char symb;
     uint32_t color;
     odesc_c *odesc;

     object_c(uint8_t r, uint8_t c, odesc_c *desc);
     ~object_c() {};
};

class actor_c {
   protected:
    virtual ~actor_c() {};

   public:
    uint16_t a;
    uint8_t loc[2];
    uint32_t color;
    int32_t speed;
    int32_t hp;
    dice dam;
    char symb;
    uint16_t currTurn;
    heap_node_t *hn;
};

class monster_c : public actor_c {
   public:
    monster_c(uint8_t r, uint8_t c, mdesc_c *desc);
    ~monster_c() {};
    mdesc_c *mdesc;
    uint8_t mem_path[HEIGHT][WIDTH];
};

class player_c : public actor_c {
   public:
    player_c(uint8_t r, uint8_t c);
    ~player_c();
    int32_t defense;
    int32_t dodge;
    terrain_t mem_dungeon[HEIGHT][WIDTH];
    // player inventory / equipment
    object_c *weapon;
    object_c *offhand;
    object_c *ranged;
    object_c *armor;
    object_c *helmet;
    object_c *cloak;
    object_c *gloves;
    object_c *boots;
    object_c *amulet;
    object_c *light;
    object_c *ring1;
    object_c *ring2;
    object_c *carry_slot[10];
};

#endif