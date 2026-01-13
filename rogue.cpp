#include <ncurses.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <algorithm>

#include "actor.h"
#include "darray.h"
#include "dungeon.h"
#include "heap.h"
#include "parsedesc.h"
#include "utility.h"

uint32_t mcount;
bool fog_toggle;

/*
 * This file essentially handles all the control functionality of the game;
 * user controls, player character inventory management, the main turnloop of
 * the game, and also rendering. This originally wasn't a lot of code, but
 * clearly it ballooned a bit.
 *
 * There is some duplicated code, which is there mainly out of laziness to
 * generalize it.
 *
 * Ideally I guess these functions should also have been split into a few
 * different files. Oh well.
 */

// Defines switches for command line args
void usage(const char *s) {
    fprintf(stderr,
            "Usage: %s [-s|--save]"
            " [-l|--load]"
            " [-n|--nummon <count>]"
            " [-p|--parse]\n",
            s);
    exit(-1);
}

// initialize the ncurses UI
static void init_UI() {
    initscr();             // starts ncurses?
    noecho();              // Hides key inputs (not typing controls)
    curs_set(0);           // Hide text cursor
    keypad(stdscr, TRUE);  // Enables keypad input
    start_color();         // Enables curses color support
    // color pair definitions
    init_pair(COLOR_WHITE, COLOR_WHITE, COLOR_BLACK);      // White   1
    init_pair(COLOR_RED, COLOR_RED, COLOR_BLACK);          // Red     2
    init_pair(COLOR_GREEN, COLOR_GREEN, COLOR_BLACK);      // Green   3
    init_pair(COLOR_YELLOW, COLOR_YELLOW, COLOR_BLACK);    // Yellow  4
    init_pair(COLOR_BLUE, COLOR_BLUE, COLOR_BLACK);        // Blue    5
    init_pair(COLOR_CYAN, COLOR_CYAN, COLOR_BLACK);        // Cyan    6
    init_pair(COLOR_MAGENTA, COLOR_MAGENTA, COLOR_BLACK);  // Magenta 7
}

// draws the main menu screen
static void draw_menu_main(WINDOW *main_pad) {
    int i, j;
    wclear(main_pad);  // clear the window
    // printing dungeon border to stdscr
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (i == 0 && j == 0) {
                mvaddch(i + 1, j, ACS_ULCORNER);
            } else if (i == 0 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_URCORNER);
            } else if (i == HEIGHT - 1 && j == 0) {
                mvaddch(i + 1, j, ACS_LLCORNER);
            } else if (i == HEIGHT - 1 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_LRCORNER);
            } else if (i == 0 || i == HEIGHT - 1) {
                mvaddch(i + 1, j, ACS_HLINE);
            } else if (j == 0 || j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_VLINE);
            }
        }
    }

    attron(COLOR_PAIR(COLOR_RED));
    mvprintw(HEIGHT + 1, 1, "Andrew Butler 2025");
    mvprintw(HEIGHT + 1, WIDTH - 6, "v1.10");
    attroff(COLOR_PAIR(COLOR_RED));

    // cool ASCII art divided into lines so I can easily display it
    // my code formatter garbled it, but it says 'Rogue 327'. 46 char wide.
    const char *line1 =
        "    ____                            ________  _________ ";
    const char *line2 =
        "   / __ \\____  ____ ___  _____     |__  /__ \\/__  / __ \\";
    const char *line3 =
        "  / /_/ / __ \\/ __ `/ / / / _ \\     /_ <__/ /  / / / / /";
    const char *line4 =
        " / _, _/ /_/ / /_/ / /_/ /  __/   ___/ / __/  / / /_/ / ";
    const char *line5 =
        "/_/ |_|\\____/\\__, /\\__,_/\\___/   /____/____/ /_/\\____/  ";
    const char *line6 =
        "            /____/                                      ";

    // Cool ASCII text for fanciness points
    wattron(main_pad, COLOR_PAIR(COLOR_RED));
    wprintw(main_pad, "%s", line1);
    wprintw(main_pad, "%s", line2);
    wprintw(main_pad, "%s", line3);
    wprintw(main_pad, "%s", line4);
    wprintw(main_pad, "%s", line5);
    wprintw(main_pad, "%s", line6);
    wattroff(main_pad, COLOR_PAIR(COLOR_RED));

    wprintw(main_pad, "\n");
    wattron(main_pad, COLOR_PAIR(COLOR_YELLOW));
    wprintw(main_pad, "                      (s) Start Game\n\n");
    wprintw(main_pad, "                      (d) Directions\n\n");
    wprintw(main_pad, "                      (m) Monsters  \n\n");
    wprintw(main_pad, "                      (i) Items     \n\n");
    wprintw(main_pad, "                      (Q) Quit      \n\n");
    wattroff(main_pad, COLOR_PAIR(COLOR_YELLOW));

    refresh();
    prefresh(main_pad, 0, 0, 3, WIDTH / 2 - 28, HEIGHT - 1, WIDTH / 2 + 28);
}

// Draws the story page within the Directions submenu
static void draw_story_page(WINDOW *dir_pad) {
    // cool ASCII art for story page; this says 'STORY'.
    const char *cntrl_line1 = "   ______________  _____  __\n";
    const char *cntrl_line2 = "  / __/_  __/ __ \\/ _ \\ \\/ /\n";
    const char *cntrl_line3 = " _\\ \\  / / / /_/ / , _/\\  / \n";
    const char *cntrl_line4 = "/___/ /_/  \\____/_/|_| /_/  \n";

    // print control ASCII art
    wattron(dir_pad, COLOR_PAIR(COLOR_RED));
    wprintw(dir_pad, "                         %s", cntrl_line1);
    wprintw(dir_pad, "                         %s", cntrl_line2);
    wprintw(dir_pad, "                         %s", cntrl_line3);
    wprintw(dir_pad, "                         %s", cntrl_line4);
    wattroff(dir_pad, COLOR_PAIR(COLOR_RED));
    wprintw(dir_pad, "\n");
    // printing text; I was told the game needed some lore.
    wprintw(dir_pad, " Welcome, travler.\n\n");
    wprintw(dir_pad,
            " You awake in a dimly lit dungeon, not remembering who you are, "
            "and not\n"
            " knowing what to do. In the darkness, you hear shuffling movement "
            "and\n"
            " disgusting, gutteral, animal-like sounds. In the background "
            "there might also\n"
            " be. . . is that right?. . . the childish laughter of Tom Kenny, "
            "but with\n"
            " a chilling malice behind it.\n\n");
    wprintw(dir_pad,
            " You know that you are not safe; it is your job to survive.\n\n");
    wprintw(dir_pad,
            " There are items scattered around the dungeon to help you; these "
            "will be\n"
            " pivotal to your survival. They will increase your speed, your "
            "ability to\n"
            " dodge damage, and you defense against attacks.\n"
            " Without them, you are as good as dead.\n\n");
    wprintw(dir_pad,
            " You have 10 carry slots to pickup and hold these items, and you "
            "have equip\n"
            " slots for weapon, offhand, ranged, armor, helmet, cloak, gloves, "
            "boots,\n"
            " amulet, light, and left & right rings.\n\n");
    wprintw(dir_pad,
            " Know that the dungeon is unforgiving; you never know what lurks "
            "in the\n"
            " darkness, and being caught unprepared is a sure way to die.\n\n");
    wprintw(dir_pad, " Good luck.\n\n");
}

// Draws the controls page within the Directions submenu
static void draw_cntrl_page(WINDOW *dir_pad) {
    // cool ASCII art for controls page; this says 'CONTROLS'.
    const char *cntrl_line1 = "  _________  _  ___________  ____  __   ____\n";
    const char *cntrl_line2 =
        " / ___/ __ \\/ |/ /_  __/ _ \\/ __ \\/ /  / __/\n";
    const char *cntrl_line3 =
        "/ /__/ /_/ /    / / / / , _/ /_/ / /___\\ \\  \n";
    const char *cntrl_line4 =
        "\\___/\\____/_/|_/ /_/ /_/|_|\\____/____/___/  \n";

    // printing the control ASCII art
    wattron(dir_pad, COLOR_PAIR(COLOR_RED));
    wprintw(dir_pad, "                 %s", cntrl_line1);
    wprintw(dir_pad, "                 %s", cntrl_line2);
    wprintw(dir_pad, "                 %s", cntrl_line3);
    wprintw(dir_pad, "                 %s", cntrl_line4);
    wattroff(dir_pad, COLOR_PAIR(COLOR_RED));

    wprintw(dir_pad, "\n");

    // and now the stupidly long controls text
    // movement
    wprintw(dir_pad,
            " ===============================   MOVEMENT   "
            "===============================  7 or y : Attempt to move PC "
            "one cell to the upper left.\n 8 or k : Attempt to move PC one "
            "cell up.\n 9 or u : Attempt to move PC one cell to the upper "
            "right.\n 6 or l : Attempt to move PC one cell to the right.\n 3 "
            "or n : Attempt to move PC one cell to the lower right.\n 2 or j : "
            "Attempt to move PC one cell down.\n 1 or b : Attempt to move PC "
            "one cell to the lower left.\n 4 or h : Attempt to move PC one "
            "cell to the left.\n > : Attempt to go down stairs. Works only if "
            "standing on down staircase.\n < : Attempt to go up stairs. Works "
            "only if standing on up staircase.\n 5 or space or . : Rest for a "
            "turn NPCs still move.\n");

    wprintw(dir_pad, "\n");

    // inventory
    wprintw(dir_pad,
            " ===============================   INVENTORY  "
            "===============================  m : Display a list of monsters "
            "in the dungeon, with their symbol and\n     position relative to "
            "the PC (e.g., \"c, 2 north and 14 west\").\n i : Gives item names "
            "that are in each of the PC's carry slots.\n e : Opens a menu that "
            "lists the item names that are equipped by the PC.\n , : Attempts "
            "to pick up an item that the PC is standing over, placing in\n   "
            "  next available carry slot. Will display message on "
            "success/failure.\n w : Asks for a carry slot, then attempts to "
            "equip the item in that slot.\n t : Aks for an equipment slot, "
            "then attempts move it to carry slot.\n x : Asks for a carry "
            "slot, then attempts to destroy  the specified item.\n d : Asks "
            "for a carry slot, then attempts to drop the specified item.\n");

    wprintw(dir_pad, "\n");

    // information
    wprintw(dir_pad,
            " ===============================  INFORMATION "
            "===============================  L : Enters target mode; 'L' "
            "again shows information about targeted monster.\n I : Asks for "
            "carry slot, then displays information about it.\n");

    wprintw(dir_pad, "\n");

    // cheats
    wprintw(dir_pad,
            " ===============================    CHEATS    "
            "===============================  f : Toggles the 'fog of war' "
            "effect.\n g : Enters teleport mode to allow PC to move across the "
            "map; Pressing 'g'\n     again teleports to cursor location; 'r' "
            "teleports to a random location.\n z : Shows distance maps, or "
            "shows monster's path while inspecting one.\n");

    wprintw(dir_pad, "\n");

    // misc
    wprintw(dir_pad,
            " =============================== MISCELLANOUS "
            "===============================  up arrow : Scrolls menu up, if "
            "scrolling is available / necessary.\n down arrow: Scrolls menu "
            "down, if scrolling is available / necessary.\n esc : Returns to "
            "character control from the various menus.\n Q : Quit to main menu "
            "or quit game.\n\n");
}

