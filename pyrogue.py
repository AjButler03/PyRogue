import dungeon
import actor
import random
from utility import exp_chancetime
from utility import PriorityQueue

# This is the main game file. Run This one.


# This prints the dungeon to console, overlaying actor positions on the terrain.
def render_dungeon(dungeon, actor_map):
    for r in range(dungeon.height):
        for c in range(dungeon.width):
            t_type = dungeon.tmap[r][c]
            if actor_map[r][c] != None:
                actor_inst = actor_map[r][c]
                # Check object type
                if isinstance(actor_inst, actor.player):
                    print("\033[34m@\033[0m", end="")
                else:
                    print("\033[31mM\033[0m", end="")
            elif t_type == dungeon.terrain.floor:
                print(".", end="")
            elif t_type == dungeon.terrain.stair:
                print("<", end="")
            elif t_type == dungeon.terrain.stdrock:
                print(" ", end="")
            elif t_type == dungeon.terrain.immrock:
                print("X", end="")  # will want to be a proper border later
            else:
                print("!", end="")  # issue flag
        print("")  # Newline for end of row


# Populates the actor_map with a dungeon size proportionate number of monsters.
# Difficulty is a modifier for the spawn rate of monsters in the dungeon.
def generate_monsters(dungeon, actor_map, monster_list, difficulty):
    attemptc = 0
    monsterc = 0
    attempt_limit = int(difficulty * max(dungeon.width, dungeon.height))
    min_monsterc = max(1, attempt_limit // 10)
    # Adjust exp_chancetime's decay curve to increase additional monster probability with difficulty
    decay_rate = 0.95 / (difficulty + 0.5)
    print("Min # Monsters:", min_monsterc)
    print("Monster Placement Attempt Limit:", attempt_limit)
    print("New Decay Rate:", decay_rate)

    # Generate monsters; runs until minimum number and attempt limit are met
    while (monsterc < min_monsterc) or (attemptc < attempt_limit):
        # Create monster
        monster = actor.monster(0)
        if monsterc <= min_monsterc or exp_chancetime(
            monsterc - min_monsterc, decay_rate
        ):
            if monster.init_pos(
                dungeon,
                actor_map,
                random.randint(1, dungeon.height - 2),
                random.randint(1, dungeon.width - 2),
            ):
                monsterc += 1
                monster_list.append(monster)
        attemptc += 1
    print("Monsters placed:", monsterc)


def main():
    h = 20
    w = 80
    d = dungeon.dungeon(h, w)
    d.generate_dungeon()
    # Difficulty modifies the monster spawn rate
    # 0.25 => easy, 0.75 => normal, 1.25 => hard, 1.75 => very hard
    difficulty = 0.75

    # Init actor map, storing where actors are relative to the dungeon
    actor_map = [[None] * d.width for _ in range(d.height)]

    # Create player character
    pc = actor.player()

    # Place pc into the dungeon
    while not pc.init_pos(
        d, actor_map, random.randint(1, h - 2), random.randint(1, w - 2)
    ):
        pass

    d.calc_dist_maps(pc.r, pc.c)

    # Generate the monsters
    monster_list = []
    generate_monsters(d, actor_map, monster_list, 0.75)

    print("Dungeon Render:")
    render_dungeon(d, actor_map)
    
    pc.handle_turn(d, actor_map)


if __name__ == "__main__":
    main()
