from utility import Dice

# This file will read monster_desc.txt and object_desc.txt to populate lists of monster descriptions and item descriptions, respectively.


# Method to parse monster descriptions. Returns True on success, False on failure.
def parse_monsters(monster_type_list) -> bool:
    # Bool fields to make sure that everything was found in file
    name = desc = color = abil = speed = hp = dam = symb = rrty = False

    # Attempt to open file
    try:
        with open("monster_desc.txt", "r") as file:
            fcontent = file.read()
            print("PARSEDESC: Reading Monster types")
    except FileNotFoundError:
        print("PARSEDESC: monster_desc.txt not found")
