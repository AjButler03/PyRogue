import dungeon

# This is the main game file. Run This one.

def main():
    d = dungeon.dungeon(20, 80)
    d.generate_dungeon()
    print("Dungeon Terrain Map:")
    d.print_terrain()
    print()
    print("Dungeon Rock Hardness Map:")
    d.print_rockmap()

if __name__ == "__main__":
    main()