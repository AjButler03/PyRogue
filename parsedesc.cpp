#include "parsedesc.h"

#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>
#include <ncurses.h>
std::vector<mdesc_c *> monster_types;
std::vector<odesc_c *> object_types;
uint32_t num_monster_types;
uint32_t num_object_types;

// garbage function; but getting custom color working
static uint32_t color_lookup(std::string s){
    if (s == "BLACK"){
        return COLOR_WHITE;
    } else if (s == "RED"){
        return COLOR_RED;
    } else if (s == "GREEN"){
        return COLOR_GREEN;
    } else if (s == "YELLOW"){
        return COLOR_YELLOW;
    } else if (s == "BLUE"){
        return COLOR_BLUE;
    } else if (s == "CYAN"){
        return COLOR_CYAN;
    } else if (s == "MAGENTA"){
        return COLOR_MAGENTA;
    } else {
        return COLOR_WHITE;
    }
}


// Reads monster descriptions from file, storing for generating monsters later.
uint8_t parse_monsters() {
    // bools to make sure all fields were specified
    bool name, desc, color, abil, speed, hp, dam, symb, rrty;
    uint32_t temp1, temp2, temp3;
    int fpathlen;
    // char *home;
    char *fpath;
    std::ifstream stream;
    std::string line, tmp;
    mdesc_c *m;
    num_monster_types = 0;
    name = desc = color = abil = speed = hp = dam = symb = rrty = false;

    // creating filepath
    // home = getenv("HOME");
    // fpathlen = strlen(home) + strlen("/.rlg327/monster_desc.txt") +
    //            1;  // +1 for the null byte

    // fpath = (char *)malloc(fpathlen * sizeof(*fpath));
    // if (!fpath) {
    //     // I *should* throw and exception or something here.
    //     printf("Memory allocation (malloc) error. Quitting.\n");
    //     return 1;
    // }
    // strcpy(fpath, home);
    // strcat(fpath, "/.rlg327/monster_desc.txt");

    fpathlen = strlen("monster_desc.txt") + 1;

    fpath = (char *)malloc(fpathlen * sizeof(*fpath));
    if (!fpath) {
        // I *should* throw and exception or something here.
        printf("Memory allocation (malloc) error. Quitting.\n");
        return 1;
    }
    strcpy(fpath, "monster_desc.txt");

    stream.open(fpath, std::ifstream::in);
    if (stream.is_open()) {
        // check that file header matches
        std::getline(stream, line);
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();  // remove carriage return if present
        }

        if (line == "RLG327 MONSTER DESCRIPTION 1") {
            // now we can parse the file
            while (std::getline(stream, line)) {
                if (!line.empty() && line.back() == '\r') {
                    line.pop_back();  // remove carriage return if present
                }

                if (line == "BEGIN MONSTER") {
                    m = new mdesc_c();  // new monster description
                    name = desc = color = abil = speed = hp = dam = symb =
                        rrty = false;
                    while (line != "END") {
                        std::getline(stream, line);
                        if (!line.empty() && line.back() == '\r') {
                            line.pop_back();  // remove carriage return if
                                              // present
                        }

                        if (line.find("NAME") == 0) {
                            m->name = line.substr(5, line.length());
                            name = true;
                        } else if (line.find("DESC") == 0) {
                            while (true) {
                                if (std::getline(stream, line)) {
                                    if (!line.empty() && line.back() == '\r') {
                                        line.pop_back();  // remove carriage
                                                          // return if present
                                    }

                                    if (line == ".") {
                                        break;
                                    } else if (line.length() > 78) {
                                        printf(
                                            "monster_desc.txt desc field too "
                                            "wide (> 77 char); "
                                            "exiting program \n");
                                        return 2;
                                    } else {
                                        m->desc += (line + "\n");
                                        m->desc_line_c++;
                                    }
                                } else {
                                    printf(
                                        "monster_desc.txt desc field invalid; "
                                        "exiting program \n");
                                    return 3;
                                }
                            }
                            desc = true;
                        } else if (line.find("COLOR") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }
                            // icky gross bad way of doing things
                            std::istringstream colorline(line);
                            colorline >> tmp >> tmp;

                            m->color = color_lookup(tmp);

                            color = true;
                        } else if (line.find("ABIL") == 0) {
                            // probably a really dumb way of doing this
                            // checks if ability is specified,
                            // then calls macro to activate bit
                            if (line.find("SMART") != std::string::npos) {
                                make_intelligent(m->abil);
                            }
                            if (line.find("TELE") != std::string::npos) {
                                make_telepath(m->abil);
                            }
                            if (line.find("TUNNEL") != std::string::npos) {
                                make_tunneler(m->abil);
                            }
                            if (line.find("ERRATIC") != std::string::npos) {
                                make_erratic(m->abil);
                            }
                            if (line.find("PASS") != std::string::npos) {
                                make_pass(m->abil);
                            }
                            if (line.find("PICKUP") != std::string::npos) {
                                make_pickup(m->abil);
                            }
                            if (line.find("DESTROY") != std::string::npos) {
                                make_destroy(m->abil);
                            }
                            if (line.find("UNIQ") != std::string::npos) {
                                make_uniq(m->abil);
                            }
                            if (line.find("BOSS") != std::string::npos) {
                                make_boss(m->abil);
                            }
                            abil = true;
                        } else if (line.find("SPEED") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "SPEED %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "monster_desc.txt speed field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            m->speed = dice(temp1, temp2, temp3);
                            speed = true;
                        } else if (line.find("HP") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "HP %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "monster_desc.txt hp field invalid; "
                                    "exiting program \n");
                                return 5;
                            }
                            m->hp = dice(temp1, temp2, temp3);
                            hp = true;
                        } else if (line.find("DAM") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "DAM %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "monster_desc.txt dam field invalid; "
                                    "exiting program \n");
                                return 6;
                            }
                            m->dam = dice(temp1, temp2, temp3);
                            dam = true;
                        } else if (line.find("SYMB") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (line[5]) {
                                m->symb = line[5];
                            } else {
                                printf(
                                    "monster_desc.txt symb field invalid; "
                                    "exiting program \n");
                                return 7;
                            }
                            symb = true;
                        } else if (line.find("RRTY") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "RRTY %u", &m->rrty))) {
                                printf(
                                    "monster_desc.txt rrty field invalid; "
                                    "exiting program \n");
                                return 8;
                            }
                            if (m->rrty > 100) {
                                printf(
                                    "monster_desc.txt rrty field invalid (> "
                                    "100); exiting program \n");
                                return 9;
                            }
                            rrty = true;
                        }
                    }

                    // now save created monster type description
                    if (name && desc && color && abil && speed && hp && dam &&
                        symb && rrty) {
                        m->gen_eligible[0] = true;
                        m->gen_eligible[1] = true;
                        monster_types.push_back(m);  // add to vector
                        num_monster_types++;

                    } else {
                        printf(
                            "monster_desc.txt contains incomplete "
                            "definitions; exiting "
                            "program \n");
                        return 1;
                    }
                }
            }
        } else {
            printf("monster_desc.txt is invalid format; exiting program \n");
            return 1;
        }

    } else {
        printf("Error opening monster_desc.txt; exiting program \n");
        return 1;
    }
    free(fpath);
    return 0;
}

