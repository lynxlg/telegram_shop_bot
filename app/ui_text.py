import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_UI_TEXTS_PATH = Path(__file__).with_name("ui_texts.json")


@lru_cache(maxsize=1)
def load_ui_texts() -> dict[str, Any]:
    with _UI_TEXTS_PATH.open(encoding="utf-8") as source:
        data = json.load(source)

    if not isinstance(data, dict):
        raise TypeError("UI texts root must be a JSON object")

    return data


def get_ui_text(*path: str) -> str:
    node: Any = load_ui_texts()
    for key in path:
        if not isinstance(node, dict) or key not in node:
            joined_path = ".".join(path)
            raise KeyError(f"UI text not found: {joined_path}")
        node = node[key]

    if not isinstance(node, str):
        joined_path = ".".join(path)
        raise TypeError(f"UI text value must be a string: {joined_path}")

    return node


def format_ui_text(*path: str, **kwargs: Any) -> str:
    return get_ui_text(*path).format(**kwargs)
