import sys
from typing import Any, Callable

from pacman.config import ConfigError, GameConfig, load_config
from pacman.game.engine import (FRIGHTENED_MOVE_PERIOD, PLAYER_MOVE_PERIOD,
                                TICKS_PER_SECOND, Engine)
from pacman.game.states import GameState
from pacman.highscores import load_highscores
from pacman.maze_loader import EAST, NORTH, SOUTH, WEST
from pacman.ui.keys import (KEY_A, KEY_D, KEY_DOWN, KEY_LEFT, KEY_P, KEY_Q,
                            KEY_RIGHT, KEY_S, KEY_UP, KEY_W)
from pacman.ui.menus import (GameOverScreen, HighscoresScreen,
                             InstructionsScreen, LevelTransitionScreen,
                             MainMenu, NameEntryScreen, PauseScreen,
                             VictoryScreen)
from pacman.ui.mlx_window import MlxWindow
from pacman.ui.renderer import MazeRenderer
from pacman.ui.screen import Screen

# Every physical key that can move the player, mapped to the engine's
# direction constants (subject VI.6: "arrows or WASD").
_DIRECTION_KEYS = {
    KEY_UP: NORTH, KEY_W: NORTH,
    KEY_DOWN: SOUTH, KEY_S: SOUTH,
    KEY_LEFT: WEST, KEY_A: WEST,
    KEY_RIGHT: EAST, KEY_D: EAST,
}


def _parse_args(argv: list[str]) -> str:
    """Validate the CLI contract: python3 pac-man.py <config.json>.

    Args:
        argv: Full argument vector, i.e. sys.argv.

    Returns:
        The path to the configuration file.

    Raises:
        SystemExit: If the argument count is wrong (usage message
        printed to stderr, no traceback).
    """
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <config.json>", file=sys.stderr)
        raise SystemExit(1)
    return argv[1]


