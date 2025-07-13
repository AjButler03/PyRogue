from utility import Dice

# This file will read monster_desc.txt and object_desc.txt to populate lists of monster descriptions and item descriptions, respectively.


# Method to parse monster descriptions. Returns True on success, False on failure.
def parse_monsters(monster_type_list) -> bool:
    # Attempt to open file
    try:
        with open("monster_desc.txt", "r") as file:
            file_lines = file.readlines()
            curr_line = 0 # To point to next line to look at
            print("PARSEDESC: monster_desc.txt opened... ", end="")
    except FileNotFoundError:
        # File wasn't found; return False for failure
        print("PARSEDESC: monster_desc.txt not found")
        return False
    
    # Start reading the lines, first checking that file header matches
    line = file_lines[curr_line]
    line = line.strip()
    if line == "PYROGUE MONSTER DESCRIPTION FILE":
        print("file header matches")
        
        # Header matches; now read the monster descriptions
        curr_line += 1
        line_count = len(file_lines)
        while curr_line < line_count:
            line = file_lines[curr_line].strip()
            # Check for beginning of monster definition
            if line == "BEGIN MONSTER":
                curr_line += 1
                # Init all fields to None, with the intention of populating them with actual values.
                name = desc = color = abil = speed = hp = dam = symb = rrty = None
                
                line = file_lines[curr_line].strip()
                while line != "END":
                    if line.startswith("NAME"):
                        # Parse name field
                        name = line[0:4]
                    elif line.startswith("DESC"):
                        # Parse text description field; read until "." found
                        curr_line += 1 # move to the line that starts the actual description
                        line = file_lines[curr_line]
                        desc = ""
                        while line != ".":
                            # Check to make sure that we don't try and read past the end of the file
                            if curr_line >= line_count:
                                # Did not find termination ".", so the file is not formatted correctly. Return False.
                                return False
                            else:
                                # Read line; add to desc field
                                desc += line
                                curr_line += 1
                                line = file_lines[curr_line]
                    elif line.startswith("COLOR"):
                        # Parse color field(s)
                        # TODO
                        pass
                    elif line.startswith("ABIL"):
                        # Parse abilities field(s)
                        # TODO
                        pass
                    elif line.startswith("SPEED"):
                        # Parse speed field
                        # TODO
                        pass
                    elif line.startswith("HP"):
                        # Parse health field
                        # TODO
                        pass
                    elif line.startswith("DAM"):
                        # Parse damage field
                        # TODO
                        pass
                    elif line.startswith("SYMB"):
                        # Parse character symbol field
                        # TODO
                        pass
                    elif line.startswith("RRTY"):
                        # Parse rarity field
                        # TODO
                        pass
    else:
        # Header does not match; file is probably in incorrect format
        # Return False for failure
        print("header mismatch")
        return False
    
        
        