// main menu instructions submenu control
static void draw_instructions() {
    WINDOW *dir_pad;
    uint8_t win_h, page, i;
    bool exit;
    char ch;
    // declaring this in one spot so that text changes are easier
    uint8_t story_page_h = 29;
    uint8_t ctrl_page_h = 46;

    exit = false;
    page = i = 0;
    win_h = story_page_h;

    move(HEIGHT + 1, 0);
    clrtoeol();

    dir_pad = newpad(win_h, WIDTH - 2);
    draw_story_page(dir_pad);

    prefresh(dir_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0,
             " Showing directions page %d of 2. Press esc to return to "
             "main menu",
             page + 1);
    mvprintw(HEIGHT + 1, 1,
             "Arrow keys: up & down scroll, left & right change page");
    attroff(COLOR_PAIR(COLOR_YELLOW));
    refresh();

    while (!exit) {
        ch = getch();
        switch (ch) {
            case 2:
                // down arrow; scroll down
                if (i <= win_h - (HEIGHT - 1)) {
                    i++;
                }
                break;
            case 3:
                // up arrow; scroll up
                if (i >= 1) {
                    i--;
                }
                break;
            case 4:
                // left arrow
                if (page >= 1) {
                    page--;
                    i = 0;
                    if (page == 0) {
                        // moved to story page
                        win_h = story_page_h;
                        dir_pad = newpad(win_h, WIDTH - 2);
                        draw_story_page(dir_pad);
                    }
                }
                break;
            case 5:
                // right arrow
                if (page < 1) {
                    page++;
                    i = 0;
                    delwin(dir_pad);  // clear existing page
                    if (page == 1) {
                        // moved to controls page
                        win_h = ctrl_page_h;
                        dir_pad = newpad(win_h, WIDTH - 2);
                        draw_cntrl_page(dir_pad);
                    }
                }
                break;
            case 27:
                // esc key
                exit = true;
                break;
            case 'Q':
                // also let this work, b/c I can
                exit = true;
                break;
            default:
                break;
        }
        prefresh(dir_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
        move(0, 0);
        clrtoeol();
        attron(COLOR_PAIR(COLOR_YELLOW));
        mvprintw(0, 0,
                 " Showing directions page %d of 2. Press esc to return to "
                 "main menu",
                 page + 1);
        attroff(COLOR_PAIR(COLOR_YELLOW));
        refresh();
    }

    wclear(dir_pad);
    delwin(dir_pad);
}

// prints mdesc_c info into pad
static void mdesc_fill_pad(WINDOW *mdesc_pad, mdesc_c *desc) {
    // Writing name
    wprintw(mdesc_pad, "Name: %s\n", desc->name.c_str());
    // writing symbol
    wprintw(mdesc_pad, "Symbol: ");
    wattron(mdesc_pad, COLOR_PAIR(desc->color));
    wprintw(mdesc_pad, "%c\n", desc->symb);
    wattroff(mdesc_pad, COLOR_PAIR(desc->color));
    // print speed
    wprintw(mdesc_pad, "Speed: %d+%dd%d\n", desc->speed.get_base(),
            desc->speed.get_number(), desc->speed.get_sides());
    // print hp
    wprintw(mdesc_pad, "HP: %d+%dd%d\n", desc->hp.get_base(),
            desc->hp.get_number(), desc->hp.get_sides());
    // print damage
    wprintw(mdesc_pad, "Damage: %d+%dd%d\n", desc->dam.get_base(),
            desc->dam.get_number(), desc->dam.get_sides());
    // print abilities
    wprintw(mdesc_pad, "Abilities: ");
    if (is_intelligent(desc->abil)) {
        wprintw(mdesc_pad, "SMART ");
    }
    if (is_telepath(desc->abil)) {
        wprintw(mdesc_pad, "TELE ");
    }
    if (is_tunneler(desc->abil)) {
        wprintw(mdesc_pad, "TUNNEL ");
    }
    if (is_erratic(desc->abil)) {
        wprintw(mdesc_pad, "ERRATIC ");
    }
    // if (is_pass(desc->abil)) {
    //     wprintw(mdesc_pad, "PASS ");
    // }
    // if (is_pickup(desc->abil)) {
    //     wprintw(mdesc_pad, "PICKUP ");
    // }
    // if (is_destroy(desc->abil)) {
    //     wprintw(mdesc_pad, "DESTROY ");
    // }
    if (is_uniq(desc->abil)) {
        wprintw(mdesc_pad, "UNIQ ");
    }
    if (is_boss(desc->abil)) {
        wprintw(mdesc_pad, "BOSS ");
    }
    wprintw(mdesc_pad, "\n");
    // print rarity
    wprintw(mdesc_pad, "Rarity: %d\n", desc->rrty);

    // print description
    wprintw(mdesc_pad, "%s", desc->desc.c_str());
}

// creates screen to cycle through monster descriptions
static void mdesc_list_scr() {
    WINDOW *mdesc_pad;
    mdesc_c *desc;
    uint8_t desc_idx, win_h, i;
    bool exit;
    char ch;

    exit = false;
    desc_idx = i = 0;
    // grabbing first monster description; technically this should check that
    // there are monster descriptions, but oh well
    desc = monster_types[desc_idx];
    win_h = desc->desc_line_c + 7;
    if (win_h < HEIGHT - 2) {
        // Make sure it takes up screen; looks weird if it doesn't
        win_h = HEIGHT - 2;
    }
    move(HEIGHT + 1, 0);
    clrtoeol();
    mdesc_pad = newpad(win_h, 78);
    mdesc_fill_pad(mdesc_pad, desc);
    prefresh(mdesc_pad, 0, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(
        0, 0,
        " Showing monster type %3d of %3d. Press esc to return to main menu",
        desc_idx + 1, num_monster_types);
    mvprintw(HEIGHT + 1, 1,
             "Arrow keys: up & down scroll, left & right change page");
    attroff(COLOR_PAIR(COLOR_YELLOW));
    refresh();

    // down 2, up 3, left 4, right 5
    while (!exit) {
        ch = getch();
        switch (ch) {
            case 2:
                // down arrow; scroll down
                if (i <= win_h - (HEIGHT - 1)) {
                    i++;
                    prefresh(mdesc_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
                    refresh();
                }
                break;
            case 3:
                // up arrow; scroll up
                if (i >= 1) {
                    i--;
                    prefresh(mdesc_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
                    refresh();
                }
                break;
            case 4:
                // left arrow; move to previous mdesc page
                if (desc_idx >= 1) {
                    desc_idx--;
                    i = 0;
                    delwin(mdesc_pad);
                    desc = monster_types[desc_idx];
                    win_h = desc->desc_line_c + 7;
                    if (win_h < HEIGHT - 2) {
                        // Make sure it takes up screen; looks weird if it
                        // doesn't
                        win_h = HEIGHT - 2;
                    }
                    mdesc_pad = newpad(win_h, 78);
                    mdesc_fill_pad(mdesc_pad, desc);
                }
                break;
            case 5:
                // right arrow; move to next mdesc page
                if (desc_idx < num_monster_types - 1) {
                    desc_idx++;
                    i = 0;
                    delwin(mdesc_pad);
                    desc = monster_types[desc_idx];
                    win_h = desc->desc_line_c + 7;
                    if (win_h < HEIGHT - 2) {
                        // Make sure it takes up screen; looks weird if it
                        // doesn't
                        win_h = HEIGHT - 2;
                    }
                    mdesc_pad = newpad(win_h, 78);
                    mdesc_fill_pad(mdesc_pad, desc);
                }
                break;
            case 27:
                // esc key
                exit = true;
                break;
            case 'Q':
                // also let this work, b/c I can
                exit = true;
                break;
            default:
                break;
        }
        prefresh(mdesc_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
        move(0, 0);
        clrtoeol();
        attron(COLOR_PAIR(COLOR_YELLOW));
        mvprintw(0, 0,
                 " Showing monster type %3d of %3d. Press esc to return to "
                 "main menu",
                 desc_idx + 1, num_monster_types);
        attroff(COLOR_PAIR(COLOR_YELLOW));
        refresh();
    }

    wclear(mdesc_pad);
    delwin(mdesc_pad);
}

// prints odesc_c info into pad
static void odesc_fill_pad(WINDOW *odesc_pad, odesc_c *desc) {
    // Writing name
    wprintw(odesc_pad, "Item: %s\n", desc->name.c_str());

    // print type
    switch (desc->type) {
        case objtype_WEAPON:
            wprintw(odesc_pad, "Type: WEAPON\n");
            break;
        case objtype_OFFHAND:
            wprintw(odesc_pad, "Type: OFFHAND\n");
            break;
        case objtype_RANGED:
            wprintw(odesc_pad, "Type: RANGED\n");
            break;
        case objtype_LIGHT:
            wprintw(odesc_pad, "Type: LIGHT\n");
            break;
        case objtype_ARMOR:
            wprintw(odesc_pad, "Type: ARMOR\n");
            break;
        case objtype_HELMET:
            wprintw(odesc_pad, "Type: HELMET\n");
            break;
        case objtype_CLOAK:
            wprintw(odesc_pad, "Type: CLOAK\n");
            break;
        case objtype_GLOVES:
            wprintw(odesc_pad, "Type: GLOVES\n");
            break;
        case objtype_BOOTS:
            wprintw(odesc_pad, "Type: BOOTS\n");
            break;
        case objtype_AMULET:
            wprintw(odesc_pad, "Type: AMULET\n");
            break;
        case objtype_RING:
            wprintw(odesc_pad, "Type: RING\n");
            break;
        case objtype_SCROLL:
            wprintw(odesc_pad, "Type: SCROLL\n");
            break;
        case objtype_BOOK:
            wprintw(odesc_pad, "Type: BOOK\n");
            break;
        case objtype_FLASK:
            wprintw(odesc_pad, "Type: FLASK\n");
            break;
        case objtype_GOLD:
            wprintw(odesc_pad, "Type: GOLD\n");
            break;
        case objtype_AMMUNITION:
            wprintw(odesc_pad, "Type: AMMUNITION\n");
            break;
        case objtype_FOOD:
            wprintw(odesc_pad, "Type: FOOD\n");
            break;
        case objtype_WAND:
            wprintw(odesc_pad, "Type: WAND\n");
            break;
        case objtype_CONTAINER:
            wprintw(odesc_pad, "Type: CONTAINER\n");
            break;
        default:
            wprintw(odesc_pad, "Type: UNKNOWN\n");
    }

    // writing symbol
    wprintw(odesc_pad, "Symbol: ");
    wattron(odesc_pad, COLOR_PAIR(desc->color));
    wprintw(odesc_pad, "%c\n", desc->symb);
    wattroff(odesc_pad, COLOR_PAIR(desc->color));
    // print aritfact
    if (desc->art) {
        wprintw(odesc_pad, "Artifact: TRUE\n");
    } else {
        wprintw(odesc_pad, "Artifact: FALSE\n");
    }
    // print damage
    wprintw(odesc_pad, "Damage: %d+%dd%d\n", desc->damage.get_base(),
            desc->damage.get_number(), desc->damage.get_sides());

    // print speed
    wprintw(odesc_pad, "Speed: %d+%dd%d\n", desc->speed.get_base(),
            desc->speed.get_number(), desc->speed.get_sides());

    // print dodge
    wprintw(odesc_pad, "Dodge: %d+%dd%d\n", desc->dodge.get_base(),
            desc->dodge.get_number(), desc->dodge.get_sides());

    // print defense
    wprintw(odesc_pad, "Defense: %d+%dd%d\n", desc->defense.get_base(),
            desc->defense.get_number(), desc->defense.get_sides());

    // print defense
    wprintw(odesc_pad, "HP Heal: %d+%dd%d\n", desc->hit.get_base(),
            desc->hit.get_number(), desc->hit.get_sides());

    // print attribute (which I assume is light)
    wprintw(odesc_pad, "Light: %d+%dd%d\n", desc->attribute.get_base(),
            desc->attribute.get_number(), desc->attribute.get_sides());

    // print rarity
    wprintw(odesc_pad, "Rarity: %d\n", desc->rrty);

    // print description
    wprintw(odesc_pad, "%s", desc->desc.c_str());

    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " Press esc to exit inspect");
    attroff(COLOR_PAIR(COLOR_YELLOW));
}

// creates a screen to cycle through object (item) descriptions
static void odesc_list_scr() {
    WINDOW *odesc_pad;
    odesc_c *desc;
    uint8_t desc_idx, win_h, i;
    bool exit;
    char ch;

    exit = false;
    desc_idx = i = 0;
    // grabbing first monster description; technically this should check that
    // there are monster descriptions, but oh well
    desc = object_types[desc_idx];
    win_h = desc->desc_line_c + 11;
    if (win_h < HEIGHT - 2) {
        // Make sure it takes up screen; looks weird if it doesn't
        win_h = HEIGHT - 2;
    }
    move(HEIGHT + 1, 0);
    clrtoeol();
    odesc_pad = newpad(win_h, 78);
    odesc_fill_pad(odesc_pad, desc);
    prefresh(odesc_pad, 0, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0,
             " Showing item type %3d of %3d. Press esc to return to main menu",
             desc_idx + 1, num_object_types);
    mvprintw(HEIGHT + 1, 1,
             "Arrow keys: up & down scroll, left & right change page");
    attroff(COLOR_PAIR(COLOR_YELLOW));
    refresh();

    // down 2, up 3, left 4, right 5
    while (!exit) {
        ch = getch();
        switch (ch) {
            case 2:
                // down arrow; scroll down
                if (i <= win_h - (HEIGHT - 1)) {
                    i++;
                }
                break;
            case 3:
                // up arrow; scroll up
                if (i >= 1) {
                    i--;
                }
                break;
            case 4:
                // left arrow; move to previous mdesc page
                if (desc_idx >= 1) {
                    desc_idx--;
                    i = 0;
                    delwin(odesc_pad);
                    desc = object_types[desc_idx];
                    win_h = desc->desc_line_c + 7;
                    if (win_h < HEIGHT - 2) {
                        // Make sure it takes up screen; looks weird if it
                        // doesn't
                        win_h = HEIGHT - 2;
                    }
                    odesc_pad = newpad(win_h, 78);
                    odesc_fill_pad(odesc_pad, desc);
                }
                break;
            case 5:
                // right arrow; move to next mdesc page
                if (desc_idx < num_object_types - 1) {
                    desc_idx++;
                    i = 0;
                    delwin(odesc_pad);
                    desc = object_types[desc_idx];
                    win_h = desc->desc_line_c + 7;
                    if (win_h < HEIGHT - 2) {
                        // Make sure it takes up screen; looks weird if it
                        // doesn't
                        win_h = HEIGHT - 2;
                    }
                    odesc_pad = newpad(win_h, 78);
                    odesc_fill_pad(odesc_pad, desc);
                }
                break;
            case 27:
                // esc key
                exit = true;
                break;
            case 'Q':
                // also let this work, b/c I can
                exit = true;
                break;
            default:
                break;
        }
        prefresh(odesc_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
        move(0, 0);
        clrtoeol();
        attron(COLOR_PAIR(COLOR_YELLOW));
        mvprintw(
            0, 0,
            " Showing item type %3d of %3d. Press esc to return to main menu",
            desc_idx + 1, num_object_types);
        attroff(COLOR_PAIR(COLOR_YELLOW));
        refresh();
    }

    wclear(odesc_pad);
    delwin(odesc_pad);
}

// Handles creating the ROGUE main menu splash screen
static uint8_t menu_main() {
    bool exit;
    uint8_t status;
    char ch;
    WINDOW *main_pad = newpad(18, 56);

    // clear screen then draw main menu
    clear();
    draw_menu_main(main_pad);

    exit = false;
    status = 0;
    while (!exit) {
        ch = getch();
        switch (ch) {
            case 's':
                // start the game
                exit = true;
                status = 1;
                break;
            case 'd':
                // directions / information screen
                draw_instructions();
                break;
            case 'm':
                // list monsters screen
                mdesc_list_scr();
                move(0, 0);
                clrtoeol();
                break;
            case 'i':
                // list items screen;
                odesc_list_scr();

                break;
            case 'Q':
                // Quit
                exit = true;
                status = 0;
                break;
            default:
                break;
        }
        move(HEIGHT + 1, 0);
        clrtoeol();
        move(0, 0);
        clrtoeol();
        draw_menu_main(main_pad);
    }
    wclear(main_pad);
    delwin(main_pad);
    return status;
}

// writes a distance map into the dungeon space on screen;
// great for debugging both calculation + monsters paths
// and looks cool (if you are a nerd)
static void render_distmap(uint8_t distmap[HEIGHT][WIDTH]) {
    int i, j;  // loop control
    // printing distmap, putting border on immutable outer edge
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (i == 0 && j == 0) {
                mvaddch(i + 1, j, ACS_ULCORNER);
            } else if (i == 0 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_URCORNER);
            } else if (i == HEIGHT - 1 && j == 0) {
                mvaddch(i + 1, j, ACS_LLCORNER);
            } else if (i == HEIGHT - 1 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_LRCORNER);
            } else if (i == 0 || i == HEIGHT - 1) {
                mvaddch(i + 1, j, ACS_HLINE);
            } else if (j == 0 || j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_VLINE);
            } else if (distmap[i][j] == UINT8_MAX || distmap[i][j] == 0) {
                mvprintw(i + 1, j, " ");
            } else {
                mvprintw(i + 1, j, "%d", distmap[i][j] % 10);
            }
        }
    }

    // print PC on map
    attron(COLOR_PAIR(COLOR_GREEN));
    mvprintw(player_character->loc[0] + 1, player_character->loc[1], "@");
    attroff(COLOR_PAIR(COLOR_GREEN));

    refresh();
}

