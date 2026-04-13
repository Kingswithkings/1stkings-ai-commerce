import json
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError


class SizePriceOption(BaseModel):
    label: str
    price: float


def normalize_size_pricing(value: Any) -> list[dict]:
    if value in (None, "", []):
        return []

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Invalid size pricing JSON") from exc
    else:
        parsed = value

    if not isinstance(parsed, list):
        raise HTTPException(status_code=422, detail="Size pricing must be a list")

    normalized: list[dict] = []
    seen: set[str] = set()

    for item in parsed:
        try:
            option = SizePriceOption.model_validate(item)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

        label = option.label.strip()
        if not label:
            raise HTTPException(status_code=422, detail="Size label cannot be empty")
        if label.lower() in seen:
            raise HTTPException(status_code=422, detail=f"Duplicate size label: {label}")
        seen.add(label.lower())
        normalized.append({"label": label, "price": float(option.price)})

    return normalized


def dumps_size_pricing(options: list[dict] | None) -> str | None:
    normalized = normalize_size_pricing(options or [])
    if not normalized:
        return None
    return json.dumps(normalized)


def loads_size_pricing(raw: str | None) -> list[dict]:
    if not raw:
        return []
    return normalize_size_pricing(raw)
