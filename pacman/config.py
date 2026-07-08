"""Load, validate and clamp the JSON game configuration."""

import json
import sys
from dataclasses import dataclass, field
from typing import Any

MIN_LEVELS = 10
MIN_WIDTH = 15
MIN_HEIGHT = 10

_KNOWN_KEYS = frozenset({
    "highscore_filename", "level", "lives", "pacgum",
    "points_per_pacgum", "points_per_super_pacgum",
    "points_per_ghost", "seed", "level_max_time",
})


@dataclass
class LevelConfig:
    """Size of one maze level."""

    width: int = 20
    height: int = 20


@dataclass
class GameConfig:
    """All game parameters, with safe default values."""

    highscore_filename: str = "highscores.json"
    lives: int = 3
    pacgum: int = 42
    points_per_pacgum: int = 10
    points_per_super_pacgum: int = 50
    points_per_ghost: int = 200
    seed: int = 42
    level_max_time: int = 90
    levels: list[LevelConfig] = field(default_factory=list)


class ConfigError(Exception):
    """Raised when the configuration file cannot be used at all."""


def strip_comments(text: str) -> str:
    """Remove comment lines from a JSON document.

    A comment line is a line whose first non-blank character is '#'.
    The line is replaced by an empty line (not deleted) so that error
    messages from the JSON parser keep pointing at the right line
    numbers in the original file.

    Args:
        text: Raw content of the configuration file.

    Returns:
        The same text with comment lines blanked out.
    """
    kept: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            kept.append("")
        else:
            kept.append(line)
    return "\n".join(kept)


def load_config(path: str) -> GameConfig:
    """Load, validate and clamp a JSON configuration file.

    Args:
        path: Path to the configuration file.

    Returns:
        A fully validated ``GameConfig`` (invalid values are clamped
        to safe defaults, with a warning on stderr).

    Raises:
        ConfigError: If the file is missing, unreadable, empty or
            not a JSON object at all.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as error:
        raise ConfigError(f"cannot read {path}: {error}") from error
    try:
        data = json.loads(strip_comments(text))
    except json.JSONDecodeError as error:
        raise ConfigError(f"{path}: not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: root element must be a JSON object")
    for key in sorted(data.keys() - _KNOWN_KEYS):
        _warn(f'unknown key "{key}" ignored')
    defaults = GameConfig()
    return GameConfig(
        highscore_filename=_read_str(
            data, "highscore_filename", defaults.highscore_filename),
        lives=_read_int(data, "lives", defaults.lives, minimum=1),
        pacgum=_read_int(data, "pacgum", defaults.pacgum, minimum=1),
        points_per_pacgum=_read_int(
            data, "points_per_pacgum", defaults.points_per_pacgum),
        points_per_super_pacgum=_read_int(
            data, "points_per_super_pacgum",
            defaults.points_per_super_pacgum),
        points_per_ghost=_read_int(
            data, "points_per_ghost", defaults.points_per_ghost),
        seed=_read_int(data, "seed", defaults.seed, minimum=1),
        level_max_time=_read_int(
            data, "level_max_time", defaults.level_max_time, minimum=10),
        levels=_read_levels(data),
    )


def _warn(message: str) -> None:
    """Print a configuration warning on stderr."""
    print(f"config: {message}", file=sys.stderr)


def _read_int(data: dict[str, Any], key: str,
              default: int, minimum: int = 0) -> int:
    """Read an integer from raw config data, clamping bad values.

    Args:
        data: Parsed JSON object.
        key: Key to look up.
        default: Value used when the key is missing or invalid.
        minimum: Smallest acceptable value.

    Returns:
        The validated integer, or ``default`` if missing/invalid,
        or ``minimum`` if the value is an integer but too small.
    """
    if key not in data:
        _warn(f'missing key "{key}", using default {default}')
        return default
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        _warn(f'invalid value for "{key}" (expected integer, '
              f'got {value!r}), using default {default}')
        return default
    if value < minimum:
        _warn(f'value {value} for "{key}" is below minimum, '
              f'clamped to {minimum}')
        return minimum
    return value


def _read_str(data: dict[str, Any], key: str, default: str) -> str:
    """Read a non-empty string from raw config data.

    Args:
        data: Parsed JSON object.
        key: Key to look up.
        default: Value used when the key is missing or invalid.

    Returns:
        The validated string, or ``default`` if missing or invalid.
    """
    if key not in data:
        _warn(f'missing key "{key}", using default {default!r}')
        return default
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        _warn(f'invalid value for "{key}" (expected non-empty '
              f'string, got {value!r}), using default {default!r}')
        return default
    return value


def _read_levels(data: dict[str, Any]) -> list[LevelConfig]:
    """Read the "level" array, padded to at least ``MIN_LEVELS``.

    Args:
        data: Parsed JSON object.

    Returns:
        A list of at least ``MIN_LEVELS`` validated level sizes.
    """
    raw = data.get("level")
    if not isinstance(raw, list):
        _warn('missing or invalid "level" array, using '
              f'{MIN_LEVELS} default levels')
        raw = []
    levels: list[LevelConfig] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            _warn(f'level {index + 1}: expected an object, got '
                  f'{entry!r}, using default size')
            entry = {}
        levels.append(LevelConfig(
            width=_read_int(entry, "width", 20, minimum=MIN_WIDTH),
            height=_read_int(entry, "height", 20, minimum=MIN_HEIGHT),
        ))
    if len(levels) < MIN_LEVELS:
        _warn(f'only {len(levels)} level(s) defined, padding to '
              f'{MIN_LEVELS} with default sizes')
        levels.extend(LevelConfig()
                      for _ in range(MIN_LEVELS - len(levels)))
    return levels
