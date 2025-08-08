import random
import abc
import copy
from enum import Enum
from dungeon import *
from utility import *

# This file contains the class information for 'actors' - Monsters, the player, and the various items.

# A monster can have any number of attributes. I will be indicating these using a bit field.
# For v03, only the first 4 will be fully implemented. The others will come later, if I decide to do them at all.
ATTR_INTELLIGENT = 0b0000_0000_0000_0001  # Bit 1 (0000 0000 0000 0001)
ATTR_TELEPATHIC_ = 0b0000_0000_0000_0010  # Bit 2 (0000 0000 0000 0010)
ATTR_TUNNEL_____ = 0b0000_0000_0000_0100  # Bit 3 (0000 0000 0000 0100)
ATTR_ERRATIC____ = 0b0000_0000_0000_1000  # Bit 4 (0000 0000 0000 1000)
ATTR_PASS_______ = 0b0000_0000_0001_0000  # Bit 5 (0000 0000 0001 0000)
ATTR_PICKUP_____ = 0b0000_0000_0010_0000  # Bit 6 (0000 0000 0010 0000)
ATTR_DESTROY____ = 0b0000_0000_0100_0000  # Bit 7 (0000 0000 0100 0000)
ATTR_UNIQ_______ = 0b0000_0000_1000_0000  # Bit 8 (0000 0000 1000 0000)
ATTR_BOSS_______ = 0b0000_0001_0000_0000  # Bit 9 (0000 0001 0000 0000)

# For defining types by string in file
item_type_opts = {
    "POTION": 0,
    "WEAPON": 1,
    "RANGED": 2,
    "OFFHAND": 3,
    "ARMOR": 4,
    "AMULET": 5,
    "LIGHT": 6,
    "RING": 7,
}

# Shortcut to turn type (int) back into corresponding string
_item_type_to_str = {
    0: "POTION",
    1: "WEAPON",
    2: "RANGED",
    3: "OFFHAND",
    4: "ARMOR",
    5: "AMULET",
    6: "LIGHT",
    7: "RING",
}

# Universal symbols depending on type
_item_symb_by_type = {
    0: "!",  # Potion
    1: "|",  # Weapon
    2: "}",  # Ranged
    3: ")",  # Offhand
    4: "[",  # Armor
    5: '"',  # Amulet
    6: "_",  # Light
    7: "=",  # Ring
}


# Activates a given attribute bit, returning the new integer value.
def add_attribute(curr_attributes: int, new_attr: int):
    curr_attributes |= new_attr
    return curr_attributes


# Returns True if the given attribute is activated in the given bitfield, False otherwise.
def has_attribute(curr_attributes: int, new_attr: int) -> bool:
    return (curr_attributes & new_attr) != 0


# Enum to define moves, whose values correspond to the move's idx in the coordinate deltas
class Move(Enum):
    up_left = 0
    up = 1
    up_right = 2
    left = 3
    right = 4
    down_left = 5
    down = 6
    down_right = 7
    none = 8


# Class to store item type definitions, which instantiated items will be based on.
class Item_Typedef:

    # Item_Definition constructor
    def __init__(
        self,
        name: str,
        type: int,
        desc: list,
        colors: list,
        hp: Dice,
        damage: Dice,
        attr: Dice,
        defense: Dice,
        dodge: Dice,
        speed: Dice,
        rarity: int,
        artifact: bool,
    ):
        self.name = name
        self.type = type
        self.desc = desc
        self.colors = colors
        self.hp_dice = hp
        self.damage_dice = damage
        self.attr_dice = attr
        self.defense_dice = defense
        self.dodge_dice = dodge
        self.speed_dice = speed
        self.rarity = rarity
        self.artifact = artifact
        self.gen_eligible = True

    def get_name(self) -> str:
        return self.name

    def get_symb(self) -> str:
        return _item_symb_by_type[self.type]

    def get_type_str(self) -> str:
        return _item_type_to_str[self.type]

    def get_type(self) -> int:
        return self.type

    def get_single_color(self) -> str:
        return self.colors[random.randint(0, len(self.colors) - 1)]

    def get_desc(self) -> list:
        return self.desc

    def get_hp_restore_str(self) -> str:
        return str(self.hp_dice)

    def get_damage_str(self) -> str:
        return str(self.damage_dice)

    def get_attr_str(self) -> str:
        return str(self.attr_dice)

    def get_defense_str(self) -> str:
        return str(self.defense_dice)

    def get_dodge_str(self) -> str:
        return str(self.dodge_dice)

    def get_speed_str(self) -> str:
        return str(self.speed_dice)

    def get_rarity(self) -> int:
        return self.rarity

    def is_gen_eligible(self) -> bool:
        return self.gen_eligible

    def is_artifact(self) -> bool:
        return self.artifact

    def __str__(self):
        string = "NAME: "
        # print name
        string += self.name + "\n"
        # print item type
        string += "TYPE: " + _item_type_to_str[self.type] + "\n"
        # print desc
        string += "DESCRIPTION: \n"
        for line in self.desc:
            string += line
        # print color(s)
        string += "COLORS: "
        for color in self.colors:
            string += color + " "
        string += "\n"
        # print speed
        string += "SPEED: " + str(self.speed_dice) + "\n"
        # print hp
        string += "HEALTH: " + str(self.hp_dice) + "\n"
        # print dam
        string += "DAMAGE: " + str(self.damage_dice) + "\n"
        # print attr
        string += "ATTR: " + str(self.attr_dice) + "\n"
        # print defense
        string += "DEFENSE: " + str(self.defense_dice) + "\n"
        # print dodge
        string += "DODGE: " + str(self.dodge_dice) + "\n"
        # print rrty
        string += "RRTY: " + str(self.rarity) + "\n"
        # Print artifact status
        if self.artifact:
            string += "ART: True\n"
        else:
            string += "ART: FALSE\n"
        return string + "\n"


