import json
import re
from pathlib import Path
from typing import Any

FOUR_DIGIT_ID = re.compile(r"\b\d{4}\b")
ROLE_NAMES = {0: "vanguard", 1: "duelist", 2: "support"}


def read_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


class NameResolver:
    def __init__(self, game_data_dir: Path):
        self.hero_names: dict[str, str] = {}
        self.hero_roles: dict[str, str] = {}
        
        for hero in read_json(game_data_dir / "heroes.json"):
            self.hero_names[str(hero["id"])] = hero["name"]
            self.hero_roles[str(hero["id"])] = ROLE_NAMES[hero["role"]]

        self.map_names: dict[str, str] = {}
        for game_map in read_json(game_data_dir / "maps.json"):
            label = f"{game_map['name']} ({game_map['type']})"
            for id_field in ["rankedId", "quickPlayId"]:
                if id_field in game_map:
                    self.map_names[str(game_map[id_field])] = label

    def resolve(self, value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {child_key: self.resolve(child_value, child_key) for child_key, child_value in value.items()}
        if isinstance(value, list):
            return [self.resolve(item, key) for item in value]
        if isinstance(value, str):
            if key == "mapId":
                return self.map_names.get(value, value)
            return FOUR_DIGIT_ID.sub(self.hero_name_for, value)
        return value

    def hero_name_for(self, id_match: re.Match) -> str:
        hero_id = id_match.group(0)
        return self.hero_names.get(hero_id, hero_id)
