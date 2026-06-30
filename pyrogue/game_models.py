# This file contains some data structures that will be used to communicate game data in/out of the game engine.

'''
This is the main data structure to return the current status of the game map;
i.e., dungeon terrain and the locations of the player, monsters, and items.
This should primarily be used for rendering map to the player.

Design consideratino note for future self:
    This will need to be returned frequently, so it should be efficient.
    However, rockmap and pathfinding map should also be available. Separate route?
    Another wrinkle: Actual mapstate will be different from what the player knows and sees.
    Another different route?
'''
class MapState:
    pass

'''
This data structure represents the current state of the player,
including health, inventory, defense, dodge, ammo, and view distance.
'''
class PlayerState:
    pass

'''
Design consideration: bulk data for all monsters, or for a given monster?
'''
class MonsterState:
    pass

