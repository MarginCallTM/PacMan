"""Tests for pacman.config: comment stripping, validation, clamping."""

from pathlib import Path

import pytest

from pacman.config import (
    MIN_HEIGHT,
    MIN_LEVELS,
    MIN_WIDTH,
    ConfigError,
    GameConfig,
    load_config,
    strip_comments,
)


def test_strip_comments_blanks_comment_lines() -> None:
    """Lines starting with '#' (even indented) become empty lines."""
    text = '# comment\n # indented\n{"lives": 3}'
    assert strip_comments(text) == '\n\n{"lives": 3}'


def test_strip_comments_preserves_line_count() -> None:
    """Blanking (not deleting) keeps JSON error line numbers correct."""
    text = "# one\n# two\n{}"
    assert len(strip_comments(text).splitlines()) == 3


def test_strip_comments_keeps_hash_inside_strings() -> None:
    """A '#' inside a JSON string is not a comment marker."""
    text = '{"highscore_filename": "file#1.json"}'
    assert strip_comments(text) == text


def test_load_config_missing_file_raises() -> None:
    """A nonexistent path raises ConfigError, never OSError."""
    with pytest.raises(ConfigError):
        load_config("does_not_exist.json")


def test_load_config_empty_file_raises(tmp_path: Path) -> None:
    """An empty file is not valid JSON at all."""
    path = tmp_path / "cfg.json"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(str(path))


def test_load_config_invalid_json_raises(tmp_path: Path) -> None:
    """Broken JSON raises ConfigError with a clear message."""
    path = tmp_path / "cfg.json"
    path.write_text('{"lives": 3,,}', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(str(path))


def test_load_config_non_object_root_raises(tmp_path: Path) -> None:
    """Valid JSON whose root is not an object is rejected."""
    path = tmp_path / "cfg.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(str(path))


def _write(tmp_path: Path, text: str) -> str:
    """Write a config file in the test dir, return its path as str."""
    path = tmp_path / "cfg.json"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("raw", ['"three"', "3.5", "true", "null", "[3]"])
def test_bad_int_type_falls_back_to_default(
        tmp_path: Path, raw: str) -> None:
    """Any non-integer 'lives' value falls back to the default."""
    cfg = load_config(_write(tmp_path, f'{{"lives": {raw}}}'))
    assert cfg.lives == GameConfig().lives


@pytest.mark.parametrize("key, minimum", [
    ("lives", 1),
    ("pacgum", 1),
    ("seed", 1),
    ("level_max_time", 10),
    ("points_per_pacgum", 0),
])
def test_int_below_minimum_is_clamped(
        tmp_path: Path, key: str, minimum: int) -> None:
    """An integer below its allowed minimum is clamped to it."""
    cfg = load_config(_write(tmp_path, f'{{"{key}": -99}}'))
    assert getattr(cfg, key) == minimum


def test_missing_keys_use_defaults(tmp_path: Path) -> None:
    """An empty JSON object yields a fully defaulted config."""
    cfg = load_config(_write(tmp_path, "{}"))
    defaults = GameConfig()
    assert cfg.lives == defaults.lives
    assert cfg.seed == defaults.seed
    assert cfg.level_max_time == defaults.level_max_time
    assert cfg.highscore_filename == defaults.highscore_filename
