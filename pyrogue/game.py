import logging

from .utility import *
from .actor import *
from .dungeon import *
from .parsedesc import parse_monster_typedefs, parse_item_typedefs


# The Pyrogue_Game class handles all the high-level game logic and control.
class Pyrogue_Game:

    '''
    This is the Pyrogue_Game Constructor.
    
    It has 3 required parameters, with 1 optional parameter:
    - mapsize_h (int, required): the height in cells of the dungeon map. Note that unusable outer border is included in this value.
    - mapsize_w (int, required): the width in cells of the dungeon map. Note that the unusable outer border is included in this value.
    - difficulty (float, required): the difficulty of the game, which modifies monster spawn rates. Higher is more difficult;
        minimum value is 0.01, with no theoretical maximum. Keeping to smaller whole digits on the high end is recommended, however.
    - enable_cheats (bool, optional): whether to enable cheat & debug modes. Default value is False.
    '''
    def __init__(
        self,
        mapsize_h: int,
        mapsize_w: int,
        difficulty: float,
        enable_cheats: bool = False,
    ):
        # Save if cheats are enabled
        self.cheats_enabled = enable_cheats

        # Init internal idea of dungeon size
        self.mapsize_h = mapsize_h
        self.mapsize_w = mapsize_w

        # Game difficulty; applies to monster spawn rates. Check for minimum value of 0.01.
        if difficulty < 0.01:
            self.difficulty = 0.01
        else:
            self.difficulty = difficulty

        # Init dungeon and player fields
        self.dungeon = None
        self.player = None
        self.player_score = 0

        # Init monster and item type definition lists, then call description parsers populate them with definitions.
        self.monster_type_list = []
        self.item_type_list = []
        parse_monster_typedefs(self.monster_type_list)
        parse_item_typedefs(self.item_type_list)

        # Init lists for monsters as well as the map storing all actor locations
        self.monster_list = []
        self.item_list = []
        self.actor_map = []
        self.item_map = []
        self.turn_pq = None

        # Initialize dungeon, item, & monster generation
        self._init_generated_game()

        # To store important game msgs; combat, new dungeon, game start, etc
        self.msg_log = ["GAME START"]

        # Misc game control fields
        self.turnloop_started = False
        self.selfdeath = False  # to check for suicide gameover message
        self.game_over = False  # Indicate game over
        self.game_exit = False  # Indicate that user intends to exit the game

        # Start the turnloop for the game
        self._start_turnloop()
        print("=== GAME START ===")

    # Nerfs speed value so that it doesn't become too overpowered.
    def _speed_nerf(self, base_speed: int) -> int:
        # speed is a legacy mechanic, where the intention was that it levels the playing field for the player.
        # In practice, the value grows way faster than is practical, and it turns overpowered very fast.
        # It still exists, but this is here to nerf it down so that it doesn't break the game.
        return min(base_speed, 50)

    # Populates the actor_map with a dungeon size proportionate number of monsters.
    def _generate_monsters(self):
        attemptc = 0
        monsterc = 0
        size_modifier = self.mapsize_w * self.mapsize_h
        attempt_limit = int(self.difficulty * size_modifier)
        min_monsterc = max(1, int(size_modifier // 100 * self.difficulty))
        # Adjust exp_chancetime's decay curve to increase additional monster probability with difficulty
        decay_rate = 0.95 / (self.difficulty + 0.5)

        # Generate monsters; runs until minimum number and attempt limit are met
        while (monsterc < min_monsterc) or (attemptc < attempt_limit):
            # Grab a monster type definition
            mtypedef = self.monster_type_list[
                random.randint(0, len(self.monster_type_list) - 1)
            ]
            if (
                mtypedef.is_gen_eligible()
                and random.randint(1, 101) >= mtypedef.get_rarity()
            ):
                # Create monster
                new_monster = Monster(mtypedef)
                if monsterc <= min_monsterc or exp_chancetime(
                    monsterc - min_monsterc, decay_rate
                ):
                    if new_monster.init_pos(
                        self.dungeon,
                        self.actor_map,
                        random.randint(1, self.mapsize_h - 2),
                        random.randint(1, self.mapsize_w - 2),
                    ):
                        # Update gen eligibility of monster type; Newly generated monster True, force reset False
                        new_monster.update_gen_eligible(True, False)
                        monsterc += 1
                        self.monster_list.append(new_monster)
            attemptc += 1
        print(
            "MONSTERS:",
            min_monsterc,
            "Min monsters,",
            attemptc,
            "Placement attempts,",
            monsterc,
            "Placed",
        )

    # Populates the item_map with a dungeon size proportionate number of items.
    def _generate_items(self):
        attemptc = 0
        itemc = 0
        size_modifier = self.mapsize_w * self.mapsize_h
        attempt_limit = size_modifier
        min_itemc = max(1, int(size_modifier // 50))
        decay_rate = 0.75

        # Generate items; runs until minimum number and attempt limit are met
        while (itemc < min_itemc) or (attemptc < attempt_limit):
            # Grab a item type definition
            itypedef = self.item_type_list[
                random.randint(0, len(self.item_type_list) - 1)
            ]
            if (
                itypedef.is_gen_eligible()
                and random.randint(1, 101) >= itypedef.get_rarity()
            ):
                # Create Item
                new_item = Item(itypedef)
                if itemc <= min_itemc or exp_chancetime(itemc - min_itemc, decay_rate):
                    if new_item.init_pos(
                        self.dungeon,
                        self.item_map,
                        random.randint(1, self.mapsize_h - 2),
                        random.randint(1, self.mapsize_w - 2),
                    ):
                        # Update gen eligibility of monster type; Newly generated monster True, force reset False
                        new_item.update_gen_eligible(True, False)
                        itemc += 1
                        self.item_list.append(new_item)
            attemptc += 1
        print(
            "ITEMS:",
            min_itemc,
            "Min items,",
            attemptc,
            "Placement attempts,",
            itemc,
            "Placed",
        )

    # Resets the generation eligibility for item/monster type definitions
    def _reset_gen_eligibility(self):
        """
        Note: This was originally written with the intention that a main menu would
        parse the monster & item definitions prior to launching a game, and that
        list would be shared among games instances. That is no longer the intended use,
        so there may be some code and checks here that are no longer necessary.
        """

        # Reset monster generation eligibility
        # Note that unique monsters only reset if they were not killed or if the game is over
        for monster in self.monster_list:
            # If game exit, force full reset. Otherwise depends on uniqueness and alive/dead
            monster.update_gen_eligible(False, self.game_exit)

        for item in self.item_list:
            # If game exit, force full reset. Otherwise depends on uniqueness and used/unused
            item.update_gen_eligible(False, self.game_exit)

    # Initializes a new dungeon for the game to use; this also re-generates the monsters and restarts the turnloop.
    def _replace_dungeon(self):

        # Reset monster generation eligibility
        self._reset_gen_eligibility()

        # Ramp difficulty by 35%
        self.difficulty *= 1.35

        print(f"GAME: New dungeon level with difficulty {self.difficulty}")

        # Init the dungeon itself
        self.dungeon = Dungeon(self.mapsize_h, self.mapsize_w)
        self.dungeon.generate_dungeon()

        # Clear actor map, monster list, and priority queue
        self.actor_map = [[None] * self.mapsize_w for _ in range(self.mapsize_h)]
        self.item_map = [[None] * self.mapsize_w for _ in range(self.mapsize_h)]
        self.monster_list = []
        self.item_list = []
        self.turn_pq = PriorityQueue()

        # Set the player's position in the dungeon
        while not self.player.init_pos(
            self.dungeon,
            self.actor_map,
            random.randint(1, self.mapsize_h - 2),
            random.randint(1, self.mapsize_w - 2),
        ):
            continue

        # Generate new monsters
        self._generate_monsters()

        # Generate new items
        self._generate_items()

        # Restart the turn loop
        self._start_turnloop()

    # Initializes the game with randomly generated dungeon and monsters
    # Dungeon is size_h * size_w, difficulty modifies monster spawn rates.
    def _init_generated_game(self):
        # Init dungeon
        self.dungeon = Dungeon(self.mapsize_h, self.mapsize_w)
        self.dungeon.generate_dungeon()

        # Init actor map and item map
        self.actor_map = [[None] * self.mapsize_w for _ in range(self.mapsize_h)]
        self.item_map = [[None] * self.mapsize_w for _ in range(self.mapsize_h)]

        # Init player
        self.player = Player()
        while not self.player.init_pos(
            self.dungeon,
            self.actor_map,
            random.randint(1, self.mapsize_h - 2),
            random.randint(1, self.mapsize_w - 2),
        ):
            continue

        # Calculate the initial dungeon distance maps relative to the player character
        pc_r, pc_c = self.player.get_pos()
        self.dungeon.calc_dist_maps(pc_r, pc_c)

        # Generate monsters to populate the dungeon
        self._generate_monsters()
        # Generate items
        self._generate_items()

        # Starts the game's turnloop

    # Initializes the start of the turnloop, starting the game.
    def start_turnloop(self):
        self.turn_pq = PriorityQueue()
        self.player.set_currturn(0)
        self.turn_pq.push(self.player, 0)
        for monster in self.monster_list:
            monster.set_currturn(monster.get_speed())
            # 9 to ensure that ALL monsters get a turn after player's first turn
            self.turn_pq.push(monster, monster.get_currturn())
        # print("GAME: Turnloop started")

    # Ends the game.
    def _end_game(self):
        self.game_exit = True
        # self._reset_gen_eligibility()
        # Relinquish control back to the main menu

    # Indicates that the game needs to handle the next turn in the turnloop.
    # This is both for players and monsters, so it may be called internally or externally.
    def next_turn(self):
        # next turn should do nothing if game_over or game_exit is true
        # Either condition indicates that the turnloop should no longer be active
        if self.game_exit or self.game_over:
            return

        # Game over check
        if not self.player.is_alive():
            # You were defeated; game over
            if self.selfdeath:
                message = "You went out on your own terms; Game Over"
            else:
                message = "You have been defeated; Game Over"
            self.msg_log.append(message)
            print("=== GAME OVER ===")
            self.game_over = True
            return

        # Level clear check
        if len(self.turn_pq) < 2:
            # Just the player is left; print level clear message
            message = "Level Clear"

        # Pop actor; check if player turn
        _, actor = self.turn_pq.pop()
        player_turn = isinstance(actor, Player)

        if actor.is_alive():
            r, c = actor.get_pos()
            # print(
            #     f"TURN {actor.get_currturn()} for {actor.get_name()} at (r:{r:0d}, c: {c:0d}) with speed {actor.get_speed()}"
            # )

            if player_turn:
                # Await player input to call its turn handeler
                # Essentially 'pauses' the turnloop until keyboard input results in end of player turn
                if self.curr_input_mode != self.input_modes["player_turn"]:
                    # Update bottom messages for player location and score
                    self.curr_input_mode = self.input_modes["player_turn"]
                    return
            else:
                # Call the monster's turn handler directly
                success, targ_actor, dmg = actor.handle_turn(
                    self.dungeon,
                    self.actor_map,
                    self.item_list,
                    self.item_map,
                    self.player,
                    8,
                )

            # Re-queue monster
            new_turn = actor.get_currturn() + (1000 // actor.get_speed())
            actor.set_currturn(new_turn)
            self.turn_pq.push(actor, new_turn)

            if isinstance(targ_actor, Player) and dmg != 0:
                message = actor.get_name() + " dealt " + str(dmg) + " damage to you"

                self.msg_log.append(message)
        elif actor.is_boss():
            # Killed a boss monster; Game ends
            message = f"{actor.get_name()} (BOSS) defeated; Game Over"
            print(message)
            self.msg_log.append(message)
            print("=== GAME OVER ===")
            self.game_over = True
