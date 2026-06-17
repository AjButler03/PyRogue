import logging

import re
from importlib import resources
from .utility import Dice
from .actor import *

logger = logging.getLogger(__name__)


# This file reads manual.txt,  monster_desc.txt, and item_desc.txt to get the manual pages, monster definitions, and item definitions, respectively.


# Takes a string in the format {base}+{num}d{sides} and creates a dice object.
def dice_from_str(str: str):
    match = re.fullmatch(r"(\d+)\+(\d+)d(\d+)", str.strip())
    if not match:
        # Just return false for failure
        return False, None
    base, num, sides = map(int, match.groups())
    return True, Dice(base, num, sides)


# Simple text parser for the manual page. Will just read whatever is typed up in manual.txt, storing that text to be displayed in the manual page.
def parse_manual_text(man_pages: list) -> bool:
    # Attempt to open file
    try:
        with resources.open_text("pyrogue.gamedata", "manual.txt") as file:
            file_lines = file.readlines()
            curr_line = 0
            logger.debug("PARSEDESC: manual.txt opened... ")

    except FileNotFoundError:
        # File wasn't found, return False for failure
        logger.error("PARSEDESC: manual.txt not found")
        return False

    # Start reading the lines, first checking that the file header matches
    line = file_lines[curr_line]
    line = line.strip()
    pages_found = 0
    if line == "PYROGUE MANUAL PAGES TEXT FILE":
        logger.debug("file header matches")
        # Header match; read text for all pages
        curr_line += 1
        line_count = len(file_lines)
        logger.debug(f"PARSEDESC: manual.txt read with {line_count} lines")
        while curr_line < line_count:
            line = file_lines[curr_line].strip()
            # Check for the beginning of a page
            if line == "BEGIN PAGE":
                page = []  # Store lines of page
                # Now just copy all lines until "END PAGE"
                curr_line += 1
                line = file_lines[curr_line]
                while line.strip() != "END PAGE":
                    # Make sure that we don't read past end of file
                    if curr_line >= line_count:
                        # Did not find termination ".", so the file is not formatted correctly. Return False.
                        logger.error(
                            f"PARSEDESC: Manual page idx {pages_found} does not terminate correctly"
                        )
                        return False
                    else:
                        # add line to page, read next line
                        page.append(line)
                        curr_line += 1
                        line = file_lines[curr_line]
                # End of page found, so append page to page list.
                man_pages.append(page)
                pages_found += 1
            curr_line += 1
        # If here without any error, then parsed successfully.
        logger.debug(f"PARSEDESC: Found {pages_found} manual pages")
        return True
    else:
        logger.error("PARSEDESC: Header mismatch in manual.txt")
        return False


