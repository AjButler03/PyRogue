import tkinter as tk
from utility import *
from actor import *
from dungeon import *


# This file handles the main gameloop and the vast majority of the tkinter user interface for PyRogue.
# I'll admit that this code is a little messier than I think is ideal.


# The Menu_Main class handles the main menu, it's sub-menus, and the main menu's control.
# Consequently, it launches game itself (Pyrogue_Game class)
class Menu_Main:
    # This class has some duplicate code from Pyrogue_game.
    # this is un-ideal, but I want main menu rendering / control to be separate from the game itself to keep things 'simpler'.

    # Pre-defined dungeon sizes
    dungeon_size_setting = {
        "tiny": (15, 30),
        "small": (20, 40),
        "medium": (25, 50),
        "large": (30, 60),
        "very large": (35, 70),
        "enormous": (40, 80),
    }

    # Pre-defined difficulty settings
    difficulty_setting = {
        "trivial": 0.10,
        "easy": 0.5,
        "normal": 1,
        "hard": 1.5,
        "very_hard": 2,
        "legendary": 2.5,
    }

    # Menu_Main constructor.
    def __init__(self, root, scrsize_h: int, scrsize_w: int):

        # Tkinter root
        self.root = root

        # Default font
        self.def_font = "Consolas"

        # Init internal idea of screen size in pixels
        self.scrsize_h = scrsize_h
        self.scrsize_w = scrsize_w

        # Init default dungeon size and difficulty
        self.difficulty = "normal"
        self.dungeon_size = "medium"

        # Now init the canvas that will hold everything
        self.canvas = tk.Canvas(
            self.root,
            bg="black",
            height=self.scrsize_h,
            width=self.scrsize_w,
            bd=0,
            highlightthickness=5,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, side="top")

        # Misc rendering related things
        self.menu_modes = {"main": 0, "settings": 1, "manual": 2, "monstencyc": 3, "itemencyc": 4}
        self.curr_mode = 0
        self.home_select_idx = 0
        self.need_full_rerender = True
        self.in_game = False

        # Some things that help handle dynamic screen resizing
        self.resize_id = None
        self.resize_event = None
        self.canvas.bind("<Configure>", self._on_win_resize)
        
        # For handeling keyboard input
        self.root.bind("<Key>", self._on_key_press)

    # Toggle 'in game' mode; hides the menu canvas, disables controls on menu, etc.
    def toggle_ingame(self):
        if self.in_game:
            self.in_game = False
            self.canvas.delete("all")
            self.canvas.pack(fill=tk.BOTH, expand=True, side="top")
            
            # Re-bind event listener for key input
            self.root.bind("<Key>", self._on_key_press)
            
            self.need_full_rerender = True
            self._resize_frame()
        else:
            self.in_game = True
            self.canvas.pack_forget()

    # Event handeler for screen resizing.
    def _on_win_resize(self, event):
        
        # First check if in game; if so, do nothing.
        if not self.in_game:
            # Save the event for redrawing
            self.resize_event = event

            # Cancel any pending redraw
            if self.resize_id:
                self.root.after_cancel(self.resize_id)

            # schedule a redraw for 50ms from now
            self.resize_id = self.root.after(100, self._resize_frame)
    
    # Input event handler for the home page
    def _home_input_handler(self, key):
            if key == "Return":
                # User made selection for new page
                if self.home_select_idx == 0:
                    # Start a new game
                    print("Starting game")
                    self.toggle_ingame()
                    mapsize_h, mapsize_w = self.dungeon_size_setting[self.dungeon_size]
                    Pyrogue_Game(self, self.root, self.scrsize_h, self.scrsize_w, mapsize_h, mapsize_w, self.difficulty_setting[self.difficulty])
                elif self.home_select_idx == 5:
                    # Force exit; maybe not the way to do it, but it seems to work fine
                    exit(0)
            elif key == "j" or key == "Down" or key == "2":
                # Move selection down
                if self.home_select_idx < 5:
                    self.home_select_idx += 1
                    self.need_full_rerender = True
                    self._render_home(self.scrsize_h, self.scrsize_w)
                else:
                    self.home_select_idx = 0
                    self.need_full_rerender = True
                    self._render_home(self.scrsize_h, self.scrsize_w)
            elif key == "k" or key == "Up" or key == "8":
                # Move selection up
                if self.home_select_idx >= 1:
                    self.home_select_idx -= 1
                    self.need_full_rerender = True
                    self._render_home(self.scrsize_h, self.scrsize_w)
                else:
                    self.home_select_idx = 5
                    self.need_full_rerender = True
                    self._render_home(self.scrsize_h, self.scrsize_w)
    
    # Input event handler for the settings page
    def _settings_input_handler(self, key):
        pass
    
    # Input event handler for the manual page
    def _manual_input_handler(self, key):
        pass
    
    # Input event handler for the monster encyclopedia page
    def _monstencyc_input_handler(self, key):
        pass
    
    # Input event handler for the item encyclopedia page
    def _itemencyc_input_handler(self, key):
        pass
    
    # Event handler for keyboard input.
    def _on_key_press(self, event):
        if not self.in_game:
            key = event.keysym
            print(f"MENU KEY INPUT: {key}")
            # Check which page that the user is on, go to the appropriate handler
            if self.curr_mode == 0:
                self._home_input_handler(key)
                        
    # Handles resizing the window.
    def _resize_frame(self):
        if not self.in_game:
            if self.resize_event == None:
                return

            event = self.resize_event
            self.scrsize_h = event.height
            self.scrsize_w = event.width
            self.need_full_rerender = True
            # Call appropriate renderer; depends on current menu to be shown
            if self.curr_mode == self.menu_modes['main']:
                print("MENU: Re-rendered main screen")
                self._render_home(self.scrsize_h, self.scrsize_w)
    
    # Renderer for the main menu's home page.
    def _render_home(self, height, width):        
        # Arbitrary bounds to determine how big home screen text should be
        home_scr_charcol = 26 # At least this many 'tiles' wide
        home_scr_charrow = 16 # At least this many 'tiles' tall
        
        # Decide how big in pixels elements should be based on screen size
        max_tile_width = width // home_scr_charcol
        max_tile_height = (
            height // home_scr_charrow
        )  # Note that there are 3 extra rows for messages / player information
        tile_size = min(max_tile_width, max_tile_height)
        self.font_size = int(tile_size / 1.5)

        x_offset = tile_size
        y_offset = tile_size

        if self.need_full_rerender:
            version_str = "v0.05 July 2025"
            
            # This is a series of string lines that form the PyRogue ASCII art text.
            # It's a little garbled here because of excape character \.
            ascii_line1 = "    ____        ____                       "
            ascii_line2 = "   / __ \\__  __/ __ \\____  ____ ___  _____ "
            ascii_line3 = "  / /_/ / / / / /_/ / __ \\/ __ `/ / / / _ \\"
            ascii_line4 = " / ____/ /_/ / _, _/ /_/ / /_/ / /_/ /  __/"
            ascii_line5 = "/_/    \\__, /_/ |_|\\____/\\__, /\\__,_/\\___/ "
            ascii_line6 = "      /____/            /____/             "
            
            # making things easier so I can just write loops for rendering home screen elements
            ascii_color = "red"
            ascii_anchor = "w"
            ascii_text = {0:ascii_line1, 1:ascii_line2, 2:ascii_line3, 3:ascii_line4, 4:ascii_line5, 5:ascii_line6}
            ascii_tags = {0:"ascii_ln1", 1:"ascii_ln2", 2:"ascii_ln3", 3:"ascii_ln4", 4:"ascii_ln5", 5:"ascii_ln6"}
            select_opts = {0:"Start Game", 1:"Settings", 2:"Manual", 3:"Monster Encyclopedia", 4:"Item Encyclopedia", 5:"Quit"}
            select_opts_tags = {0:"opt_startgame", 1:"opt_settings", 2:"opt_manual", 3:"opt_monstencyc", 4:"opt_itemencyc", 5:"opt_quit"}
            select_opts_colors = {0:"gold", 1:"gray", 2:"gray", 3:"gray", 4:"gray", 5:"gold"}
            
            # Deleting existing tagged canvas objects
            self.canvas.delete("all")

            # Now clunkily render the ASCII art text line by line
            x = x_offset
            y = y_offset

            # Render the ASCII art text
            for i in range(6):
                self.canvas.create_text(
                    x,
                    y,
                    text=ascii_text[i],
                    fill=ascii_color,
                    font=(self.def_font, self.font_size),
                    tag=ascii_tags[i],
                    anchor=ascii_anchor,
                )
                y += tile_size
            
            # Now draw the home page options
            opt_color = "gold"
            opt_fontsize = int(self.font_size // 1.25)
            x = x_offset * 2
            y += tile_size * 2
            
            for i in range(6):
                self.canvas.create_text(
                    x,
                    y,
                    text=select_opts[i],
                    fill=select_opts_colors[i],
                    font=(self.def_font, opt_fontsize),
                    tag=select_opts_tags[i],
                    anchor=ascii_anchor,
                )
                y += tile_size
            
            # append arrow to whichever selection is currently being made
            new_opt_text = select_opts[self.home_select_idx] + " <--"
            self.canvas.itemconfigure(select_opts_tags[self.home_select_idx], text=new_opt_text)
            
            # Little version number at the bottom of the screen
            x = int(width - tile_size * 3.25)
            y = height - tile_size // 2
            self.canvas.create_text(
                x,
                y,
                text=version_str,
                fill='white',
                font=(self.def_font, (opt_fontsize // 2)),
                tag="version",
                anchor=ascii_anchor,
            )
            
            self.need_full_rerender = False
    
    # Renderer for the main menu's settings page.      
    def _render_settings(self, height, width):
        # Arbitrary bounds to determine how big the screen text should be
        settings_scr_charcol = 35 # width
        settings_scr_charrow = 15 # height
        
        # Decide how big in pixels elements should be based on screen size
        max_tile_width = width // settings_scr_charcol
        max_tile_height = (
            height // settings_scr_charrow
        )  # Note that there are 3 extra rows for messages / player information
        tile_size = min(max_tile_width, max_tile_height)
        self.font_size = int(tile_size / 1.5)
        
        if self.need_full_rerender:
            # This is a series of string lines that form the Settings ASCII art text.
            # It's a little garbled here because of excape character \.
            ascii_line1 = "   ____    __  __  _             "
            ascii_line2 = "  / __/__ / /_/ /_(_)__  ___ ____"
            ascii_line3 = " _\\ \\/ -_) __/ __/ / _ \\/ _ `(_-<"
            ascii_line4 = "/___/\\__/\\__/\\__/_/_//_/\\_, /___/"
            ascii_line5 = "                       /___/     "
        
        
# The Pyrogue_Game class handles all the high-level game logic and control.
class Pyrogue_Game:

    # Pyrogue_Game constructor.
    def __init__(
        self,
        menu_main : Menu_Main,
        root,
        scrsize_h: int,
        scrsize_w: int,
        mapsize_h: int,
        mapsize_w: int,
        difficulty: float,
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
        tile_size = min(max_tile_width, max_tile_height)
        self.font_size = int(tile_size / 1.5)

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
        # {(row, col): (char, color)}. Stores last updated render info.
        self.render_cache = {}
        self.resize_id = None
        self.resize_event = None
        self.canvas.bind("<Configure>", self._on_win_resize)

        # Store what messages and font color should be displayed
        # Cache is to prevent unnecessary updates in render
        self.top_msg_cache = ("", "")
        self.top_msg = "Press any key to start"
        self.top_msg_color = "gold"
        self.score_msg_cache = ("", "")
        self.score_msg = "Score: 0"
        self.score_msg_color = "white"
        self.pinfo_msg_cache = ("", "")
        pc_r, pc_c = self.player.get_pos()
        self.pinfo_msg = "Player Location: Row " + str(pc_r) + ", Column: " + str(pc_c)
        self.pinfo_msg_color = "white"

        # For handeling keyboard input
        self.root.bind("<Key>", self._on_key_press)
        self.turnloop_started = False
        self.game_over = False
        self.awaiting_player_input = False

    # Event handeler for screen resizing.
    def _on_win_resize(self, event):
        # Save the event for redrawing
        self.resize_event = event

        # Cancel any pending redraw
        if self.resize_id:
            self.root.after_cancel(self.resize_id)

        # schedule a redraw for 50ms from now
        self.resize_id = self.root.after(100, self._resize_frame)

    # Event handeler for keyboard input
    def _on_key_press(self, event):
        key = event.keysym
        print(f"GAME KEY INPUT: {key}")
        if not self.turnloop_started:
            # Until I create a main menu, any key input force starts the game.
            self.turnloop_started = True
            self._start_turnloop()
            self._render_frame(self.scrsize_h, self.scrsize_w)
            print("=== GAME START ===")
            # Game start done
            return

        if self.awaiting_player_input:
            success = self._handle_player_input(key)
            if success:
                self.awaiting_player_input = False
                print("PLAYER INPUT SUCCESS")
                # Requeue player
                new_turn = self.player.get_currturn() + self.player.get_speed()
                self.turn_pq.push(self.player, new_turn)
                self.player.set_currturn(new_turn)
                self.root.after(10, self._next_turn)
            else:
                print("PLAYER INPUT FAIL")
        
        # Any input after end of game returns control to main menu
        if self.game_over:
            # Destroy the canvas for this game, also unbinding event listeners
            self.canvas.unbind("<Configure>")
            self.canvas.destroy()
            self.root.unbind("<Key>")
            # Relinquish control back to the main menu
            self.menu_main.toggle_ingame()

    # Populates the actor_map with a dungeon size proportionate number of monsters.
    # Difficulty is a modifier for the spawn rate of monsters in the dungeon.
    def _generate_monsters(self):
        attemptc = 0
        monsterc = 0
        attempt_limit = int(
            self.difficulty * max(self.dungeon.width, self.dungeon.height)
        )
        min_monsterc = max(1, attempt_limit // 10)
        # Adjust exp_chancetime's decay curve to increase additional monster probability with difficulty
        decay_rate = 0.95 / (self.difficulty + 0.5)

        # Generate monsters; runs until minimum number and attempt limit are met
        while (monsterc < min_monsterc) or (attemptc < attempt_limit):
            # Create monster
            new_monster = Monster(random.randint(0, 15), random.randint(5, 20))
            if monsterc <= min_monsterc or exp_chancetime(
                monsterc - min_monsterc, decay_rate
            ):
                if new_monster.init_pos(
                    self.dungeon,
                    self.actor_map,
                    random.randint(1, self.dungeon.height - 2),
                    random.randint(1, self.dungeon.width - 2),
                ):
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

    # Initializes a new dungeon for the game to use; this also re-generates the monsters and restarts the turnloop.
    def _replace_dungeon(self):
        print("STAIRCASE; NEW DUNGEON")
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

    # Handles input for player turn
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
                        "Player Location: Row " + str(pc_r) + ", Column: " + str(pc_c)
                    )
                    self._update_pinfo_label(pinfo_msg)
                    message = "You escaped to a new level of the dungeon"
                    self._update_top_label(message, "gold")
                    return True
                else:
                    message = "You can't escape from here; no staircase"
                    self._update_top_label(message)
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
                    message = "You killed a " + targ_actor.get_char()
                    self.player_score += 10
                    self._update_top_label(message)
                    print("COMBAT:", message)
                else:
                    # Just a plain successful move; reset message
                    self._update_top_label("")
                    self.player_score += 1
                return success
            else:
                message = "You can't move there"
                print("INPUT:", message)
                self._update_top_label(message)
                return False

    # Wrapper to update top message label. Cyan is the default message color.
    def _update_top_label(self, message: str, font_color: str = "cyan"):
        self.top_msg = message
        self.top_msg_color = font_color

    # Wrapper to update the bottom label for score. White is default message color.
    def _update_score_label(self, message: str, font_color: str = "white"):
        self.score_msg = message
        self.score_msg_color = font_color

    # Wrapper to update bottom label for player info. White is default message color.
    def _update_pinfo_label(self, message: str, font_color: str = "white"):
        self.pinfo_msg = message
        self.pinfo_msg_color = font_color

    # Error handeling for screen resizing event handeler.
    def _resize_frame(self):
        if self.resize_event == None:
            return

        event = self.resize_event
        self.scrsize_h = event.height
        self.scrsize_w = event.width
        self.need_full_rerender = True
        self._render_frame(self.scrsize_h, self.scrsize_w)

    # Renders the dungeon to the screen canvas.
    def _render_frame(self, height, width):
        max_tile_width = width // self.dungeon.width
        max_tile_height = (
            height // self.scrn_rows
        )  # Note that there are 3 extra rows for messages / player information
        tile_size = min(max_tile_width, max_tile_height)
        self.font_size = int(tile_size / 1.5)

        terrain_char = {
            Dungeon.Terrain.floor: ".",
            Dungeon.Terrain.stair: ">",
            Dungeon.Terrain.stdrock: " ",
            Dungeon.Terrain.immrock: "X",
            Dungeon.Terrain.debug: "!",
        }

        x_offset = (width - tile_size * self.dungeon.width) // 2  # To center
        y_offset = tile_size  # To leave room for top message

        if self.need_full_rerender:
            self.render_cache.clear()

            # Calculate dungeon bounds in pixels
            dungeon_left = x_offset + tile_size
            dungeon_top = y_offset + tile_size
            dungeon_right = (
                dungeon_left + ((self.dungeon.width - 1) * tile_size) - tile_size
            )
            dungeon_bottom = (
                dungeon_top + ((self.dungeon.height - 1) * tile_size) - tile_size
            )

            # Deleting existing messages and border
            self.canvas.delete("all")

            # Draw top message label
            x = x_offset
            y = 0
            self.canvas.create_text(
                x + tile_size // 2,
                y + tile_size // 1.25,
                text=self.top_msg,
                fill=self.top_msg_color,
                font=(self.def_font, self.font_size),
                tag="top_msg",
                anchor="w",
            )

            # Draw score message label
            y = (self.dungeon.height + 1) * tile_size
            self.canvas.create_text(
                x + tile_size // 2,
                y + tile_size // 2.5,
                text=self.score_msg,
                fill=self.score_msg_color,
                font=(self.def_font, self.font_size),
                tag="score_msg",
                anchor="w",
            )

            # Draw pinfo message label
            y = (self.dungeon.height + 2) * tile_size
            self.canvas.create_text(
                x + tile_size // 2,
                y + tile_size // 2.5,
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
                width=tile_size,
                tag="dungeon_border",
            )
            self.need_full_rerender = False

        # Update text labels, if needed
        # First check top message
        if (self.top_msg, self.top_msg_color) != self.top_msg_cache:
            self.canvas.itemconfig(
                "top_msg", text=self.top_msg, fill=self.top_msg_color
            )
            self.top_msg_cache = (self.top_msg, self.top_msg_color)

        # Check score message
        if (self.score_msg, self.score_msg_color) != self.score_msg_cache:
            self.canvas.itemconfig(
                "score_msg", text=self.score_msg, fill=self.score_msg_color
            )
            self.score_msg_cache = (self.score_msg, self.score_msg_color)

        # Finally check pinfo message
        if (self.pinfo_msg, self.pinfo_msg_color) != self.pinfo_msg_cache:
            self.canvas.itemconfig(
                "pinfo_msg", text=self.pinfo_msg, fill=self.pinfo_msg_color
            )
            self.pinfo_msg_cache = (self.pinfo_msg, self.pinfo_msg_color)

        for row in range(self.dungeon.height):
            for col in range(self.dungeon.width):
                is_border_tile = (
                    row == 0
                    or col == 0
                    or row == self.dungeon.height - 1
                    or col == self.dungeon.width - 1
                )

                if not is_border_tile:
                    x = col * tile_size + x_offset
                    y = row * tile_size + y_offset

                    actor = self.actor_map[row][col]
                    if actor:
                        char = actor.get_char()
                        color = "gold" if isinstance(actor, Player) else "red"
                    else:
                        terrain = self.dungeon.tmap[row][col]
                        char = terrain_char[terrain]
                        color = "white"

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
                            x + tile_size,
                            y + tile_size,
                            fill="black",
                            outline="",
                            tag=f"tile_{row}_{col}",
                        )
                        # Draw character
                        self.canvas.create_text(
                            x + tile_size // 2,
                            y + tile_size // 2,
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
        self._update_top_label("")
        print("GAME: Turnloop started")
        self._next_turn()

    # Handles a single turn in the turnloop.
    def _next_turn(self):
        # If player's turn, do nothing and wait
        if self.awaiting_player_input:
            return

        # Game over check
        if len(self.turn_pq) < 2 or not self.player.is_alive():
            score_msg = "Score: " + str(self.player_score)
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
            self.game_over = True
            self._render_frame(self.scrsize_h, self.scrsize_w)
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
                if not self.awaiting_player_input:
                    # Update bottom messages for player location and score
                    pc_r, pc_c = self.player.get_pos()
                    pinfo_msg = (
                        "Player Location: Row " + str(pc_r) + ", Column: " + str(pc_c)
                    )
                    score_msg = "Score: " + str(self.player_score)
                    self._update_pinfo_label(pinfo_msg)
                    self._update_score_label(score_msg)
                    self.awaiting_player_input = True
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
                message = "a " + actor.get_char() + " dealt damage to you"
                self._update_top_label(message)
                print("COMBAT:", message)

        # Wait 1ms before running next turn
        self.root.after(1, self._next_turn)
