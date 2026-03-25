from __future__ import annotations

from typing import Any

from pydantic import BaseModel


PLACEHOLDER_TEXT = {
    "",
    "unknown",
    "n/a",
    "未提供信息",
    "无法确定",
}


def ensure_model_has_data(model: BaseModel) -> None:
    data = model.model_dump()
    if not data:
        raise ValueError("Structured output is empty.")
    for value in data.values():
        if isinstance(value, list) and not value:
            raise ValueError("Structured output contains an empty list field.")


def ensure_no_placeholder_values(payload: dict[str, Any]) -> None:
    def _walk(value: Any) -> None:
        if isinstance(value, str) and value.strip().lower() in PLACEHOLDER_TEXT:
            raise ValueError("Structured output still contains placeholder text.")
        if isinstance(value, dict):
            for nested_value in value.values():
                _walk(nested_value)
        if isinstance(value, list):
            for nested_value in value:
                _walk(nested_value)

    _walk(payload)