# Method to parse monster descriptions. Returns True on success, False on failure.
def parse_monster_typedefs(monster_type_list: list) -> bool:
    # Attempt to open file
    try:
        with resources.open_text("pyrogue.gamedata", "monster_desc.txt") as file:
            file_lines = file.readlines()
            curr_line = 0  # To point to next line to look at
            logger.debug("PARSEDESC: monster_desc.txt opened... ")
    except FileNotFoundError:
        # File wasn't found; return False for failure
        logger.error("PARSEDESC: monster_desc.txt not found")
        return False

    # Start reading the lines, first checking that file header matches
    line = file_lines[curr_line]
    line = line.strip()
    types_found = 0
    if line == "PYROGUE MONSTER DESCRIPTION FILE":
        logger.debug("file header matches")
        # Header matches; now read the monster descriptions
        curr_line += 1
        line_count = len(file_lines)
        logger.debug(f"PARSEDESC: monster_desc.txt read with {line_count} lines")
        while curr_line < line_count:
            line = file_lines[curr_line].strip()
            # Check for beginning of monster definition
            if line == "BEGIN MONSTER":
                curr_line += 1
                # Init all fields to None, with the intention of populating them with actual values.
                name = desc = color = abil = speed = hp = dam = symb = rrty = None
                is_uniq = False

                line = file_lines[curr_line].strip()
                while line != "END":
                    if line.startswith("NAME"):
                        # Parse name field
                        name = line[5:].strip()
                    elif line.startswith("DESC"):
                        # Parse text description field; read until "." found
                        curr_line += 1
                        line = file_lines[curr_line]
                        desc = []
                        while line.strip() != ".":
                            # Check to make sure that we don't try and read past the end of the file
                            if curr_line >= line_count:
                                # Did not find termination ".", so the file is not formatted correctly. Return False.
                                logger.error(
                                    f"PARSEDESC: Monster definition idx {types_found} has incorrect DESC field"
                                )
                                return False
                            else:
                                # Read line; add to desc field
                                desc.append(line)
                                curr_line += 1
                                line = file_lines[curr_line]
                    elif line.startswith("COLOR"):
                        # Parse color field(s), placing into list
                        line = line[
                            6:
                        ].strip()  # Remove "COLOR " and newline character from line
                        color = line.split()  # Split into the color keywords
                    elif line.startswith("ABIL"):
                        # Parse abilities field(s)
                        line = line[
                            5:
                        ].strip()  # Remove "ABIL " and newline character from line
                        abil_keys = line.split()  # Split into the ability keywords
                        abil = 0b0000_0000_0000_0000  # Init ability bitfield
                        for currkey in abil_keys:
                            # Determine what the keyword indicates; add that ability.
                            # There are 9 possibilites; not all are fully implented in monsters, but still want to parse them.
                            if currkey == "SMART":
                                abil = add_attribute(abil, ATTR_INTELLIGENT)
                            elif currkey == "TELE":
                                abil = add_attribute(abil, ATTR_TELEPATHIC_)
                            elif currkey == "TUNNEL":
                                abil = add_attribute(abil, ATTR_TUNNEL_____)
                            elif currkey == "ERRATIC":
                                abil = add_attribute(abil, ATTR_ERRATIC____)
                            elif currkey == "PASS":
                                abil = add_attribute(abil, ATTR_PASS_______)
                            elif currkey == "PICKUP":
                                abil = add_attribute(abil, ATTR_PICKUP_____)
                            elif currkey == "DESTROY":
                                abil = add_attribute(abil, ATTR_DESTROY____)
                            elif currkey == "UNIQ":
                                abil = add_attribute(abil, ATTR_UNIQ_______)
                                is_uniq = True
                            elif currkey == "BOSS":
                                abil = add_attribute(abil, ATTR_BOSS_______)
                    elif line.startswith("SPEED"):
                        # Parse speed field
                        line = line[
                            6:
                        ]  # Remove "SPEED " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            speed = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Monster definition idx {types_found} has incorrect SPEED field"
                            )
                            return False
                    elif line.startswith("HP"):
                        # Parse health field
                        line = line[3:]  # Remove "HP " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            hp = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Monster definition idx {types_found} has incorrect HP field"
                            )
                            return False
                    elif line.startswith("DAM"):
                        # Parse damage field
                        line = line[4:]  # Remove "DAM " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            dam = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(f"PARSEDESC: Monster definition idx {types_found} has incorrect DAM field")
                            return False
                    elif line.startswith("SYMB"):
                        symb = line[5]  # 5th character will be the symbol
                    elif line.startswith("RRTY"):
                        # Parse rarity field
                        match = re.fullmatch(r"RRTY (\d+)", line.strip())
                        if not match:
                            # return False for format mismatch
                            logger.error(f"PARSEDESC: Monster definition idx {types_found} has incorrect RRTY field")
                            return False
                        else:
                            rrty = int(match.group(1))
                    curr_line += 1
                    line = file_lines[curr_line].strip()
                # Check that all fields were filled
                complete = (
                    name != None
                    and desc != None
                    and color != None
                    and abil != None
                    and speed != None
                    and hp != None
                    and dam != None
                    and symb != None
                    and rrty != None
                )
                if complete:
                    # Append the new monster type definition
                    monster_type_list.append(
                        Monster_Typedef(
                            name,
                            symb,
                            desc,
                            color,
                            abil,
                            speed,
                            hp,
                            dam,
                            rrty,
                            is_uniq,
                        )
                    )
                    types_found += 1
                else:
                    # One or more fields were not found; return False, as there is an incomplete definition
                    logger.error(f"PARSEDESC: Monster definition idx {types_found} is incomplete")
                    error = "     Missing fields: "
                    if name == None:
                        error += "NAME "
                    if symb == None:
                        error += "SYMB "
                    if desc == None:
                        error += "DESC "
                    if color == None:
                        error += "COLOR "
                    if abil == None:
                        error += "ABIL "
                    if speed == None:
                        error += "SPEED "
                    if hp == None:
                        error += "HP "
                    if dam == None:
                        error += "DAM "
                    if rrty == None:
                        error += "RRTY "
                    logger.error(error)
                    return False
            curr_line += 1

        logger.debug(f"PARSEDESC: Found {types_found} Monster definitions")
        return True  # True for success
    else:
        # Header does not match; file is probably in incorrect format
        # Return False for failure
        logger.error("Header mismatch")
        return False


