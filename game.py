import tkinter as tk
from time import sleep
from utility import *
from actor import *
from dungeon import *


# This file handles the main gameloop and the vast majority of the tkinter user interface for PyRogue.
class pyrogue_game:

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
            new_monster = monster(random.randint(0, 15), 10)
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

    # Initializes the game with randomly generated dungeon and monsters
    # Dungeon is size_h * size_w, difficulty modifies monster spawn rates.
    def init_generated_game(self):
        # Init dungeon
        self.dungeon = dungeon(self.mapsize_h, self.mapsize_w)
        self.dungeon.generate_dungeon()

        # Init actor map
        self.actor_map = [
            [None] * self.dungeon.width for _ in range(self.dungeon.height)
        ]

        # Init player
        self.player = player()
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
        # Init fields
        self.scrsize_h = scrsize_h
        self.scrsize_w = scrsize_w
        self.mapsize_h = mapsize_h
        self.mapsize_w = mapsize_w
        self.difficulty = difficulty
        self.dungeon = None
        self.monster_list = []
        self.player = None
        self.actor_map = []
        self.root = root
        self.fontsize = 12
        if generate:
            # Ideally I'll take input for game size beforehand.
            self.init_generated_game()
        # Eventually I would like to have a setting for default screen size. Until then, 720p to start.
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
            self.turnloop()
            self.render_dungeon(self.scrsize_w, self.scrsize_h)

    # Error handeling for screen resizing event handeler.
    def _rerender_dungeon(self):
        if self.resize_event == None:
            return

        event = self.resize_event
        self.render_dungeon(event.width, event.height)

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
                    if isinstance(actor, player):
                        color = "gold"
                    else:
                        color = "red"
                else:
                    color = "white"
                    terrain = self.dungeon.tmap[row][col]
                    if terrain == self.dungeon.terrain.floor:
                        char = "."
                    elif terrain == self.dungeon.terrain.stair:
                        char = ">"
                    elif terrain == self.dungeon.terrain.stdrock:
                        char = " "
                    elif terrain == self.dungeon.terrain.immrock:
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
        self.canvas.update()

    # Handles the main turnloop for the game, discrete-event simulation style.
    def turnloop(self):
        # Create priorityqueue, starting player with turn 0 and monsters with 10 (player goes first)
        pq = PriorityQueue()
        pq.push(self.player, 0)
        for monster in self.monster_list:
            monster.set_currturn(10)
            pq.push(monster, 10)

        while len(pq) > 1 and self.player.is_alive():
            _, a = pq.pop()
            # Double check that actor has not died; If it has, ignore and move on
            if a.is_alive():
                targ_a, dmg_dealt = a.handle_turn(
                    self.dungeon, self.actor_map, self.player
                )
                curr_turn = a.get_currturn()
                new_turn = curr_turn + a.get_speed()
                a.set_currturn(new_turn)
                pq.push(a, new_turn)
                if isinstance(a, player):
                    # if targ_a != None:
                    #     print("You Killed a", targ_a.get_char())
                    self.render_dungeon(self.scrsize_w, self.scrsize_h)
                    # Wait 5000ms to show updated render
                    self.root.after(500000, lambda: None)
                # elif isinstance(targ_a, actor.player):
                #     print("a", a.get_char(), "killed you")
