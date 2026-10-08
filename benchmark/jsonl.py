"""Läsning och skrivning av JSONL."""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path


def read_jsonl(path: str | Path) -> Iterator[tuple[int, dict]]:
    """Ger (radnummer, post) för varje icke-tom rad."""
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if line.strip():
                yield lineno, json.loads(line)


def write_jsonl(path: str | Path, records: Iterable[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n