# Method to parse item descriptions. Returns True on success, False on failure.
def parse_item_typedefs(item_type_list: list) -> bool:
    # Attempt to open file
    try:
        with resources.open_text("pyrogue.gamedata", "item_desc.txt") as file:
            file_lines = file.readlines()
            curr_line = 0  # To point to next line to look at
            logger.debug("PARSEDESC: item_desc.txt opened... ")
    except FileNotFoundError:
        # File wasn't found; return False for failure
        logger.error("PARSEDESC: item_desc.txt not found")
        return False

    # Start reading the lines, first checking that file header matches
    line = file_lines[curr_line]
    line = line.strip()
    types_found = 0
    if line == "PYROGUE ITEM DESCRIPTION FILE":
        logger.debug("file header matches")
        # Header matches; now read the monster descriptions
        curr_line += 1
        line_count = len(file_lines)
        logger.debug(f"PARSEDESC: item_desc.txt read with {line_count} lines")
        while curr_line < line_count:
            line = file_lines[curr_line].strip()
            # Check for beginning of monster definition
            if line == "BEGIN ITEM":
                curr_line += 1
                # Init all fields to None, with the intention of populating them with actual values.
                name = desc = itype = color = hp = dam = attr = defense = dodge = (
                    speed
                ) = rarity = artifact = None

                line = file_lines[curr_line].strip()
                while line != "END":
                    if line.startswith("NAME"):
                        # Parse name field
                        name = line[5:].strip()
                    elif line.startswith("TYPE"):
                        type_key = line[5:].strip()
                        if type_key not in item_type_opts:
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} is unknown type '{type_key}'"
                            )
                            return False
                        else:
                            itype = item_type_opts[type_key]

                    elif line.startswith("DESC"):
                        # Parse text description field; read until "." found
                        curr_line += 1
                        line = file_lines[curr_line]
                        desc = []
                        while line.strip() != ".":
                            # Check to make sure that we don't try and read past the end of the file
                            if curr_line >= line_count:
                                # Did not find termination ".", so the file is not formatted correctly. Return False.
                                logger.error(
                                    f"PARSEDESC: Item definition idx {types_found + 1} has incorrect DESC field"
                                )
                                return False
                            else:
                                # Read line; add to desc field
                                desc.append(line)
                                curr_line += 1
                                line = file_lines[curr_line]
                    elif line.startswith("COLOR"):
                        # Parse color field(s), placing into list
                        line = line[
                            6:
                        ].strip()  # Remove "COLOR " and newline character from line
                        color = line.split()  # Split into the color keywords
                    elif line.startswith("SPEED"):
                        # Parse speed field
                        line = line[
                            6:
                        ]  # Remove "SPEED " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            speed = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} has incorrect SPEED field"
                            )
                            return False
                    elif line.startswith("HIT"):
                        # Parse health field
                        line = line[3:]  # Remove "HP " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            hp = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} has incorrect HP field"
                            )
                            return False
                    elif line.startswith("DAM"):
                        # Parse damage field
                        line = line[4:]  # Remove "DAM " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            dam = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} has incorrect DAM field"
                            )
                            return False
                    elif line.startswith("ATTR"):
                        # Parse ATTR, or special field
                        line = line[
                            5:
                        ]  # Remove "ATTR " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            attr = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} has incorrect ATTR field"
                            )
                            return False
                    elif line.startswith("DEF"):
                        # Parse defense field
                        line = line[4:]  # Remove "DEF " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            defense = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} has incorrect DEF field"
                            )
                            return False
                    elif line.startswith("DODGE"):
                        # Parse dodge field
                        line = line[
                            6:
                        ]  # Remove "DODGE " and newline character from line
                        success, dice = dice_from_str(line)
                        if success:
                            dodge = dice
                        else:
                            # Formatting error; return False for read failure
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} has incorrect DODGE field"
                            )
                            return False
                    elif line.startswith("RRTY"):
                        # Parse rarity field
                        match = re.fullmatch(r"RRTY (\d+)", line.strip())
                        if not match:
                            # return False for format mismatch
                            logger.error(
                                f"PARSEDESC: Item definition idx {types_found + 1} has incorrect RRTY field"
                            )
                            return False
                        else:
                            rrty = int(match.group(1))
                    elif line.startswith("ART"):
                        line = line[4:].strip()
                        if line == "TRUE":
                            artifact = True
                        else:
                            artifact = False
                    curr_line += 1
                    line = file_lines[curr_line].strip()
                # Check that all fields were filled
                complete = (
                    name != None
                    and itype != None
                    and desc != None
                    and color != None
                    and speed != None
                    and hp != None
                    and dam != None
                    and attr != None
                    and defense != None
                    and dodge != None
                    and rrty != None
                    and artifact != None
                )
                if complete:
                    # Append the new item type definition
                    item_type_list.append(
                        Item_Typedef(
                            name,
                            itype,
                            desc,
                            color,
                            hp,
                            dam,
                            attr,
                            defense,
                            dodge,
                            speed,
                            rrty,
                            artifact,
                        )
                    )
                    types_found += 1
                else:
                    # One or more fields were not found; return False, as there is an incomplete definition
                    logger.error(
                        f"PARSEDESC: Item definition idx {types_found + 1} is incomplete"
                    )
                    error = "     Missing fields: "
                    if name == None:
                        error += "NAME "
                    if itype == None:
                        error += "TYPE "
                    if desc == None:
                        error += "DESC "
                    if color == None:
                        error += "COLOR "
                    if speed == None:
                        error += "SPEED "
                    if hp == None:
                        error += "HP "
                    if dam == None:
                        error += "DAM "
                    if attr == None:
                        error += "ATTR "
                    if defense == None:
                        error += "DEF "
                    if dodge == None:
                        error += "DODGE"
                    if rrty == None:
                        error += "RRTY "
                    if artifact == None:
                        error += "ART "
                    logger.error(error)
                    return False
            curr_line += 1

        logger.info(f"PARSEDESC: Found {types_found} Item definitions")
        return True  # True for success
    else:
        # Header does not match; file is probably in incorrect format
        # Return False for failure
        logger.error("PARSEDESC: Header mismatch")
        return False


# FOR TESTING PURPOSES
# def print_monst_defs(monster_type_list: list):
#     num = 1
#     for mdef in monster_type_list:
#         print("MONSTER TYPE DEFINITION", num)
#         print(mdef)
#         num += 1


# FOR TESTING PURPOSES
# def print_item_defs(item_type_list: list):
#     num = 1
#     for idef in item_type_list:
#         print("ITEM TYPE DEFINITION", num)
#         print(idef)
#         num += 1