// Prints the dungeon map with a border around it.
static void render_dungeon() {
    int i, j, hp;  // loop control

    // printing map, putting border on immutable outer edge
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (i == 0 && j == 0) {
                mvaddch(i + 1, j, ACS_ULCORNER);
            } else if (i == 0 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_URCORNER);
            } else if (i == HEIGHT - 1 && j == 0) {
                mvaddch(i + 1, j, ACS_LLCORNER);
            } else if (i == HEIGHT - 1 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_LRCORNER);
            } else if (i == 0 || i == HEIGHT - 1) {
                mvaddch(i + 1, j, ACS_HLINE);
            } else if (j == 0 || j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_VLINE);
            } else {
                if (amap[i][j] != NULL) {
                    // there be an actor here
                    attron(COLOR_PAIR(amap[i][j]->color));
                    mvprintw(i + 1, j, "%c", amap[i][j]->symb);
                    attroff(COLOR_PAIR(amap[i][j]->color));
                } else if (omap[i][j]) {
                    // there be an object here
                    attron(COLOR_PAIR(omap[i][j]->color));
                    mvprintw(i + 1, j, "%c", omap[i][j]->symb);
                    attroff(COLOR_PAIR(omap[i][j]->color));
                } else {
                    switch (dmap[i][j]) {
                        case floor_room:
                            mvprintw(i + 1, j, ".");
                            break;
                        case floor_corridor:
                            mvprintw(i + 1, j, "#");
                            break;
                        case stair_up:
                            mvprintw(i + 1, j, "<");
                            break;
                        case stair_down:
                            mvprintw(i + 1, j, ">");
                            break;
                        case rock_std:
                            mvprintw(i + 1, j, " ");
                            break;
                        case rock_immutable:
                            mvprintw(i + 1, j, "I");
                            break;
                        case debug:
                            mvprintw(i + 1, j, "!");
                            break;
                        default:
                            mvprintw(i + 1, j, "D");
                            break;
                    }
                }
            }
        }
    }
    move(HEIGHT + 1, 0);
    clrtoeol();
    mvprintw(HEIGHT + 1, 0, " Score: %d", score);
    mvprintw(HEIGHT + 2, 0, " HP: ");
    hp = player_character->hp;

    if (hp > 150) {
        attron(COLOR_PAIR(COLOR_GREEN));
        printw("%3d", hp);
        attroff(COLOR_PAIR(COLOR_GREEN));
    } else if (hp > 75) {
        attron(COLOR_PAIR(COLOR_YELLOW));
        printw("%3d", hp);
        attroff(COLOR_PAIR(COLOR_YELLOW));
    } else {
        attron(COLOR_PAIR(COLOR_RED));
        printw("%3d", hp);
        attroff(COLOR_PAIR(COLOR_RED));
    }
    printw(" Speed: %3d", player_character->speed);
    printw(" Dodge: %3d", player_character->dodge);
    printw(" Def: %3d", player_character->defense);
    refresh();  // refresh display with updated window
}

// renders dungeon with 'fog of war'.
static void render_dungeon_f() {
    int i, j, hp;  // loop control

    // printing map, putting border on immutable outer edge
    for (i = 0; i < HEIGHT; i++) {
        for (j = 0; j < WIDTH; j++) {
            if (i == 0 && j == 0) {
                mvaddch(i + 1, j, ACS_ULCORNER);
            } else if (i == 0 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_URCORNER);
            } else if (i == HEIGHT - 1 && j == 0) {
                mvaddch(i + 1, j, ACS_LLCORNER);
            } else if (i == HEIGHT - 1 && j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_LRCORNER);
            } else if (i == 0 || i == HEIGHT - 1) {
                mvaddch(i + 1, j, ACS_HLINE);
            } else if (j == 0 || j == WIDTH - 1) {
                mvaddch(i + 1, j, ACS_VLINE);
            } else {
                switch (player_character->mem_dungeon[i][j]) {
                    case floor_room:
                        mvprintw(i + 1, j, ".");
                        break;
                    case floor_corridor:
                        mvprintw(i + 1, j, "#");
                        break;
                    case stair_up:
                        mvprintw(i + 1, j, "<");
                        break;
                    case stair_down:
                        mvprintw(i + 1, j, ">");
                        break;
                    case rock_std:
                        mvprintw(i + 1, j, " ");
                        break;
                    case rock_immutable:
                        mvprintw(i + 1, j, "I");
                        break;
                    case debug:
                        mvprintw(i + 1, j, "!");
                        break;
                    default:
                        mvprintw(i + 1, j, " ");
                        break;
                }
            }
        }
    }
    // check for visable monsters
    // Loop through all points within radius PC_VIEW_DIST around PC
    for (i = player_character->loc[0] - pc_view_dist;
         i <= player_character->loc[0] + pc_view_dist; i++) {
        for (j = player_character->loc[1] - pc_view_dist;
             j <= player_character->loc[1] + pc_view_dist; j++) {
            // make sure the point is a valid one + monster present
            if (validPoint(i, j)) {
                if (amap[i][j] != NULL) {
                    // there be an actor here
                    attron(COLOR_PAIR(amap[i][j]->color));
                    mvprintw(i + 1, j, "%c", amap[i][j]->symb);
                    attroff(COLOR_PAIR(amap[i][j]->color));
                } else if (omap[i][j]) {
                    // there be an object here
                    attron(COLOR_PAIR(omap[i][j]->color));
                    mvprintw(i + 1, j, "%c", omap[i][j]->symb);
                    attroff(COLOR_PAIR(omap[i][j]->color));
                } else {
                    // highlight by bolding to show that this is visible
                    attron(A_BOLD);
                    switch (player_character->mem_dungeon[i][j]) {
                        case floor_room:
                            mvprintw(i + 1, j, ".");
                            break;
                        case floor_corridor:
                            mvprintw(i + 1, j, "#");
                            break;
                        case stair_up:
                            mvprintw(i + 1, j, "<");
                            break;
                        case stair_down:
                            mvprintw(i + 1, j, ">");
                            break;
                        case rock_std:
                            mvprintw(i + 1, j, " ");
                            break;
                        case rock_immutable:
                            mvprintw(i + 1, j, "I");
                            break;
                        case debug:
                            mvprintw(i + 1, j, "!");
                            break;
                        default:
                            mvprintw(i + 1, j, "D");
                            break;
                    }
                    attroff(A_BOLD);
                }
            }
        }
    }
    move(HEIGHT + 1, 0);
    clrtoeol();
    mvprintw(HEIGHT + 1, 0, " Score: %d", score);
    mvprintw(HEIGHT + 2, 0, " HP: ");
    hp = player_character->hp;

    if (hp > 150) {
        attron(COLOR_PAIR(COLOR_GREEN));
        printw("%3d", hp);
        attroff(COLOR_PAIR(COLOR_GREEN));
    } else if (hp > 75) {
        attron(COLOR_PAIR(COLOR_YELLOW));
        printw("%3d", hp);
        attroff(COLOR_PAIR(COLOR_YELLOW));
    } else {
        attron(COLOR_PAIR(COLOR_RED));
        printw("%3d", hp);
        attroff(COLOR_PAIR(COLOR_RED));
    }
    printw(" Speed: %3d", player_character->speed);
    printw(" Dodge: %3d", player_character->dodge);
    printw(" Def: %3d", player_character->defense);
    refresh();  // refresh display with updated window
}

// handles staircases and potentially regenerating the dungeon.
static uint8_t attempt_stairs(terrain_t dir) {
    actor_c *m2;
    if (dmap[player_character->loc[0]][player_character->loc[1]] == dir) {
        // it is, in fact, a staircase; wipe current dungeon, generate new
        // remove player character from actor map
        amap[player_character->loc[0]][player_character->loc[1]] = NULL;
        // remove all monsters from amap
        while ((m2 = (actor_c *)heap_remove_min(&turnh))) {
            amap[m2->loc[0]][m2->loc[1]] = NULL;
        }
        heap_delete(&turnh);  // destroy the turn heap
        // Generate all the dungeon crap
        generate_Dungeon();
        calc_walkdist();
        calc_tunneldist();
        // nummon is declared in dungeon.c when monster generation is
        // originally called.
        reset_gen_elig();  // reset monster generation eligibility (except
                           // unique deaths)
        generate_Monsters(nummon);
        generate_Objects();
        score += 10;
        return 2;
    } else {
        if (dir == '<') {
            return 5;
        } else {
            return 6;
        }
    }
}

// handles creating the monster list.
static uint8_t handle_monster_list() {
    int i;
    char ch;
    int mloc[2];
    monster_c *m3 = NULL;
    WINDOW *mlist_pad = newpad(nummon + 2, 54);
    int pcloc[2] = {player_character->loc[0], player_character->loc[1]};

    wprintw(mlist_pad, " overwritten \n");  // overwritten by border
    // add monsters to window
    for (i = 0; i < nummon; i++) {
        darray_at(monList, i, &m3);
        // simply so I don't have to call this every time
        mloc[0] = m3->loc[0];
        mloc[1] = m3->loc[1];

        // check coordinate delta's for east, west, north, south in
        // output
        if (m3 && (m3->hp > 0)) {
            if (mloc[1] > pcloc[1]) {
                // m to east
                if (mloc[0] > pcloc[0]) {
                    // m to south
                    wprintw(mlist_pad, " %3d: ", i + 1);
                    wattron(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, "%c", m3->symb);
                    wattroff(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, " %-26s %2d South, %2d East\n",
                            m3->mdesc->name.c_str(), mloc[0] - pcloc[0],
                            mloc[1] - pcloc[1]);
                } else {
                    // m to north
                    wprintw(mlist_pad, " %3d: ", i + 1);
                    wattron(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, "%c", m3->symb);
                    wattroff(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, " %-26s %2d North, %2d East\n",
                            m3->mdesc->name.c_str(), pcloc[0] - mloc[0],
                            mloc[1] - pcloc[1]);
                }
            } else {
                // m to west
                if (mloc[0] > pcloc[0]) {
                    // m to south
                    wprintw(mlist_pad, " %3d: ", i + 1);
                    wattron(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, "%c", m3->symb);
                    wattroff(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, " %-26s %2d South, %2d West\n",
                            m3->mdesc->name.c_str(), mloc[0] - pcloc[0],
                            pcloc[1] - mloc[1]);

                } else {
                    // m to north
                    wprintw(mlist_pad, " %3d: ", i + 1);
                    wattron(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, "%c", m3->symb);
                    wattroff(mlist_pad, COLOR_PAIR(m3->color));
                    wprintw(mlist_pad, " %-26s %2d North, %2d West\n",
                            m3->mdesc->name.c_str(), pcloc[0] - mloc[0],
                            pcloc[1] - mloc[1]);
                }
            }
        } else {
            wprintw(mlist_pad, " %3d: ", i + 1);
            wattron(mlist_pad, COLOR_PAIR(m3->color));
            wprintw(mlist_pad, "%c", m3->symb);
            wattroff(mlist_pad, COLOR_PAIR(m3->color));
            wprintw(mlist_pad, " %-26s", m3->mdesc->name.c_str());
            wattron(mlist_pad, COLOR_PAIR(COLOR_RED));
            wprintw(mlist_pad, "  -- Was Killed --\n");
            wattroff(mlist_pad, COLOR_PAIR(COLOR_RED));
        }
    }
    wprintw(mlist_pad, " overwritten \n");  // overwritten by border

    // initial print
    box(mlist_pad, 0, 0);  // draw border around window
    prefresh(mlist_pad, 0, 0, 2, WIDTH / 2 - 27, HEIGHT - 1, WIDTH / 2 + 27);
    refresh();

    i = 0;
    ch = 'a';  // just call it something that isn't esc
    // take input until esc key
    while (ch != 27) {
        ch = getch();
        switch (ch) {
            case 3:
                // up arrow
                if (i >= 1) {
                    i--;
                    prefresh(mlist_pad, i, 0, 2, WIDTH / 2 - 27, HEIGHT - 1,
                             WIDTH / 2 + 27);
                    refresh();
                }
                break;
            case 2:
                // down arrow
                if (i <= nummon - (HEIGHT - 3)) {
                    i++;
                    prefresh(mlist_pad, i, 0, 2, WIDTH / 2 - 27, HEIGHT - 1,
                             WIDTH / 2 + 27);
                    refresh();
                }
                break;
            case 'Q':
                delwin(mlist_pad);
                return 86;  // signal for quit
                break;
            default:
                attron(COLOR_PAIR(COLOR_CYAN));
                mvprintw(0, 0, " Key Not Mapped: %c (ASCII %d)", ch, ch);
                attroff(COLOR_PAIR(COLOR_CYAN));
                break;
        }
    }
    delwin(mlist_pad);  // delete window
    return 7;           // success signal (non-standard, I know)
}

