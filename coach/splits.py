from typing import Any

ROLE_NAMES = ["vanguard", "duelist", "support"]
SPLIT_KEYS = {"split": "splitInWords", "vsEnemySplit": "vsEnemySplitInWords"}


def role_count_words(count: int, role_name: str) -> str:
    if count == 1:
        return f"1 {role_name}"
    return f"{count} {role_name}s"


def split_in_words(split: str) -> str | None:
    parts = split.split("-")
    if len(parts) != len(ROLE_NAMES) or not all(part.isdigit() for part in parts):
        return None
    role_words = []
    for count_text, role_name in zip(parts, ROLE_NAMES):
        role_words.append(role_count_words(int(count_text), role_name))
    return ", ".join(role_words)


def describe_splits(value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            describe_splits(item)
        return
    if not isinstance(value, dict):
        return

    for split_key, words_key in SPLIT_KEYS.items():
        split = value.get(split_key)
        if isinstance(split, str):
            words = split_in_words(split)
            if words is not None:
                value[words_key] = words

    for child_value in list(value.values()):
        describe_splits(child_value)
