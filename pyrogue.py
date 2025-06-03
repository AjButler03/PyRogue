import dungeon
import actor
import random

# This is the main game file. Run This one.

def main():
    h = 20
    w = 80
    d = dungeon.dungeon(h, w)
    d.generate_dungeon()
    print("Dungeon Terrain Map:")
    d.print_terrain()
    
    # print()
    # print("Dungeon Rock Hardness Map:")
    # d.print_rockmap()
    
    # Create player character
    pc = actor.player()
    
    # Place pc into the dungeon
    while not pc.init_pos(d, random.randint(1, h - 2), random.randint(1, w - 2)):
        pass
    
    d.calc_dist_maps(pc.r, pc.c)
    print()
    print("Walking Distance Map:")
    d.print_walk_distmap()
    print()
    print("Tunneling Distance Map:")
    d.print_tunn_distmap()
    
if __name__ == "__main__":
    main()