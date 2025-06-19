import tkinter as tk
from time import sleep
from utility import *
from actor import *
from dungeon import *


# This file handles the main gameloop and the vast majority of the tkinter user interface for PyRogue.
class Pyrogue_Game:

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
            new_monster = Monster(random.randint(0, 15), 10)
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

    # Initializes the game with randomly generated dungeon and monsters
    # Dungeon is size_h * size_w, difficulty modifies monster spawn rates.
    def init_generated_game(self):
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

        # Init internal idea of screen size
        self.scrsize_h = scrsize_h
        self.scrsize_w = scrsize_w

        # Internal idea of fontsize for UI elements; scales with screensize on render.
        self.fontsize = 12  # Default 12 until renderer called

        # Init internal idea of dungeon size
        self.mapsize_h = mapsize_h
        self.mapsize_w = mapsize_w

        # Game difficulty; applies to monster spawn rates
        self.difficulty = difficulty

        # Init dungeon and player fields
        self.dungeon = None
        self.player = None

        # Init lists for monsters as well as the map storing all actor locations
        self.monster_list = []
        self.actor_map = []
        self.turn_pq = None

        # here in case I implement game save/load; until then, always randomly generate
        if generate:
            self.init_generated_game()

        # Init the canvas to display dungeon / actors
        self.canvas = tk.Canvas(root, width=scrsize_w, height=scrsize_h, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # For handeling window resizes
        self.resize_id = None
        self.resize_event = None
        self.root.bind("<Configure>", self.on_resize)

        # For handeling keyboard input
        self.root.bind("<Key>", self.on_key_press)
        self.key_pressed = False

    # Event handeler for screen resizing.
    def on_resize(self, event):
        # Save the event for redrawing
        self.resize_event = event

        # Cancel any pending redraw
        if self.resize_id:
            self.root.after_cancel(self.resize_id)

        # schedule a redraw for 50ms from now
        self.resize_id = self.root.after(100, self._rerender_dungeon)

    # Event handeler for keyboard input
    def on_key_press(self, event):
        print(f"Key pressed: {event.keysym}")
        if not self.key_pressed:
            self.key_pressed = True
            self.start_turnloop()
            self.render_dungeon(self.scrsize_w, self.scrsize_h)

    # Error handeling for screen resizing event handeler.
    def _rerender_dungeon(self):
        if self.resize_event == None:
            return

        event = self.resize_event
        self.scrsize_h = event.height
        self.scrsize_w = event.width
        self.render_dungeon(self.scrsize_w, self.scrsize_h)

    # Renders the dungeon to the screen canvas.
    def render_dungeon(self, width, height):
        self.canvas.delete("all")  # Clear canvas
        max_tile_width = width // self.dungeon.width
        max_tile_height = height // (self.dungeon.height + 3)
        tile_size = min(max_tile_width, max_tile_height)
        self.fontsize = int(tile_size / 1.5)

        # For properly centering the dungeon
        x_offset = (width - tile_size * self.dungeon.width) // 2
        y_offset = tile_size * 2

        for row, line in enumerate(self.dungeon.tmap):
            for col, char in enumerate(line):
                x = col * tile_size + x_offset
                y = row * tile_size + y_offset
                if self.actor_map[row][col] != None:
                    actor = self.actor_map[row][col]
                    char = actor.get_char()
                    # Check actor type for color; later this will be unique to monster types
                    if isinstance(actor, Player):
                        color = "gold"
                    else:
                        color = "red"
                else:
                    color = "white"
                    terrain = self.dungeon.tmap[row][col]
                    if terrain == self.dungeon.Terrain.floor:
                        char = "."
                    elif terrain == self.dungeon.Terrain.stair:
                        char = ">"
                    elif terrain == self.dungeon.Terrain.stdrock:
                        char = " "
                    elif terrain == self.dungeon.Terrain.immrock:
                        char = "X"
                    else:
                        char = "!"
                self.canvas.create_rectangle(
                    x, y, x + tile_size, y + tile_size, fill="black", outline=""
                )
                self.canvas.create_text(
                    x + tile_size // 2,
                    y + tile_size // 2,
                    text=char,
                    fill=color,
                    font=("Consolas", self.fontsize),
                )
        # Force updates the canvas. Maybe suboptimal.
        # self.canvas.update()

    # Starts the game's turnloop
    def start_turnloop(self):
        self.turn_pq = PriorityQueue()
        self.turn_pq.push(self.player, 0)
        for monster in self.monster_list:
            monster.set_currturn(10)
            self.turn_pq.push(monster, 10)
        self._next_turn()

    # Handles a single turn in the turnloop.
    def _next_turn(self):
        if len(self.turn_pq) < 2 or not self.player.is_alive():
            print("Game Over")
            self.render_dungeon(self.scrsize_w, self.scrsize_h)
            return

        _, actor = self.turn_pq.pop()

        if actor.is_alive():
            # Call the actor's turn handler
            targ_actor, dmg = actor.handle_turn(
                self.dungeon, self.actor_map, self.player
            )

            # Re-queue actor
            new_turn = actor.get_currturn() + actor.get_speed()
            actor.set_currturn(new_turn)
            self.turn_pq.push(actor, new_turn)

            if isinstance(actor, Player):
                if targ_actor != None:
                    print("You Killed a", targ_actor.get_char())
                self.render_dungeon(self.scrsize_w, self.scrsize_h)
            elif isinstance(targ_actor, Player):
                print("a", actor.get_char(), "killed you")

        # Wait 50ms before next turn
        self.root.after(50, self._next_turn)
