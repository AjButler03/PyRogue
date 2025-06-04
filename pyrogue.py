import dungeon
import actor
import random

# This is the main game file. Run This one.

# This prints the dungeon to console, overlaying actor positions on the terrain.
def render_dungeon(dungeon, actor_map):
    for r in range(dungeon.height):
        for c in range(dungeon.width):
            t_type = dungeon.tmap[r][c]
            if actor_map[r][c] != None:
                # Print the actor's character representation
                # For now, there is only the PC. So just '@'.
                print('\033[94m@\033[0m', end="")
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

def main():
    h = 20
    w = 80
    d = dungeon.dungeon(h, w)
    d.generate_dungeon()
    print("Dungeon Terrain Map:")
    d.print_terrain()
    
    print()
    print("Dungeon Rock Hardness Map:")
    d.print_rockmap()
    
    # Init actor map, storing where actors are relative to the dungeon
    actor_map = [[None] * d.width for _ in range(d.height)]
    
    # Create player character
    pc = actor.player()
    
    # Place pc into the dungeon
    while not pc.init_pos(d, actor_map, random.randint(1, h - 2), random.randint(1, w - 2)):
        pass
    
    d.calc_dist_maps(pc.r, pc.c)
    print()
    print("Walking Distance Map:")
    d.print_walk_distmap()
    print()
    print("Tunneling Distance Map:")
    d.print_tunn_distmap()
    
    print()
    print("Dungeon Render:")
    render_dungeon(d, actor_map)
    
if __name__ == "__main__":
    main()