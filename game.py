import tkinter as tk
from utility import *
from actor import *
from dungeon import *


# This file handles the main gameloop and the vast majority of the tkinter user interface for PyRogue.
# I'll admit that this code is a little messier than I think is ideal.
class Pyrogue_Game:

    # Pyrogue_game constructor.
    def __init__(
        self,
        root,
        scrsize_h: int,
        scrsize_w: int,
        mapsize_h: int,
        mapsize_w: int,
        difficulty: float,
        generate=True,
    ):
        # Tkinter root
        self.root = root

        # Init internal idea of screen size in pixels
        self.scrsize_h = scrsize_h
        self.scrsize_w = scrsize_w

        # Internal idea of size for UI elements; scales with screensize on render.
        # number of char 'rows' in screen; one for each row in dungeon + 3 for messages / player info
        self.scrn_rows = mapsize_h + 3
        self.tile_size = 16  # Default 16 until renderer called
        self.font_size = 12  # Default 12 until renderer called
        self.padx = 50  # The amount that the dungeon render is moved away from the left edge of the screen.

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

        # Init frame that will form the top message, dungeon, then player information, in that order
        self.frame = tk.Frame(
            root,
            bd=0,
            highlightthickness=5,
            bg="black",
            width=scrsize_w,
            height=scrsize_h,
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Init top label for combat / movement messages
        self.top_label = tk.Label(
            self.frame,
            text="Press any key to start",
            font=("Consolas", self.font_size),
            bg="black",
            fg="gold",
            anchor="w",
        )
        self.top_label.pack(fill="x", ipady=0, side="top")

        # here in case I implement game save/load; until then, always randomly generate
        if generate:
            self._init_generated_game()

        # Init the canvas to display dungeon / actors
        self.canvas = tk.Canvas(
            self.frame,
            bg="black",
            height = scrsize_h,
            width = scrsize_w,
            bd=0,
            highlightthickness=0,
        )

        self.canvas.pack(fill=tk.BOTH, expand=True, side="top")

        # Init bottom labels for current score and player information
        self.bottom_label_score = tk.Label(
            self.frame,
            text="Score: 0",
            font=("Consolas", self.font_size),
            bg="black",
            fg="white",
            anchor="w",
        )
        self.bottom_label_score.pack(fill="x", ipady=0, side="top")
        self.bottom_label_pinfo = tk.Label(
            self.frame,
            text="Your location: ",
            font=("Consolas", self.font_size),
            bg="black",
            fg="white",
            anchor="w",
        )
        self.bottom_label_pinfo.pack(fill="x", ipady=0, side="top")

        # Init some fields related to rendering
        self.need_full_rerender = True
        # {(row, col): (char, color)}. Stores last updated render info.
        self.render_cache = {}
        self.resize_id = None
        self.resize_event = None
        self.frame.bind("<Configure>", self._on_win_resize)

        # For handeling keyboard input
        self.root.bind("<Key>", self._on_key_press)
        self.turnloop_started = False
        self.awaiting_player_input = False

        # Render an initial frame
        self._render_frame(scrsize_h, scrsize_w)
        pc_r, pc_c = self.player.get_pos()
        pinfo_msg = "Player Location: Row " + str(pc_r) + ", Column: " + str(pc_c)
        self._update_pinfo_label(pinfo_msg)

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
        print(f"KEY INPUT: {key}")
        if not self.turnloop_started:
            # Until I create a main menu, any key input force starts the game.
            self.turnloop_started = True
            self._start_turnloop()
            self._render_frame(self.scrsize_w, self.scrsize_h)
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
        else:
            return

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
                    self._render_frame
                    pc_r, pc_c = self.player.get_pos()
                    pinfo_msg = "Player Location: Row " + str(pc_r) + ", Column: " + str(pc_c)
                    self._update_pinfo_label(pinfo_msg)
                    message = "You escaped to a new level of the dungeon"
                    self._update_top_label(message, "gold")
                    return True
                else :
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
                self._update_top_label("You can't move there")

    # Wrapper to update top message label. Cyan is the default message color.
    def _update_top_label(self, message: str, font_color: str = "cyan"):
        self.top_label.configure(text=message, fg=font_color)

    # Wrapper to update the bottom label for score. White is default message color.
    def _update_score_label(self, message: str, font_color: str = "white"):
        self.bottom_label_score.configure(text=message, fg=font_color)

    # Wrapper to update bottom label for player info. White is default message color.
    def _update_pinfo_label(self, message: str, font_color: str = "white"):
        self.bottom_label_pinfo.configure(text=message, fg=font_color)

    # Error handeling for screen resizing event handeler.
    def _resize_frame(self):
        if self.resize_event == None:
            return

        event = self.resize_event
        self.scrsize_h = event.height
        self.scrsize_w = event.width
        self.need_full_rerender = True
        self._render_frame(self.scrsize_w, self.scrsize_h)

    # Renders the dungeon to the screen canvas.
    def _render_frame(self, width, height):
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

        x_offset = (width - tile_size * self.dungeon.width) // 2
        y_offset = 0

        # Update top/bottom label fontsize and x/y padding
        self.top_label.configure(
            font=("Consolas", self.font_size), padx=x_offset + tile_size // 2
        )
        self.bottom_label_score.configure(
            font=("Consolas", self.font_size), padx=x_offset + tile_size // 2
        )
        self.bottom_label_pinfo.configure(
            font=("Consolas", self.font_size), padx=x_offset + tile_size // 2
        )

        if self.need_full_rerender:
            self.render_cache.clear()

            # Update canvas size
            # self.canvas.configure(height=(self.dungeon.height * tile_size) - 1, width= self.dungeon.width * tile_size)

            # Calculate dungeon bounds in pixels
            dungeon_left = x_offset + tile_size
            dungeon_top = y_offset + tile_size
            dungeon_right = (
                dungeon_left + ((self.dungeon.width - 1) * tile_size) - tile_size
            )
            dungeon_bottom = (
                dungeon_top + ((self.dungeon.height - 1) * tile_size) - tile_size
            )

            # Deleting existing border
            self.canvas.delete("dungeon_border")

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
                            font=("Consolas", self.font_size),
                            tag=f"tile_{row}_{col}",
                        )
        # Note for later: when generating new dungeon, need to call this.
        # self.render_cache.clear()

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
        print("=== GAME START ===")
        self._next_turn()

    # Handles a single turn in the turnloop.
    def _next_turn(self):
        # If player's turn, do nothing and wait
        if self.awaiting_player_input:
            return

        self._render_frame(self.scrsize_w, self.scrsize_h)

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
            return

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
