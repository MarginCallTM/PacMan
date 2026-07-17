"""Tests for pacman.config: comments, validation, clamping, evil files."""

from pathlib import Path

import pytest

from pacman.config import (
    MAX_HEIGHT, MIN_LEVELS, MIN_WIDTH,
    ConfigError, GameConfig, load_config, strip_comments,
)

EVIL_DIR = Path(__file__).parent / "evils_configs"
EVIL_FILES = sorted(p.name for p in EVIL_DIR.glob("*.json"))


def write(tmp_path: Path, text: str) -> str:
    """Write a temporary config file and return its path as a string."""
    path = tmp_path / "config.json"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_strip_comments_blanks_lines() -> None:
    """Comment lines are blanked, not removed (line numbers kept)."""
    text = '# header\n{\n# inner\n"lives": 3\n}'
    assert strip_comments(text) == '\n{\n\n"lives": 3\n}'


def test_valid_config(tmp_path: Path) -> None:
    """A well-formed file is loaded verbatim."""
    config = load_config(write(tmp_path, '{"lives": 5, "seed": 7}'))
    assert config.lives == 5
    assert config.seed == 7


def test_missing_file_raises(tmp_path: Path) -> None:
    """A missing file is a fatal ConfigError, not a traceback."""
    with pytest.raises(ConfigError):
        load_config(str(tmp_path / "nope.json"))


def test_empty_file_raises(tmp_path: Path) -> None:
    """An empty file is not valid JSON: fatal ConfigError."""
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, ""))


def test_non_json_raises(tmp_path: Path) -> None:
    """Garbage content is a fatal ConfigError."""
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, "hello world"))


def test_non_object_root_raises(tmp_path: Path) -> None:
    """A JSON root that is not an object is a fatal ConfigError."""
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, "[1, 2]"))


def test_wrong_types_fall_back(tmp_path: Path) -> None:
    """Mistyped values (incl. bool-as-int) fall back to defaults."""
    config = load_config(
        write(tmp_path, '{"lives": "three", "seed": true}'))
    assert config.lives == GameConfig().lives
    assert config.seed == GameConfig().seed


def test_out_of_range_clamped(tmp_path: Path) -> None:
    """Out-of-range values are clamped to the nearest bound."""
    config = load_config(write(tmp_path, '{"lives": 99}'))
    assert config.lives == 9


def test_unknown_keys_ignored(tmp_path: Path) -> None:
    """Unknown keys are ignored, known keys still applied."""
    config = load_config(write(tmp_path, '{"wat": 1, "lives": 4}'))
    assert config.lives == 4


def test_levels_padded_and_clamped(tmp_path: Path) -> None:
    """Level list is clamped per entry and padded to MIN_LEVELS."""
    config = load_config(
        write(tmp_path, '{"level": [{"width": 1, "height": 99}]}'))
    assert len(config.levels) == MIN_LEVELS
    assert config.levels[0] == (MIN_WIDTH, MAX_HEIGHT)


def test_evil_files_present() -> None:
    """Guard: the defense drill files must exist (task 2.9)."""
    assert len(EVIL_FILES) >= 5


@pytest.mark.parametrize("name", EVIL_FILES)
def test_evil_config_never_tracebacks(name: str) -> None:
    """Every evil file yields a GameConfig or a clean ConfigError."""
    try:
        config = load_config(str(EVIL_DIR / name))
    except ConfigError:
        return
    assert isinstance(config, GameConfig)
