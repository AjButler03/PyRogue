#include "actor.h"

#include <ncurses.h>

#include <cstring>

mdesc_c::mdesc_c() {
    name = "";
    desc = "";
    desc_line_c = 0;
    color = 0;
    abil = 0;
    boss = false;
    symb = ' ';
    rrty = 100;
    gen_eligible[0] = true;
    gen_eligible[1] = true;
}

odesc_c::odesc_c() {
    name = "";
    desc = "";
    desc_line_c = 0;
    color = 0;
    type = objtype_no_type;
    art = false;
    rrty = 100;
}

object_c::object_c(uint8_t r, uint8_t c, odesc_c *desc) {
    loc[0] = r;
    loc[1] = c;
    hit = desc->hit.roll();
    dodge = desc->dodge.roll();
    defense = desc->defense.roll();
    weight = desc->weight.roll();
    speed = desc->speed.roll();
    attribute = desc->attribute.roll();
    value = desc->value.roll();
    rrty = desc->rrty;
    this->art = desc->art;
    damage = desc->damage;
    symb = desc->symb;
    color = desc->color;
    odesc = desc;
}

monster_c::monster_c(uint8_t r, uint8_t c, mdesc_c *desc) {
    a = desc->abil;
    loc[0] = r;
    loc[1] = c;
    color = desc->color;
    speed = desc->speed.roll();
    hp = desc->hp.roll();
    dam = desc->dam;
    symb = desc->symb;
    currTurn = 0;
    this->mdesc = desc;
    memset(mem_path, 0x00, sizeof(mem_path));  // init path to all 0
}

player_c::player_c(uint8_t r, uint8_t c) {
    a = ATT_PC;  // designate as PC
    loc[0] = r;
    loc[1] = c;
    color = COLOR_GREEN;
    // speed, hp, and dam are all arbitrary for now.
    speed = 10;
    hp = 200;
    dam = dice(1, 1, 4);
    symb = '@';
    currTurn = 0;
    defense = 10;
    dodge = 10;
    memset(mem_dungeon, rock_std, sizeof(mem_dungeon));  // init dungeon memory

    // set inventory to all NULL
    weapon = offhand = ranged = armor = helmet = cloak = gloves = boots =
        amulet = light = ring1 = ring2 = NULL;
    for (int i = 0; i < 10; i++) {
        carry_slot[i] = NULL;
    }
}

player_c::~player_c() {
    if (weapon){
        delete weapon;
        weapon = NULL;
    }
    if (offhand){
        delete offhand;
        offhand = NULL;
    }
    if (ranged){
        delete ranged;
        ranged = NULL;
    }
    if (armor){
        delete armor;
        armor = NULL;
    }
    if (helmet){
        delete helmet;
        helmet = NULL;
    }
    if (cloak){
        delete cloak;
        cloak = NULL;
    }
    if (gloves){
        delete gloves;
        gloves = NULL;
    }
    if (boots){
        delete boots;
        boots = NULL;
    }
    if (amulet){
        delete amulet;
        amulet = NULL;
    }
    if (light){
        delete light;
        light = NULL;
    }
    if (ring1){
        delete ring1;
        ring1 = NULL;
    }
    if (ring2){
        delete ring2;
        ring2 = NULL;
    }
    for (int i = 0; i < 10; i++){
        if (carry_slot[i]){
            delete carry_slot[i];
            carry_slot[i] = NULL;
        }
    }
}