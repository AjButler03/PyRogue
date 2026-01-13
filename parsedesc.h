#ifndef PARSEDESC_H
#define PARSEDESC_H

#include "actor.h"
#include "darray.h"

/*
 * The purpose of this file is to parse monster and item definitions in
 * monster_desc.txt and object_desc.txt, respectively.
 * These files *should* be located in the home directory of the user running
 * this program. If they are not, the program will automatically exit.
 */

uint8_t parse_monsters();     // parse monsters, placing in vector
void delete_mdescriptions();  // deletes monster descriptions
uint8_t parse_objects();      // parse objects, placing in vector
void delete_odescriptions();  // deletes object descriptions
void reset_gen_elig();  // resets the generation eligibility (only for first
                        // part; not for 'if killed' part)
void print_monsters();  // print monster parse results to console
void print_objects();   // print object parse results to console

#endif