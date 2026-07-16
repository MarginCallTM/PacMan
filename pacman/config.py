"""Load, validate and clamp the JSON game configuration."""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Safe defaults and bounds (documented in README "Configuration")
DEFAULT_HIGHSCORE_FILENAME = "highscores.json"
DEFAULT_LIVES = 3
DEFAULT_PACGUM = 42
DEFAULT_POINTS_PER_PACGUM = 10
DEFAULT_POINTS_PER_SUPER_PACGUM = 50
DEFAULT_POINTS_PER_GHOST = 200
DEFAULT_SEED = 42
DEFAULT_LEVEL_MAX_TIME = 90
DEFAULT_LEVEL_SIZE = (21, 15)
MIN_LEVELS = 10
MIN_WIDTH, MAX_WIDTH = 15, 41
MIN_HEIGHT, MAX_HEIGHT = 10, 41

KNOWN_KEYS = frozenset({
    "highscore_filename", "level", "lives", "pacgum",
    "points_per_pacgum", "points_per_super_pacgum",
    "points_per_ghost", "seed", "level_max_time",
})


class ConfigError(Exception):
    """Fatal configuration error (unreadable or non-JSON file)"""


def _default_levels() -> list[tuple[int, int]]:
    """Return the default level list (MIN_LEVELS default-sized mazes). """
    return [DEFAULT_LEVEL_SIZE] * MIN_LEVELS


@dataclass
class GameConfig:
    """Validated game settings, every field guaranteed safe to use."""
    highscore_filename: str = DEFAULT_HIGHSCORE_FILENAME
    levels: list[tuple[int, int]] = field(default_factory=_default_levels)
    lives: int = DEFAULT_LIVES
    pacgum: int = DEFAULT_PACGUM
    points_per_pacgum: int = DEFAULT_POINTS_PER_PACGUM
    points_per_super_pacgum: int = DEFAULT_POINTS_PER_SUPER_PACGUM
    points_per_ghost: int = DEFAULT_POINTS_PER_GHOST
    seed: int = DEFAULT_SEED
    level_max_time: int = DEFAULT_LEVEL_MAX_TIME


def strip_comments(text: str) -> str:
    """Blank out comment lines so the text becomes valid JSON.

    A line is a comment when its first non-whitespace character is ``#``.
    Comment lines are replaced by empty lines (not removed) so that line
    numbers in ``json.JSONDecodeError`` messages still match the file.

    Args:
        text: Raw content of the configuration file.

    Returns:
        The same text with every comment line blanked out.
    """
    lines = text.split("\n")
    cleaned = ["" if ln.lstrip().startswith("#") else ln for ln in lines]
    return "\n".join(cleaned)


def _clamp_int(data: dict[str, object], key: str,
               default: int, low: int, high: int) -> int:
    """Read an int key; wrong type -> default, out of range -> clamped

    Args:
        data: Parsed JSON object.
        key: Key to read.
        default: Value used when the key is missing or mistyped.
        low: lowest accepted value.
        high: Highest accepted value.

    Returns:
        A value guaranteed to be within [low, high].
    """
    value = data.get(key, default)
    # bool is a subclass of int: reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        logger.warning("config: '%s' invalid (%r), using %d",
                       key, value, default)
        return default
    if not low <= value <= high:
        clamped = max(low, min(high, value))
        logger.warning("config: '%s'=%d out of [%d, %d], clamped to %d",
                       key, value, low, high, clamped)
        return clamped
    return value


def _read_filename(data: dict[str, object]) -> str:
    """Read 'highscore_filename'; any invalid value -> default.

    Args:
        data: Parsed JSON object.

    Returns:
        A non-empty file name.
    """
    value = data.get("highscore_filename", DEFAULT_HIGHSCORE_FILENAME)
    if not isinstance(value, str) or not value.strip():
        logger.warning("config: 'highscore_filename' invalid, using '%s'",
                       DEFAULT_HIGHSCORE_FILENAME)
        return DEFAULT_HIGHSCORE_FILENAME
    return value


def _parse_levels(data: dict[str, object]) -> list[tuple[int, int]]:
    """Read the 'level' array into a list of (width, height) tuples.

    Invalid entries fall back to the default size; the list is padded
    with default-sized levels up to MIN_LEVELS (subject: >= 10 levels).

    Args:
        data: Parsed JSON object.

    Returns:
        At least MIN_LEVELS (width, height) tuples, all within bounds.
    """
    raw = data.get("level")
    levels: list[tuple[int, int]] = []
    if isinstance(raw, list):
        for index, entry in enumerate(raw):
            if not isinstance(entry, dict):
                logger.warning("config: level %d invalid, using default",
                               index + 1)
                levels.append(DEFAULT_LEVEL_SIZE)
                continue
            width = _clamp_int(entry, "width", DEFAULT_LEVEL_SIZE[0],
                               MIN_WIDTH, MAX_WIDTH)
            height = _clamp_int(entry, "height", DEFAULT_LEVEL_SIZE[1],
                                MIN_HEIGHT, MAX_HEIGHT)
            levels.append((width, height))
    elif raw is not None:
        logger.warning("config: 'level' is not an array, using defaults")
    if len(levels) < MIN_LEVELS:
        missing = MIN_LEVELS - len(levels)
        logger.warning("config: only %d level(s), padding to %d",
                       len(levels), MIN_LEVELS)
        levels.extend([DEFAULT_LEVEL_SIZE] * missing)
    return levels


def load_config(path: str) -> GameConfig:
    """Load, parse and validate the JSON configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        A fully validated GameConfig.

    Raises:
        ConfigError: If the file is unreadable, not valid JSON, or its
        root is not a JSON object
    """
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        raise ConfigError(f"cannot read '{path}': {exc}") from exc
    try:
        data = json.loads(strip_comments(raw))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"'{path}' is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"'{path}': root must be a JSON object")
    for key in data:
        if key not in KNOWN_KEYS:
            logger.warning("config: unknown key '%s' ignored", key)
    return GameConfig(
        highscore_filename=_read_filename(data),
        levels=_parse_levels(data),
        lives=_clamp_int(data, "lives", DEFAULT_LIVES, 1, 9),
        pacgum=_clamp_int(data, "pacgum", DEFAULT_PACGUM, 1, 10_000),
        points_per_pacgum=_clamp_int(
            data, "points_per_pacgum",
            DEFAULT_POINTS_PER_PACGUM, 0, 1_000_000),
        points_per_super_pacgum=_clamp_int(
            data, "points_per_super_pacgum",
            DEFAULT_POINTS_PER_SUPER_PACGUM, 0, 1_000_000),
        points_per_ghost=_clamp_int(
            data, "points_per_ghost",
            DEFAULT_POINTS_PER_GHOST, 0, 1_000_000),
        seed=_clamp_int(data, "seed", DEFAULT_SEED, 1, 2**31 - 1),
        level_max_time=_clamp_int(
            data, "level_max_time",
            DEFAULT_LEVEL_MAX_TIME, 5, 3_600),
    )