// delete stored monster descriptions (freeing memory)
void delete_mdescriptions() {
    uint32_t i;
    for (i = 0; i < num_monster_types; i++) {
        delete monster_types[i];
    }
}

// Reads object descriptions from file, storing for generating objects later.
uint8_t parse_objects() {
    // bools to make sure all fields were specified
    bool name, desc, color, type, hit, damage, dodge, defence, weight, speed,
        attribute, value, artifact, rrty;
    uint32_t temp1, temp2, temp3;
    int fpathlen;
    char *fpath;
    std::ifstream stream;
    std::string line, tmp;
    odesc_c *o;
    num_object_types = 0;
    name = desc = color = type = hit = damage = dodge = defence = weight =
        speed = attribute = value = artifact = rrty = false;

    // creating filepath
    // home = getenv("HOME");
    // fpathlen = strlen(home) + strlen("/.rlg327/object_desc.txt") +
    //            1;  // +1 for the null byte
    // fpath = (char *)malloc(fpathlen * sizeof(*fpath));
    // if (!fpath) {
    //     // I *should* throw and exception or something here.
    //     printf("Memory allocation (malloc) error. Quitting.\n");
    //     return 1;
    // }
    // strcpy(fpath, home);
    // strcat(fpath, "/.rlg327/object_desc.txt");

    fpathlen = strlen("object_desc.txt") + 1;
    fpath = (char *)malloc(fpathlen * sizeof(*fpath));
    if (!fpath) {
        // I *should* throw and exception or something here.
        printf("Memory allocation (malloc) error. Quitting.\n");
        return 1;
    }
    strcpy(fpath, "object_desc.txt");

    stream.open(fpath, std::ifstream::in);
    if (stream.is_open()) {
        // check that file header matches
        std::getline(stream, line);
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();  // remove carriage return if present
        }

        if (line == "RLG327 OBJECT DESCRIPTION 1") {
            // now we can parse the file
            while (std::getline(stream, line)) {
                if (!line.empty() && line.back() == '\r') {
                    line.pop_back();  // remove carriage return if present
                }

                if (line == "BEGIN OBJECT") {
                    o = new odesc_c();  // new monster description
                    name = desc = color = type = hit = damage = dodge =
                        defence = weight = speed = attribute = value =
                            artifact = rrty = false;
                    while (line != "END") {
                        std::getline(stream, line);
                        if (!line.empty() && line.back() == '\r') {
                            line.pop_back();  // remove carriage return if
                                              // present
                        }

                        if (line.find("NAME") == 0) {
                            o->name = line.substr(5, line.length());
                            name = true;
                        } else if (line.find("DESC") == 0) {
                            while (true) {
                                if (std::getline(stream, line)) {
                                    if (!line.empty() && line.back() == '\r') {
                                        line.pop_back();  // remove carriage
                                                          // return if present
                                    }

                                    if (line == ".") {
                                        break;
                                    } else if (line.length() > 78) {
                                        printf(
                                            "object_desc.txt desc field too "
                                            "wide (> 77 char); "
                                            "exiting program \n");
                                        return 2;
                                    } else {
                                        o->desc += (line + "\n");
                                        o->desc_line_c++;
                                    }
                                } else {
                                    printf(
                                        "object_desc.txt desc field invalid; "
                                        "exiting program \n");
                                    return 3;
                                }
                            }
                            desc = true;
                        } else if (line.find("COLOR") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }
                          // icky gross bad way of doing things
                          std::istringstream colorline(line);
                          colorline >> tmp >> tmp;

                          o->color = color_lookup(tmp);

                          color = true;
                        } else if (line.find("TYPE") == 0) {
                            if (line.find("WEAPON") != std::string::npos) {
                                o->type = objtype_WEAPON;
                                o->symb = '|';
                            } else if (line.find("OFFHAND") !=
                                       std::string::npos) {
                                o->type = objtype_OFFHAND;
                                o->symb = ')';
                            } else if (line.find("RANGED") !=
                                       std::string::npos) {
                                o->type = objtype_RANGED;
                                o->symb = '}';
                            } else if (line.find("LIGHT") !=
                                       std::string::npos) {
                                o->type = objtype_LIGHT;
                                o->symb = '_';
                            } else if (line.find("ARMOR") !=
                                       std::string::npos) {
                                o->type = objtype_ARMOR;
                                o->symb = '[';
                            } else if (line.find("HELMET") !=
                                       std::string::npos) {
                                o->type = objtype_HELMET;
                                o->symb = ']';
                            } else if (line.find("CLOAK") !=
                                       std::string::npos) {
                                o->type = objtype_CLOAK;
                                o->symb = '(';
                            } else if (line.find("GLOVES") !=
                                       std::string::npos) {
                                o->type = objtype_GLOVES;
                                o->symb = '{';
                            } else if (line.find("BOOTS") !=
                                       std::string::npos) {
                                o->type = objtype_BOOTS;
                                o->symb = '\\';
                            } else if (line.find("AMULET") !=
                                       std::string::npos) {
                                o->type = objtype_AMULET;
                                o->symb = '\"';
                            } else if (line.find("RING") != std::string::npos) {
                                o->type = objtype_RING;
                                o->symb = '=';
                            } else if (line.find("SCROLL") !=
                                       std::string::npos) {
                                o->type = objtype_SCROLL;
                                o->symb = '~';
                            } else if (line.find("BOOK") != std::string::npos) {
                                o->type = objtype_BOOK;
                                o->symb = '?';
                            } else if (line.find("FLASK") !=
                                       std::string::npos) {
                                o->type = objtype_FLASK;
                                o->symb = '!';
                            } else if (line.find("GOLD") != std::string::npos) {
                                o->type = objtype_GOLD;
                                o->symb = '$';
                            } else if (line.find("AMMUNITION") !=
                                       std::string::npos) {
                                o->type = objtype_AMMUNITION;
                                o->symb = '/';
                            } else if (line.find("FOOD") != std::string::npos) {
                                o->type = objtype_FOOD;
                                o->symb = ',';
                            } else if (line.find("WAND") != std::string::npos) {
                                o->type = objtype_WAND;
                                o->symb = '-';
                            } else if (line.find("CONTAINER") !=
                                       std::string::npos) {
                                o->type = objtype_CONTAINER;
                                o->symb = '%';
                            } else {
                                // mixing printf and cout b/c anarchy is fun
                                // (I'm lazy)
                                printf("object_desc obj type not recognized\n");
                                std::cout << "Read: \"" << line << "\""
                                          << std::endl;
                                return 4;
                            }
                            type = true;
                        } else if (line.find("HIT") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "HIT %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt hit field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->hit = dice(temp1, temp2, temp3);
                            hit = true;
                        } else if (line.find("DAM") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "DAM %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt dam field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->damage = dice(temp1, temp2, temp3);
                            damage = true;
                        } else if (line.find("DODGE") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "DODGE %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt dodge field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->dodge = dice(temp1, temp2, temp3);
                            dodge = true;
                        } else if (line.find("DEF") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "DEF %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt def field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->defense = dice(temp1, temp2, temp3);
                            defence = true;
                        } else if (line.find("WEIGHT") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "WEIGHT %u+%ud%u",
                                         &temp1, &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt weight field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->weight = dice(temp1, temp2, temp3);
                            weight = true;
                        } else if (line.find("SPEED") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "SPEED %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt speed field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->speed = dice(temp1, temp2, temp3);
                            speed = true;
                        } else if (line.find("ATTR") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "ATTR %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt attr field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->attribute = dice(temp1, temp2, temp3);
                            attribute = true;
                        } else if (line.find("VAL") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "VAL %u+%ud%u", &temp1,
                                         &temp2, &temp3))) {
                                printf(
                                    "object_desc.txt val field invalid; "
                                    "exiting program \n");
                                return 4;
                            }
                            o->value = dice(temp1, temp2, temp3);
                            value = true;
                        } else if (line.find("ART") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }
                            if (line.find("TRUE") != std::string::npos) {
                                o->art = true;
                            } else if (line.find("FALSE") !=
                                       std::string::npos) {
                                o->art = false;
                            } else {
                                printf(
                                    "object_desc.txt art field invalid; "
                                    "exiting program \n");
                                return 5;
                            }
                            artifact = true;
                        } else if (line.find("RRTY") == 0) {
                            if (!line.empty() && line.back() == '\r') {
                                line.pop_back();  // remove carriage return if
                                                  // present
                            }

                            if (!(sscanf(line.c_str(), "RRTY %u", &o->rrty))) {
                                printf(
                                    "object_desc.txt rrty field invalid; "
                                    "exiting program \n");
                                return 8;
                            }
                            if (o->rrty > 100) {
                                printf(
                                    "object_desc.txt rrty field invalid (> "
                                    "100); exiting program \n");
                                return 9;
                            }
                            rrty = true;
                        }
                    }

                    // now save created object type description
                    if (name && desc && color && type && hit && damage &&
                        defence && weight && speed && attribute && value &&
                        artifact && rrty) {
                        o->gen_eligible[0] = true;
                        o->gen_eligible[1] = true;
                        object_types.push_back(o);  // add to vector
                        num_object_types++;
                    } else {
                        printf(
                            "object_desc.txt contains incomplete "
                            "definitions; exiting "
                            "program \n");
                        return 1;
                    }
                }
            }
        } else {
            printf("object_desc.txt is invalid format; exiting program \n");
            return 1;
        }

    } else {
        printf("Error opening object_desc.txt; exiting program \n");
        return 1;
    }
    free(fpath);
    return 0;
}

