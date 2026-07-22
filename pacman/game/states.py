"""Screen state machine: which screen is active, and legal transitions."""

from enum import Enum, auto


class GameState(Enum):
    """One value per screen; the game is always in exactly one."""

    MENU = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    NAME_ENTRY = auto()


# Legal moves between screens. Anything absent here is a bug.
TRANSITIONS: dict[GameState, frozenset[GameState]] = {
    GameState.MENU: frozenset({GameState.PLAYING, GameState.HIGHSCORES,
                               GameState.INSTRUCTIONS}),
    GameState.HIGHSCORES: frozenset({GameState.MENU}),
    GameState.INSTRUCTIONS: frozenset({GameState.MENU}),
    GameState.PLAYING: frozenset({GameState.PAUSED, GameState.GAME_OVER,
                                  GameState.VICTORY}),
    GameState.PAUSED: frozenset({GameState.PLAYING, GameState.MENU}),
    GameState.GAME_OVER: frozenset({GameState.NAME_ENTRY}),
    GameState.VICTORY: frozenset({GameState.NAME_ENTRY}),
    GameState.NAME_ENTRY: frozenset({GameState.MENU}),
}


class StateMachine:
    """Holds the current screen and enforces legal transitions."""

    def __init__(self) -> None:
        """Start on the main menu, like the subject requires."""
        self.state = GameState.MENU

    def transition_to(self, target: GameState) -> None:
        """Move to ``target`` if the transition is legal.

        Args:
            target: The screen to switch to.

        Raises:
            ValueError: If the transition is not in TRANSITIONS -
                always a programming error, never a user action.
        """
        if target not in TRANSITIONS[self.state]:
            raise ValueError(
                f"illegal transition: {self.state.name} -> {target.name}"
            )
        self.state = target
