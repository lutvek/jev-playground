"""Gränssnittet mot den LLM som skriver texterna.

Generatorn bryr sig inte om var modellen körs. En klient behöver ett namn, som hamnar i
source.generator, och en metod som tar en prompt och ger modellens svar. Klienter för Vertex AI
och andra miljöer läggs till när åtkomsten finns (avsnitt 9 i PLAN_BENCHMARK.md).
"""

from collections.abc import Iterable, Iterator
from typing import Protocol

from benchmark.generering.prompt import build_prompt


class LLM(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


def respond(specs: Iterable[dict], llm: LLM) -> Iterator[dict]:
    """En rad till svarsfilen per spec, i det format benchmark.generering.build läser."""
    for spec in specs:
        response = llm.complete(build_prompt(spec))
        yield {"scenario_id": spec["scenario_id"], "generator": llm.name, "response": response}