# Class to instantiate an item based on it's Item_Typedef definition.
class Item:

    def __init__(self, item_typedef: Item_Typedef):
        # Remember type definition
        self.typedef = item_typedef

        # Health restore
        self.hp_restore = self.typedef.hp_dice.roll()

        # Remember damage dice pointer (is it a pointer in python?)
        self.damage_dice = self.typedef.damage_dice

        # Misc Attr value
        self.attr = self.typedef.attr_dice.roll()

        # Defense bonus
        self.defense = self.typedef.defense_dice.roll()

        # Dodge Bonus
        self.dodge = self.typedef.dodge_dice.roll()

        # Speed Bonus
        self.speed = self.typedef.speed_dice.roll()

        # To make sure one-time bonuses can't be repeatedly applied
        self.used = False
        # To disable generation on artifact items once they have been picked up (interacted with)
        self.picked_up = False

        # Placeholder for position information
        self.r = 0
        self.c = 0

    # Determines if the item can be at this position.
    def _valid_pos(self, dungeon: Dungeon, r: int, c: int) -> bool:
        """
        This function checks that the row, column coordinate is a valid position for the item to be within the dungeon.
        Returns True if it is, False otherwise.
        """

        if dungeon.valid_point(r, c):
            if dungeon.rmap[r][c] == 0:
                return True
        return False

    # This method is to initialize the position of the item within the dungeon, verifying the location as valid.
    # Returns True on successful placement, False otherwise.
    def init_pos(self, dungeon: Dungeon, item_map: list, r: int, c: int) -> bool:
        if (
            dungeon.valid_point(r, c)
            and dungeon.rmap[r][c] == 0
            and item_map[r][c] == None
        ):
            self.r = r
            self.c = c
            item_map[r][c] = self
            return True
        else:
            return False

    # Returns the single character to represent this item in the dungeon.
    def get_char(self):
        return self.typedef.get_symb()

    def get_name(self):
        return self.typedef.get_name()

    def get_type(self):
        return self.typedef.get_type()

    # Returns a str keyword for a single Tkinter color.
    def get_color(self):
        return self.typedef.get_single_color()

    def is_unique(self):
        return self.typedef.artifact

    def set_picked_up(self, bool):
        self.picked_up = bool

    def get_picked_up_status(self):
        # Once picked up at all, this should be true. Even after dropping the item.
        return self.picked_up

    def get_used_status(self):
        return self.used

    # resets generation eligibility of type definition
    def update_gen_eligible(self, is_new_item: bool, force_reset: bool):
        """
        This function updates the generation eligibility of this item's type definition.
        It is only intended to be called in a few circumstances:
        A) Initial generation, in which case it will be updated to False if this is an artifact.
        B) Changing to new dungeon level, in which case the eligibility will be updated based on uniqueness.
        C) Game over, in which case it will be force updated back to True.

        Calling this method in any other situation will likely produce unintended behavior.

        The first parameter, is_new_item, is a boolean if this is the first call after creating the item.
            This should be false anytime except immediately following the creation of a item instance.
        The second parameter, force_rest, indicates that the game is over and eligibility should be automatically reset to True.
        """
        if force_reset:
            # Force reset to True
            self.typedef.gen_eligible = True
        elif self.typedef.artifact:
            if is_new_item:
                # Newly generated item, so set eligibility to False so there aren't duplicates.
                self.typedef.gen_eligible = False
            elif not self.picked_up and not is_new_item:
                # has not been interacted with, and not the initial generation.
                # This will reset to True for a new dungeon (presumably why this was called)
                self.typedef.gen_eligible = True


