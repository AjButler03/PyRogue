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
        item_type_list: list,
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
        self.item_type_list = item_type_list
        self.monster_list = []
        self.item_list = []
        self.actor_map = []
        self.item_map = []
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
            highlightthickness=0,
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
        self.inspect_obj = None  # Monster/item to be inspected; storing to be able re-render inspect window
        self.need_submenu_rerender = False
        self.display_submenus = {
            "none": 0,
            "menu_exit": 1,
            "menu_monster_list": 2,
            "menu_inventory": 3,
            "menu_equipment": 4,
            "inspect_monster": 5,
            "inspect_item": 6,
        }
        self.curr_submenu = self.display_submenus["none"]

        # To handle screen resizes
        self.resize_id = None
        self.resize_event = None
        self.canvas.bind("<Configure>", self._on_win_resize)

        # Store what messages and font color should be displayed
        # Cache is to prevent unnecessary updates in render
        self.top_msg_cache = ("", "")
        self.top_msg = "Press any key to start"
        self.top_msg_color = "gold"
        self.score_msg_cache = ("", "")
        r, c = self.player.get_pos()
        self.score_msg = f"SCORE: {self.player_score:06d}   MODIFIER: {self.difficulty:.2f}   POS: (R:{r:0d}, C:{c:0d})"
        self.score_msg_color = "white"
        self.hp_msg_cache = ("", "")
        self.hp_msg = f"{self.player.get_hp():03d}/{self.player.get_hp_cap():03d}"
        self.hp_msg_color = "#00FF00"
        self.pinfo_msg_cache = ("", "")
        self.pinfo_msg = f"HP:           SPEED: {self.player.get_speed():03d}   DEFENSE: {self.player.get_defense():03d}   DODGE: {self.player.get_dodge():03d}"
        self.pinfo_msg_color = "white"

        # Fields for handling keyboard input
        self.root.bind("<Key>", self._on_key_press)
        self.input_modes = {
            "none": 0,  # No input should be taken
            "player_turn": 1,  # Main player input for their turn
            "menu_exit": 2,  # Input for exit/pause menu
            "menu_monster_list": 3,  # Input for monster list menu
            "menu_inventory": 4,  # Input for inventory (carry slots) menu
            "menu_equipment": 5,  # Input for equipment menu
            "targeting": 6,  # Input for targeting mode (ranged attacks, teleport, item/monster inspection)
            "inspect": 7,
        }
        # Targeted position information for when using targeting mode
        self.target_r = 0
        self.target_c = 0
        self.curr_input_mode = self.input_modes["player_turn"]

        # To store important game msgs; combat, new dungeon, game start, etc
        self.msg_log = ["GAME START"]

        # Misc game control fields
        self.turnloop_started = False
        self.game_over = False  # Indicate game over
        self.game_exit = False  # Indicate that user intends to exit to main menu

        # Start the turnloop for the game
        self._start_turnloop()
        print("=== GAME START ===")

    # Nerfs speed value so that it doesn't become too overpowered.
    def _speed_nerf(self, base_speed: int) -> int:
        # I don't know how best to do this, so i'm just capping the speed for the player.
        # Anything higher than that seems a little too OP, since it brings every other monster to a standstill.
        return min(base_speed, 50)

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
        # print(f"GAME KEY INPUT: {key}")

        # Check the current input mode and call the appropriate input handler
        if self.curr_input_mode == self.input_modes["player_turn"]:
            # Calling player input handler
            turn_completed = self._handle_player_input(key)
            if turn_completed:
                self.curr_input_mode = self.input_modes["none"]
                print("GAME: Player turn completed")

                # Requeue player
                new_turn = self.player.get_currturn() + (
                    1000 // self._speed_nerf(self.player.get_speed())
                )
                self.turn_pq.push(self.player, new_turn)
                self.player.set_currturn(new_turn)
                self.root.after(10, self._next_turn)
            else:
                # Player turn was not concluded; turn continues
                print("GAME: Player turn continues")
        elif self.curr_input_mode == self.input_modes["menu_exit"]:
            # Calling exit submenu input handler
            self._handle_exit_input(key)
        elif self.curr_input_mode == self.input_modes["menu_monster_list"]:
            # Calling the monster list input handler
            self._handle_mlist_input(key)
        elif self.curr_input_mode == self.input_modes["menu_inventory"]:
            # Calling the inventory menu input handler
            self._handle_inventory_input(key)
        elif self.curr_input_mode == self.input_modes["menu_equipment"]:
            # Calling the equipment menu input handler
            self._handle_equipment_input(key)
        elif self.curr_input_mode == self.input_modes["targeting"]:
            # Calling the targeting mode input handler
            self._handle_targeting_input(key)
        elif self.curr_input_mode == self.input_modes["inspect"]:
            # Inspection window input handler
            self._handle_inspect_input(key)
        # Any input after end of game returns control to main menu
        if self.game_over and (key == "Return" or key == "Escape"):
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
                if self.dungeon.get_terrain_at(pc_r, pc_c) == Dungeon.Terrain.stair:
                    # replace the dungeon, re-generating monsters and restarting the turn loop
                    self._replace_dungeon()
                    pc_r, pc_c = self.player.get_pos()
                    self._update_hud()
                    message = "You escaped to a new level of the dungeon"
                    self._update_top_label(message, "gold")

                    message = "TURN " + str(self.player.get_currturn()) + ": " + message
                    self.msg_log.append(message)
                    return True
                else:
                    message = "You can't escape from here; no staircase"
                    self._update_top_label(message)
            elif key == "e":
                # Enter the player equipment menu
                self.curr_input_mode = self.input_modes["menu_equipment"]
                self.curr_submenu = self.display_submenus["menu_equipment"]
                self.need_submenu_rerender = True
                self.submenu_select_idx = 0
                self._render_equipment()
                self._update_top_label("PAUSED")
                print("GAME: Player equipment sub-menu activated")
                return False  # Turn not over
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
                return False  # Turn not over
            elif key == "i":
                # Enter the player inventory menu
                self.curr_input_mode = self.input_modes["menu_inventory"]
                self.curr_submenu = self.display_submenus["menu_inventory"]
                self.need_submenu_rerender = True
                self.submenu_select_idx = 0
                self._render_inventory()
                self._update_top_label("PAUSED")
                print("GAME: Player inventory sub-menu activated")
                return False  # Turn not over
            elif key == "m":
                # Enter the monster list menu
                self.curr_input_mode = self.input_modes["menu_monster_list"]
                self.curr_submenu = self.display_submenus["menu_monster_list"]
                self.need_submenu_rerender = True
                self._render_monster_list()
                self._update_top_label("PAUSED")
                print("GAME: Monster list sub-menu activated")
                return False  # Turn not over
            elif key == "p":
                # Attempt to pickup item
                r, c = self.player.get_pos()
                success, item = self.player.pickup_item(
                    self.dungeon, self.item_map, r, c
                )
                if success:
                    text = "You picked up " + item.get_name()
                else:
                    text = "You are unable to pick up item"
                self._update_top_label(text)
            elif key == "t":
                # Enter targeting mode; This will allow the user to inspect items & monsters,
                # teleport, and potentially (if I implement it) to use ranged weapons from a distance.
                self.curr_input_mode = self.input_modes["targeting"]
                self.target_r, self.target_c = self.player.get_pos()
                self._update_top_label("Targeting mode activated")
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
                return False  # Turn not over
            elif key == "plus":
                self.player.force_max_health()
                self._update_hud()
                self._update_top_label("Restored hit points", "gold")
            elif key == "Escape":
                # Enter the "exit" menu for exit options
                self.curr_input_mode = self.input_modes["menu_exit"]
                self.curr_submenu = self.display_submenus["menu_exit"]
                self.submenu_select_idx = 0
                self._render_exit_menu()
                self._update_top_label("PAUSED")
                print("GAME: Exit sub-menu activated")
                return False  # Turn not over
            else:
                # Misinput; turn not over
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
                        message = (
                            "You dealt " + str(dmg) + " dmg to " + targ_actor.get_name()
                        )
                    else:
                        # Print kill message
                        message = "You killed " + targ_actor.get_name()
                        # Remove monster from map
                        targ_r, targ_c = targ_actor.get_pos()
                        self.actor_map[targ_r][targ_c] = None
                        self.player_score += int(
                            targ_actor.get_score_val() * self.difficulty
                        )

                    self._update_top_label(message)
                    message = "TURN " + str(self.player.get_currturn()) + ": " + message
                    self.msg_log.append(message)
                else:
                    # Just a plain successful move; reset message
                    self._update_top_label("")
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
            if self.submenu_canvas:
                self.submenu_canvas.destroy()
            self.need_full_rerender = True
            print("GAME: Exit sub-menu closed")
            self._update_top_label("")

    # Handles input for the monster list submenu
    def _handle_mlist_input(self, key):
        if key == "Escape" or key == "m":
            # Return to player input
            self.curr_input_mode = self.input_modes["player_turn"]
            self.curr_submenu = self.display_submenus["none"]
            if self.submenu_canvas:
                self.submenu_canvas.destroy()
            self.need_full_rerender = True
            print("GAME: Monster list sub-menu closed")
            self._update_top_label("")
        elif key == "j" or key == "Down" or key == "2":
            # Scroll down
            self.submenu_canvas.yview_scroll(1, "units")
        elif key == "k" or key == "Up" or key == "8":
            # Attempt to grab current y scroll value to return to it
            try:
                scroll_val = self.submenu_canvas.yview()[0]
            except (tk.TclError, IndexError, AttributeError):
                scroll_val = 0.0  # Revert to zero

            # Scroll up, but only if possible (scroll_val > 0/0)
            if scroll_val > 0.0:
                self.submenu_canvas.yview_scroll(-1, "units")

    # Handles input for the inventory submenu
    def _handle_inventory_input(self, key):
        if key == "Escape":
            # Return to player input
            self.curr_input_mode = self.input_modes["player_turn"]
            self.curr_submenu = self.display_submenus["none"]
            if self.submenu_canvas:
                self.submenu_canvas.destroy()
            self.need_full_rerender = True
            # Forces Update to player's area of sight
            self.player.handle_turn(
                self.dungeon, self.actor_map, self.player, Move(Move.none)
            )
            print("GAME: Player inventory sub-menu closed")
            self._update_top_label("")
        elif (
            key == "Right"
            or key == "l"
            or key == "6"
            or key == "Left"
            or key == "h"
            or key == "4"
        ):
            # Move to player equipment menu
            self.submenu_select_idx = 0
            self.curr_input_mode = self.input_modes["menu_equipment"]
            self.curr_submenu = self.display_submenus["menu_equipment"]
            self.submenu_canvas.destroy()
            self.need_submenu_rerender = True
            print("GAME: Player inventory sub-menu closed")
            print("GAME: Player equipment sub-menu opened")
            self._render_equipment()
        elif key == "Return":
            # Attempt to equip item
            success, item = self.player.equip_use_item(self.submenu_select_idx)
            if success:
                # Check for message phrasing
                if item.get_type() == item_type_opts["POTION"]:
                    self._update_top_label("You used " + item.get_name())
                else:
                    self._update_top_label("You equipped " + item.get_name())
                self.need_submenu_rerender = True
                self._render_inventory()
                self._update_hud()
            else:
                self._update_top_label("No item to equip")
        elif key == "i":
            success, item = self.player.get_inventory_item(self.submenu_select_idx)
            if success:
                self.inspect_obj = item
                self._update_top_label(f"Inspecting {self.inspect_obj.get_name()}")
                self.curr_input_mode = self.input_modes["inspect"]
                self.curr_submenu = self.display_submenus["inspect_item"]
                self.need_submenu_rerender = True
                self._render_item_inspect(self.inspect_obj)
            else:
                self._update_top_label("No item to inspect")
        elif key == "j" or key == "Down" or key == "2":
            # Move selection down
            if self.submenu_select_idx < self.player.get_inventory_size() - 1:
                self.submenu_select_idx += 1
            else:
                self.submenu_select_idx = 0
            self.need_submenu_rerender = True
            self._render_inventory()
        elif key == "k" or key == "Up" or key == "8":
            # Move selection up
            if self.submenu_select_idx >= 1:
                self.submenu_select_idx -= 1
            else:
                self.submenu_select_idx = self.player.get_inventory_size() - 1
            self.need_submenu_rerender = True
            self._render_inventory()
        elif key == "d":
            success, item = self.player.drop_item(
                self.submenu_select_idx, self.item_list, self.item_map
            )
            if success:
                msg = f"You dropped {item.get_name()}"
                self.need_submenu_rerender = True
                self._render_inventory()
            elif item != None:
                msg = f"Cannot drop; item already on floor"
            else:
                msg = f"No item to drop"
            self._update_top_label(msg)
        elif key == "x":
            # Attempt to destroy an item
            success, item = self.player.expunge_item(self.submenu_select_idx)
            if success:
                self._update_top_label("You destroyed " + item.get_name())
                self.need_submenu_rerender = True
                self._render_inventory()
            else:
                self._update_top_label("No item to destroy")

    # Handles input for the equipment submenu
    def _handle_equipment_input(self, key):
        if key == "Escape" or key == "e":
            # Return to player input
            self.curr_input_mode = self.input_modes["player_turn"]
            self.curr_submenu = self.display_submenus["none"]
            if self.submenu_canvas:
                self.submenu_canvas.destroy()
            self.need_full_rerender = True
            # Forces Update to player's area of sight
            self.player.handle_turn(
                self.dungeon, self.actor_map, self.player, Move(Move.none)
            )
            print("GAME: Player equipment sub-menu closed")
            self._update_top_label("")
        elif (
            key == "Right"
            or key == "l"
            or key == "6"
            or key == "Left"
            or key == "h"
            or key == "4"
        ):
            # Move to player inventory menu
            self.submenu_select_idx = 0
            self.curr_input_mode = self.input_modes["menu_inventory"]
            self.curr_submenu = self.display_submenus["menu_inventory"]
            self.submenu_canvas.destroy()
            self.need_submenu_rerender = True
            print("GAME: Player equipment sub-menu closed")
            print("GAME: Player iventory sub-menu opened")
            self._render_inventory()
        elif key == "Return":
            key_str = {
                0: "weapon",
                1: "ranged",
                2: "offhand",
                3: "armor",
                4: "amulet",
                5: "ring_l",
                6: "ring_r",
                7: "light",
            }
            success, inventory_problem, item = self.player.unequip_item(
                key_str[self.submenu_select_idx]
            )
            if success:
                self._update_top_label(f"{item.get_name()} returned to inventory")
                self.need_submenu_rerender = True
                self._render_equipment()
                self._update_hud()
            elif inventory_problem:
                self._update_top_label("No room in inventory to unequip item")
        elif key == "i":
            key_str = {
                0: "weapon",
                1: "ranged",
                2: "offhand",
                3: "armor",
                4: "amulet",
                5: "ring_l",
                6: "ring_r",
                7: "light",
            }
            item = self.player.get_equipped_by_key(key_str[self.submenu_select_idx])
            if item != None:
                self.inspect_obj = item
                self._update_top_label(f"Inspecting {self.inspect_obj.get_name()}")
                self.curr_input_mode = self.input_modes["inspect"]
                self.curr_submenu = self.display_submenus["inspect_item"]
                self.need_submenu_rerender = True
                self._render_item_inspect(self.inspect_obj)
            else:
                self._update_top_label("No item to inspect")

        elif key == "j" or key == "Down" or key == "2":
            # Move selection down
            if self.submenu_select_idx < 7:
                self.submenu_select_idx += 1
            else:
                self.submenu_select_idx = 0
            self.need_submenu_rerender = True
            self._render_equipment()
        elif key == "k" or key == "Up" or key == "8":
            # Move selection up
            if self.submenu_select_idx >= 1:
                self.submenu_select_idx -= 1
            else:
                self.submenu_select_idx = 7
            self.need_submenu_rerender = True
            self._render_equipment()

    # Handles input for targeting mode
    def _handle_targeting_input(self, key):
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

        # Coordinate deltas for 8 surrounding points of a given point.
        # up_left, up, up_right, left, right, down_left, down, down_right, none
        delta_r = [-1, -1, -1, 0, 0, 1, 1, 1, 0]
        delta_c = [-1, 0, 1, -1, 1, -1, 0, 1, 0]
        # self.target_r + delta_r[move.value], self.c + self._delta_c[move.value]
        if key not in move_delta:
            # Input is not to move targeting cursor
            if key == "Escape" or key == "t":
                # Return to player input
                self.curr_input_mode = self.input_modes["player_turn"]
                self.curr_submenu = self.display_submenus["none"]
                self.need_full_rerender = True
                self._render_frame(self.scrsize_h, self.scrsize_w)
                self._update_top_label("")
            elif key == "g":
                # teleport cheat
                success, targ_actor = self.player.teleport(
                    self.dungeon, self.actor_map, self.target_r, self.target_c
                )
                if success:
                    # Check for murdered actor
                    if targ_actor != None:
                        message = f"You teleported, killing {targ_actor.get_name()}"
                        # Killing via teleport is super cheesy, so no points are awarded here.
                    else:
                        message = f"You successfully teleported"
                    # Return to player input
                    self.curr_input_mode = self.input_modes["player_turn"]
                    self.curr_submenu = self.display_submenus["none"]
                    self.need_full_rerender = True
                    self._render_frame(self.scrsize_h, self.scrsize_w)
                else:
                    message = "You cannot teleport there"
                self._update_top_label(message)
            elif key == "i":
                player_r, player_c = self.player.get_pos()
                # Double check that not inspecting yourself
                if not (self.target_r == player_r and self.target_c == player_c):
                    # Attempt to grab monster, then attempt to grab item.
                    if self.actor_map[self.target_r][self.target_c]:
                        self.inspect_obj = self.actor_map[self.target_r][self.target_c]
                        self._update_top_label(
                            f"Inspecting {self.inspect_obj.get_name()}"
                        )
                        self.curr_input_mode = self.input_modes["inspect"]
                        self.curr_submenu = self.display_submenus["inspect_monster"]
                        self.need_submenu_rerender = True
                        self._render_monster_inspect(self.inspect_obj)
                    elif self.item_map[self.target_r][self.target_c]:
                        self.inspect_obj = self.item_map[self.target_r][self.target_c]
                        self._update_top_label(
                            f"Inspecting {self.inspect_obj.get_name()}"
                        )
                        self.curr_input_mode = self.input_modes["inspect"]
                        self.curr_submenu = self.display_submenus["inspect_item"]
                        self.need_submenu_rerender = True
                        self._render_item_inspect(self.inspect_obj)
                    else:
                        message = "No monster or item to inspect"
                        self._update_top_label(message)
        else:
            # Attempt to move targeting cursor
            move = move_delta[key]
            new_r = self.target_r + delta_r[move.value]
            new_c = self.target_c + delta_c[move.value]
            # Now determine if targeting position is valid
            if self.dungeon.valid_point(new_r, new_c):
                # Valid point within dungeon; is targeted tile visible to player, or x-ray render enabled?
                if self.curr_render_mode == self.render_modes[
                    "x-ray"
                ] or self.player.is_visible_tile(new_r, new_c):
                    # Tile is otherwise known about, so it can be targeted by player.
                    self.target_c = new_c
                    self.target_r = new_r
                    # Update render for snappier feeling response
                    self._render_frame(self.scrsize_h, self.scrsize_w)

    # Handles inspection menu input
    def _handle_inspect_input(self, key):
        # Exit or scrolling input
        if key == "Escape" or key == "t":
            # Return to player input
            if self.submenu_canvas:
                self.submenu_canvas.destroy()
            self.curr_input_mode = self.input_modes["player_turn"]
            self.curr_submenu = self.display_submenus["none"]
            self.inspect_obj = None  # Reset stored inspection pointer to None
            self.need_full_rerender = True
            self._render_frame(self.scrsize_h, self.scrsize_w)
            self._update_top_label("")
        elif key == "j" or key == "Down" or key == "2":
            # Scroll down
            self.submenu_canvas.yview_scroll(1, "units")
        elif key == "k" or key == "Up" or key == "8":
            # Attempt to grab current y scroll value
            try:
                scroll_val = self.submenu_canvas.yview()[0]
            except (tk.TclError, IndexError, AttributeError):
                scroll_val = 0.0  # Revert to zero

            # Scroll up, but only if possible (scroll_val > 0.0)
            if scroll_val > 0.0:
                self.submenu_canvas.yview_scroll(-1, "units")
        elif key == "Right" or key == "l" or key == "6":
            # Scroll right
            self.submenu_canvas.xview_scroll(1, "units")
        elif key == "Left" or key == "h" or key == "4":
            # Attempt to grab current x scroll value
            try:
                scroll_val = self.submenu_canvas.xview()[0]
            except (tk.TclError, IndexError, AttributeError):
                scroll_val = 0.0  # Revert to zero

            # Scroll left, but only if possible (scroll_val > 0.0)
            if scroll_val > 0.0:
                self.submenu_canvas.xview_scroll(-1, "units")

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
            "Min items,",
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
        min_itemc = max(1, int(size_modifier // 100))
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

    # Updates the player's hud (the two layers of text at the bottom of the screen)
    def _update_hud(self):
        r, c = self.player.get_pos()
        if not self.game_over:
            # Player score and position (line 1)
            self.score_msg = f"SCORE: {self.player_score:06d}   MODIFIER: {self.difficulty:.2f}   POS: (R:{r:0d}, C:{c:0d})"
            self.score_msg_color = "white"

            # Player stats (line 2)
            curr_hp = self.player.get_hp()
            hp_cap = self.player.get_hp_cap()
            self.hp_msg = f"{curr_hp:03d}/{hp_cap:03d}"
            # Determine HP color based on current percentage of health
            ratio = max(0.0, min(curr_hp / hp_cap, 1.0))

            if ratio > 0.5:
                # gradient between green and yellow
                red = int(255 * (1 - (ratio - 0.5) * 2))
                green = 255
            else:
                # gradient between yellow and red
                red = 255
                green = int(255 * ratio * 2)
            blue = 0
            self.hp_msg_color = f"#{red:02X}{green:02X}{blue:02X}"
            self.pinfo_msg = f"HP:           SPEED: {self._speed_nerf(self.player.get_speed()):03d}   DEFENSE: {self.player.get_defense():03d}   DODGE: {self.player.get_dodge():03d}"
            self.pinfo_msg_color = "white"
        else:
            # Player score and position (line 1)
            self.score_msg = f"FINAL SCORE: {self.player_score:06d}"
            self.score_msg_color = "#00FF00"

            # Player stats (line 2)
            self.hp_msg = ""
            self.pinfo_msg = "Press esc to exit"

        # Update score and location
        if (self.score_msg, self.score_msg_color) != self.score_msg_cache:
            self.canvas.itemconfig(
                "score_msg", text=self.score_msg, fill=self.score_msg_color
            )
            self.score_msg_cache = (self.score_msg, self.score_msg_color)

        # Update player health section
        if (self.hp_msg, self.hp_msg_color) != self.hp_msg_cache:
            self.canvas.itemconfig("hp_msg", text=self.hp_msg, fill=self.hp_msg_color)
            self.hp_msg_cache = (self.hp_msg, self.hp_msg_color)

        # Update other player information
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
            (self.tile_size * self.mapsize_h // 2) + self.tile_size,
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

    # Handles creating/rendering the monster list menu
    def _render_monster_list(self):

        lines = []
        i = 1
        max_line_width = 0

        # Create lines first; longest line will determine menu width
        for monster in self.monster_list:
            r, c = monster.get_pos()
            if monster.is_alive():
                if (
                    self.player.visible_tiles[r][c]
                    or self.curr_render_mode == self.render_modes["x-ray"]
                ):
                    # Location known, so display that information
                    text = f"{i:3d}:   {monster.get_name()} at (R:{r:2d}, C:{c:2d})"
                else:
                    # Location unknown, so don't present that information
                    text = f"{i:3d}:   {monster.get_name()} at (R:?, C:?)"
            else:
                # monster is dead, so there is no location
                text = f"{i:3d}:   {monster.get_name()} (DEFEATED)"
            length = len(text)
            if length > max_line_width:
                max_line_width = length
            lines.append(text)
            i += 1

        # Number of monsters + menu header
        ideal_height = int((len(self.monster_list) + 2) * self.tile_size)
        max_height = (self.mapsize_h - 3) * self.tile_size
        visible_menu_height = min(ideal_height, max_height)

        # Not quite the whole screen width
        menu_width = min(
            self.tile_size * (self.mapsize_w - 3),
            (self.tile_size // 1.85) * max_line_width,
        )

        # Attempt to grab current y scroll value to return to it
        try:
            scroll_val = self.submenu_canvas.yview()[0]
        except (tk.TclError, IndexError, AttributeError):
            scroll_val = 0.0  # Revert to zero

        # Determine if full canvas redraw needed
        if self.need_submenu_rerender:
            if self.submenu_canvas:
                self.submenu_canvas.destroy()

            self.submenu_canvas = tk.Canvas(
                self.canvas,
                height=visible_menu_height,
                width=menu_width,
                bg="black",
                highlightthickness=self.tile_size // 6,
                yscrollincrement=self.tile_size,
            )

            self.canvas.create_window(
                self.scrsize_w // 2,
                (self.tile_size * self.mapsize_h // 2) + self.tile_size,
                height=visible_menu_height,
                width=menu_width,
                window=self.submenu_canvas,
                anchor="center",
            )

            # Init canvas' ability to scroll
            self.submenu_canvas.config(
                scrollregion=(0, 0, menu_width, ideal_height - self.tile_size)
            )

        # Draw menu header
        offset = self.tile_size // 2
        self.submenu_canvas.create_text(
            menu_width // 2,
            int(offset * 1.5),
            text=f"Monsters ({len(self.monster_list)} listed)",
            fill="red",
            font=(self.def_font, self.font_size),
            tag="mlist_header",
            anchor="center",
        )

        # Add all text lines to display
        i = 0
        for text in lines:
            monster = self.monster_list[i]
            color = "white" if monster.is_alive() else "grey"
            # Monster name and coordinate
            self.submenu_canvas.create_text(
                offset,
                offset + (self.tile_size * (i + 1)),
                text=text,
                fill=color,
                font=(self.def_font, self.font_size),
                tag=f"monster_txt_{i + 1}",
                anchor="nw",
            )

            color = monster.get_color() if monster.is_alive() else "grey"
            # Add in monster character separately, with color
            self.submenu_canvas.create_text(
                offset + int(self.tile_size * 2.25),
                offset + (self.tile_size * (i + 1)),
                text=monster.get_char(),
                fill=color,
                font=(self.def_font, self.font_size),
                tag=f"monster_symb_{i + 1}",
                anchor="nw",
            )
            i += 1

        # Return to previous scroll value; I.e., scroll back to where user had it before redrawing
        self.submenu_canvas.yview_moveto(scroll_val)

    # Handles creating/rendering the player inventory menu.
    def _render_inventory(self):

        lines = []
        line_colors = []
        lines.append("Inventory Slots")
        line_colors.append("red")
        curr_line = 0
        max_line_width = 22  # Minimum based on "00: --- EMPTY --- <-- "

        # Create lines first; longest line will determine menu width
        inventory = self.player.get_inventory_slots()
        # Ideally isize is the same as player.get_inventory_size().
        # In reality, this will print any extra items, enabling easier error checking.
        isize = len(inventory)
        for i in range(isize):
            item = inventory[i]
            line = ""

            if item != None:
                # Grab item name
                line = f"{i+1:2d}: {item.get_name()} "

                # Check if line length is longer than previous maximum
                length = len(line) + 3
                if length > max_line_width:
                    max_line_width = length

                # Add arrow and gold color if current select IDX
                if self.submenu_select_idx == i:
                    line = line + "<-- "
                    line_colors.append("gold")
                else:
                    line_colors.append("white")
            else:
                line = f"{i+1:2d}: --- EMPTY --- "
                line_colors.append("gray")

                # Add arrow if current select IDX
                if self.submenu_select_idx == i:
                    line = line + "<-- "
            lines.append(line)

        # Number of inventory slots + menu header
        line_count = len(lines)
        ideal_height = int((line_count + 1) * self.tile_size)
        max_height = (self.mapsize_h - 3) * self.tile_size
        visible_menu_height = min(ideal_height, max_height)

        # Not quite the whole screen width
        menu_width = min(
            self.tile_size * (self.mapsize_w - 3),
            (self.tile_size // 1.85) * max_line_width,
        )

        # Determine if full canvas redraw needed
        if self.need_submenu_rerender:
            if self.submenu_canvas:
                self.submenu_canvas.destroy()

            self.submenu_canvas = tk.Canvas(
                self.canvas,
                height=visible_menu_height,
                width=menu_width,
                bg="black",
                highlightthickness=self.tile_size // 6,
                yscrollincrement=self.tile_size,
            )

            self.canvas.create_window(
                self.scrsize_w // 2,
                (self.tile_size * self.mapsize_h // 2) + self.tile_size,
                height=visible_menu_height,
                width=menu_width,
                window=self.submenu_canvas,
                anchor="center",
            )

        # Draw menu header
        offset = self.tile_size // 2
        self.submenu_canvas.create_text(
            menu_width // 2,
            int(offset * 1.5),
            text=lines[curr_line],
            fill="red",
            font=(self.def_font, self.font_size),
            tag="inventory_header",
            anchor="center",
        )
        curr_line += 1

        # Draw remaining lines
        while curr_line < line_count:
            self.submenu_canvas.create_text(
                offset,
                offset + (self.tile_size * (curr_line)),
                text=lines[curr_line],
                fill=line_colors[curr_line],
                font=(self.def_font, self.font_size),
                tag=f"inventory_slot_{curr_line}",
                anchor="nw",
            )
            curr_line += 1

    # Handles creating/rendering the player equipment menu.
    def _render_equipment(self):
        lines = []
        line_colors = []
        lines.append("Equipment Slots")
        line_colors.append("red")
        curr_line = 0
        max_line_width = 21  # Minimum based on "RING RIGHT: None <-- "

        start_str = {
            0: "WEAPON:     ",
            1: "RANGED:     ",
            2: "OFFHAND:    ",
            3: "ARMOR:      ",
            4: "AMULET:     ",
            5: "RING LEFT:  ",
            6: "RING RIGHT: ",
            7: "LIGHT:      ",
        }

        equipped_items = {
            0: self.player.get_weapon(),
            1: self.player.get_ranged(),
            2: self.player.get_offhand(),
            3: self.player.get_armor(),
            4: self.player.get_amulet(),
            5: self.player.get_ring_l(),
            6: self.player.get_ring_r(),
            7: self.player.get_light(),
        }

        # Create lines first; longest line will determine menu width. 8 equipment slots.
        for i in range(8):
            item = equipped_items[i]
            line = ""

            if item != None:
                # Grab item name
                line = f"{start_str[i]}{item.get_name()} "

                # Check if line length is longer than previous maximum
                length = len(line) + 3
                if length > max_line_width:
                    max_line_width = length

                # Add arrow and gold color if current select IDX
                if self.submenu_select_idx == i:
                    line = line + "<-- "
                    line_colors.append("gold")
                else:
                    line_colors.append("white")
            else:
                line = f"{start_str[i]}None "
                line_colors.append("gray")

                # Add arrow if current select IDX
                if self.submenu_select_idx == i:
                    line = line + "<-- "
            lines.append(line)

        # Number of equipment slots + menu header
        line_count = len(lines)
        ideal_height = int((line_count + 1) * self.tile_size)
        max_height = (self.mapsize_h - 3) * self.tile_size
        visible_menu_height = min(ideal_height, max_height)

        # Not quite the whole screen width
        menu_width = min(
            self.tile_size * (self.mapsize_w - 3),
            (self.tile_size // 1.85) * max_line_width,
        )

        # Determine if full canvas redraw needed
        if self.need_submenu_rerender:
            if self.submenu_canvas:
                self.submenu_canvas.destroy()

            self.submenu_canvas = tk.Canvas(
                self.canvas,
                height=visible_menu_height,
                width=menu_width,
                bg="black",
                highlightthickness=self.tile_size // 6,
                yscrollincrement=self.tile_size,
            )

            self.canvas.create_window(
                self.scrsize_w // 2,
                (self.tile_size * self.mapsize_h // 2) + self.tile_size,
                height=visible_menu_height,
                width=menu_width,
                window=self.submenu_canvas,
                anchor="center",
            )

        # Draw menu header
        offset = self.tile_size // 2
        self.submenu_canvas.create_text(
            menu_width // 2,
            int(offset * 1.5),
            text=lines[curr_line],
            fill=line_colors[curr_line],
            font=(self.def_font, self.font_size),
            tag="equip_header",
            anchor="center",
        )
        curr_line += 1

        # Draw remaining lines
        while curr_line < line_count:
            self.submenu_canvas.create_text(
                offset,
                offset + (self.tile_size * (curr_line)),
                text=lines[curr_line],
                fill=line_colors[curr_line],
                font=(self.def_font, self.font_size),
                tag=f"equip_slot_{curr_line}",
                anchor="nw",
            )
            curr_line += 1

    # Renders monster inspection screen
    def _render_monster_inspect(self, monster: Monster):
        curr_line = 0
        desc_lines = monster.get_desc()
        line_count = 8 + len(desc_lines)

        longest_line = self.mapsize_w  # default to at least the dungeon width
        # Determine what is actually the longest line, depending on description lines
        for line in desc_lines:
            new_len = len(line)
            if new_len > longest_line:
                longest_line = new_len

        # Determine screen sizing, both visible and full scrollable size
        ideal_height = int((line_count + 1) * self.tile_size)
        max_height = (self.mapsize_h - 3) * self.tile_size
        ideal_width = int(
            longest_line * (self.tile_size / 1.85)
        )  # This may need to be adjusted
        visible_menu_height = min(ideal_height, max_height)
        visible_menu_width = min(self.tile_size * (self.mapsize_w - 3), ideal_width)

        # Attempt to grab current x/y scroll values to return to it
        try:
            y_scroll_val = self.submenu_canvas.yview()[0]
            x_scroll_val = self.submenu_canvas.xview()[0]
        except (tk.TclError, IndexError, AttributeError):
            y_scroll_val = 0.0  # Revert to zero
            x_scroll_val = 0.0

        if self.need_submenu_rerender:
            if self.submenu_canvas:
                self.submenu_canvas.destroy()

            self.submenu_canvas = tk.Canvas(
                self.canvas,
                height=visible_menu_height,
                width=visible_menu_width,
                bg="black",
                highlightthickness=self.tile_size // 6,
                yscrollincrement=self.tile_size,
            )

            self.canvas.create_window(
                self.scrsize_w // 2,
                (self.tile_size * self.mapsize_h // 2) + self.tile_size,
                height=visible_menu_height,
                width=visible_menu_width,
                window=self.submenu_canvas,
                anchor="center",
            )

            # Init canvas' ability to scroll
            self.submenu_canvas.config(
                scrollregion=(
                    0,
                    0,
                    ideal_width - self.tile_size,
                    ideal_height - self.tile_size,
                )
            )

        # Draw text
        offset = self.tile_size // 2
        curr_line = 0.3  # Weird value in attempt to center text

        # Symbol (separate for defined color, appears on same line as name)
        color = monster.get_color()
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=monster.get_char(),
            fill=color,
            font=(self.def_font, self.font_size),
            tag="monstinspect_symb",
            anchor="nw",
        )

        # Name (same line as symbol, again separate for separate colors)
        self.submenu_canvas.create_text(
            offset + self.tile_size,
            curr_line * self.tile_size,
            text=monster.get_name(),
            fill="white",
            font=(self.def_font, self.font_size),
            tag="monstinspect_name",
            anchor="nw",
        )
        curr_line += 1

        # Description
        curr_line += 1
        i = 1
        for line in desc_lines:
            self.submenu_canvas.create_text(
                offset,
                (self.tile_size * (curr_line)),
                text=line,
                fill="white",
                font=(self.def_font, self.font_size),
                tag=f"monstinspect_desc_{i}",
                anchor="nw",
            )
            i += 1
            curr_line += 1
        curr_line += 1

        # Abilities
        text = "ATTRIBUTES:  " + monster.get_abil_str()
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=text,
            fill="white",
            font=(self.def_font, self.font_size),
            tag="monstinspect_abil",
            anchor="nw",
        )
        curr_line += 1

        # Speed
        text = f"SPEED:       {monster.get_speed()}"
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=text,
            fill="white",
            font=(self.def_font, self.font_size),
            tag="monstinspect_speed",
            anchor="nw",
        )
        curr_line += 1

        # Health
        text = f"HIT POINTS:  {monster.get_hp()}"
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=text,
            fill="white",
            font=(self.def_font, self.font_size),
            tag="monstinspect_hp",
            anchor="nw",
        )
        curr_line += 1

        # Damage
        text = "DAMAGE:      " + monster.get_damage_str()
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=text,
            fill="white",
            font=(self.def_font, self.font_size),
            tag="monstinspect_damage",
            anchor="nw",
        )
        curr_line += 1

        # Rarity
        text = f"SCORE VALUE: {monster.get_score_val()}"
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=text,
            fill="white",
            font=(self.def_font, self.font_size),
            tag="monstinspect_val",
            anchor="nw",
        )

        # Return to previous scroll values; I.e., scroll back to where user had it before redrawing
        self.submenu_canvas.yview_moveto(y_scroll_val)
        self.submenu_canvas.xview_moveto(x_scroll_val)

    # Renders item inspection screen
    def _render_item_inspect(self, item: Item):
        curr_line = 0
        desc_lines = item.get_desc()

        # Line count will be dependant on what type of item it is. There may be duplicates here, but this leaves room for granularity later.
        # Actual lines are created further down.
        itype = item.get_type()
        if itype == item_type_opts["POTION"]:
            line_count = 9 + len(desc_lines)
        elif itype == item_type_opts["LIGHT"]:
            line_count = 5 + len(desc_lines)
        else:
            line_count = 9 + len(desc_lines)

        longest_line = self.mapsize_w  # default to at least the dungeon width
        # Determine what is actually the longest line, depending on description lines
        for line in desc_lines:
            new_len = len(line)
            if new_len > longest_line:
                longest_line = new_len

        # Determine screen sizing, both visible and full scrollable size
        ideal_height = int((line_count + 1) * self.tile_size)
        max_height = (self.mapsize_h - 3) * self.tile_size
        ideal_width = int(
            longest_line * (self.tile_size / 1.85)
        )  # This may need to be adjusted
        visible_menu_height = min(ideal_height, max_height)
        visible_menu_width = min(self.tile_size * (self.mapsize_w - 3), ideal_width)

        # Attempt to grab current x/y scroll values to return to it
        try:
            y_scroll_val = self.submenu_canvas.yview()[0]
            x_scroll_val = self.submenu_canvas.xview()[0]
        except (tk.TclError, IndexError, AttributeError):
            y_scroll_val = 0.0  # Revert to zero
            x_scroll_val = 0.0

        if self.need_submenu_rerender:
            if self.submenu_canvas:
                self.submenu_canvas.destroy()

            self.submenu_canvas = tk.Canvas(
                self.canvas,
                height=visible_menu_height,
                width=visible_menu_width,
                bg="black",
                highlightthickness=self.tile_size // 6,
                yscrollincrement=self.tile_size,
            )

            self.canvas.create_window(
                self.scrsize_w // 2,
                (self.tile_size * self.mapsize_h // 2) + self.tile_size,
                height=visible_menu_height,
                width=visible_menu_width,
                window=self.submenu_canvas,
                anchor="center",
            )

            # Init canvas' ability to scroll
            self.submenu_canvas.config(
                scrollregion=(
                    0,
                    0,
                    ideal_width - self.tile_size,
                    ideal_height - self.tile_size,
                )
            )

        # Draw text
        offset = self.tile_size // 2
        curr_line = 0.3  # Weird value in attempt to center text

        # Symbol (separate for defined color, appears on same line as name)
        color = item.get_color()
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=item.get_char(),
            fill=color,
            font=(self.def_font, self.font_size),
            tag="iteminspect_symb",
            anchor="nw",
        )

        # Name (same line as symbol, again separate for separate colors)
        self.submenu_canvas.create_text(
            offset + self.tile_size,
            curr_line * self.tile_size,
            text=item.get_name(),
            fill="white",
            font=(self.def_font, self.font_size),
            tag="iteminspect_name",
            anchor="nw",
        )
        curr_line += 1

        # Description
        curr_line += 1
        i = 1
        for line in desc_lines:
            self.submenu_canvas.create_text(
                offset,
                (self.tile_size * (curr_line)),
                text=line,
                fill="white",
                font=(self.def_font, self.font_size),
                tag=f"iteminspect_desc_{i}",
                anchor="nw",
            )
            i += 1
            curr_line += 1
        curr_line += 1

        # From here on, what is printed depends on the type of the item.
        if itype == item_type_opts["POTION"]:
            # Hit Point Restore
            text = f"HITPOINT RESTORE:  {item.get_hp_restore()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_hp_r",
                anchor="nw",
            )
            curr_line += 1

            # MAX HIT POINT BONUS
            text = f"HP CAP BONUS:      {item.get_attr_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_hp_b",
                anchor="nw",
            )
            curr_line += 1

            # speed
            text = f"SPEED BONUS:       {item.get_speed_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_spd",
                anchor="nw",
            )
            curr_line += 1

            # Dodge
            text = f"DODGE BONUS:       {item.get_dodge_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_dodge",
                anchor="nw",
            )
            curr_line += 1

            # Defense
            text = f"DEFENSE BONUS:     {item.get_defense_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_def",
                anchor="nw",
            )
            curr_line += 1
        elif itype == item_type_opts["LIGHT"]:
            # VIEW DIST BONUS
            text = f"VIEW DIST BONUS:   {item.get_attr_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_attr",
                anchor="nw",
            )
            curr_line += 1
        else:
            # All other types will present the same information
            # Damage
            text = f"DAMAGE BONUS:      {item.get_damage_str()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_dam",
                anchor="nw",
            )
            curr_line += 1

            # hp restore
            text = f"HIT POINT RESTORE: {item.get_hp_restore()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_hp_r",
                anchor="nw",
            )
            curr_line += 1

            # speed
            text = f"SPEED BONUS:       {item.get_speed_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_spd",
                anchor="nw",
            )
            curr_line += 1

            # Dodge
            text = f"DODGE BONUS:       {item.get_dodge_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_dodge",
                anchor="nw",
            )
            curr_line += 1

            # Defense
            text = f"DEFENSE BONUS:     {item.get_defense_bonus()}"
            self.submenu_canvas.create_text(
                offset,
                curr_line * self.tile_size,
                text=text,
                fill="white",
                font=(self.def_font, self.font_size),
                tag="iteminspect_def",
                anchor="nw",
            )
            curr_line += 1

        # Rarity
        text = "RARITY:            " + str(item.get_rarity())
        self.submenu_canvas.create_text(
            offset,
            curr_line * self.tile_size,
            text=text,
            fill="white",
            font=(self.def_font, self.font_size),
            tag="iteminspect_rrty",
            anchor="nw",
        )

        # Return to previous scroll values; I.e., scroll back to where user had it before redrawing
        self.submenu_canvas.yview_moveto(y_scroll_val)
        self.submenu_canvas.xview_moveto(x_scroll_val)

    # Renders the dungeon to the screen canvas.
    def _render_frame(self, height, width):
        max_tile_width = width // self.mapsize_w
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

        x_offset = (width - self.tile_size * self.mapsize_w) // 2  # To center
        y_offset = self.tile_size  # To leave room for top message

        if self.need_full_rerender:
            self.render_cache.clear()

            # Calculate dungeon bounds in pixels
            dungeon_left = x_offset + self.tile_size
            dungeon_top = y_offset + self.tile_size
            dungeon_right = (
                dungeon_left + ((self.mapsize_w - 1) * self.tile_size) - self.tile_size
            )
            dungeon_bottom = (
                dungeon_top + ((self.mapsize_h - 1) * self.tile_size) - self.tile_size
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
            y = int((self.mapsize_h + 0.5) * self.tile_size)
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

            # Individual section for health for color indication
            self.canvas.create_text(
                x + self.tile_size // 2 + (self.tile_size * 2),
                y + self.tile_size // 2.5,
                text=self.hp_msg,
                fill=self.hp_msg_color,
                font=(self.def_font, self.font_size),
                tag="hp_msg",
                anchor="w",
            )
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

        # To loop through monster / item symbol colors in submenu
        if self.curr_submenu == self.display_submenus["menu_monster_list"]:
            self._render_monster_list()
        elif self.curr_submenu == self.display_submenus["inspect_monster"]:
            self._render_monster_inspect(self.inspect_obj)
        elif self.curr_submenu == self.display_submenus["inspect_item"]:
            self._render_item_inspect(self.inspect_obj)

        self.need_full_rerender = False

        # To check if targeting mode is active
        is_targeting = self.curr_input_mode == self.input_modes["targeting"]

        for row in range(self.mapsize_h):
            for col in range(self.mapsize_w):
                is_border_tile = (
                    row == 0
                    or col == 0
                    or row == self.mapsize_h - 1
                    or col == self.mapsize_w - 1
                )

                if not is_border_tile:
                    x = col * self.tile_size + x_offset
                    y = row * self.tile_size + y_offset

                    # default
                    char = "#"
                    color = "gray15"

                    # determine the current render mode to grab char & color
                    if self.curr_render_mode == self.render_modes["standard"]:
                        actor = self.actor_map[row][col]
                        item = self.item_map[row][col]
                        if self.player.is_visible_tile(row, col):
                            # Tile is visible, just render as normal.
                            if is_targeting and (
                                col == self.target_c and row == self.target_r
                            ):
                                # Targeting cursor
                                char = "@"
                                color = "white" if random.randint(0, 1) > 0 else "cyan"
                            elif actor:
                                char = actor.get_char()
                                color = actor.get_color()
                            elif item:
                                char = item.get_char()
                                color = item.get_color()
                            else:
                                terrain = self.dungeon.get_terrain_at(row, col)
                                char = terrain_char[terrain]
                                color = "white"
                        else:
                            # Tile is not visible, so only render player's remembered terrain.
                            terrain = self.player.tmem[row][col]
                            char = terrain_char[terrain]
                    elif self.curr_render_mode == self.render_modes["x-ray"]:
                        # Ignoring player memory of dungeon; just displaying dungeon
                        actor = self.actor_map[row][col]
                        item = self.item_map[row][col]
                        if is_targeting and (
                            col == self.target_c and row == self.target_r
                        ):
                            # Targeting cursor
                            char = "@"
                            color = "white" if random.randint(0, 1) > 0 else "cyan"
                        elif actor:
                            char = actor.get_char()
                            color = actor.get_color()
                        elif item:
                            char = item.get_char()
                            color = item.get_color()
                        else:
                            terrain = self.dungeon.get_terrain_at(row, col)
                            char = terrain_char[terrain]
                            color = "white"
                    elif self.curr_render_mode == self.render_modes["walkmap"]:
                        # Grab walkmap character
                        val = self.dungeon.get_walking_weight_at(row, col)
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
                        val = self.dungeon.get_tunneling_weight_at(row, col)
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
        if not self.player.is_alive():
            # You were defeated; game over
            message = "You have been defeated; Game Over"
            self._update_top_label(message, "red")
            print(message)
            self.msg_log.append(message)
            print("=== GAME OVER ===")
            self.curr_render_mode = self.render_modes["x-ray"]
            self.need_full_rerender = True
            self.game_over = True
            self.root.after(200, self._next_turn)
            self._update_hud()
            return

        # Level clear check
        if len(self.turn_pq) < 2:
            # Just the player is left; print level clear message
            message = "Level Clear"
            self._update_top_label(message, "gold")

        self._render_frame(self.scrsize_h, self.scrsize_w)

        # Pop actor; check if player turn
        _, actor = self.turn_pq.pop()
        player_turn = isinstance(actor, Player)

        if actor.is_alive():
            r, c = actor.get_pos()
            print(
                f"TURN {actor.get_currturn()} for {actor.get_name()} at (r:{r:0d}, c: {c:0d}) with speed {actor.get_speed()}"
            )

            if player_turn:
                # Await player input to call its turn handeler
                # Essentially 'pauses' the turnloop until keyboard input results in end of player turn
                if self.curr_input_mode != self.input_modes["player_turn"]:
                    # Update bottom messages for player location and score
                    self._update_hud()
                    self.curr_input_mode = self.input_modes["player_turn"]
                    return
            else:
                # Call the monster's turn handler directly
                success, targ_actor, dmg = actor.handle_turn(
                    self.dungeon, self.actor_map, self.player, 8
                )

            # Re-queue monster
            new_turn = actor.get_currturn() + (1000 // actor.get_speed())
            actor.set_currturn(new_turn)
            self.turn_pq.push(actor, new_turn)

            if isinstance(targ_actor, Player) and dmg != 0:
                message = actor.get_name() + " dealt " + str(dmg) + " damage to you"

                self._update_top_label(message)
                message = "TURN " + str(actor.get_currturn()) + ": " + message
                self.msg_log.append(message)
        elif actor.is_boss():
            # Killed a boss monster; Game ends
            message = f"{actor.get_name()} (BOSS) defeated; Game Over"
            self._update_top_label(message, "gold")
            print(message)
            self.msg_log.append(message)
            print("=== GAME OVER ===")
            self.curr_render_mode = self.render_modes["x-ray"]
            self.need_full_rerender = True
            self.game_over = True
            self.root.after(200, self._next_turn)
            self._update_hud()

        # Wait 1ms before running next turn
        self.root.after(1, self._next_turn)
