import tkinter as tk
from game import Pyrogue_Game

# This file handles PyRogue's main menu, its associated submenus, input handling, etc. with Tkinter.


# The Menu_Main class handles the main menu, it's sub-menus, and the main menu's control.
class Menu_Main:
    # This class has some duplicate code from Pyrogue_game.
    # this is un-ideal, but I want main menu rendering / control to be separate from the game itself to keep things 'simpler'.

    # Pre-defined dungeon sizes
    dungeon_size_setting = {
        0: (15, 30),
        1: (20, 40),
        2: (25, 50),
        3: (30, 60),
        4: (35, 70),
        5: (40, 80),
    }

    # Pre-defined difficulty settings
    difficulty_setting = {0: 0.05, 1: 0.25, 2: 0.5, 3: 0.75, 4: 1.5, 5: 2.5}

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
        self.difficulty = 2
        self.dungeon_size = 2

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
        self.menu_modes = {
            "home": 0,
            "settings": 1,
            "manual": 2,
            "monstencyc": 3,
            "itemencyc": 4,
        }
        self.curr_mode = 0
        self.need_full_rerender = True
        self.in_game = False

        # Stuff for keeping track of what is currently being hovered on when selecting
        self.home_select_idx = 0
        self.setting_select_row = 0
        self.setting_select_col = 0

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

            difficulty_idx = {
                0: "trivial",
                1: "easy",
                2: "normal",
                3: "hard",
                4: "very hard",
                5: "legendary",
            }

            dungeon_size_idx = {
                0: "tiny",
                1: "small",
                2: "medium",
                3: "large",
                4: "very large",
                5: "enormous",
            }

            print(
                "MENU: New game with size",
                dungeon_size_idx[self.dungeon_size],
                " and diff",
                difficulty_idx[self.difficulty],
            )

            mapsize_h, mapsize_w = self.dungeon_size_setting[self.dungeon_size]
            Pyrogue_Game(
                self,
                self.root,
                self.scrsize_h,
                self.scrsize_w,
                mapsize_h,
                mapsize_w,
                self.difficulty_setting[self.difficulty],
            )
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
                self.toggle_ingame()
            elif self.home_select_idx == 1:
                # Settings page
                self.curr_mode = self.menu_modes["settings"]
                self.need_full_rerender = True
                self.setting_select_col = 0
                self.setting_select_row = 0
                self._render_settings(self.scrsize_h, self.scrsize_w)
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
        if key == "Escape":
            # Head back to main menu
            self.curr_mode = self.menu_modes["home"]
            self.need_full_rerender = True
            self._render_home(self.scrsize_h, self.scrsize_w)
        elif key == "Return":
            # Making a setting selection
            if self.setting_select_col == 0:
                # Selecting new dungeon size
                self.dungeon_size = self.setting_select_row
                self.need_full_rerender = True
                self._render_settings(self.scrsize_h, self.scrsize_w)
            else:
                self.difficulty = self.setting_select_row
                self.need_full_rerender = True
                self._render_settings(self.scrsize_h, self.scrsize_w)

        elif (
            key == "Right"
            or key == "l"
            or key == "6"
            or key == "Left"
            or key == "h"
            or key == "4"
        ):
            # Move select arrow left/right (two col, so just swap)
            if self.setting_select_col == 1:
                self.setting_select_col = 0
            else:
                self.setting_select_col = 1

            self.need_full_rerender = True
            self._render_settings(self.scrsize_h, self.scrsize_w)
        elif key == "j" or key == "Down" or key == "2":
            # Move selection down
            if self.setting_select_row < 5:
                self.setting_select_row += 1
            else:
                self.setting_select_row = 0
            self.need_full_rerender = True
            self._render_settings(self.scrsize_h, self.scrsize_w)
        elif key == "k" or key == "Up" or key == "8":
            # Move selection up
            if self.setting_select_row > 0:
                self.setting_select_row -= 1
            else:
                self.setting_select_row = 5
            self.need_full_rerender = True
            self._render_settings(self.scrsize_h, self.scrsize_w)

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
            # Check which page that the user is on, go to the appropriate handler
            if self.curr_mode == self.menu_modes["home"]:
                print(f"MENU HOME INPUT: {key}")
                self._home_input_handler(key)
            elif self.curr_mode == self.menu_modes["settings"]:
                print(f"MENU SETTINGS INPUT: {key}")
                self._settings_input_handler(key)
            elif self.curr_mode == self.menu_modes["manual"]:
                print(f"MENU MANUAL INPUT: {key}")
                self._manual_input_handler(key)
            elif self.curr_mode == self.menu_modes["monstencyc"]:
                print(f"MENU MONST INPUT: {key}")
                self._monstencyc_input_handler(key)
            elif self.curr_mode == self.menu_modes["itemencyc"]:
                print(f"MENU ITEM INPUT: {key}")
                self._itemencyc_input_handler(key)

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
            if self.curr_mode == self.menu_modes["home"]:
                print("MENU: Rendered home")
                self._render_home(self.scrsize_h, self.scrsize_w)
            elif self.curr_mode == self.menu_modes["settings"]:
                print("MENU: Rendered settings")
                self._render_settings(self.scrsize_h, self.scrsize_w)

    # Renderer for the main menu's home page.
    def _render_home(self, height, width):
        # Arbitrary bounds to determine how big home screen text should be
        home_scr_charcol = 26  # At least this many 'tiles' wide
        home_scr_charrow = 16  # At least this many 'tiles' tall

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
            ascii_text = {
                0: ascii_line1,
                1: ascii_line2,
                2: ascii_line3,
                3: ascii_line4,
                4: ascii_line5,
                5: ascii_line6,
            }
            ascii_tags = {
                0: "ascii_ln1",
                1: "ascii_ln2",
                2: "ascii_ln3",
                3: "ascii_ln4",
                4: "ascii_ln5",
                5: "ascii_ln6",
            }
            select_opts = {
                0: "Start Game",
                1: "Settings",
                2: "Manual",
                3: "Monster Encyclopedia",
                4: "Item Encyclopedia",
                5: "Quit",
            }
            select_opts_tags = {
                0: "opt_startgame",
                1: "opt_settings",
                2: "opt_manual",
                3: "opt_monstencyc",
                4: "opt_itemencyc",
                5: "opt_quit",
            }
            select_opts_colors = {
                0: "gold",
                1: "gold",
                2: "gray",
                3: "gray",
                4: "gray",
                5: "gold",
            }

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
            self.canvas.itemconfigure(
                select_opts_tags[self.home_select_idx], text=new_opt_text
            )

            # Little version number at the bottom of the screen
            x = int(width - tile_size * 3.25)
            y = height - tile_size // 2
            self.canvas.create_text(
                x,
                y,
                text=version_str,
                fill="white",
                font=(self.def_font, (opt_fontsize // 2)),
                tag="version",
                anchor=ascii_anchor,
            )

            self.need_full_rerender = False

    # Renderer for the main menu's settings page.
    def _render_settings(self, height, width):
        # A lot of this code is just some arbitrary numbers to try and eyball things into looking good.
        # If it works, it works. I'm not going to claim that this bit in specific is the most clean, though.

        # Arbitrary bounds to determine how big the screen text should be
        settings_scr_charcol = 18  # width
        settings_scr_charrow = 15  # height

        # Decide how big in pixels elements should be based on screen size
        max_tile_width = width // settings_scr_charcol
        max_tile_height = (
            height // settings_scr_charrow
        )  # Note that there are 3 extra rows for messages / player information
        tile_size = min(max_tile_width, max_tile_height)
        self.font_size = int(tile_size / 1.5)

        x_offset = tile_size
        y_offset = tile_size

        if self.need_full_rerender:
            # Clear canvas
            self.canvas.delete("all")

            opt_fontsize = int(self.font_size // 1.5)

            # This is a series of string lines that form the Settings ASCII art text.
            # It's a little garbled here because of excape character \.
            ascii_line1 = "   ____    __  __  _             "
            ascii_line2 = "  / __/__ / /_/ /_(_)__  ___ ____"
            ascii_line3 = " _\\ \\/ -_) __/ __/ / _ \\/ _ `(_-<"
            ascii_line4 = "/___/\\__/\\__/\\__/_/_//_/\\_, /___/"
            ascii_line5 = "                       /___/     "

            ascii_text = {
                0: ascii_line1,
                1: ascii_line2,
                2: ascii_line3,
                3: ascii_line4,
                4: ascii_line5,
            }
            ascii_tags = {
                0: "ascii_ln1",
                1: "ascii_ln2",
                2: "ascii_ln3",
                3: "ascii_ln4",
                4: "ascii_ln5",
            }

            ascii_color = "red"

            size_opts = {
                0: "Tiny       (15x30)",
                1: "Small      (20x40)",
                2: "Medium     (25x50)",
                3: "Large      (30x60)",
                4: "Very Large (35x70)",
                5: "Enormous   (40x80)",
            }
            size_opts_tags = {
                0: "size_opt_tiny",
                1: "size_opt_small",
                2: "size_opt_medium",
                3: "size_opt_large",
                4: "size_opt_vlarge",
                5: "size_opt_enormous",
            }
            diff_opts = {
                0: "Trivial",
                1: "Easy",
                2: "Normal",
                3: "Hard",
                4: "Very Hard",
                5: "Legendary",
            }
            diff_opts_tags = {
                0: "diff_opt_trivial",
                1: "diff_opt_easy",
                2: "diff_opt_normal",
                3: "diff_opt_hard",
                4: "diff_opt_vhard",
                5: "dif_opt_legend",
            }

            x = x_offset
            y = y_offset

            # Draw ASCII art text
            for i in range(5):
                self.canvas.create_text(
                    x,
                    y,
                    text=ascii_text[i],
                    fill=ascii_color,
                    font=(self.def_font, self.font_size),
                    tag=ascii_tags[i],
                    anchor="w",
                )
                y += tile_size

            # Draw headings to setting options
            header_color = "white"
            x1 = x_offset
            x2 = x_offset + (tile_size * 10)
            y = y_offset + (tile_size * 6)
            # Dungeon Size header
            self.canvas.create_text(
                x1,
                y,
                text="Dungeon Size",
                fill=header_color,
                font=(self.def_font, self.font_size),
                tag="header_size_opt",
                anchor="w",
            )
            # Difficulty header
            self.canvas.create_text(
                x2,
                y,
                text="Difficulty",
                fill=header_color,
                font=(self.def_font, self.font_size),
                tag="header_diff_opt",
                anchor="w",
            )

            y = y_offset + (tile_size * 7)

            # Draw setting options
            for i in range(6):
                # Draw size setting
                color = "gold" if self.dungeon_size == i else "gray"
                self.canvas.create_text(
                    x1,
                    y,
                    text=size_opts[i],
                    fill=color,
                    font=(self.def_font, opt_fontsize),
                    tag=size_opts_tags[i],
                    anchor="w",
                )

                # Draw difficulty size setting
                color = "gold" if self.difficulty == i else "gray"
                self.canvas.create_text(
                    x2,
                    y,
                    text=diff_opts[i],
                    fill=color,
                    font=(self.def_font, opt_fontsize),
                    tag=diff_opts_tags[i],
                    anchor="w",
                )
                y += tile_size

            # Render arrow for selection
            if self.setting_select_col == 0:
                x = x_offset + (tile_size * 6)
            else:
                x = x_offset + (tile_size * 13)

            y = (self.setting_select_row * tile_size) + (tile_size * 8)

            self.canvas.create_text(
                x,
                y,
                text="<--",
                fill="gold",
                font=(self.def_font, opt_fontsize),
                tag="setting_select_arrow",
                anchor="w",
            )