# Class to store monster type definitions, which instantiated monsters will be based on.
class Monster_Typedef:

    # Monster_Type constructor
    def __init__(
        self,
        name: str,
        symb: str,
        desc: list,
        colors: list,
        abilities: int,
        speed_dice: Dice,
        health_dice: Dice,
        damage_dice: Dice,
        rarity: int,
        is_unique: bool,
    ):
        self.name = name
        self.symb = symb
        self.desc = desc
        self.colors = colors
        self.abilities = abilities
        self.speed_dice = speed_dice
        self.hp_dice = health_dice
        self.damage_dice = damage_dice
        self.rarity = rarity
        self.is_unique = is_unique
        self.gen_eligible = True

    # String method; mainly for testing
    def __str__(self):
        string = "NAME: "
        # print name
        string += self.name + "\n"
        # print desc
        string += "DESCRIPTION: \n"
        for line in self.desc:
            string += line
        # print color(s)
        string += "COLORS: "
        for color in self.colors:
            string += color + " "
        string += "\n"
        # print abilities
        string += "ABILITIES: "
        abil = self.abilities
        if has_attribute(abil, ATTR_INTELLIGENT):
            string += "SMART "
        if has_attribute(abil, ATTR_TELEPATHIC_):
            string += "TELE "
        if has_attribute(abil, ATTR_TUNNEL_____):
            string += "TUNNEL "
        if has_attribute(abil, ATTR_ERRATIC____):
            string += "ERRATIC "
        if has_attribute(abil, ATTR_PASS_______):
            string += "PASS "
        if has_attribute(abil, ATTR_PICKUP_____):
            string += "PICKUP "
        if has_attribute(abil, ATTR_DESTROY____):
            string += "DESTROY "
        if has_attribute(abil, ATTR_UNIQ_______):
            string += "UNIQ "
        if has_attribute(abil, ATTR_BOSS_______):
            string += "BOSS "
        string += "\n"
        # print speed
        string += "SPEED: " + str(self.speed_dice) + "\n"
        # print hp
        string += "HEALTH: " + str(self.hp_dice) + "\n"
        # print dam
        string += "DAMAGE: " + str(self.damage_dice) + "\n"
        # print symb
        string += "SYMB: " + self.symb + "\n"
        # print rrty
        string += "RRTY: " + str(self.rarity) + "\n"
        string += "GENERATION ELIGIBLE: " + str(self.gen_eligible)
        return string + "\n"

    def get_name(self) -> str:
        return self.name

    def get_symb(self) -> str:
        return self.symb

    def get_single_color(self) -> list:
        return self.colors[random.randint(0, len(self.colors) - 1)]

    def get_desc(self):
        return self.desc

    def get_abil_str(self) -> str:
        abil_str = ""
        if has_attribute(self.abilities, ATTR_INTELLIGENT):
            abil_str = abil_str + "SMART "
        if has_attribute(self.abilities, ATTR_TELEPATHIC_):
            abil_str = abil_str + "TELEPATHIC "
        if has_attribute(self.abilities, ATTR_TUNNEL_____):
            abil_str = abil_str + "TUNNELER "
        if has_attribute(self.abilities, ATTR_ERRATIC____):
            abil_str = abil_str + "ERRATIC "
        if has_attribute(self.abilities, ATTR_PASS_______):
            abil_str = abil_str + "PASS "
        if has_attribute(self.abilities, ATTR_PICKUP_____):
            abil_str = abil_str + "PICKUP "
        if has_attribute(self.abilities, ATTR_DESTROY____):
            abil_str = abil_str + "DESTROY "
        if has_attribute(self.abilities, ATTR_UNIQ_______):
            abil_str = abil_str + "UNIQUE "
        if has_attribute(self.abilities, ATTR_BOSS_______):
            abil_str = abil_str + "BOSS "
        return abil_str

    def get_speed_str(self) -> str:
        return str(self.speed_dice)

    def get_hp_str(self) -> str:
        return str(self.hp_dice)

    def get_damage_str(self) -> str:
        return str(self.damage_dice)

    def get_rarity(self) -> int:
        return self.rarity

    def is_gen_eligible(self) -> bool:
        return self.gen_eligible

    def is_unique(self) -> bool:
        return self.is_unique


# This is the generic actor class to be used in the general turn loop.
class Actor(abc.ABC):

    # Coordinate deltas for 8 surrounding points of a given point.
    # up_left, up, up_right, left, right, down_left, down, down_right, none
    _delta_r = [-1, -1, -1, 0, 0, 1, 1, 1, 0]
    _delta_c = [-1, 0, 1, -1, 1, -1, 0, 1, 0]

    # This method is to initialize the position of the actor within the dungeon, verifying the location as valid.
    # Returns True on successful placement, False otherwise.
    def init_pos(self, dungeon: Dungeon, actor_map: list, r: int, c: int) -> bool:
        if (
            dungeon.valid_point(r, c)
            and dungeon.rmap[r][c] == 0
            and actor_map[r][c] == None
        ):
            self.r = r
            self.c = c
            actor_map[r][c] = self
            return True
        else:
            return False

    # Returns the row, column coordinate of the actor, in that order.
    def get_pos(self):
        return self.r, self.c

    # Returns the current turn of the given actor.
    def get_currturn(self) -> int:
        return self.turn

    # Returns the speed (turn number increase per turn).
    def get_speed(self) -> int:
        return self.speed

    # Returns the current number of hitpoints of the actor.
    def get_hp(self) -> int:
        return self.hp

    # Returns the character representation of the actor.
    @abc.abstractmethod
    def get_char(self) -> str:
        pass

    # Returns a color for the character of the actor.
    @abc.abstractmethod
    def get_color(self) -> str:
        pass

    # Sets the current turn of the given actor.
    def set_currturn(self, turn: int):
        self.turn = turn

    # Returns True if the actor is alive, False otherwise.
    def is_alive(self):
        return self.alive

    # Declare this actor as dead.
    def kill(self):
        self.alive = False

    # Handles the turn for the actor.
    @abc.abstractmethod
    def handle_turn(self, dungeon: Dungeon, actor_map: list, player, move: Move):
        pass

    # Returns the row, column coordinate of where the actor is attempting to move to.
    def target_pos(self, move):
        return self.r + self._delta_r[move.value], self.c + self._delta_c[move.value]


