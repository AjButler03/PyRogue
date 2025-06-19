import dungeon
import actor
import random
import time
import tkinter as tk
from utility import PriorityQueue
from game import pyrogue_game

# This is the main game file. Run This one.


# This prints the dungeon to console, overlaying actor positions on the terrain.
# Leftover from initial development without tkinter UI.
# def render_dungeon(dungeon, actor_map):
#     for r in range(dungeon.height):
#         for c in range(dungeon.width):
#             t_type = dungeon.tmap[r][c]
#             if actor_map[r][c] != None:
#                 actor_inst = actor_map[r][c]
#                 # Check object type
#                 if isinstance(actor_inst, actor.player):
#                     print("\033[34m", end="")
#                     print(actor_inst.get_char(), end="")
#                     print("\033[0m", end="")
#                 else:
#                     # This is an ugly print statement which easily shows attribute combinations for monsters.
#                     # Eventually, monsters will have more unique symbols.
#                     print("\033[31m", end="")
#                     print(actor_inst.char, end="")
#                     print("\033[0m", end="")
#             elif t_type == dungeon.terrain.floor:
#                 print(".", end="")
#             elif t_type == dungeon.terrain.stair:
#                 print("<", end="")
#             elif t_type == dungeon.terrain.stdrock:
#                 print(" ", end="")
#             elif t_type == dungeon.terrain.immrock:
#                 print("X", end="")  # will want to be a proper border later
#             else:
#                 print("!", end="")  # issue flag
#         print("")  # Newline for end of row


# Handles the main turnloop for the game, discrete-event simulation style.
def turnloop(dungeon, pc, monster_list, actor_map):
    # Create priorityqueue, starting player with turn 0 and monsters with 10 (player goes first)
    pq = PriorityQueue()
    pq.push(pc, 0)
    for monster in monster_list:
        monster.set_currturn(10)
        pq.push(monster, 10)

    while len(pq) > 1 and pc.is_alive():
        _, a = pq.pop()
        # Double check that actor has not died; If it has, ignore and move on
        if a.is_alive():
            targ_a, dmg_dealt = a.handle_turn(dungeon, actor_map, pc)
            curr_turn = a.get_currturn()
            new_turn = curr_turn + a.get_speed()
            a.set_currturn(new_turn)
            pq.push(a, new_turn)
            if isinstance(a, actor.player):
                # print("Turn:", curr_turn)
                if targ_a != None:
                    print("You Killed a", targ_a.get_char())
                render_dungeon(dungeon, actor_map)
                time.sleep(0.25)
            elif isinstance(targ_a, actor.player):
                print("a", a.get_char(), "killed you")


def main():
    screen_h = 720
    screen_w = 1280
    map_h = 30
    map_w = 60
    # Easy: 0.25, normal: 0.75, hard = 1.25
    difficulty = 0.75
    root = tk.Tk()
    root.title("Dungeon render test")
    game = pyrogue_game(root, screen_h, screen_w, map_h, map_w, difficulty)
    root.mainloop()


if __name__ == "__main__":
    main()
