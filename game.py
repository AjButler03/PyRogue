import tkinter as tk
from utility import *
from actor import *
from dungeon import *


# This file handles the main gameloop and the tkinter UI for the game itself.


# The Pyrogue_Game class handles all the high-level game logic and control.
class Pyrogue_Game:

    # Pyrogue_Game constructor.
    def __init__(
        self,
        menu_main,
        root,
        scrsize_h: int,
        scrsize_w: int,
        mapsize_h: int,
        mapsize_w: int,
        difficulty: float,
        monster_type_list: list,
        generate=True,
    ):
        # Menu from which this game instance was launched from
        self.menu_main = menu_main

        # Tkinter root
        self.root = root

        # Default font
        self.def_font = "Consolas"

        # Init internal idea of screen size in pixels
        self.scrsize_h = scrsize_h
        self.scrsize_w = scrsize_w

        # Internal idea of size for UI elements; scales with screensize on render.
        # number of char 'rows' in screen; one for each row in dungeon + 3 for messages / player info
        self.scrn_rows = mapsize_h + 3
        max_tile_width = scrsize_w // mapsize_w
        max_tile_height = (
            scrsize_h // self.scrn_rows
        )  # Note that there are 3 extra rows for messages / player information
        self.tile_size = min(max_tile_width, max_tile_height)
        self.font_size = int(self.tile_size / 1.5)

        # Init internal idea of dungeon size
        self.mapsize_h = mapsize_h
        self.mapsize_w = mapsize_w

        # Game difficulty; applies to monster spawn rates
        self.difficulty = difficulty

        # Init dungeon and player fields
        self.dungeon = None
        self.player = None
        self.player_score = 0

        # Init lists for monsters as well as the map storing all actor locations
        self.monster_type_list = monster_type_list
        self.monster_list = []
        self.actor_map = []
        self.turn_pq = None

        # here in case I implement game save/load; until then, always randomly generate
        if generate:
            self._init_generated_game()

        # Init the canvas to display dungeon / actors
        self.canvas = tk.Canvas(
            self.root,
            bg="black",
            height=scrsize_h,
            width=scrsize_w,
            bd=0,
            highlightthickness=5,
        )

        self.canvas.pack(fill=tk.BOTH, expand=True, side="top")

        # Init some fields related to rendering
        self.need_full_rerender = True
        # Dungeon display modes; displays different aspects of the map.
        self.render_modes = {"standard": 0, "x-ray": 1, "walkmap": 2, "tunnmap": 3}
        self.curr_render_mode = self.render_modes["standard"]
        # {(row, col): (char, color)}. Stores last updated render info.
        self.render_cache = {}

        # Fields to handle submenus and their navigation
        self.submenu_canvas = None
        self.submenu_select_idx = 0
        self.need_submenu_rerender = False
        self.display_submenus = {
            "none": 0,
            "menu_exit": 1,
            "menu_monster_list": 2,
            "menu_inventory": 3,
            "menu_equipment": 4,
        }
        self.curr_submenu = self.display_submenus["none"]

        # To handle screen resizes
        self.resize_id = None
        self.resize_event = None
        self.canvas.bind("<Configure>", self._on_win_resize)

        # Store what messages and font color should be displayed
        # Cache is to prevent unnecessary updates in render
        self.top_msg_cache = ("", "")
        self.score_msg_cache = ("", "")
        self.pinfo_msg_cache = ("", "")
        self.top_msg = "Press any key to start"
        self.score_msg = "SCORE: 0"
        pc_r, pc_c = self.player.get_pos()
        self.pinfo_msg = (
            "HEALTH: "
            + str(self.player.hp)
            + "   POS: (R:"
            + str(pc_r)
            + ", C:"
            + str(pc_c)
            + ")"
        )
        self.top_msg_color = "gold"
        self.score_msg_color = "white"
        self.pinfo_msg_color = "white"

        # Fields for handling keyboard input
        self.root.bind("<Key>", self._on_key_press)
        self.input_modes = {"none": 0, "player_turn": 1, "menu_exit": 2}
        self.curr_input_mode = self.input_modes["player_turn"]

        # Misc game control fields
        self.turnloop_started = False
        self.game_over = False  # Indicate game over
        self.game_exit = False  # Indicate that user intends to exit to main menu

        # Start the turnloop for the game
        self._start_turnloop()
        print("=== GAME START ===")

    # Event handeler for screen resizing.
    def _on_win_resize(self, event):
        # Save the event for redrawing
        self.resize_event = event

        # Cancel any pending redraw
        if self.resize_id:
            self.root.after_cancel(self.resize_id)

        # schedule a redraw for 50ms from now
        self.resize_id = self.root.after(100, self._resize_frame)

    # High-level event handler for keyboard input. Will call different handlers based on current input mode, enabling / disabling those modes as necessary.
    def _on_key_press(self, event):
        key = event.keysym
        print(f"GAME KEY INPUT: {key}")

        # Check the current input mode and call the appropriate input handler
        if self.curr_input_mode == self.input_modes["menu_exit"]:
            # Calling exit submenu input handler
            self._handle_exit_input(key)
        elif self.curr_input_mode == self.input_modes["player_turn"]:
            # Calling player input handler
            turn_completed = self._handle_player_input(key)
            if turn_completed:
                self.curr_input_mode = self.input_modes["none"]
                print("GAME: Player turn completed")

                # Requeue player
                new_turn = self.player.get_currturn() + self.player.get_speed()
                self.turn_pq.push(self.player, new_turn)
                self.player.set_currturn(new_turn)
                self.root.after(10, self._next_turn)
            else:
                # Player turn was not concluded; turn continues
                print("GAME: Player turn continues")

        # Any input after end of game returns control to main menu
        if self.game_over:
            # For now, just end game.
            # Maybe I'll print a message to use the exit menu, but thats a design choice, not a technical limitation.
            self._end_game()

    # Handles input for player turn. Returns True on completion of turn, false if turn is still ongoing.
    def _handle_player_input(self, key) -> int:
        # Compact way of checking for movement keys and grabbing the respective move
        move_delta = {
            "7": Move.up_left,
            "y": Move.up_left,
            "8": Move.up,
            "k": Move.up,
            "9": Move.up_right,
            "u": Move.up_right,
            "4": Move.left,
            "h": Move.left,
            "5": Move.none,
            "space": Move.none,
            "period": Move.none,
            "6": Move.right,
            "l": Move.right,
            "1": Move.down_left,
            "b": Move.down_left,
            "2": Move.down,
            "j": Move.down,
            "3": Move.down_right,
            "n": Move.down_right,
        }

        if key not in move_delta:
            # Other input; Either navigating to a submenu or passing staircase
            if key == "greater" or key == "0":
                pc_r, pc_c = self.player.get_pos()
                # Wanting to navigate staircase; check that staircase is present where player is standing
                if self.dungeon.tmap[pc_r][pc_c] == Dungeon.Terrain.stair:
                    # replace the dungeon, re-generating monsters and restarting the turn loop
                    self._replace_dungeon()
                    pc_r, pc_c = self.player.get_pos()
                    pinfo_msg = (
                        "HEALTH: "
                        + str(self.player.hp)
                        + "   POS: (R:"
                        + str(pc_r)
                        + ", C:"
                        + str(pc_c)
                        + ")"
                    )
                    self._update_pinfo_label(pinfo_msg)
                    message = "You escaped to a new level of the dungeon"
                    self._update_top_label(message, "gold")
                    return True
                else:
                    message = "You can't escape from here; no staircase"
                    self._update_top_label(message)
            elif key == "z":
                # Rotate through distance map displays
                if self.curr_render_mode == self.render_modes["standard"]:
                    self.curr_render_mode = self.render_modes["walkmap"]
                elif self.curr_render_mode == self.render_modes["walkmap"]:
                    self.curr_render_mode = self.render_modes["tunnmap"]
                elif self.curr_render_mode == self.render_modes["tunnmap"]:
                    self.curr_render_mode = self.render_modes["standard"]
                self.need_full_rerender = True
                self._render_frame(self.scrsize_h, self.scrsize_w)
            elif key == "f":
                # Toggle fog of war
                if self.curr_render_mode == self.render_modes["standard"]:
                    # Turn on x-ray mode to show the full dungeon
                    self.curr_render_mode = self.render_modes["x-ray"]
                    print("GAME: Enabled x-ray render mode")
                else:
                    # return to standard render mode, known tiles
                    self.curr_render_mode = self.render_modes["standard"]
                    print("GAME: Returned to standard render mode")
                self.need_full_rerender = True
                self._render_frame(self.scrsize_h, self.scrsize_w)
            elif key == "Escape":
                # Enter the "exit" menu for exit options
                self.curr_input_mode = self.input_modes["menu_exit"]
                self.curr_submenu = self.display_submenus["menu_exit"]
                self.submenu_select_idx = 0
                self._render_exit_menu()
                self._update_top_label("PAUSED")
                print("GAME: Exit sub-menu activated")
                return False
            else:
                # Misinput; return false
                return False
        else:
            # Regular valid move
            move = move_delta[key]
            success, targ_actor, dmg = self.player.handle_turn(
                self.dungeon, self.actor_map, self.player, move
            )
            if success:
                if targ_actor != None:
                    if targ_actor.is_alive():
                        if targ_actor.is_unique():
                            message = (
                                "You dealt "
                                + str(dmg)
                                + " dmg to "
                                + targ_actor.typedef.name
                            )
                        else:
                            message = (
                                "You dealt "
                                + str(dmg)
                                + " dmg to a "
                                + targ_actor.typedef.name
                            )
                    else:
                        # Print kill message
                        if targ_actor.is_unique():
                            message = "You killed " + targ_actor.typedef.name
                        else:
                            message = "You killed a " + targ_actor.typedef.name
                        # Remove monster from map
                        targ_r, targ_c = targ_actor.get_pos()
                        self.actor_map[targ_r][targ_c] = None
                        self.player_score += targ_actor.get_score_val()

                    self._update_top_label(message)
                else:
                    # Just a plain successful move; reset message
                    self._update_top_label("")
                    self.player_score += 1
                return success
            else:
                message = "You can't move there"
                self._update_top_label(message)
                return False

    # Handles input for exit submenu
    def _handle_exit_input(self, key):
        if key == "Return":
            # User made selection
            if self.submenu_select_idx == 0:
                self.curr_input_mode = self.input_modes["player_turn"]
                self.curr_submenu = self.display_submenus["none"]
                self.submenu_canvas.destroy()
                self.need_full_rerender = True
                print("GAME: Exit sub-menu closed")
                self._update_top_label("")
            elif self.submenu_select_idx == 1:
                self._end_game()
            elif self.submenu_select_idx == 2:
                # Force exit; maybe not the way to do it, but it seems to work fine
                exit(0)
        elif key == "j" or key == "Down" or key == "2":
            # Move selection down
            if self.submenu_select_idx < 2:
                self.submenu_select_idx += 1
            else:
                self.submenu_select_idx = 0
            self.need_submenu_rerender = True
            self._render_exit_menu()
        elif key == "k" or key == "Up" or key == "8":
            # Move selection up
            if self.submenu_select_idx >= 1:
                self.submenu_select_idx -= 1
            else:
                self.submenu_select_idx = 2
            self.need_submenu_rerender = True
            self._render_exit_menu()
        elif key == "Escape":
            self.curr_input_mode = self.input_modes["player_turn"]
            self.curr_submenu = self.display_submenus["none"]
            self.submenu_canvas.destroy()
            self.need_full_rerender = True
            print("GAME: Exit sub-menu closed")
            self._update_top_label("")

    # Populates the actor_map with a dungeon size proportionate number of monsters.
    # Difficulty is a modifier for the spawn rate of monsters in the dungeon.
    def _generate_monsters(self):
        attemptc = 0
        monsterc = 0
        size_modifier = self.dungeon.width * self.dungeon.height
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
            if mtypedef.is_gen_eligible() and random.randint(0, 100) >= mtypedef.rarity:
                # Create monster
                new_monster = Monster(mtypedef)
                if monsterc <= min_monsterc or exp_chancetime(
                    monsterc - min_monsterc, decay_rate
                ):
                    if new_monster.init_pos(
                        self.dungeon,
                        self.actor_map,
                        random.randint(1, self.dungeon.height - 2),
                        random.randint(1, self.dungeon.width - 2),
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

    # Resets the generation eligibility for item/monster type definitions
    def _reset_gen_eligibility(self):
        # Reset monster generation eligibility
        # Note that unique monsters only reset if they were not killed or if the game is over
        for monster in self.monster_list:
            # If game exit, force full reset. Otherwise depends on uniqueness and alive/dead
            monster.update_gen_eligible(False, self.game_exit)

    # Initializes a new dungeon for the game to use; this also re-generates the monsters and restarts the turnloop.
    def _replace_dungeon(self):
        print("STAIRCASE; NEW DUNGEON")

        # Reset monster generation eligibility
        self._reset_gen_eligibility()

        # Init the dungeon itself
        self.dungeon = Dungeon(self.mapsize_h, self.mapsize_w)
        self.dungeon.generate_dungeon()

        # Clear actor map, monster list, and priority queue
        self.actor_map = [
            [None] * self.dungeon.width for _ in range(self.dungeon.height)
        ]
        self.monster_list = []
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

        # Restart the turn loop
        self._start_turnloop()

    # Initializes the game with randomly generated dungeon and monsters
    # Dungeon is size_h * size_w, difficulty modifies monster spawn rates.
    def _init_generated_game(self):
        # Init dungeon
        self.dungeon = Dungeon(self.mapsize_h, self.mapsize_w)
        self.dungeon.generate_dungeon()

        # Init actor map
        self.actor_map = [
            [None] * self.dungeon.width for _ in range(self.dungeon.height)
        ]

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

    # Wrapper to update top message label. Cyan is the default message color.
    def _update_top_label(self, message: str, font_color: str = "cyan"):
        print("GAME MSG:", message)
        self.top_msg = message
        self.top_msg_color = font_color

        # Update canvas
        if (self.top_msg, self.top_msg_color) != self.top_msg_cache:
            self.canvas.itemconfig(
                "top_msg", text=self.top_msg, fill=self.top_msg_color
            )
            self.top_msg_cache = (self.top_msg, self.top_msg_color)

    # Wrapper to update the bottom label for score. White is default message color.
    def _update_score_label(self, message: str, font_color: str = "white"):
        self.score_msg = message
        self.score_msg_color = font_color

        # Update text on canvas
        if (self.score_msg, self.score_msg_color) != self.score_msg_cache:
            self.canvas.itemconfig(
                "score_msg", text=self.score_msg, fill=self.score_msg_color
            )
            self.score_msg_cache = (self.score_msg, self.score_msg_color)

    # Wrapper to update bottom label for player info. White is default message color.
    def _update_pinfo_label(self, message: str, font_color: str = "white"):
        self.pinfo_msg = message
        self.pinfo_msg_color = font_color

        # update text on canvas
        if (self.pinfo_msg, self.pinfo_msg_color) != self.pinfo_msg_cache:
            self.canvas.itemconfig(
                "pinfo_msg", text=self.pinfo_msg, fill=self.pinfo_msg_color
            )
            self.pinfo_msg_cache = (self.pinfo_msg, self.pinfo_msg_color)

    # Error handeling for screen resizing event handeler.
    def _resize_frame(self):
        if self.resize_event == None:
            return

        event = self.resize_event
        self.scrsize_h = event.height
        self.scrsize_w = event.width
        self.need_full_rerender = True
        self._render_frame(self.scrsize_h, self.scrsize_w)

    # Handles creating/rendering the exit menu
    def _render_exit_menu(self):
        menu_height = int(self.tile_size * 3.75)
        menu_width = self.tile_size * 7

        if self.need_full_rerender or self.need_submenu_rerender:
            self.submenu_canvas.destroy()

        self.submenu_canvas = tk.Canvas(
            self.canvas,
            height=menu_height,
            width=menu_width,
            bg="black",
            highlightthickness=self.tile_size // 6,
        )
        self.canvas.create_window(
            self.scrsize_w // 2,
            (self.tile_size * self.mapsize_h // 2),
            height=menu_height,
            width=menu_width,
            window=self.submenu_canvas,
            anchor="center",
        )

        offset = self.tile_size // 2
        if self.submenu_select_idx == 0:
            text = "Continue <--"
        else:
            text = "Continue"
        self.submenu_canvas.create_text(
            offset,
            offset // 2,
            text=text,
            fill="gold",
            font=(self.def_font, self.font_size),
            tag="exit_opt_continue",
            anchor="nw",
        )

        if self.submenu_select_idx == 1:
            text = "End game <--"
        else:
            text = "End game"
        self.submenu_canvas.create_text(
            offset,
            offset // 2 + self.tile_size,
            text=text,
            fill="gold",
            font=(self.def_font, self.font_size),
            tag="exit_opt_endgame",
            anchor="nw",
        )

        if self.submenu_select_idx == 2:
            text = "Quit <--"
        else:
            text = "Quit"
        self.submenu_canvas.create_text(
            offset,
            offset // 2 + (self.tile_size * 2),
            text=text,
            fill="gold",
            font=(self.def_font, self.font_size),
            tag="exit_opt_quit",
            anchor="nw",
        )

    # Renders the dungeon to the screen canvas.
    def _render_frame(self, height, width):
        max_tile_width = width // self.dungeon.width
        max_tile_height = (
            height // self.scrn_rows
        )  # Note that there are 3 extra rows for messages / player information
        self.tile_size = min(max_tile_width, max_tile_height)
        self.font_size = int(self.tile_size / 1.5)

        terrain_char = {
            Dungeon.Terrain.floor: ".",
            Dungeon.Terrain.stair: ">",
            Dungeon.Terrain.stdrock: " ",
            Dungeon.Terrain.immrock: "X",
            Dungeon.Terrain.debug: " ",
        }

        x_offset = (width - self.tile_size * self.dungeon.width) // 2  # To center
        y_offset = self.tile_size  # To leave room for top message

        if self.need_full_rerender:
            self.render_cache.clear()

            # Calculate dungeon bounds in pixels
            dungeon_left = x_offset + self.tile_size
            dungeon_top = y_offset + self.tile_size
            dungeon_right = (
                dungeon_left
                + ((self.dungeon.width - 1) * self.tile_size)
                - self.tile_size
            )
            dungeon_bottom = (
                dungeon_top
                + ((self.dungeon.height - 1) * self.tile_size)
                - self.tile_size
            )

            # Deleting existing messages and border
            self.canvas.delete("all")

            # Draw top message label
            x = x_offset + (self.tile_size // 4)
            y = self.tile_size // 4
            self.canvas.create_text(
                x + self.tile_size // 2,
                y + self.tile_size // 1.25,
                text=self.top_msg,
                fill=self.top_msg_color,
                font=(self.def_font, self.font_size),
                tag="top_msg",
                anchor="w",
            )

            # Draw score message label
            y = int((self.dungeon.height + 0.5) * self.tile_size)
            self.canvas.create_text(
                x + self.tile_size // 2,
                y + self.tile_size // 2.5,
                text=self.score_msg,
                fill=self.score_msg_color,
                font=(self.def_font, self.font_size),
                tag="score_msg",
                anchor="w",
            )

            # Draw pinfo message label
            y += self.tile_size
            self.canvas.create_text(
                x + self.tile_size // 2,
                y + self.tile_size // 2.5,
                text=self.pinfo_msg,
                fill=self.pinfo_msg_color,
                font=(self.def_font, self.font_size),
                tag="pinfo_msg",
                anchor="w",
            )

            # Drawing new white border around dungeon
            self.canvas.create_rectangle(
                dungeon_left,
                dungeon_top,
                dungeon_right,
                dungeon_bottom,
                outline="white",
                width=self.tile_size // 2,
                tag="dungeon_border",
            )

        if self.curr_submenu == self.display_submenus["menu_exit"]:
            self._render_exit_menu()

        self.need_full_rerender = False

        for row in range(self.dungeon.height):
            for col in range(self.dungeon.width):
                is_border_tile = (
                    row == 0
                    or col == 0
                    or row == self.dungeon.height - 1
                    or col == self.dungeon.width - 1
                )

                if not is_border_tile:
                    x = col * self.tile_size + x_offset
                    y = row * self.tile_size + y_offset

                    # default
                    char = "!"
                    color = "gray15"

                    # determine the current render mode to grab char & color
                    if self.curr_render_mode == self.render_modes["standard"]:
                        actor = self.actor_map[row][col]
                        if self.player.visible_tiles[row][col]:
                            # Tile is visible, just render as normal.
                            if actor:
                                char = actor.get_char()
                                color = actor.get_color()
                            else:
                                terrain = self.dungeon.tmap[row][col]
                                char = terrain_char[terrain]
                                color = "white"
                        else:
                            # Tile is not visible, so only render player's remembered terrain.
                            terrain = self.player.tmem[row][col]
                            char = terrain_char[terrain]
                    elif self.curr_render_mode == self.render_modes["x-ray"]:
                        # Ignoring player memory of dungeon; just displaying dungeon
                        actor = self.actor_map[row][col]
                        if actor:
                            char = actor.get_char()
                            color = actor.get_color()
                        else:
                            terrain = self.dungeon.tmap[row][col]
                            char = terrain_char[terrain]
                            color = "white"
                    elif self.curr_render_mode == self.render_modes["walkmap"]:
                        # Grab walkmap character
                        val = self.dungeon.walk_distmap[row][col]
                        if val == 0:
                            char = "@"
                            color = "gold"
                        elif val == float("inf"):
                            char = " "
                        else:
                            val = val % 10
                            char = f"{val}"
                    elif self.curr_render_mode == self.render_modes["tunnmap"]:
                        # Grab walkmap character
                        val = self.dungeon.tunn_distmap[row][col]
                        if val == 0:
                            char = "@"
                            color = "gold"
                        elif val == float("inf"):
                            char = " "
                        else:
                            val = val % 10
                            char = f"{val}"

                    # Use a tuple to represent what should be rendered at this tile
                    current_draw = (char, color)
                    cached_draw = self.render_cache.get((row, col))

                    # Only redraw if changed
                    if current_draw != cached_draw:
                        self.render_cache[(row, col)] = current_draw

                        # First, remove anything previously drawn at this location
                        self.canvas.delete(f"tile_{row}_{col}")

                        # Draw black background (optional)
                        self.canvas.create_rectangle(
                            x,
                            y,
                            x + self.tile_size,
                            y + self.tile_size,
                            fill="black",
                            outline="",
                            tag=f"tile_{row}_{col}",
                        )
                        # Draw character
                        self.canvas.create_text(
                            x + self.tile_size // 2,
                            y + self.tile_size // 2,
                            text=char,
                            fill=color,
                            font=(self.def_font, self.font_size),
                            tag=f"tile_{row}_{col}",
                        )

    # Starts the game's turnloop
    def _start_turnloop(self):
        self.turn_pq = PriorityQueue()
        self.player.set_currturn(0)
        self.turn_pq.push(self.player, 0)
        for monster in self.monster_list:
            monster.set_currturn(monster.get_speed())
            # 9 to ensure that ALL monsters get a turn after player's first turn
            self.turn_pq.push(monster, monster.get_currturn())
        print("GAME: Turnloop started")
        self._next_turn()

    # Ends the game, destroying the canvas and unbinding event listeners.
    def _end_game(self):
        self.game_exit = True
        # Destroy the canvas for this game, also unbinding event listeners
        self.canvas.unbind("<Configure>")
        self.canvas.destroy()
        self.root.unbind("<Key>")
        self._reset_gen_eligibility()
        # Relinquish control back to the main menu
        self.menu_main.toggle_ingame()

    # Handles a single turn in the turnloop.
    def _next_turn(self):
        # Stop calling _next_turn if user is exiting game
        if self.game_exit:
            return

        # loop for re-rendering the dungeon
        if self.curr_input_mode != self.input_modes["none"] or self.game_over:
            self._render_frame(self.scrsize_h, self.scrsize_w)
            self.root.after(200, self._next_turn)
            return

        # Game over check
        if len(self.turn_pq) < 2 or not self.player.is_alive():
            score_msg = "SCORE: " + str(self.player_score)
            self._update_score_label(score_msg, "gold")

            # Game has ended; if player is alive, then player won. Otherwise, the monsters won.
            if self.player.is_alive():
                self._update_top_label(
                    "You have defeated all monsters; Game Over", "gold"
                )
                print("You have defeated all monsters; Game Over")
            else:
                self._update_pinfo_label("Player Location: N/A")
                self._update_top_label("You have been defeated; Game Over", "red")
                print("You have been defeated; Game Over")
            print("=== GAME OVER ===")
            self.curr_render_mode = self.render_modes["x-ray"]
            self.need_full_rerender = True
            self.game_over = True
            self.root.after(200, self._next_turn)
            return

        self._render_frame(self.scrsize_h, self.scrsize_w)

        # Pop actor; check if player turn
        _, actor = self.turn_pq.pop()
        player_turn = isinstance(actor, Player)

        if actor.is_alive():
            print("TURN", actor.get_currturn(), "for", actor.get_char())

            if player_turn:
                # Await player input to call its turn handeler
                # Essentially 'pauses' the turnloop until keyboard input results in end of player turn
                if self.curr_input_mode != self.input_modes["player_turn"]:
                    # Update bottom messages for player location and score
                    pc_r, pc_c = self.player.get_pos()
                    pinfo_msg = (
                        "HEALTH: "
                        + str(self.player.hp)
                        + "   POS: (R:"
                        + str(pc_r)
                        + ", C:"
                        + str(pc_c)
                        + ")"
                    )
                    score_msg = "SCORE: " + str(self.player_score)
                    self._update_pinfo_label(pinfo_msg)
                    self._update_score_label(score_msg)
                    self.curr_input_mode = self.input_modes["player_turn"]
                    return
            else:
                # Call the monster's turn handler directly
                success, targ_actor, dmg = actor.handle_turn(
                    self.dungeon, self.actor_map, self.player, 8
                )

            # Re-queue monster
            new_turn = actor.get_currturn() + actor.get_speed()
            actor.set_currturn(new_turn)
            self.turn_pq.push(actor, new_turn)

            if isinstance(targ_actor, Player):
                if actor.is_unique():
                    message = (
                        actor.typedef.name + " dealt " + str(dmg) + " damage to you"
                    )
                else:
                    message = (
                        "a "
                        + actor.typedef.name
                        + " dealt "
                        + str(dmg)
                        + " damage to you"
                    )
                self._update_top_label(message)

        # Wait 1ms before running next turn
        self.root.after(1, self._next_turn)
