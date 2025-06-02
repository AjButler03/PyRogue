import dungeon
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
    
    d.calc_dist_maps(random.randint(1, h - 2), random.randint(1, w - 2))
    print()
    print("Walking Distance Map:")
    d.print_walk_distmap()
if __name__ == "__main__":
    main()