// delete stored object descriptions (freeing memory)
void delete_odescriptions() {
    uint32_t i;
    for (i = 0; i < num_object_types; i++) {
        delete object_types[i];
    }
}

// resets generation eligibility (case 1, not case 2) for monsters/objects
void reset_gen_elig() {
    uint32_t i;

    for (i = 0; i < num_monster_types; i++) {
        monster_types[i]->gen_eligible[0] = true;
    }
    for (i = 0; i < num_object_types; i++) {
        object_types[i]->gen_eligible[0] = true;
    }
}

// Debug; make sure monster descriptions are correct.
void print_monsters() {
    uint32_t i;
    mdesc_c *m;

    for (i = 0; i < num_monster_types; i++) {
        m = monster_types[i];
        // print name
        std::cout << m->name << std::endl;
        // print description
        std::cout << m->desc;
        // print symbol
        std::cout << m->symb << std::endl;
        // print color(s)
        std::cout << m->color << std::endl;
        // print speed
        std::cout << m->speed.get_base() << "+" << m->speed.get_number() << "d"
                  << m->speed.get_sides() << std::endl;
        // print abilities
        if (is_boss(m->abil)) {
            std::cout << "BOSS ";
        }
        if (is_intelligent(m->abil)) {
            std::cout << "SMART ";
        }
        if (is_telepath(m->abil)) {
            std::cout << "TELE ";
        }
        if (is_tunneler(m->abil)) {
            std::cout << "TUNNEL ";
        }
        if (is_erratic(m->abil)) {
            std::cout << "ERRATIC ";
        }
        if (is_pass(m->abil)) {
            std::cout << "PASS ";
        }
        if (is_pickup(m->abil)) {
            std::cout << "PICKUP ";
        }
        if (is_destroy(m->abil)) {
            std::cout << "DESTROY ";
        }
        if (is_uniq(m->abil)) {
            std::cout << "UNIQ ";
        }
        std::cout << "" << std::endl;
        // print hp
        std::cout << m->hp.get_base() << "+" << m->hp.get_number() << "d"
                  << m->hp.get_sides() << std::endl;
        // print damage
        std::cout << m->dam.get_base() << "+" << m->dam.get_number() << "d"
                  << m->dam.get_sides()

                  << std::endl;
        // print rarity
        std::cout << m->rrty << "\n" << std::endl;
    }
}

// Debug; make sure object descriptions are correct.
void print_objects() {
    uint32_t i;
    odesc_c *o;

    for (i = 0; i < num_object_types; i++) {
        o = object_types[i];
        std::cout << o->name << std::endl;
        std::cout << o->desc;
        // type; lazy to write out right now

        std::cout << o->color << std::endl;
        std::cout << o->hit << std::endl;
        std::cout << o->damage << std::endl;
        std::cout << o->dodge << std::endl;
        std::cout << o->defense << std::endl;
        std::cout << o->weight << std::endl;
        std::cout << o->speed << std::endl;
        std::cout << o->attribute << std::endl;
        std::cout << o->value << std::endl;
        std::cout << o->art << std::endl;
        std::cout << o->rrty << '\n' << std::endl;
    }
    return;
}