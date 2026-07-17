"""Persistent top-10 highscore storage (load, validate, save)."""

import json
import logging
import os

logger = logging.getLogger(__name__)

MAX_ENTRIES = 10
MAX_NAME_LENGTH = 10


def is_valid_name(name: str) -> bool:
    """Check that a player name satisfies the subject rules.

    A valid name is non-empty, at most MAX_NAME_LENGTH characters
    long, and contains only alphanumeric characters and spaces.

    Args:
        name: Candidate player name.

    Returns:
        True if the name is acceptable, False otherwise.
    """
    if not name or len(name) > MAX_NAME_LENGTH:
        return False
    return all(char.isalnum() or char == " " for char in name)


def _validate_entry(entry: object) -> tuple[str, int] | None:
    """Turn one raw JSON entry into a (name, score) pair, or None.

    Args:
        entry: One item of the decoded JSON list.

    Returns:
        A validated (name, score) tuple, or None when invalid
    """
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    score = entry.get("score")
    if not isinstance(name, str) or not is_valid_name(name):
        return None
    if isinstance(score, bool) or not isinstance(score, int) or score < 0:
        return None
    return (name, score)


def _top_ten(scores: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Sort scores descending and keep the MAX_ENTRIES best.

    Args:
        scores: Any list of (name, score) pairs.

    Returns:
        A new list, best score first, at most MAX_ENTRIES long.
    """
    return sorted(scores, key=lambda pair: pair[1],
                  reverse=True)[:MAX_ENTRIES]


def load_highscores(path: str) -> list[tuple[str, int]]:
    """Load highscores from a JSON file, tolerating any faulty input

    A missing, unreadable or corrupt file yields an empty list
    (with a log message) - The game never crashes because of highscores.

    Args:
        path: Path to the highscore JSON file.
    Returns:
        Up to MAX_ENTRIES validated (name, score) pairs, best first
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Highscores: cannot load '%s' (%s), starting "
                       "empty", path, exc)
        return []
    if not isinstance(data, list):
        logger.warning("Highscores: '%s' root is not a list, ignoring", path)
        return []
    scores: list[tuple[str, int]] = []
    for entry in data:
        pair = _validate_entry(entry)
        if pair is None:
            logger.warning("Highscores: dropping invalid entry %r", entry)
        else:
            scores.append(pair)
    return _top_ten(scores)


def add_score(scores: list[tuple[str, int]], name: str,
              score: int) -> list[tuple[str, int]]:
    """Insert a new result and return the updated top-10

    Args:
        scores: Current (name, score) pairs.
        name: Player name (already validated by the caller).
        score: Non-negative final score.

    Returns:
        A new sorted list containing at most MAX_ENTRIES pairs
    """
    return _top_ten(scores + [(name, score)])


def save_highscores(path: str, scores: list[tuple[str, int]]) -> None:
    """Write highscores to disk with an atomic-ish replace

    Data is first written to a temporary file next to the target,
    then moved over it with os.replace, so a crash mid-write can
    never leave a half-written file. Failures are logged, not raised.

    Args:
        path: Destination JSON file.
        scores: (name, score) pairs to persist.
    """
    payload = [{"name": name, "score": score} for name, score in scores]
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(tmp_path, path)
    except OSError as exc:
        logger.warning("highscores: cannot save '%s': %s", path, exc)