def run_app(config: GameConfig, scores: list[tuple[str, int]]) -> None:
    """Bootstrap the MLX window and hand control to the engine.

    Every screen is built once. From then on a single loop hook and a
    single key hook drive the whole game: which screen renders, and
    which screen a key press reaches, is decided every tick by
    ``engine.machine.state`` - the one authoritative answer to "what
    is on screen right now". The engine itself owns every transition
    that has a game-logic side effect (starting a game, pausing,
    ending a level in GAME_OVER/VICTORY, saving a highscore); this
    function only ever reacts to the state it lands in.

    Args:
        config: Validated game settings.
        scores: Loaded top-10 highscores, shown by the Highscores
            screen (best first, as returned by ``load_highscores``).
    """
    window = MlxWindow()
    window.create_window("PacMan")
    engine = Engine(config)

    menu = MainMenu(window)
    instructions = InstructionsScreen(window)
    highscores_screen = HighscoresScreen(window)
    highscores_screen.load(scores)
    name_entry = NameEntryScreen(window)
    game_over = GameOverScreen(window)
    victory = VictoryScreen(window)
    pause_screen = PauseScreen(window)
    level_transition = LevelTransitionScreen(window)
    maze_renderer = MazeRenderer(window)

    last_state: GameState | None = None
    last_level_number: int | None = None

    def sync_maze_view() -> None:
        """Re-point the renderer at the engine's current level.

        ``MazeRenderer`` never builds anything itself: it only draws
        whatever ``Maze``/``Pellets`` object it was last handed. This
        must run again every time the engine swaps in a new ``Level``
        (new game, or clearing a level), or the renderer would keep
        showing the previous level's now-stale maze and pellets.
        """
        assert engine.level is not None
        maze_renderer.load(engine.level.maze)
        maze_renderer.load_pellets(engine.level.pellets)
        maze_renderer.load_entities(
            engine.level.player, engine.level.ghosts,
            player_pace=PLAYER_MOVE_PERIOD,
            ghost_pace=FRIGHTENED_MOVE_PERIOD)

    def handle_menu_key(*params: Any) -> None:
        nonlocal last_level_number
        menu.handle_key(*params)
        if menu.chosen == "Start Game":
            menu.chosen = None
            last_level_number = None
            engine.start_game()
        elif menu.chosen == "View Highscores":
            menu.chosen = None
            engine.machine.transition_to(GameState.HIGHSCORES)
        elif menu.chosen == "Instructions":
            menu.chosen = None
            engine.machine.transition_to(GameState.INSTRUCTIONS)
        elif menu.chosen == "Exit":
            window.destroy()

    def handle_highscores_key(*params: Any) -> None:
        highscores_screen.handle_key(*params)
        if highscores_screen.done:
            highscores_screen.done = False
            engine.machine.transition_to(GameState.MENU)

    def handle_instructions_key(*params: Any) -> None:
        instructions.handle_key(*params)
        if instructions.done:
            instructions.done = False
            engine.machine.transition_to(GameState.MENU)

    def handle_playing_key(*params: Any) -> None:
        keycode = params[0]
        if keycode == KEY_P:
            engine.toggle_pause()
        elif keycode == KEY_Q:
            window.destroy()
        elif keycode in _DIRECTION_KEYS:
            engine.turn(_DIRECTION_KEYS[keycode])

    def handle_level_transition_key(*_: Any) -> None:
        """No input during the "Level N" banner; it times out on its own."""

    def handle_paused_key(*params: Any) -> None:
        pause_screen.handle_key(*params)
        if pause_screen.chosen == "Resume":
            pause_screen.chosen = None
            engine.toggle_pause()
        elif pause_screen.chosen == "Return to Main Menu":
            pause_screen.chosen = None
            engine.quit_to_menu()

    def handle_game_over_key(*params: Any) -> None:
        game_over.handle_key(*params)
        if game_over.done:
            game_over.done = False
            engine.enter_name_entry()

    def handle_victory_key(*params: Any) -> None:
        victory.handle_key(*params)
        if victory.done:
            victory.done = False
            engine.enter_name_entry()

    def handle_name_entry_key(*params: Any) -> None:
        name_entry.handle_key(*params)
        if name_entry.confirmed is not None:
            if engine.submit_name(name_entry.confirmed):
                highscores_screen.load(
                    load_highscores(config.highscore_filename))
            name_entry.confirmed = None

    key_handlers: dict[GameState, Callable[..., None]] = {
        GameState.MENU: handle_menu_key,
        GameState.HIGHSCORES: handle_highscores_key,
        GameState.INSTRUCTIONS: handle_instructions_key,
        GameState.PLAYING: handle_playing_key,
        GameState.LEVEL_TRANSITION: handle_level_transition_key,
        GameState.PAUSED: handle_paused_key,
        GameState.GAME_OVER: handle_game_over_key,
        GameState.VICTORY: handle_victory_key,
        GameState.NAME_ENTRY: handle_name_entry_key,
    }
    screens: dict[GameState, Screen] = {
        GameState.MENU: menu,
        GameState.HIGHSCORES: highscores_screen,
        GameState.INSTRUCTIONS: instructions,
        GameState.PLAYING: maze_renderer,
        GameState.LEVEL_TRANSITION: level_transition,
        GameState.PAUSED: pause_screen,
        GameState.GAME_OVER: game_over,
        GameState.VICTORY: victory,
        GameState.NAME_ENTRY: name_entry,
    }

    def on_state_entered(state: GameState) -> None:
        """Run one-shot setup the instant the engine switches to ``state``.

        Args:
            state: The screen the engine just transitioned into.
        """
        if state is GameState.GAME_OVER:
            game_over.set_score(engine.score)
        elif state is GameState.VICTORY:
            victory.set_score(engine.score)
        elif state is GameState.NAME_ENTRY:
            name_entry.reset()
        elif state is GameState.LEVEL_TRANSITION:
            assert engine.pending_level_number is not None
            level_transition.set_level(engine.pending_level_number)
        else:
            screens[state].refresh()

    def frame(*_: Any) -> None:
        """MLX loop hook: advance the simulation, then draw one frame.

        ``engine.update()`` is a no-op outside PLAYING, so calling it
        unconditionally every tick is safe. ``last_state`` catches the
        moment the engine's state machine switches screens on its own
        (e.g. losing the last life into GAME_OVER); ``last_level_number``
        separately catches clearing a level, which keeps the machine in
        PLAYING but swaps in a brand new ``Level`` that the renderer
        must be re-synced to.
        """
        nonlocal last_state, last_level_number
        engine.update()
        state = engine.machine.state
        if state is not last_state:
            last_state = state
            window.hook_key(key_handlers[state])
            on_state_entered(state)
        if state is GameState.PLAYING and engine.level is not None:
            level = engine.level
            if level.number != last_level_number:
                last_level_number = level.number
                sync_maze_view()
            maze_renderer.sync_tick(engine.ticks_elapsed)
            seconds_left = level.ticks_left // TICKS_PER_SECOND
            maze_renderer.set_hud(engine.score, level.number, seconds_left)
            maze_renderer.set_tick_progress(engine.tick_progress())
        screens[state].render_if_dirty()

    window.hook_loop(frame)
    window.hook_close_icon(window.destroy)
    window.start_loop()


def main(argv: list[str]) -> int:
    """Load config and highscores, then start the application.

    Args:
        argv: Full argument vector, i.e. sys.argv.

    Returns:
        Process exit code (0 on success, 1 on a controlled failure).
    """
    config_path = _parse_args(argv)
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    scores = load_highscores(config.highscore_filename)
    run_app(config, scores)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:  # last-resort guard: never a traceback
        print(f"error: unexpected failure: {exc}", file=sys.stderr)
        sys.exit(1)
