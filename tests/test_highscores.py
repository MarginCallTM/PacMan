"""Tests for pacman.highscores: validation, trimming, persistence."""

import json
from pathlib import Path

from pacman.highscores import (
    MAX_ENTRIES, add_score, is_valid_name,
    load_highscores, save_highscores,
)


def test_valid_names() -> None:
    """Alphanumeric + spaces, up to 10 chars, are accepted."""
    assert is_valid_name("Adrien")
    assert is_valid_name("a b 42")


def test_invalid_names() -> None:
    """Empty, too long, or punctuated names are rejected."""
    assert not is_valid_name("")
    assert not is_valid_name("x" * 11)
    assert not is_valid_name("bad!name")


def test_load_missing_file(tmp_path: Path) -> None:
    """A missing file yields an empty list, no crash."""
    assert load_highscores(str(tmp_path / "nope.json")) == []


def test_load_corrupt_file(tmp_path: Path) -> None:
    """A non-JSON file yields an empty list, no crash."""
    path = tmp_path / "scores.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_highscores(str(path)) == []


def test_load_non_list_root(tmp_path: Path) -> None:
    """A JSON root that is not a list yields an empty list."""
    path = tmp_path / "scores.json"
    path.write_text('{"name": "x"}', encoding="utf-8")
    assert load_highscores(str(path)) == []


def test_load_drops_invalid_entries(tmp_path: Path) -> None:
    """Bad names, negative/bool scores, non-dicts are dropped."""
    entries = [
        {"name": "Good", "score": 10},
        {"name": "bad!", "score": 10},
        {"name": "Neg", "score": -5},
        {"name": "Bool", "score": True},
        "not a dict",
    ]
    path = tmp_path / "scores.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    assert load_highscores(str(path)) == [("Good", 10)]


def test_load_sorts_and_trims(tmp_path: Path) -> None:
    """Entries come back best-first and capped at MAX_ENTRIES."""
    entries = [{"name": f"P{i}", "score": i} for i in range(15)]
    path = tmp_path / "scores.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    scores = load_highscores(str(path))
    assert len(scores) == MAX_ENTRIES
    assert scores[0] == ("P14", 14)
    assert scores[-1] == ("P5", 5)


def test_add_score_trims_to_ten() -> None:
    """Adding an 11th score drops the lowest one."""
    scores = [(f"P{i}", 100 - i) for i in range(MAX_ENTRIES)]
    updated = add_score(scores, "New", 95)
    assert len(updated) == MAX_ENTRIES
    assert ("New", 95) in updated
    assert ("P9", 91) not in updated


def test_add_score_stable_on_tie() -> None:
    """On equal scores, the older entry stays ahead (stable sort)."""
    assert add_score([("Old", 50)], "New", 50) == [
        ("Old", 50), ("New", 50)]


def test_save_load_round_trip(tmp_path: Path) -> None:
    """What we save is exactly what we load back."""
    path = str(tmp_path / "scores.json")
    scores = [("Adrien", 4200), ("Sloubiat", 1000)]
    save_highscores(path, scores)
    assert load_highscores(path) == scores


def test_save_failure_never_raises(tmp_path: Path) -> None:
    """Saving into a missing directory logs but never raises."""
    save_highscores(str(tmp_path / "no_dir" / "s.json"), [("A", 1)])