# This is the class for the player character and its turn/movement methods.
class Player(Actor):

    # Player constructor
    def __init__(self):
        # Declare fields for location
        self.r = 0
        self.c = 0
        # Player character's memory of the dungeon, as it appeared on sight.
        self.memmap = []
        # Init the player's turn to zero
        self.turn = 0
        # Init the player's speed (turn number increase per turn) to 10
        self.speed = 10
        # Define the player as alive
        self.alive = True

        # Initial HP cap, and hp set to that maximum
        self.hp_cap = 100
        self.hp = self.hp_cap

        # Initial defense and dodge of 10
        self.defense = 10
        self.dodge = 10

        # Initial view distance of 3
        self.view_dist = 3

        # Base damage for the player, assuming that it has no other weapons
        self.fisticuffs_dice = Dice(0, 2, 3)

        # Player's memory of dungeon
        self.tmem = []

        # To keep track of if a given tile is currently 'visible' to the player; either true/false.
        self.visible_tiles = []

        # Player inventory / equipment slots
        self.inventory_size = 10  # Carry slot limit
        self.inventory = [None for _ in range(self.inventory_size)]
        self.equip_slots = {
            "weapon": None,
            "ranged": None,
            "offhand": None,
            "armor": None,
            "amulet": None,
            "light": None,
            "ring_l": None,
            "ring_r": None,
        }

    # Gets the correct information for an octant, or part of the scan circle for player visually scanning dungeon.
    def _get_octant_transform(self, octant):
        """
        Return the transformation matrix for the given octant.
        These are used to rotate the FOV scan into the correct direction.
        """
        # Each tuple: (xx, xy, yx, yy)
        # These control how dx/dy are applied to reach other octants
        mult = [
            (1, 0, 0, 1),  # Octant 0: E
            (0, 1, 1, 0),  # Octant 1: NE
            (-1, 0, 0, 1),  # Octant 2: W
            (0, -1, 1, 0),  # Octant 3: SE
            (-1, 0, 0, -1),  # Octant 4: W2
            (0, -1, -1, 0),  # Octant 5: SW
            (1, 0, 0, -1),  # Octant 6: E2
            (0, 1, -1, 0),  # Octant 7: NW
        ]
        return mult[octant]

    # Shadowcasting helper method for determining what the player can 'see'.
    def _cast_light(
        self, row, start_slope, end_slope, xx, xy, yx, yy, dungeon: Dungeon
    ):
        """
        Recursively 'casts light' in a given octant from the player (source_x, source_y),
        effectively finding tiles that are visible to the PC in that octant.

        Parameters:
            source_x, source_y      — origin (player position)
            radius      — max vision distance
            row         — current row (distance from origin)
            start_slope — left bound of current scan sector
            end_slope   — right bound of current scan sector
            xx, xy,
            yx, yy      — octant transform multipliers (from get_octant_transform)
            map_data    — 2D list of map tiles
            visible     — set collecting visible tile coordinates
        """

        source_x = self.c
        source_y = self.r
        radius = self.view_dist

        # Stop if the current scan sector is invalid
        if start_slope < end_slope:
            return

        for i in range(row, radius + 1):
            dx = -i
            blocked = False
            new_start = start_slope

            while dx <= 0:
                dy = -i
                # Map coordinates for this octant
                X = source_x + dx * xx + dy * xy
                Y = source_y + dx * yx + dy * yy

                # Compute slopes
                l_slope = (dx - 0.5) / (dy + 0.5)
                r_slope = (dx + 0.5) / (dy - 0.5)

                # Skip tile if outside of this field-of-view segment
                if r_slope > start_slope:
                    dx += 1
                    continue
                elif l_slope < end_slope:
                    break

                # Bounds check
                if dungeon.valid_point(Y, X):
                    dist = dx * dx + dy * dy

                    # Check if new point is rock (wall)
                    is_wall = dungeon.tmap[Y][X] in {
                        Dungeon.Terrain.stdrock,
                        Dungeon.Terrain.immrock,
                    }

                    if dist <= radius * radius:
                        self.tmem[Y][X] = dungeon.tmap[Y][X]
                        # hard check to make sure walls aren't marked as visible by mistake
                        if not is_wall:
                            self.visible_tiles[Y][X] = True

                    if blocked:
                        if is_wall:
                            new_start = r_slope  # Wall continues
                        else:
                            blocked = False
                            start_slope = new_start
                    else:
                        if is_wall and i < radius:
                            blocked = True
                            self._cast_light(
                                i + 1, start_slope, l_slope, xx, xy, yx, yy, dungeon
                            )
                            new_start = r_slope

                dx += 1
            if blocked:
                break

    # Starts recursive shadowcasting to determine what the player can 'see'.
    def _update_terrain_memory(self, dungeon: Dungeon):
        """
        Compute what the player can see from its current location using recursive shadowcasting.
        Updates player.tmem, which is the player's remembered dungeon terrain.
        """
        self.visible_tiles = [[False] * dungeon.width for _ in range(dungeon.height)]

        cx = self.c
        cy = self.r
        self.tmem[cy][cx] = dungeon.tmap[cy][cx]
        self.visible_tiles[cy][cx] = True

        for octant in range(8):
            # Process all 8 octants
            self._cast_light(1, 1, 0, *self._get_octant_transform(octant), dungeon)

    # Determines if the player can be at this position.
    def _valid_pos(self, dungeon: Dungeon, r: int, c: int) -> bool:
        if dungeon.valid_point(r, c) and dungeon.rmap[r][c] == 0:
            return True
        else:
            return False

    # Forces the player into this position. Does not check that position is 'valid'.
    def _force_pos_update(self, dungeon: Dungeon, actor_map: list, r: int, c: int):
        actor_map[self.r][self.c] = None
        actor_map[r][c] = self
        self.r = r
        self.c = c
        # Update the player's knowledge of the dungeon.
        self._update_terrain_memory(dungeon)

    # Rolls dice to determine dmg output in melee combat
    def _dmg_roll_melee(self) -> int:
        dmg = 0
        # Roll dice of main weapons/ equipment
        item = self.equip_slots["weapon"]
        if item != None:
            dmg += item.damage_dice.roll()
        # If and when ranged combat is implemented, this will not be rolled here.
        item = self.equip_slots["ranged"]
        if item != None:
            dmg += item.damage_dice.roll()
        item = self.equip_slots["offhand"]
        if item != None:
            dmg += item.damage_dice.roll()

        # If no damage yet applied, default to fisticuffs dice.
        if dmg == 0:
            dmg = self.fisticuffs_dice.roll()

        # Now roll for damage of rings/ amulets; they act as bonuses, so will be applied anywhere damage is applied
        item = self.equip_slots["amulet"]
        if item != None:
            dmg += item.damage_dice.roll()
        item = self.equip_slots["ring_l"]
        if item != None:
            dmg += item.damage_dice.roll()
        item = self.equip_slots["ring_r"]
        if item != None:
            dmg += item.damage_dice.roll()

        return dmg

    # Attempts to place an item into inventory
    def _place_in_inventory(self, item: Item):
        # Check that there is room in the player carry slots
        # Fill first available slot, if there is one
        for slot_idx in range(self.inventory_size):
            slot = self.inventory[slot_idx]
            if slot == None:
                self.inventory[slot_idx] = item
                item.picked_up = True
                return True  # Successfully placed into inventory
        return False  # Failed to find room; cannot place into inventory

    # Player specific implementation for initializing position in dungeon
    def init_pos(self, dungeon: Dungeon, actor_map: list, r: int, c: int) -> bool:
        # Clear the player's memory of the dungeon.
        self.tmem = [
            [Dungeon.Terrain.debug] * dungeon.width for _ in range(dungeon.height)
        ]

        if (
            dungeon.valid_point(r, c)
            and dungeon.rmap[r][c] == 0
            and actor_map[r][c] == None
        ):
            self.r = r
            self.c = c
            actor_map[r][c] = self

            # Initialize the player's memory of the dungeon
            self._update_terrain_memory(dungeon)

            return True
        else:
            return False

    # Attempts to pickup an item from the floor, placing in inventory.
    # Returns True/False on success/failure.
    def pickup_item(self, dungeon: Dungeon, item_map: list, r: int, c: int) -> bool:
        # First check that (r, c) is a valid position within the dungeon
        if dungeon.valid_point(r, c):
            # Now check that there is an item present
            item = item_map[r][c]
            if item != None:
                if self._place_in_inventory(item):
                    item_map[r][c] = None
                    return True, item
        return False, None

    # Attempts to equip an item in given inventory slot
    # Returns a bool for success/failure, and the item equipped
    def equip_use_item(self, idx: int):
        item = self.inventory[idx]
        self.inventory[idx] = None

        if item == None:
            return False, None

        # Grab type to check which equip slot it should go into
        # Unequipping whatever might be there first
        itype = item.get_type()
        if itype == item_type_opts["WEAPON"]:
            self.unequip_item("weapon")
            self.equip_slots["weapon"] = item
        elif itype == item_type_opts["RANGED"]:
            self.unequip_item("ranged")
            self.equip_slots["ranged"] = item
        elif itype == item_type_opts["OFFHAND"]:
            self.unequip_item("offhand")
            self.equip_slots["offhand"] = item
        elif itype == item_type_opts["ARMOR"]:
            self.unequip_item("armor")
            self.equip_slots["armor"] = item
        elif itype == item_type_opts["AMULET"]:
            self.unequip_item("amulet")
            self.equip_slots["amulet"] = item
        elif itype == item_type_opts["RING"]:
            # Rotate rings. Inventory -> L -> R -> inventory
            self.unequip_item("ring_r")
            self.equip_slots["ring_r"] = self.equip_slots["ring_l"]
            self.equip_slots["ring_l"] = item
        elif itype == item_type_opts["LIGHT"]:
            self.unequip_item("light")
            self.equip_slots["light"] = item

        # Now add bonuses; what is applied depends on item type
        if itype == item_type_opts["LIGHT"]:
            self.view_dist += item.attr
        elif itype == item_type_opts["POTION"]:
            # Use and then destroy potion
            self.hp_cap += item.attr
            new_hp = self.hp + item.hp_restore
            self.hp = min(new_hp, self.hp_cap)
            self.speed += item.speed
            self.defense += item.defense
            self.dodge += item.defense
            self.inventory[idx] = None
        else:
            # regular bonuses; speed, defense, dodge and hp restore
            if not item.used:
                # Only add hp_restore on first equip
                new_hp = self.hp + item.hp_restore
                self.hp = min(new_hp, self.hp_cap)
                item.used = True
            self.speed += item.speed
            self.defense += item.defense
            self.dodge += item.dodge

        return True, item

    # Unequips an item in a given slot, using keystring to indicate which slot.
    # Returns bool for general success, bool for inventory problem, and then the item.
    def unequip_item(self, key_str: str):
        item = self.equip_slots[key_str]
        if item != None:
            if self._place_in_inventory(item):
                itype = item.get_type()
                if itype == item_type_opts["LIGHT"]:
                    self.view_dist -= item.attr
                else:
                    self.speed -= item.speed
                    self.defense -= item.defense
                    self.dodge -= item.dodge
                self.equip_slots[key_str] = None
                return True, False, item
            else:
                return False, True, item
        return False, False, item

    # Forcefully teleports the player to row, col within the dungeon, instantly killing any monster that is there.
    # Returns true/false for success and any killed monster.
    def teleport(self, dungeon: Dungeon, actor_map: list, row: int, col: int):
        if dungeon.valid_point(row, col) and not (row == self.r and col == self.c):
            # Grab any monster that might occupy that space
            actor = actor_map[row][col]
            if actor != None:
                # Commit instant, brutal vaporization of the monster (kill them)
                actor.hp = 0
                actor.kill()
            # Move player into that position
            self._force_pos_update(dungeon, actor_map, row, col)
            return True, actor

        return False, None

    # Turn handler for the player.
    def handle_turn(self, dungeon: Dungeon, actor_map: list, player, move: int):
        """
        This function handles the turn for the player.
        It requires the dungeon instance, the actor map for that dungeon, the player object (redundant), and a specified move, in that order.
        It will return a target actor (potentially None) and a damage value (potentially 0) for comabt messages.
        """

        if move == Move.none:
            self._update_terrain_memory(dungeon)
            return True, None, 0

        move = Move(move)
        new_r, new_c = self.target_pos(move)
        # Check that new position is valid for the PC to be at
        if not self._valid_pos(dungeon, new_r, new_c):
            return False, None, 0

        # Move the PC, removing whatever monster may be there
        a = actor_map[new_r][new_c]
        if a != None:
            dmg = self._dmg_roll_melee()
            new_hp = a.hp - dmg
            if new_hp <= 0:
                a.hp = 0
                a.kill()
            else:
                a.hp = new_hp
        else:
            # No actor; move
            dmg = 0
            self._force_pos_update(dungeon, actor_map, new_r, new_c)
            dungeon.calc_dist_maps(new_r, new_c)

        # For combat dialog
        return True, a, dmg

    # Returns true/false for if tile at row, col is visible to the player.
    def is_visible_tile(self, row, col):
        return self.visible_tiles[row][col]

    # Returns the character representation of the player.
    def get_char(self) -> str:
        return "@"

    def get_name(self) -> str:
        return "=== PLAYER ==="

    # Returns a color for the character of the actor.
    def get_color(self) -> str:
        return "gold"

    def get_hp_cap(self) -> int:
        return self.hp_cap

    def get_defense(self) -> int:
        return self.defense

    def get_dodge(self) -> int:
        return self.dodge

    # Returns the player's inventory size
    def get_inventory_size(self) -> int:
        return self.inventory_size

    # Returns the player's inventory list.
    def get_inventory_slots(self) -> list:
        return self.inventory

    # Returns what is inside a given inventory slot.
    def get_inventory_item(self, idx: int):
        if idx >= self.inventory_size:
            return False, None
        else:
            return True, self.inventory[idx]

    # Attempts to delete an item from inventory.
    def expunge_item(self, idx: int):
        item = None
        if idx >= self.inventory_size:
            return False, item
        else:
            item = self.inventory[idx]
            if item != None:
                self.inventory[idx] = None
                return True, item
            else:
                return False, item

    # Attempts to drop an item from inventory into the dungeon.
    def drop_item(self, idx: int, item_list: list, item_map: list):
        item = None
        if idx >= self.inventory_size:
            return False, item
        else:
            item = self.inventory[idx]
            if item != None:
                # Now need to check if dropping the item is possible at current location
                existing_item = item_map[self.r][self.c]
                if existing_item == None:
                    # Possible to drop item, since there is not an item in place already.
                    # Add the item to the game's item_list, if necessary.
                    if item not in item_list:
                        item_list.append(item)
                    self.inventory[idx] = None
                    item_map[self.r][self.c] = item
                    return True, item
        return False, item

    def get_weapon(self):
        return self.equip_slots["weapon"]

    def get_ranged(self):
        return self.equip_slots["ranged"]

    def get_offhand(self):
        return self.equip_slots["offhand"]

    def get_armor(self):
        return self.equip_slots["armor"]

    def get_amulet(self):
        return self.equip_slots["amulet"]

    def get_ring_l(self):
        return self.equip_slots["ring_l"]

    def get_ring_r(self):
        return self.equip_slots["ring_r"]

    def get_light(self):
        return self.equip_slots["light"]