// Handles the creation of the monster inspection window + scrolling
static void inspect_monster_win(monster_c *m) {
    char ch;
    int i;
    uint8_t win_h = m->mdesc->desc_line_c + 7;

    if (win_h < HEIGHT - 2) {
        // Make sure it takes up screen; looks weird if it doesn't
        win_h = HEIGHT - 2;
    }
    // sized to fit within the border of the dungeon map
    // With height being total number of lines to fit fields
    WINDOW *mdesc_pad = newpad(win_h, 78);

    // clear existing message at top of screen
    move(0, 0);
    clrtoeol();

    // Writing name
    wprintw(mdesc_pad, "Name: %s\n", m->mdesc->name.c_str());
    // writing symbol
    wprintw(mdesc_pad, "Symbol: ");
    wattron(mdesc_pad, COLOR_PAIR(m->color));
    wprintw(mdesc_pad, "%c\n", m->symb);
    wattroff(mdesc_pad, COLOR_PAIR(m->color));
    // print speed
    wprintw(mdesc_pad, "Speed: %d\n", m->speed);
    // print hp
    wprintw(mdesc_pad, "Hit Points: %d\n", m->hp);
    // print damage
    wprintw(mdesc_pad, "Damage: %d+%dd%d\n", m->dam.get_base(),
            m->dam.get_number(), m->dam.get_sides());
    // print abilities
    wprintw(mdesc_pad, "Abilities: ");
    if (is_intelligent(m->a)) {
        wprintw(mdesc_pad, "SMART ");
    }
    if (is_telepath(m->a)) {
        wprintw(mdesc_pad, "TELE ");
    }
    if (is_tunneler(m->a)) {
        wprintw(mdesc_pad, "TUNNEL ");
    }
    if (is_erratic(m->a)) {
        wprintw(mdesc_pad, "ERRATIC ");
    }
    // if (is_pass(m->a)) {
    //     wprintw(mdesc_pad, "PASS ");
    // }
    // if (is_pickup(m->a)) {
    //     wprintw(mdesc_pad, "PICKUP ");
    // }
    // if (is_destroy(m->a)) {
    //     wprintw(mdesc_pad, "DESTROY ");
    // }
    if (is_uniq(m->a)) {
        wprintw(mdesc_pad, "UNIQ ");
    }
    if (is_boss(m->a)) {
        wprintw(mdesc_pad, "BOSS ");
    }
    wprintw(mdesc_pad, "\n");
    // print rarity
    wprintw(mdesc_pad, "Rarity: %d\n", m->mdesc->rrty);

    // print description
    wprintw(mdesc_pad, "%s", m->mdesc->desc.c_str());

    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " Press esc to exit inspect");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    // Display window
    prefresh(mdesc_pad, 0, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
    refresh();

    // yay scrolling
    i = 0;
    ch = 'a';  // just call it something that isn't esc
    // take input until esc key
    while (ch != 27) {
        ch = getch();
        switch (ch) {
            case 3:
                // up arrow
                if (i >= 1) {
                    i--;
                }
                break;
            case 2:
                // down arrow
                if (i <= win_h - (HEIGHT - 1)) {
                    i++;
                }
                break;
            case 'z':
                // show its distance map, or its idea of where to go
                render_distmap(m->mem_path);
                render_distmap(m->mem_path);
                attron(COLOR_PAIR(COLOR_YELLOW));
                mvprintw(0, 0, " Showing monster's path memory; 'z' to end");
                attroff(COLOR_PAIR(COLOR_YELLOW));
                attron(COLOR_PAIR(m->color));
                mvprintw(m->loc[0] + 1, m->loc[1], "%c", m->symb);
                attroff(COLOR_PAIR(m->color));
                refresh();
                while (getch() != 'z');
            default:
                break;
        }
        move(0, 0);
        clrtoeol();
        attron(COLOR_PAIR(COLOR_YELLOW));
        mvprintw(0, 0, " Press esc to exit inspect");
        attroff(COLOR_PAIR(COLOR_YELLOW));
        prefresh(mdesc_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
        refresh();
    }

    delwin(mdesc_pad);  // delete window
}

// handles targeting for the monster-inspection feature.
static uint8_t inspect_monster_control() {
    int r = (int)player_character->loc[0];
    int c = (int)player_character->loc[1];
    int dr[] = {-1, -1, -1, 0, 0, 0, 1, 1, 1};  // delta row
    int dc[] = {-1, 0, 1, -1, 0, 1, -1, 0, 1};  // delta column
    int pcloc[2] = {player_character->loc[0], player_character->loc[1]};

    // update the map
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " Press 'L' again to inspect monster at cursor '*'");
    attroff(COLOR_PAIR(COLOR_YELLOW));
    attron(COLOR_PAIR(COLOR_BLUE));
    mvprintw(r + 1, c, "%c", '*');
    attroff(COLOR_PAIR(COLOR_BLUE));
    char ch;
    bool exit = false;
    if (fog_toggle) {
        while (!exit) {
            ch = getch();
            switch (ch) {
                case '7':
                    render_dungeon_f();
                    if (validPoint(r + dr[up_left], c + dc[up_left]) &&
                        r > pcloc[0] - pc_view_dist &&
                        c > pcloc[1] - pc_view_dist) {
                        r += dr[up_left];
                        c += dc[up_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'y':
                    render_dungeon_f();
                    if (validPoint(r + dr[up_left], c + dc[up_left]) &&
                        r > pcloc[0] - pc_view_dist &&
                        c > pcloc[1] - pc_view_dist) {
                        r += dr[up_left];
                        c += dc[up_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '8':
                    render_dungeon_f();
                    if (validPoint(r + dr[up], c + dc[up]) &&
                        r > pcloc[0] - pc_view_dist) {
                        r += dr[up];
                        c += dc[up];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'k':
                    render_dungeon_f();
                    if (validPoint(r + dr[up], c + dc[up]) &&
                        r > pcloc[0] - pc_view_dist) {
                        r += dr[up];
                        c += dc[up];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '9':
                    render_dungeon_f();
                    if (validPoint(r + dr[up_right], c + dc[up_right]) &&
                        r > pcloc[0] - pc_view_dist &&
                        c < pcloc[1] + pc_view_dist) {
                        r += dr[up_right];
                        c += dc[up_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'u':
                    render_dungeon_f();
                    if (validPoint(r + dr[up_right], c + dc[up_right]) &&
                        r > pcloc[0] - pc_view_dist &&
                        c < pcloc[1] + pc_view_dist) {
                        r += dr[up_right];
                        c += dc[up_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '6':
                    render_dungeon_f();
                    if (validPoint(r + dr[right], c + dc[right]) &&
                        c < pcloc[1] + pc_view_dist) {
                        r += dr[right];
                        c += dc[right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'l':
                    render_dungeon_f();
                    if (validPoint(r + dr[right], c + dc[right]) &&
                        c < pcloc[1] + pc_view_dist) {
                        r += dr[right];
                        c += dc[right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '3':
                    render_dungeon_f();
                    if (validPoint(r + dr[down_right], c + dc[down_right]) &&
                        r < pcloc[0] + pc_view_dist &&
                        c < pcloc[1] + pc_view_dist) {
                        r += dr[down_right];
                        c += dc[down_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'n':
                    render_dungeon_f();
                    if (validPoint(r + dr[down_right], c + dc[down_right]) &&
                        r < pcloc[0] + pc_view_dist &&
                        c < pcloc[1] + pc_view_dist) {
                        r += dr[down_right];
                        c += dc[down_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '2':
                    render_dungeon_f();
                    if (validPoint(r + dr[down], c + dc[down]) &&
                        r < pcloc[0] + pc_view_dist) {
                        r += dr[down];
                        c += dc[down];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'j':
                    render_dungeon_f();
                    if (validPoint(r + dr[down], c + dc[down]) &&
                        r < pcloc[0] + pc_view_dist) {
                        r += dr[down];
                        c += dc[down];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '1':
                    render_dungeon_f();
                    if (validPoint(r + dr[down_left], c + dc[down_left]) &&
                        r < pcloc[0] + pc_view_dist &&
                        c > pcloc[1] - pc_view_dist) {
                        r += dr[down_left];
                        c += dc[down_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'b':
                    render_dungeon_f();
                    if (validPoint(r + dr[down_left], c + dc[down_left]) &&
                        r < pcloc[0] + pc_view_dist &&
                        c > pcloc[1] - pc_view_dist) {
                        r += dr[down_left];
                        c += dc[down_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '4':
                    render_dungeon_f();
                    if (validPoint(r + dr[left], c + dc[left]) &&
                        c > pcloc[1] - pc_view_dist) {
                        r += dr[left];
                        c += dc[left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'h':
                    render_dungeon_f();
                    if (validPoint(r + dr[left], c + dc[left]) &&
                        c > pcloc[1] - pc_view_dist) {
                        r += dr[left];
                        c += dc[left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'L':
                    if (amap[r][c]) {
                        if (is_pc(amap[r][c]->a)) {
                            return 10;  // error return code
                        } else {
                            inspect_monster_win((monster_c *)amap[r][c]);
                            return 7;  // return code for success, but
                                       // do not consume turn
                        }
                    } else {
                        return 10;  // error return code
                    }
                    break;
                case 27:
                    // escape key
                    return 7;  // exit targeting mode
                default:
                    break;  // do nothing
            }
        }
    } else {
        while (!exit) {
            ch = getch();
            switch (ch) {
                case '7':
                    render_dungeon();
                    if (validPoint(r + dr[up_left], c + dc[up_left])) {
                        r += dr[up_left];
                        c += dc[up_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'y':
                    render_dungeon();
                    if (validPoint(r + dr[up_left], c + dc[up_left])) {
                        r += dr[up_left];
                        c += dc[up_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '8':
                    render_dungeon();
                    if (validPoint(r + dr[up], c + dc[up])) {
                        r += dr[up];
                        c += dc[up];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'k':
                    render_dungeon();
                    if (validPoint(r + dr[up], c + dc[up])) {
                        r += dr[up];
                        c += dc[up];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '9':
                    render_dungeon();
                    if (validPoint(r + dr[up_right], c + dc[up_right])) {
                        r += dr[up_right];
                        c += dc[up_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'u':
                    render_dungeon();
                    if (validPoint(r + dr[up_right], c + dc[up_right])) {
                        r += dr[up_right];
                        c += dc[up_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '6':
                    render_dungeon();
                    if (validPoint(r + dr[right], c + dc[right])) {
                        r += dr[right];
                        c += dc[right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'l':
                    render_dungeon();
                    if (validPoint(r + dr[right], c + dc[right])) {
                        r += dr[right];
                        c += dc[right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '3':
                    render_dungeon();
                    if (validPoint(r + dr[down_right], c + dc[down_right])) {
                        r += dr[down_right];
                        c += dc[down_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'n':
                    render_dungeon();
                    if (validPoint(r + dr[down_right], c + dc[down_right])) {
                        r += dr[down_right];
                        c += dc[down_right];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '2':
                    render_dungeon();
                    if (validPoint(r + dr[down], c + dc[down])) {
                        r += dr[down];
                        c += dc[down];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'j':
                    render_dungeon();
                    if (validPoint(r + dr[down], c + dc[down])) {
                        r += dr[down];
                        c += dc[down];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '1':
                    render_dungeon();
                    if (validPoint(r + dr[down_left], c + dc[down_left])) {
                        r += dr[down_left];
                        c += dc[down_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'b':
                    render_dungeon();
                    if (validPoint(r + dr[down_left], c + dc[down_left])) {
                        r += dr[down_left];
                        c += dc[down_left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case '4':
                    render_dungeon();
                    if (validPoint(r + dr[left], c + dc[left])) {
                        r += dr[left];
                        c += dc[left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'h':
                    render_dungeon();
                    if (validPoint(r + dr[left], c + dc[left])) {
                        r += dr[left];
                        c += dc[left];
                    }
                    attron(COLOR_PAIR(COLOR_BLUE));
                    mvprintw(r + 1, c, "%c", '*');
                    attroff(COLOR_PAIR(COLOR_BLUE));
                    break;
                case 'L':
                    if (amap[r][c]) {
                        if (is_pc(amap[r][c]->a)) {
                            return 10;  // error return code
                        } else {
                            inspect_monster_win((monster_c *)amap[r][c]);
                            return 7;  // return code for success, but
                                       // do not consume turn
                        }
                    } else {
                        return 10;  // error return code
                    }
                    break;
                case 27:
                    // escape key
                    return 7;  // exit targeting mode
                default:
                    break;  // do nothing
            }
        }
    }

    return 10;  // error code to be handled in turnloop
}

// takes input for a carry slot to use
static uint8_t carry_slot_input() {
    char ch;
    while (true) {
        ch = getch();
        switch (ch) {
            case '0':
                return 0;
                break;
            case '1':
                return 1;
                break;
            case '2':
                return 2;
                break;
            case '3':
                return 3;
                break;
            case '4':
                return 4;
                break;
            case '5':
                return 5;
                break;
            case '6':
                return 6;
                break;
            case '7':
                return 7;
                break;
            case '8':
                return 8;
                break;
            case '9':
                return 9;
                break;
            case 27:
                return 27;
            default:
                // nada
                break;
        }
    }
}

// handles the creation of the item description window + scrolling
static void inspect_obj_win(object_c *o) {
    char ch;
    int i;
    uint8_t win_h = o->odesc->desc_line_c + 10;

    if (win_h < 19) {
        // Make sure it takes up screen; looks weird if it doesn't
        win_h = 19;
    }
    // sized to fit within the border of the dungeon map
    // With height being total number of lines to fit fields
    WINDOW *odesc_pad = newpad(win_h, 78);

    // clear existing message at top of screen
    move(0, 0);
    clrtoeol();

    // Writing name
    wprintw(odesc_pad, "Item: %s\n", o->odesc->name.c_str());

    // print type
    switch (o->odesc->type) {
        case objtype_WEAPON:
            wprintw(odesc_pad, "Type: WEAPON\n");
            break;
        case objtype_OFFHAND:
            wprintw(odesc_pad, "Type: OFFHAND\n");
            break;
        case objtype_RANGED:
            wprintw(odesc_pad, "Type: RANGED\n");
            break;
        case objtype_LIGHT:
            wprintw(odesc_pad, "Type: LIGHT\n");
            break;
        case objtype_ARMOR:
            wprintw(odesc_pad, "Type: ARMOR\n");
            break;
        case objtype_HELMET:
            wprintw(odesc_pad, "Type: HELMET\n");
            break;
        case objtype_CLOAK:
            wprintw(odesc_pad, "Type: CLOAK\n");
            break;
        case objtype_GLOVES:
            wprintw(odesc_pad, "Type: GLOVES\n");
            break;
        case objtype_BOOTS:
            wprintw(odesc_pad, "Type: BOOTS\n");
            break;
        case objtype_AMULET:
            wprintw(odesc_pad, "Type: AMULET\n");
            break;
        case objtype_RING:
            wprintw(odesc_pad, "Type: RING\n");
            break;
        case objtype_SCROLL:
            wprintw(odesc_pad, "Type: SCROLL\n");
            break;
        case objtype_BOOK:
            wprintw(odesc_pad, "Type: BOOK\n");
            break;
        case objtype_FLASK:
            wprintw(odesc_pad, "Type: FLASK\n");
            break;
        case objtype_GOLD:
            wprintw(odesc_pad, "Type: GOLD\n");
            break;
        case objtype_AMMUNITION:
            wprintw(odesc_pad, "Type: AMMUNITION\n");
            break;
        case objtype_FOOD:
            wprintw(odesc_pad, "Type: FOOD\n");
            break;
        case objtype_WAND:
            wprintw(odesc_pad, "Type: WAND\n");
            break;
        case objtype_CONTAINER:
            wprintw(odesc_pad, "Type: CONTAINER\n");
            break;
        default:
            wprintw(odesc_pad, "Type: UNKNOWN\n");
    }

    // writing symbol
    wprintw(odesc_pad, "Symbol: ");
    wattron(odesc_pad, COLOR_PAIR(o->color));
    wprintw(odesc_pad, "%c\n", o->symb);
    wattroff(odesc_pad, COLOR_PAIR(o->color));
    // print aritfact
    if (o->art) {
        wprintw(odesc_pad, "Artifact: TRUE\n");
    } else {
        wprintw(odesc_pad, "Artifact: FALSE\n");
    }
    // print damage
    wprintw(odesc_pad, "Damage: %d+%dd%d\n", o->damage.get_base(),
            o->damage.get_number(), o->damage.get_sides());

    // print rarity
    wprintw(odesc_pad, "Speed: %d\n", o->speed);

    // print dodge
    wprintw(odesc_pad, "Dodge: %d\n", o->dodge);

    // print defense
    wprintw(odesc_pad, "Defense: %d\n", o->defense);

    // print attribute (which I assume is light)
    wprintw(odesc_pad, "Light: %d\n", o->attribute);

    // print rarity
    wprintw(odesc_pad, "Rarity: %d\n", o->odesc->rrty);

    // print description
    wprintw(odesc_pad, "%s", o->odesc->desc.c_str());

    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " Press esc to exit inspect");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    // Display window
    prefresh(odesc_pad, 0, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
    refresh();

    // yay scrolling
    i = 0;
    ch = 'a';  // just call it something that isn't esc
    // take input until esc key
    while (ch != 27) {
        ch = getch();
        switch (ch) {
            case 3:
                // up arrow
                if (i >= 1) {
                    i--;
                    prefresh(odesc_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
                    refresh();
                }
                break;
            case 2:
                // down arrow
                if (i <= win_h - (HEIGHT - 1)) {
                    i++;
                    prefresh(odesc_pad, i, 0, 2, 1, HEIGHT - 1, WIDTH - 1);
                    refresh();
                }
                break;
            default:
                break;
        }
    }

    delwin(odesc_pad);  // delete window
}

// handles the input for which carry slot to inspect from.
static uint8_t inspect_obj_control() {
    int i, idx;

    WINDOW *cslot_pad = newpad(14, 50);

    // writing control message at top of screen
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " enter 0-9 to inspect item");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    wprintw(cslot_pad, "\n");  // overwritten by border

    wattron(cslot_pad, A_BOLD);
    wattron(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wprintw(cslot_pad, " - - - - - - - - - Carry  Slots - - - - - - - - - ");
    wattroff(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wattroff(cslot_pad, A_BOLD);

    wprintw(cslot_pad, "\n");

    // printing the carry slots + item name contained within
    // it would be nice if this were centered, but variable name lengths make
    // that annoying to an extent that I don't want to do that right now.
    for (i = 0; i < 10; i++) {
        if (player_character->carry_slot[i]) {
            wprintw(cslot_pad, "  %d: %s\n", i,
                    player_character->carry_slot[i]->odesc->name.c_str());
        } else {
            wprintw(cslot_pad, "  %d: [ EMPTY ]\n", i);
        }
    }

    wprintw(cslot_pad, "\n");  // overwritten by border

    // Display window
    box(cslot_pad, 0, 0);  // add fancy border around window
    prefresh(cslot_pad, 0, 0, 2, WIDTH / 2 - 25, HEIGHT - 1, WIDTH / 2 + 25);
    refresh();

    // handle input for carry slot to inspect
    idx = carry_slot_input();

    if (idx == 27) {
        // escape key was entered, exit
        delwin(cslot_pad);  // delete window
        return 31;
    }

    if (player_character->carry_slot[idx]) {
        inspect_obj_win(player_character->carry_slot[idx]);
        delwin(cslot_pad);  // delete window
        return 31;          // return success code
    } else {
        delwin(cslot_pad);  // delete window
        return 30;          // failure code
    }
}

// displays a list of the item name in each carry slot.
static void list_carry_slots() {
    int i;
    char ch;
    // just filling the screen b/c I am lazy
    WINDOW *cslot_pad = newpad(14, 50);

    // writing control message at top of screen
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " press esc to exit");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    wprintw(cslot_pad, "\n");  // overwritten by border

    wattron(cslot_pad, A_BOLD);
    wattron(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wprintw(cslot_pad, " - - - - - - - - - Carry  Slots - - - - - - - - - ");
    wattroff(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wattroff(cslot_pad, A_BOLD);

    wprintw(cslot_pad, "\n");

    // printing the carry slots + item name contained within
    // it would be nice if this were centered, but variable name lengths make
    // that annoying to an extent that I don't want to do that right now.
    for (i = 0; i < 10; i++) {
        if (player_character->carry_slot[i]) {
            wprintw(cslot_pad, "  %d: %s\n", i,
                    player_character->carry_slot[i]->odesc->name.c_str());
        } else {
            wprintw(cslot_pad, "  %d: [ EMPTY ]\n", i);
        }
    }

    wprintw(cslot_pad, "\n");  // overwritten by border

    // Display window
    box(cslot_pad, 0, 0);  // add fancy border around window
    prefresh(cslot_pad, 0, 0, 2, WIDTH / 2 - 25, HEIGHT - 1, WIDTH / 2 + 25);
    refresh();

    ch = 'a';
    while (ch != 27) {
        ch = getch();
    }

    delwin(cslot_pad);  // delete window
}

// displays a list of the names of equipped items in each slot.
static void list_equipment() {
    char ch;
    // just filling the screen b/c I am lazy
    WINDOW *eslot_pad = newpad(16, 50);

    // writing control message at top of screen
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " press esc to exit");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    wprintw(eslot_pad, "\n");  // overwritten by border

    wattron(eslot_pad, A_BOLD);
    wattron(eslot_pad, COLOR_PAIR(COLOR_GREEN));
    wprintw(eslot_pad, " - - - - - - - - - Equip  Slots - - - - - - - - - ");
    wattroff(eslot_pad, COLOR_PAIR(COLOR_GREEN));
    wattroff(eslot_pad, A_BOLD);

    wprintw(eslot_pad, "\n");

    // printint the name of each equip slot
    if (player_character->weapon) {
        wprintw(eslot_pad, "  WEAPON  (a): %s\n",
                player_character->weapon->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  WEAPON  (a): [ EMPTY ]\n");
    }

    if (player_character->offhand) {
        wprintw(eslot_pad, "  OFFHAND (b): %s\n",
                player_character->offhand->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  OFFHAND (b): [ EMPTY ]\n");
    }

    if (player_character->ranged) {
        wprintw(eslot_pad, "  RANGED  (c): %s\n",
                player_character->ranged->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  RANGED  (c): [ EMPTY ]\n");
    }

    if (player_character->armor) {
        wprintw(eslot_pad, "  ARMOR   (d): %s\n",
                player_character->armor->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  ARMOR   (d): [ EMPTY ]\n");
    }

    if (player_character->helmet) {
        wprintw(eslot_pad, "  HELMET  (e): %s\n",
                player_character->helmet->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  HELMET  (e): [ EMPTY ]\n");
    }

    if (player_character->cloak) {
        wprintw(eslot_pad, "  CLOAK   (f): %s\n",
                player_character->cloak->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  CLOAK   (f): [ EMPTY ]\n");
    }

    if (player_character->gloves) {
        wprintw(eslot_pad, "  GLOVES  (g): %s\n",
                player_character->gloves->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  GLOVES  (g): [ EMPTY ]\n");
    }

    if (player_character->boots) {
        wprintw(eslot_pad, "  BOOTS   (h): %s\n",
                player_character->boots->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  BOOTS   (h): [ EMPTY ]\n");
    }

    if (player_character->amulet) {
        wprintw(eslot_pad, "  AMULET  (i): %s\n",
                player_character->amulet->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  AMULET  (i): [ EMPTY ]\n");
    }

    if (player_character->light) {
        wprintw(eslot_pad, "  LIGHT   (j): %s\n",
                player_character->light->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  LIGHT   (j): [ EMPTY ]\n");
    }

    if (player_character->ring1) {
        wprintw(eslot_pad, "  R RING  (k): %s\n",
                player_character->ring1->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  R RING  (k): [ EMPTY ]\n");
    }

    if (player_character->ring2) {
        wprintw(eslot_pad, "  L RING  (l): %s\n",
                player_character->ring2->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  L RING  (l): [ EMPTY ]\n");
    }

    wprintw(eslot_pad, "\n");  // overwritten by border

    // Display window
    box(eslot_pad, 0, 0);  // add fancy border around window
    prefresh(eslot_pad, 0, 0, 2, WIDTH / 2 - 25, HEIGHT - 1, WIDTH / 2 + 25);
    refresh();

    ch = 'a';
    while (ch != 27) {
        ch = getch();
    }

    delwin(eslot_pad);  // delete window
}

// attempts to wear an item, asking for carry slot.
static uint8_t wear_obj() {
    int i, idx, new_speed, new_dodge, new_defense, new_view;
    object_c *o;
    // just filling the screen b/c I am lazy
    WINDOW *cslot_pad = newpad(14, 50);

    // writing control message at top of screen
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " press 0-9 for item to equip");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    wprintw(cslot_pad, "\n");  // overwritten by border

    wattron(cslot_pad, A_BOLD);
    wprintw(cslot_pad, " - - - - - - - - - Carry  Slots - - - - - - - - - ");
    wattroff(cslot_pad, A_BOLD);

    wprintw(cslot_pad, "\n");

    // printing the carry slots + item name contained within
    // it would be nice if this were centered, but variable name lengths make
    // that annoying to an extent that I don't want to do that right now.
    for (i = 0; i < 10; i++) {
        if (player_character->carry_slot[i]) {
            wprintw(cslot_pad, "  %d: %s\n", i,
                    player_character->carry_slot[i]->odesc->name.c_str());
        } else {
            wprintw(cslot_pad, "  %d: [ EMPTY ]\n", i);
        }
    }

    wprintw(cslot_pad, "\n");  // overwritten by border

    // Display window
    box(cslot_pad, 0, 0);  // add fancy border around window
    prefresh(cslot_pad, 0, 0, 2, WIDTH / 2 - 25, HEIGHT - 1, WIDTH / 2 + 25);
    refresh();

    idx = carry_slot_input();

    if (idx == 27) {
        // esc key; exit
        delwin(cslot_pad);  // delete window
        return 31;
    }

    // more uggo if statements (yay!)
    // stuff like this could really use a pass of 'can I do this less stupid?',
    // but I'm mostly aiming for functionality and don't care enough to do so.
    if (player_character->carry_slot[idx]) {
        o = player_character->carry_slot[idx];
        // add items bonuses
        new_speed = player_character->speed + o->speed;
        new_dodge = player_character->dodge + o->dodge;
        new_defense = player_character->defense + o->defense;
        new_view = pc_view_dist + o->attribute;
        switch (o->odesc->type) {
            case objtype_WEAPON:
                if (player_character->weapon) {
                    // swap
                    player_character->carry_slot[idx] =
                        player_character->weapon;
                    new_speed -= player_character->weapon->speed;
                    new_dodge -= player_character->weapon->dodge;
                    new_defense -= player_character->weapon->defense;
                    new_view -= player_character->weapon->attribute;
                    player_character->weapon = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->weapon = o;
                }
                break;
            case objtype_OFFHAND:
                if (player_character->offhand) {
                    // swap
                    player_character->carry_slot[idx] =
                        player_character->offhand;
                    new_speed -= player_character->offhand->speed;
                    new_dodge -= player_character->offhand->dodge;
                    new_defense -= player_character->offhand->defense;
                    new_view -= player_character->offhand->attribute;
                    player_character->offhand = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->offhand = o;
                }
                break;
            case objtype_RANGED:
                if (player_character->ranged) {
                    // swap
                    player_character->carry_slot[idx] =
                        player_character->ranged;
                    new_speed -= player_character->ranged->speed;
                    new_dodge -= player_character->ranged->dodge;
                    new_defense -= player_character->ranged->defense;
                    new_view -= player_character->ranged->attribute;
                    player_character->ranged = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->ranged = o;
                }
                break;
            case objtype_ARMOR:
                if (player_character->armor) {
                    // swap
                    player_character->carry_slot[idx] = player_character->armor;
                    new_speed -= player_character->armor->speed;
                    new_dodge -= player_character->armor->dodge;
                    new_defense -= player_character->armor->defense;
                    new_view -= player_character->armor->attribute;
                    player_character->armor = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->armor = o;
                }
                break;
            case objtype_HELMET:
                if (player_character->helmet) {
                    // swap
                    player_character->carry_slot[idx] =
                        player_character->helmet;
                    new_speed -= player_character->helmet->speed;
                    new_dodge -= player_character->helmet->dodge;
                    new_defense -= player_character->helmet->defense;
                    new_view -= player_character->helmet->attribute;
                    player_character->helmet = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->helmet = o;
                }
                break;
            case objtype_CLOAK:
                if (player_character->cloak) {
                    // swap
                    player_character->carry_slot[idx] = player_character->cloak;
                    new_speed -= player_character->cloak->speed;
                    new_dodge -= player_character->cloak->dodge;
                    new_defense -= player_character->cloak->defense;
                    new_view -= player_character->cloak->attribute;
                    player_character->cloak = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->cloak = o;
                }
                break;
            case objtype_GLOVES:
                if (player_character->gloves) {
                    // swap
                    player_character->carry_slot[idx] =
                        player_character->gloves;
                    new_speed -= player_character->gloves->speed;
                    new_dodge -= player_character->gloves->dodge;
                    new_defense -= player_character->gloves->defense;
                    new_view -= player_character->gloves->attribute;
                    player_character->gloves = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->gloves = o;
                }
                break;
            case objtype_BOOTS:
                if (player_character->boots) {
                    // swap
                    player_character->carry_slot[idx] = player_character->boots;
                    new_speed -= player_character->boots->speed;
                    new_dodge -= player_character->boots->dodge;
                    new_defense -= player_character->boots->defense;
                    new_view -= player_character->boots->attribute;
                    player_character->boots = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->boots = o;
                }
                break;
            case objtype_AMULET:
                if (player_character->amulet) {
                    // swap
                    player_character->carry_slot[idx] =
                        player_character->amulet;
                    new_speed -= player_character->amulet->speed;
                    new_dodge -= player_character->amulet->dodge;
                    new_defense -= player_character->amulet->defense;
                    new_view -= player_character->amulet->attribute;
                    player_character->amulet = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->amulet = o;
                }
                break;
            case objtype_LIGHT:
                if (player_character->light) {
                    // swap
                    player_character->carry_slot[idx] = player_character->light;
                    new_speed -= player_character->light->speed;
                    new_dodge -= player_character->light->dodge;
                    new_defense -= player_character->light->defense;
                    new_view -= player_character->light->attribute;
                    player_character->light = o;
                } else {
                    player_character->carry_slot[idx] = NULL;
                    player_character->light = o;
                }
                break;
            case objtype_RING:
                // since there are two ring slots, this will rotate if both are
                // already equipped. so carry => 1 => 2 => carry
                if (player_character->ring1) {
                    // rotate
                    player_character->carry_slot[idx] = player_character->ring2;
                    if (player_character->ring2) {
                        // remove bonuses from original ring2
                        new_speed -= player_character->ring2->speed;
                        new_dodge -= player_character->ring2->dodge;
                        new_defense -= player_character->ring2->defense;
                        new_view -= player_character->ring2->attribute;
                    }
                    player_character->ring2 = player_character->ring1;
                    player_character->ring1 = o;
                } else {
                    player_character->ring1 = o;
                    player_character->carry_slot[idx] = NULL;
                }
                break;
            default:
                delwin(cslot_pad);  // delete window
                return 40;          // unequipable item failure
                break;
        }
        player_character->speed +=
            o->speed;  // add speed bonus to player character

        // update speed, dodge, and defense
        if (new_speed >= 1) {
            player_character->speed = new_speed;
        } else {
            // min 1; division by zero otherwise
            // technically this also introduces an exploit for infinite speed
            player_character->speed = 1;
        }
        if (new_dodge >= 1) {
            player_character->dodge = new_dodge;
        } else {
            player_character->dodge = 1;
        }
        if (new_defense >= 1) {
            player_character->defense = new_defense;
        } else {
            player_character->defense = 1;
        }
        // this one should never matter; but I'll create it here just in case
        if (new_view >= 1) {
            pc_view_dist = new_view;
        } else {
            pc_view_dist = 1;
        }
        pc_move(none);  // update PC memory
        return 42;      // success return code
    } else {
        delwin(cslot_pad);  // delete window
        return 30;          // empty inventory slot failure
    }
}

// attempts to place object into the earliest available carry slot
// true if successful, false otherwise
static bool carry(object_c *o) {
    int i;
    for (i = 0; i < 10 && player_character->carry_slot[i]; i++);
    if (i < 10) {
        player_character->carry_slot[i] = o;
        return true;
    } else {
        return false;
    }
}

// Asks for carry slot, attempts to destory item.
static uint8_t expunge_obj() {
    int i, idx;
    // just filling the screen b/c I am lazy
    WINDOW *cslot_pad = newpad(14, 50);

    // writing control message at top of screen
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " press 0-9 to destroy item");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    wprintw(cslot_pad, "\n");  // overwritten by border

    wattron(cslot_pad, A_BOLD);
    wattron(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wprintw(cslot_pad, " - - - - - - - - - Carry  Slots - - - - - - - - - ");
    wattroff(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wattroff(cslot_pad, A_BOLD);

    wprintw(cslot_pad, "\n");
    for (i = 0; i < 10; i++) {
        if (player_character->carry_slot[i]) {
            wprintw(cslot_pad, "  %d: %s\n", i,
                    player_character->carry_slot[i]->odesc->name.c_str());
        } else {
            wprintw(cslot_pad, "  %d: [ EMPTY ]\n", i);
        }
    }

    wprintw(cslot_pad, "\n");  // overwritten by border

    // Display window
    box(cslot_pad, 0, 0);  // add fancy border around window
    prefresh(cslot_pad, 0, 0, 2, WIDTH / 2 - 25, HEIGHT - 1, WIDTH / 2 + 25);
    refresh();

    idx = carry_slot_input();

    if (idx == 27) {
        // esc key; exit
        delwin(cslot_pad);  // delete window
        return 31;
    }

    if (player_character->carry_slot[idx]) {
        delete (player_character->carry_slot[idx]);  // delete item
        player_character->carry_slot[idx] = NULL;
        delwin(cslot_pad);  // delete window
        return 31;          // return success code
    } else {
        delwin(cslot_pad);  // delete window
        return 30;          // failure code
    }
}

// Asks for a carry slot, then attempts to drop item.
static uint8_t drop_obj() {
    int i, idx;
    object_c *o;
    // just filling the screen b/c I am lazy
    WINDOW *cslot_pad = newpad(14, 50);

    // writing control message at top of screen
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " press 0-9 to drop item");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    wprintw(cslot_pad, "\n");  // overwritten by border

    wattron(cslot_pad, A_BOLD);
    wattron(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wprintw(cslot_pad, " - - - - - - - - - Carry  Slots - - - - - - - - - ");
    wattroff(cslot_pad, COLOR_PAIR(COLOR_CYAN));
    wattroff(cslot_pad, A_BOLD);

    wprintw(cslot_pad, "\n");
    for (i = 0; i < 10; i++) {
        if (player_character->carry_slot[i]) {
            wprintw(cslot_pad, "  %d: %s\n", i,
                    player_character->carry_slot[i]->odesc->name.c_str());
        } else {
            wprintw(cslot_pad, "  %d: [ EMPTY ]\n", i);
        }
    }

    wprintw(cslot_pad, "\n");  // overwritten by border

    // Display window
    box(cslot_pad, 0, 0);  // add fancy border around window
    prefresh(cslot_pad, 0, 0, 2, WIDTH / 2 - 25, HEIGHT - 1, WIDTH / 2 + 25);
    refresh();

    idx = carry_slot_input();

    if (idx == 27) {
        // esc key; exit
        delwin(cslot_pad);  // delete window
        return 31;
    }

    if (player_character->carry_slot[idx]) {
        if (omap[player_character->loc[0]][player_character->loc[1]]) {
            delwin(cslot_pad);  // delete window
            return 35;          // omap occupied failure code
        } else {
            // drop item
            o = player_character->carry_slot[idx];
            omap[player_character->loc[0]][player_character->loc[1]] = o;
            o->loc[0] = player_character->loc[0];
            o->loc[1] = player_character->loc[1];
            objList.push_back(o);  // re-add to vector
            numobj++;
            player_character->carry_slot[idx] = NULL;
            delwin(cslot_pad);  // delete window
            return 31;          // return success code
        }
    } else {
        delwin(cslot_pad);  // delete window
        return 30;          // inventory failure code
    }
}

// unequips specified equipment
static uint8_t takeoff_obj() {
    char ch;
    bool exit, success;
    int new_speed, new_dodge, new_defense, new_view;
    // just filling the screen b/c I am lazy
    WINDOW *eslot_pad = newpad(16, 50);

    // writing control message at top of screen
    move(0, 0);
    clrtoeol();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0, " press a-l to unequip item");
    attroff(COLOR_PAIR(COLOR_YELLOW));

    wprintw(eslot_pad, "\n");  // overwritten by border

    wattron(eslot_pad, A_BOLD);
    wattron(eslot_pad, COLOR_PAIR(COLOR_GREEN));
    wprintw(eslot_pad, " - - - - - - - - - Equip  Slots - - - - - - - - - ");
    wattroff(eslot_pad, COLOR_PAIR(COLOR_GREEN));
    wattroff(eslot_pad, A_BOLD);

    wprintw(eslot_pad, "\n");

    // printint the name of each equip slot
    if (player_character->weapon) {
        wprintw(eslot_pad, "  WEAPON  (a): %s\n",
                player_character->weapon->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  WEAPON  (a): [ EMPTY ]\n");
    }

    if (player_character->offhand) {
        wprintw(eslot_pad, "  OFFHAND (b): %s\n",
                player_character->offhand->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  OFFHAND (b): [ EMPTY ]\n");
    }

    if (player_character->ranged) {
        wprintw(eslot_pad, "  RANGED  (c): %s\n",
                player_character->ranged->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  RANGED  (c): [ EMPTY ]\n");
    }

    if (player_character->armor) {
        wprintw(eslot_pad, "  ARMOR   (d): %s\n",
                player_character->armor->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  ARMOR   (d): [ EMPTY ]\n");
    }

    if (player_character->helmet) {
        wprintw(eslot_pad, "  HELMET  (e): %s\n",
                player_character->helmet->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  HELMET  (e): [ EMPTY ]\n");
    }

    if (player_character->cloak) {
        wprintw(eslot_pad, "  CLOAK   (f): %s\n",
                player_character->cloak->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  CLOAK   (f): [ EMPTY ]\n");
    }

    if (player_character->gloves) {
        wprintw(eslot_pad, "  GLOVES  (g): %s\n",
                player_character->gloves->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  GLOVES  (g): [ EMPTY ]\n");
    }

    if (player_character->boots) {
        wprintw(eslot_pad, "  BOOTS   (h): %s\n",
                player_character->boots->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  BOOTS   (h): [ EMPTY ]\n");
    }

    if (player_character->amulet) {
        wprintw(eslot_pad, "  AMULET  (i): %s\n",
                player_character->amulet->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  AMULET  (i): [ EMPTY ]\n");
    }

    if (player_character->light) {
        wprintw(eslot_pad, "  LIGHT   (j): %s\n",
                player_character->light->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  LIGHT   (j): [ EMPTY ]\n");
    }

    if (player_character->ring1) {
        wprintw(eslot_pad, "  R RING  (k): %s\n",
                player_character->ring1->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  R RING  (k): [ EMPTY ]\n");
    }

    if (player_character->ring2) {
        wprintw(eslot_pad, "  L RING  (l): %s\n",
                player_character->ring2->odesc->name.c_str());
    } else {
        wprintw(eslot_pad, "  L RING  (l): [ EMPTY ]\n");
    }

    wprintw(eslot_pad, "\n");  // overwritten by border

    // Display window
    box(eslot_pad, 0, 0);  // add fancy border around window
    prefresh(eslot_pad, 0, 0, 2, WIDTH / 2 - 25, HEIGHT - 1, WIDTH / 2 + 25);
    refresh();

    exit = false;
    while (!exit) {
        ch = getch();
        switch (ch) {
            case 'a':
                if (player_character->weapon) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->weapon->speed;
                    new_dodge = player_character->dodge -
                                player_character->weapon->dodge;
                    new_defense = player_character->defense -
                                  player_character->weapon->defense;
                    new_view =
                        pc_view_dist - player_character->weapon->attribute;
                    success = carry(player_character->weapon);
                    player_character->weapon = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'b':
                if (player_character->offhand) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->offhand->speed;
                    new_dodge = player_character->dodge -
                                player_character->offhand->dodge;
                    new_defense = player_character->defense -
                                  player_character->offhand->defense;
                    new_view =
                        pc_view_dist - player_character->offhand->attribute;
                    success = carry(player_character->offhand);
                    player_character->offhand = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'c':
                if (player_character->ranged) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->ranged->speed;
                    new_dodge = player_character->dodge -
                                player_character->ranged->dodge;
                    new_defense = player_character->defense -
                                  player_character->ranged->defense;
                    new_view =
                        pc_view_dist - player_character->ranged->attribute;
                    success = carry(player_character->ranged);
                    player_character->ranged = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'd':
                if (player_character->armor) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->armor->speed;
                    new_dodge = player_character->dodge -
                                player_character->armor->dodge;
                    new_defense = player_character->defense -
                                  player_character->armor->defense;
                    new_view =
                        pc_view_dist - player_character->armor->attribute;
                    success = carry(player_character->armor);
                    player_character->armor = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'e':
                if (player_character->helmet) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->helmet->speed;
                    new_dodge = player_character->dodge -
                                player_character->helmet->dodge;
                    new_defense = player_character->defense -
                                  player_character->helmet->defense;
                    new_view =
                        pc_view_dist - player_character->helmet->attribute;
                    success = carry(player_character->helmet);
                    player_character->helmet = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'f':
                if (player_character->cloak) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->cloak->speed;
                    new_dodge = player_character->dodge -
                                player_character->cloak->dodge;
                    new_defense = player_character->defense -
                                  player_character->cloak->defense;
                    new_view =
                        pc_view_dist - player_character->cloak->attribute;
                    success = carry(player_character->cloak);
                    player_character->cloak = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'g':
                if (player_character->gloves) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->gloves->speed;
                    new_dodge = player_character->dodge -
                                player_character->gloves->dodge;
                    new_defense = player_character->defense -
                                  player_character->gloves->defense;
                    new_view =
                        pc_view_dist - player_character->gloves->attribute;
                    success = carry(player_character->gloves);
                    player_character->gloves = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'h':
                if (player_character->boots) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->boots->speed;
                    new_dodge = player_character->dodge -
                                player_character->boots->dodge;
                    new_defense = player_character->defense -
                                  player_character->boots->defense;
                    new_view =
                        pc_view_dist - player_character->boots->attribute;
                    success = carry(player_character->boots);
                    player_character->boots = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'i':
                if (player_character->amulet) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->amulet->speed;
                    new_dodge = player_character->dodge -
                                player_character->amulet->dodge;
                    new_defense = player_character->defense -
                                  player_character->amulet->defense;
                    new_view =
                        pc_view_dist - player_character->amulet->attribute;
                    success = carry(player_character->amulet);
                    player_character->amulet = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'j':
                if (player_character->light) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->light->speed;
                    new_dodge = player_character->dodge -
                                player_character->light->dodge;
                    new_defense = player_character->defense -
                                  player_character->light->defense;
                    new_view =
                        pc_view_dist - player_character->light->attribute;

                    success = carry(player_character->light);
                    player_character->light = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'k':
                if (player_character->ring1) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->ring1->speed;
                    new_dodge = player_character->dodge -
                                player_character->ring1->dodge;
                    new_defense = player_character->defense -
                                  player_character->ring1->defense;
                    new_view =
                        pc_view_dist - player_character->ring1->attribute;

                    success = carry(player_character->ring1);
                    player_character->ring1 = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 'l':
                if (player_character->ring2) {
                    exit = true;
                    new_speed = player_character->speed -
                                player_character->ring2->speed;
                    new_dodge = player_character->dodge -
                                player_character->ring2->dodge;
                    new_defense = player_character->defense -
                                  player_character->ring2->defense;
                    new_view =
                        pc_view_dist - player_character->ring2->attribute;

                    success = carry(player_character->ring2);
                    player_character->ring2 = NULL;
                } else {
                    delwin(eslot_pad);  // delete window
                    return 45;          // not equipped error
                }
                break;
            case 27:
                // escape key; exit
                delwin(eslot_pad);  // delete window
                return 7;
                break;
        }
    }

    if (success) {
        delwin(eslot_pad);  // delete window
        // update speed, dodge, and defense
        if (new_speed >= 1) {
            player_character->speed = new_speed;
        } else {
            // min 1; division by zero otherwise
            // technically this also introduces an exploit for infinite speed
            player_character->speed = 1;
        }
        if (new_dodge >= 1) {
            player_character->dodge = new_dodge;
        } else {
            player_character->dodge = 1;
        }
        if (new_defense >= 1) {
            player_character->defense = new_defense;
        } else {
            player_character->defense = 1;
        }
        if (new_view >= 1) {
            pc_view_dist = new_view;
        } else {
            pc_view_dist = 1;
        }
        return 7;  // generic success
    } else {
        delwin(eslot_pad);  // delete window
        return 21;          // inventory limit error return code
    }
}

// handles the teleport cheat.
static void handle_teleport() {
    int r = (int)player_character->loc[0];
    int c = (int)player_character->loc[1];
    int dr[] = {-1, -1, -1, 0, 0, 0, 1, 1, 1};  // delta row
    int dc[] = {-1, 0, 1, -1, 0, 1, -1, 0, 1};  // delta column
    // initial print
    render_dungeon();
    attron(COLOR_PAIR(COLOR_YELLOW));
    mvprintw(0, 0,
             " Press 'g' to teleport to cursor *; 'r' to teleport to random "
             "location");
    attroff(COLOR_PAIR(COLOR_YELLOW));
    attron(COLOR_PAIR(COLOR_BLUE));
    mvprintw(r + 1, c, "%c", '*');
    attroff(COLOR_PAIR(COLOR_BLUE));
    char ch;
    bool exit = false;
    while (!exit) {
        ch = getch();
        switch (ch) {
            case '7':
                render_dungeon();
                if (validPoint(r + dr[up_left], c + dc[up_left])) {
                    r += dr[up_left];
                    c += dc[up_left];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'y':
                render_dungeon();
                if (validPoint(r + dr[up_left], c + dc[up_left])) {
                    r += dr[up_left];
                    c += dc[up_left];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case '8':
                render_dungeon();
                if (validPoint(r + dr[up], c + dc[up])) {
                    r += dr[up];
                    c += dc[up];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'k':
                render_dungeon();
                if (validPoint(r + dr[up], c + dc[up])) {
                    r += dr[up];
                    c += dc[up];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case '9':
                render_dungeon();
                if (validPoint(r + dr[up_right], c + dc[up_right])) {
                    r += dr[up_right];
                    c += dc[up_right];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'u':
                render_dungeon();
                if (validPoint(r + dr[up_right], c + dc[up_right])) {
                    r += dr[up_right];
                    c += dc[up_right];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case '6':
                render_dungeon();
                if (validPoint(r + dr[right], c + dc[right])) {
                    r += dr[right];
                    c += dc[right];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'l':
                render_dungeon();
                if (validPoint(r + dr[right], c + dc[right])) {
                    r += dr[right];
                    c += dc[right];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case '3':
                render_dungeon();
                if (validPoint(r + dr[down_right], c + dc[down_right])) {
                    r += dr[down_right];
                    c += dc[down_right];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'n':
                render_dungeon();
                if (validPoint(r + dr[down_right], c + dc[down_right])) {
                    r += dr[down_right];
                    c += dc[down_right];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case '2':
                render_dungeon();
                if (validPoint(r + dr[down], c + dc[down])) {
                    r += dr[down];
                    c += dc[down];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'j':
                render_dungeon();
                if (validPoint(r + dr[down], c + dc[down])) {
                    r += dr[down];
                    c += dc[down];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case '1':
                render_dungeon();
                if (validPoint(r + dr[down_left], c + dc[down_left])) {
                    r += dr[down_left];
                    c += dc[down_left];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'b':
                render_dungeon();
                if (validPoint(r + dr[down_left], c + dc[down_left])) {
                    r += dr[down_left];
                    c += dc[down_left];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case '4':
                render_dungeon();
                if (validPoint(r + dr[left], c + dc[left])) {
                    r += dr[left];
                    c += dc[left];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'h':
                render_dungeon();
                if (validPoint(r + dr[left], c + dc[left])) {
                    r += dr[left];
                    c += dc[left];
                }
                attron(COLOR_PAIR(COLOR_BLUE));
                mvprintw(r + 1, c, "%c", '*');
                attroff(COLOR_PAIR(COLOR_BLUE));
                break;
            case 'g':
                if (!(actorteleport(r, c, player_character)) ||
                    (r == player_character->loc[0] &&
                     c == player_character->loc[1])) {
                    exit = true;
                }
                break;
            case 'r':
                while (!exit) {
                    r = rand() % (HEIGHT - 2) + 1;
                    c = rand() % (WIDTH - 2) + 1;
                    if (!(actorteleport(r, c, player_character))) {
                        exit = true;
                    }
                }
                break;
            case 27:
                // escape key
                exit = true;
            default:
                // do nothing
                break;
        }
    }
    render_dungeon();
}

// PC attempts to pick up item it is standing on.
uint8_t pc_pickup_obj() {
    int pcloc[2] = {player_character->loc[0], player_character->loc[1]};
    bool success;
    object_c *o;

    if (omap[pcloc[0]][pcloc[1]]) {
        // attempt to pick up object
        o = omap[pcloc[0]][pcloc[1]];
        success = carry(o);

        if (success) {
            // remove object from objList vector
            auto it = std::find(objList.begin(), objList.end(), o);
            if (it != objList.end()) {
                objList.erase(it);
                numobj--;
            }

            omap[o->loc[0]][o->loc[1]] = NULL;  // remove from object map
            // reseting o's location
            o->loc[0] = 0;
            o->loc[1] = 0;
            if (o->odesc->art) {
                // mark artifact as illegibile for future generation
                o->odesc->gen_eligible[1] = false;
            }

            attron(COLOR_PAIR(COLOR_CYAN));
            mvprintw(0, 0, " You picked up %s", o->odesc->name.c_str());
            attroff(COLOR_PAIR(COLOR_CYAN));

            // apply items hitpoint bonus
            player_character->hp += o->hit;
            o->hit = 0;
            return 22;  // general code
        } else {
            return 21;  // inventory failure code;
        }
    }
    return 20;  // no obj failure code
}

// Handles main turnloop for game
// 0 indicates monsters won, 1 indicates PC won
static int8_t turnloop() {
    actor_c *m;
    actor_c *m2;     // to peak
    monster_c *mon;  // to print killed message when dead monster comes through
    char ch;
    uint8_t turn_success, newDungeon;
    fog_toggle = true;
    while ((m = (actor_c *)heap_remove_min(&turnh))) {
        m->hn = NULL;
        m2 = (actor_c *)heap_peek_min(&turnh);
        if (m->hp <= 0) {
            if (is_pc(m->a)) {
                // Monsters won
                render_dungeon();
                return 0;
            } else {
                // dead monster of some sort
                mon = (monster_c *)m;
                if (is_boss(m->a)) {
                    // Boss defeated; Player won
                    score += (mon->mdesc->rrty * 100);
                    render_dungeon();
                    return 1;
                }
                // print message about monster PC killed
                score += (mon->mdesc->rrty * 10);
                if (is_uniq(mon->a)) {
                    mvprintw(0, 0, " You defeated %s (",
                             mon->mdesc->name.c_str());
                    attron(COLOR_PAIR(mon->color));
                    printw("%c", mon->symb);
                    attroff(COLOR_PAIR(mon->color));
                    printw(")");
                } else {
                    mvprintw(0, 0, " You defeated a %s (",
                             mon->mdesc->name.c_str());
                    attron(COLOR_PAIR(mon->color));
                    printw("%c", mon->symb);
                    attroff(COLOR_PAIR(mon->color));
                    printw(")");
                }
            }
        } else if (is_pc(m->a)) {
            if (fog_toggle) {
                render_dungeon_f();
            } else {
                render_dungeon();
            }
            turn_success = newDungeon = 0;
            // take input for movement
            while ((turn_success != 1) && (turn_success != 2)) {
                if (fog_toggle) {
                    render_dungeon_f();
                } else {
                    render_dungeon();
                }
                ch = getch();  // grab input
                // ugly switch case to handle key commands
                switch (ch) {
                    case '7':
                        turn_success = pc_move(up_left);
                        break;
                    case 'y':
                        turn_success = pc_move(up_left);
                        break;
                    case '8':
                        turn_success = pc_move(up);
                        break;
                    case 'k':
                        turn_success = pc_move(up);
                        break;
                    case '9':
                        turn_success = pc_move(up_right);
                        break;
                    case 'u':
                        turn_success = pc_move(up_right);
                        break;
                    case '6':
                        turn_success = pc_move(right);
                        break;
                    case 'l':
                        turn_success = pc_move(right);
                        break;
                    case '3':
                        turn_success = pc_move(down_right);
                        break;
                    case 'n':
                        turn_success = pc_move(down_right);
                        break;
                    case '2':
                        turn_success = pc_move(down);
                        break;
                    case 'j':
                        turn_success = pc_move(down);
                        break;
                    case '1':
                        turn_success = pc_move(down_left);
                        break;
                    case 'b':
                        turn_success = pc_move(down_left);
                        break;
                    case '4':
                        turn_success = pc_move(left);
                        break;
                    case 'h':
                        turn_success = pc_move(left);
                        break;
                    case '5':
                        turn_success = 1;  // No movement; simply resting
                        break;
                    case '.':
                        turn_success = 1;  // No movement; simply resting
                        break;
                    case 32:
                        // space key
                        turn_success = 1;  // No movement; simply resting
                        break;
                    case 'm':
                        turn_success = handle_monster_list();
                        // reset the screen
                        if (fog_toggle) {
                            render_dungeon_f();
                        } else {
                            render_dungeon();
                        }
                        break;
                    case 'f':
                        if (fog_toggle) {
                            fog_toggle = false;
                            render_dungeon();
                        } else {
                            fog_toggle = true;
                            render_dungeon_f();
                        }
                        turn_success = 7;
                        break;
                    case 'g':
                        handle_teleport();
                        turn_success = 1;
                        break;
                    case 'i':
                        list_carry_slots();
                        turn_success = 7;
                        break;
                    case 'w':
                        turn_success = wear_obj();
                        break;
                    case 'e':
                        list_equipment();
                        turn_success = 7;
                        break;
                    case 't':
                        turn_success = takeoff_obj();
                        break;
                    case 'x':
                        // expunge (destroy) item
                        turn_success = expunge_obj();
                        break;
                    case 'd':
                        // drop item
                        turn_success = drop_obj();
                        break;
                    case 'z':
                        // debug; show distance maps
                        render_distmap(walkingDist);
                        attron(COLOR_PAIR(COLOR_YELLOW));
                        mvprintw(
                            0, 0,
                            " Showing walking distance map. 'z' to cycle/end");
                        attroff(COLOR_PAIR(COLOR_YELLOW));
                        while (getch() != 'z');
                        render_distmap(tunnelingDist);
                        attron(COLOR_PAIR(COLOR_YELLOW));
                        mvprintw(0, 0,
                                 " Showing tunneling distance map. 'z' to "
                                 "cycle/end");
                        attroff(COLOR_PAIR(COLOR_YELLOW));
                        while (getch() != 'z');
                        turn_success = 7;
                        break;
                    case 60:
                        // staircase (<)
                        turn_success = attempt_stairs(stair_up);
                        break;
                    case 62:
                        // staircase (>)
                        turn_success = attempt_stairs(stair_down);
                        break;
                    case 'Q':
                        turn_success = 86;
                        break;
                    case 'L':
                        // look at a monster
                        turn_success = inspect_monster_control();
                        // reset the screen
                        if (fog_toggle) {
                            render_dungeon_f();
                        } else {
                            render_dungeon();
                        }
                        break;
                    case 'I':
                        // inspect an item in pc carry slot
                        turn_success = inspect_obj_control();
                        break;
                    case ',':
                        turn_success = pc_pickup_obj();
                        break;
                    default:
                        turn_success = 100;  // key not recognized or not mapped
                        break;
                }
                if (turn_success != 22) {
                    // remove message
                    // code 22 is in item pickup, which creates it's own
                    // message. We don't want to remove that.
                    move(0, 0);
                    clrtoeol();
                }
                // Different messages depending on turn_success value
                if (turn_success == 0) {
                    // Movement error code
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " You Cannot Move There");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 5) {
                    // down staircase errorcode; handlestairs function
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " < Staircase Not Present");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 6) {
                    // up staircase errorcode; handlestairs function
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " > Staircase Not Present");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 10) {
                    // error code in inspect_monster_control
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " No monster at that location");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 20) {
                    // pickup failure (no object present)
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " There is no item here to pick up");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 21) {
                    // pickup failure (inventory failure)
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " You don't have room for this item");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 30) {
                    // carry slot select failure (no item carried)
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0,
                             " You aren't carrying anything in that slot");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 35) {
                    // drop failure (item already in position)
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0,
                             " There is already an item on the floor here");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 40) {
                    // equip failure; item is not an equippable type
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " That item is not equippable");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 45) {
                    // take off failure; no equipped item
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " No item is equipped in that slot");
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (turn_success == 86) {
                    // Fun fact: 86 is also the code to close out (quit) a
                    // register at ALDI, where I currently work.
                    return 2;  // return code to indicate quit
                } else if (turn_success == 100) {
                    attron(COLOR_PAIR(COLOR_CYAN));
                    mvprintw(0, 0, " Key Not Mapped: %c (ASCII %d)", ch, ch);
                    attroff(COLOR_PAIR(COLOR_CYAN));
                } else if (!m2 && turn_success != 22) {
                    // again, 22 code is from item pickup
                    // do not want to overwrite message.
                    attron(COLOR_PAIR(COLOR_GREEN));
                    mvprintw(0, 0, " Level Cleared");
                    attroff(COLOR_PAIR(COLOR_GREEN));
                }
            }
            // Update distance maps; only if new dungeon was not generated
            if (!(turn_success == 2)) {
                calc_walkdist();
                calc_tunneldist();
                m->currTurn = m->currTurn + (1000 / (m->speed));
                m->hn = heap_insert(&turnh, m);
            }
        } else {
            // Monster Turn
            monster_Turn((monster_c *)m);
            m->currTurn = m->currTurn + (1000 / (m->speed));
            m->hn = heap_insert(&turnh, m);
        }
    }
    heap_delete(&turnh);
    return 1;
}

// Main program
int main(int argc, char *argv[]) {
    int i;
    uint32_t longarg, do_l, do_s, parse_print, seed, fpathlen;
    int8_t survive;  // game outcome
    char *home;
    char *fpath;
    actor_c *m2;

    seed = time(NULL);
    srand(seed);
    do_l = do_s = parse_print = 0;

    // NOTE: the next 9 lines (constructing filepath) are essentailly just
    // pulled from piazza from the post demoing how to create the filepath
    // string. It really isn't changed much. So, credit goes to our
    // professor Jeremy Sheaffer for this bit.
    home = getenv("HOME");
    fpathlen =
        strlen(home) + strlen("/.rlg327/dungeon") + 1;  // +1 for the null byte
    fpath = (char *)malloc(fpathlen * sizeof(*fpath));
    if (!fpath) {
        printf("Memory allocation (malloc) error. Quitting.\n");
        return 0;
    }
    strcpy(fpath, home);
    strcat(fpath, "/.rlg327/dungeon");

    printf("Rogue 3270 by Andrew Butler (AjButler@iastate.edu) Spring 2025 \n");
    printf("v1.10 Project Complete \n");

    // Command line parsing; this is mostly pulled from the v1.03 solution
    // by Jeremy Sheaffer, so credit to him.
    if (argc > 1) {
        for (i = 1, longarg = 0; i < argc; i++, longarg = 0) {
            if (argv[i][0] == '-') {
                if (argv[i][1] == '-') {
                    argv[i]++;
                    longarg = 1;
                }
                switch (argv[i][1]) {
                    case 'l':
                        if ((!longarg && argv[i][2]) ||
                            (longarg && strcmp(argv[i], "-load"))) {
                            usage(argv[0]);
                        }
                        do_l = 1;
                        break;
                    case 's':
                        if ((!longarg && argv[i][2]) ||
                            (longarg && strcmp(argv[i], "-save"))) {
                            usage(argv[0]);
                        }
                        do_s = 1;
                        break;
                    case 'n':
                        if ((!longarg && argv[i][2]) ||
                            (longarg && strcmp(argv[i], "-nummon")) ||
                            argc < ++i + 1 /* No more arguments */ ||
                            !sscanf(argv[i], "%d",
                                    &mcount) /* Argument is not an integer */) {
                            usage(argv[0]);
                        }
                        break;
                    case 'p':
                        if ((!longarg && argv[i][2]) ||
                            (longarg && strcmp(argv[i], "-parse"))) {
                            usage(argv[0]);
                        }
                        parse_print = 1;
                        break;
                    default:
                        usage(argv[0]);
                }
            } else {
                usage(argv[0]);
            }
        }
    }

    // now we do the things

    if (parse_print) {
        // we do a little parsing
        std::cout << "MONSTERS: " << std::endl;
        if (!(parse_monsters())) {
            print_monsters();
        } else {
            std::cout << "Monster parse error" << std::endl;
        }
        std::cout << "OBJECTS: " << std::endl;
        if (!(parse_objects())) {
            print_objects();
        } else {
            std::cout << "object parse error" << std::endl;
        }
        delete_mdescriptions();
        delete_odescriptions();
        free(fpath);
        return 0;
    } else {
        init_UI();
        parse_monsters();
        parse_objects();
        while (menu_main()) {
            if (do_l) {
                // printf("Loading dungeon from file . . . ");
                // load from file
                if (loadDungeonFromFile(fpath)) {
                    // printf("failure\n");
                    exit(-1);
                } else {
                    // printf("success\n");
                }
            } else {
                // randomly generate
                // printf("Generate with seed %d\n", seed);
                generate_Dungeon();
            }

            // calling the various initialization things
            calc_tunneldist();
            calc_walkdist();
            generate_Monsters(mcount);
            generate_Objects();

            survive = turnloop();  // main game loop
            // only run exit code if Q not already pressed
            if (survive != 2) {
                if (survive == 1) {
                    // win condition; currently unused
                    attron(COLOR_PAIR(COLOR_GREEN));
                    mvprintw(
                        0, 0,
                        " ==================== Game Over: Boss Monster Was "
                        "Defeated ====================");
                    attroff(COLOR_PAIR(COLOR_GREEN));
                    refresh();
                } else {
                    // loss message
                    attron(COLOR_PAIR(COLOR_RED));
                    mvprintw(
                        0, 0,
                        " ==================== Game Over: PC Was Defeated In "
                        "Battle ====================");
                    attroff(COLOR_PAIR(COLOR_RED));
                    refresh();
                }
                attron(COLOR_PAIR(COLOR_YELLOW));
                mvprintw(HEIGHT + 1, 0, " FINAL SCORE: %d \n", score);
                mvprintw(HEIGHT + 2, 0, " Press 'Q' To return to main menu \n");
                attroff(COLOR_PAIR(COLOR_YELLOW));
                while (getch() != 'Q') {
                }  // wait for user to press key to end
            }

            if (do_s) {
                printf("Saving dungeon to file . . . ");
                if (saveDungeonToFile(fpath)) {
                    printf("failure\n");
                } else {
                    printf("success\n");
                }
            }
            // reset things in case player wants to play again
            // remove player character from actor map
            amap[player_character->loc[0]][player_character->loc[1]] = NULL;
            // remove all monsters / actors from amap
            while ((m2 = (actor_c *)heap_remove_min(&turnh))) {
                amap[m2->loc[0]][m2->loc[1]] = NULL;
            }
            heap_delete(&turnh);  // destroy the turn heap
            score = 0;
            pc_view_dist = 3;
            delete player_character;
            player_character = NULL;
        }
    }
    delete_mdescriptions();
    delete_odescriptions();
    clear();  // clear screen
    refresh();
    endwin();  // close ncurses window
    free(fpath);
    return 0;
}