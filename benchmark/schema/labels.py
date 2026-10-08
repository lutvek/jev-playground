"""Etiketterna i formatet. JSON-schemat är enda källan, så att kod och schema inte glider isär."""

import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent

_defs = json.loads((SCHEMA_DIR / "record.schema.json").read_text(encoding="utf-8"))["$defs"]

PARTS: tuple[str, ...] = tuple(_defs["part"]["enum"])
SPLITS: tuple[str, ...] = tuple(_defs["split"]["enum"])
ROLES: tuple[str, ...] = tuple(_defs["role"]["enum"])
EXPRESSIONS: tuple[str, ...] = tuple(_defs["expression"]["enum"])
CATEGORIES: tuple[str, ...] = tuple(_defs["category"]["enum"])
IDENTIFIER_TYPES: tuple[str, ...] = tuple(_defs["identifierType"]["enum"])