# This is the class for monsters and their turn/movement methods.
class Monster(Actor):

    # Monster constructor
    def __init__(self, typedef: Monster_Typedef):
        # Declare fields for location
        self.r = 0
        self.c = 0
        self.typedef = typedef
        # Monster's 'path'; this is a distance map of the dungeon to determine where to move next
        self.path = []
        # Speed modifier; lower is better
        self.speed = typedef.speed_dice.roll()
        # bitfield to indicate what sort of attributes that the monster has
        self.attributes = typedef.abilities
        # Set the monsters current turn to zero
        self.turn = 0
        # Declare the monster as initially alive
        self.alive = True
        self.hp = typedef.hp_dice.roll()

    # Returns the character representation of the actor.
    def get_char(self) -> str:
        return self.typedef.symb

    # Returns the string name for the monster.
    def get_name(self) -> str:
        return self.typedef.name

    # Returns a color for the character of the actor.
    def get_color(self) -> str:
        """
        Returns a string for a Tkinter color that the monster's sybol is intended to be.
        """
        return self.typedef.colors[random.randint(0, len(self.typedef.colors) - 1)]

    # Returns the list of lines for the monster's description.
    def get_desc(self) -> list:
        return self.typedef.desc

    # Returns True if the monster is unqiue, false otherwise.
    def is_unique(self) -> bool:
        """
        Returns the uniqueness of the monster's type definition.
        """
        return self.typedef.is_unique

    def is_boss(self) -> bool:
        return has_attribute(self.attributes, ATTR_BOSS_______)

    # Returns the score value for defeating this monster.
    def get_score_val(self) -> int:
        base_val = self.typedef.rarity * 10
        if self.typedef.is_unique:
            base_val *= 5
        if has_attribute(self.attributes, ATTR_BOSS_______):
            base_val *= 10

        return base_val

    # resets generation eligibility of type definition
    def update_gen_eligible(self, is_new_mon: bool, force_reset: bool):
        """
        This function updates the generation eligibility of this monster's type definition.
        It is only intended to be called in a few circumstances:
        A) Initial generation, in which case it will be updated to False if this is a unique monster.
        B) Changing to new dungeon level, in which case the eligibility will be updated based on uniqueness and then if alive/dead.
        C) Game over, in which case it will be force updated back to True.

        Calling this method in any other situation will likely produce unintended behavior.

        The first parameter, is_new_mon, is a boolean if this is the first call after creating the monster.
            This should be false anytime except immediately following the creation of a monster instance.
        The second parameter, force_rest, indicates that the game is over and eligibility should be automatically reset to True.
        """
        if force_reset:
            # Force reset to True
            self.typedef.gen_eligible = True
        elif self.typedef.is_unique:
            if is_new_mon:
                # Newly generated monster, so set eligibility to False so there aren't duplicates.
                self.typedef.gen_eligible = False
            elif self.alive and not is_new_mon:
                # still alive, and not the initial generation.
                # This will reset to True for a new dungeon (presumably why this was called)
                self.typedef.gen_eligible = True

    # Determines if the monster can be at this position.
    def _valid_pos(self, dungeon: Dungeon, r: int, c: int) -> bool:
        """
        This function checks that the row, column coordinate is a valid position for the monster to be within the dungeon.
        Returns True if it is, False otherwise.
        """

        if dungeon.valid_point(r, c):
            if (
                dungeon.rmap[r][c] == 0
                or has_attribute(self.attributes, ATTR_TUNNEL_____)
                or has_attribute(self.attributes, ATTR_PASS_______)
            ):
                return True
        return False

    # Determines if the monster has a line of sight to the player; returns True if so, False otherwise.
    def _has_pc_los(self, dungeon: Dungeon, player: Player) -> bool:
        dest_r, dest_c = player.get_pos()
        curr_r, curr_c = self.get_pos()
        diff_r = abs(dest_r - curr_r)
        diff_c = abs(dest_c - curr_c)
        step_dir_r = 0 if curr_r == dest_r else (1 if curr_r < dest_r else -1)
        step_dir_c = 0 if curr_c == dest_c else (1 if curr_c < dest_c else -1)
        error = diff_c - diff_r

        # Scan from the monster's position, moving towards the player's location.
        while True:
            # Check if there is rock in the way
            if dungeon.rmap[curr_r][curr_c] > 0:
                # Rock is in the way; no line of sight, so return False.
                return False

            # Check if scan has reached the player
            if curr_r == dest_r and curr_c == dest_c:
                # Reached the player; so line of sight established and return True.
                return True

            # Iterate towards the PC
            e2 = 2 * error
            if e2 > -diff_r:
                error -= diff_r
                curr_c += step_dir_c

            if e2 < diff_c:
                error += diff_c
                curr_r += step_dir_r

    # Calculates a straightline path to the player character.
    def _calc_straight_path(self, dungeon: Dungeon, player: Player):
        # Note: this method ignores if the monster is a tunneler or not.
        dest_r, dest_c = self.get_pos()
        curr_r, curr_c = player.get_pos()
        diff_r = abs(dest_r - curr_r)
        diff_c = abs(dest_c - curr_c)
        step_dir_r = 0 if dest_r == curr_r else (1 if dest_r > curr_r else -1)
        step_dir_c = 0 if dest_c == curr_c else (1 if dest_c > curr_c else -1)
        error = diff_c - diff_r
        # dist is to give the path a useful weight to use when deciding where to go
        dist = 0
        # Init path to 'infinite' weight at every point; slow, but prevents multiple paths overlapping if LOS broken and regained
        self.path = [[float("inf")] * dungeon.width for _ in range(dungeon.height)]

        # Scan from the player's position, moving towards the monster's location.
        while True:
            # Update the path for distance from player
            self.path[curr_r][curr_c] = dist

            if curr_r == dest_r and curr_c == dest_c:
                # Reached the monster's position; stop here
                break

            # Iterate towards the monster
            e2 = 2 * error
            if e2 > -diff_r:
                error -= diff_r
                curr_c += step_dir_c

            if e2 < diff_c:
                error += diff_c
                curr_r += step_dir_r

            dist += 1

    # Handles an actor at a target location.
    def _handle_target_actor(
        self, dungeon: Dungeon, actor_map: list, dest_r: int, dest_c: int
    ) -> int:
        a = actor_map[dest_r][dest_c]

        if isinstance(a, Player):
            if not dodge_chance(a.dodge):
                # Player was unable to dodge attack
                # Roll for initial damage, then calculate defense reduction
                dam = def_dmg_reduction(self.typedef.damage_dice.roll(), a.defense)
                new_hp = a.get_hp() - dam
                if new_hp <= 0:
                    a.hp = 0
                    a.kill()
                    actor_map[dest_r][dest_c] = None
                else:
                    a.hp = new_hp
                return dam
            else:
                return 0  # player dodged attack

        # Attempt to displace monster
        delta_r = [-1, -1, -1, 0, 0, 1, 1, 1]
        delta_c = [-1, 0, 1, -1, 1, -1, 0, 1]

        # Randomize the order in which the 8 surrounding points are attempted
        indices = list(range(8))
        random.shuffle(indices)

        for idx in indices:
            new_r = dest_r + delta_r[idx]
            new_c = dest_c + delta_c[idx]
            if (
                dungeon.valid_point(new_r, new_c)
                and actor_map[new_r][new_c] is None
                and a._valid_pos(dungeon, new_r, new_c)
            ):
                # Move displaced monster
                actor_map[new_r][new_c] = a
                a.r = new_r
                a.c = new_c

                # Move self into vacated spot
                actor_map[dest_r][dest_c] = self
                actor_map[self.r][self.c] = None
                self.r = dest_r
                self.c = dest_c

                return 0

        # If displacement failed, swap positions
        actor_map[self.r][self.c] = a
        a.r = self.r
        a.c = self.c

        actor_map[dest_r][dest_c] = self
        self.r = dest_r
        self.c = dest_c

        return 0

    # Handles moving monster, once target position found.
    def _move_handeler(self, dungeon: Dungeon, actor_map: list, new_r: int, new_c: int):
        # Move the monster, handling whatever actor may be there
        a = actor_map[new_r][new_c]
        if a != None:
            # Call the handler for targeting another actor
            dmg = self._handle_target_actor(dungeon, actor_map, new_r, new_c)
        else:
            dmg = 0  # to have a return value
            # Check if there is rock in the way
            if dungeon.rmap[new_r][new_c] != 0:
                hardness = dungeon.rmap[new_r][new_c]
                if has_attribute(self.attributes, ATTR_TUNNEL_____):
                    # Bore rock
                    hardness = max(0, hardness - 86)
                    dungeon.rmap[new_r][new_c] = hardness
                if hardness < 1 or has_attribute(self.attributes, ATTR_PASS_______):
                    # Rock has been cleared and/or monster can pass through
                    if has_attribute(self.attributes, ATTR_TUNNEL_____):
                        dungeon.tmap[new_r][new_c] = dungeon.Terrain.floor
                    # Update the actor map + position information
                    actor_map[self.r][self.c] = None
                    actor_map[new_r][new_c] = self
                    self.r = new_r
                    self.c = new_c
            else:
                # No actor, no rock in the way; so move into new location
                # Update the actor map + position information
                actor_map[self.r][self.c] = None
                actor_map[new_r][new_c] = self
                self.r = new_r
                self.c = new_c
        # Return actor + damage dealt for combat messages
        return a, dmg

    # Monster moves in a random direction.
    def _random_move(self, dungeon: Dungeon, actor_map: list):
        move = Move(random.randint(0, 7))
        new_r, new_c = self.target_pos(move)
        # Check that new position is valid for the monster to be at
        # Repeat until this is the case
        while not self._valid_pos(dungeon, new_r, new_c):
            move = Move(random.randint(0, 7))
            new_r, new_c = self.target_pos(move)
        a, dmg = self._move_handeler(dungeon, actor_map, new_r, new_c)
        # Return actor + damage dealt for combat messages
        return a, dmg

    # Monster moves based on its path.
    def _path_move(self, dungeon: Dungeon, actor_map: list):
        # Definine the min cost to be infinite to start
        min_cost = float("inf")
        minc_pt_idx = None
        # Find minimum cost point in surrounding 8
        for pt_idx in range(8):
            # Grabs the new point
            new_r, new_c = self.target_pos(Move(pt_idx))
            if dungeon.valid_point(new_r, new_c):
                cost = self.path[new_r][new_c]
                if cost < min_cost:
                    # Better, so overwrite minimum cost point
                    min_cost = cost
                    minc_pt_idx = pt_idx

        # Error handeling; In theory, this shouldn't happen. My logic is broken somewhere such that this is an incredibly rare problem.
        if minc_pt_idx == None:
            # No min cost point was found; so don't move anywhere.
            minc_pt_idx = 8

        # Now attempt to move to that minimum cost point
        new_r, new_c = self.target_pos(Move(minc_pt_idx))
        a, dmg = self._move_handeler(dungeon, actor_map, new_r, new_c)
        # Return actor + damage dealt for combat messages
        return a, dmg

    # Updates the monster's path, depending on the attributes that it has.
    # Returns True on a successful path update, False otherwise.
    def _update_path(self, dungeon: Dungeon, player: Player) -> bool:
        # Check if monster is intelligent
        if has_attribute(self.attributes, ATTR_INTELLIGENT):
            # Check if monster is a telepath
            if has_attribute(self.attributes, ATTR_TELEPATHIC_):
                # Monster is intelligent and telepathic; thus, it should get a full distance map; not a copy.
                # Check if monster is a tunneling monster to determine which it should get.
                if has_attribute(self.attributes, ATTR_TUNNEL_____):
                    # Tunneler, get tunneling distance map.
                    self.path = dungeon.tunn_distmap
                    return True
                else:
                    # Not a tunneler, get walking distance map.
                    self.path = dungeon.walk_distmap
                    return True
            else:
                # Monster is intelligent, but not telepathic. Need to check for line of sight.
                if self._has_pc_los(dungeon, player):
                    # Has line of sight, so need to check which distance map monster should recieve a copy of.
                    # Also: Copy instead of direct assignment to emmulate 'memory' of last PC sighting.
                    if has_attribute(self.attributes, ATTR_TUNNEL_____):
                        self.path = copy.deepcopy(dungeon.tunn_distmap)
                        return True
                    else:
                        self.path = copy.deepcopy(dungeon.walk_distmap)
                        return True
        else:
            if has_attribute(self.attributes, ATTR_TELEPATHIC_):
                # Monster is telepathic, but not intelligent. Will need to calculate a straightline path.
                self._calc_straight_path(dungeon, player)
                return True
            else:
                # Monster is not telepathic, nor intelligent. Will need to check line of sight.
                if self._has_pc_los(dungeon, player):
                    self._calc_straight_path(dungeon, player)
                    return True
                # If there is not any line of sight, then no changes.
        return False

    # Turn handler for this monster.
    def handle_turn(
        self, dungeon: Dungeon, actor_map: list, player: Player, move: Move
    ):
        """
        This function handles the turn for the monster.
        It requires the dungeon instance, the actor map for that dungeon, the player object, and a specified move, in that order.
        It will return a target actor (potentially None) and a damage value (potentially 0) for comabt messages.
        """
        # Update the monster's path.
        if self._update_path(dungeon, player):
            if (
                has_attribute(self.attributes, ATTR_ERRATIC____)
                and random.randint(0, 1) > 0
            ):
                # Erratic attribute triggered
                a, dmg = self._random_move(dungeon, actor_map)
            else:
                # Move based on path
                a, dmg = self._path_move(dungeon, actor_map)
        else:
            # Path update failure indicates that the monster should move randomly
            a, dmg = self._random_move(dungeon, actor_map)
        # Return actor + damage dealt for combat messages
        return True, a, dmg
