"""Namn och personnummer till scenariospecarna.

Planen är att ta namn från SCB:s namnstatistik och personnummer från Skatteverkets
testpersonnummer (se KALLOR.md). Ingen av källorna går att nå från molnmiljön ännu, så tills
vidare används platshållarna här. Specar som bygger på dem får placeholders: true.

Namnen dras oberoende av de känsliga uppgifterna, så att ett namn aldrig avslöjar en kategori.
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Resources:
    female: tuple[str, ...]
    male: tuple[str, ...]
    surnames: tuple[str, ...]
    placeholder: bool


# Vanliga namn i Sverige. Namn som också är vanliga ord med stor bokstav i början av en mening,
# som Hans och Per, är utelämnade, eftersom kontrollen av omärkta namn annars ger falsklarm.
PLACEHOLDERS = Resources(
    female=(
        "Anna", "Eva", "Maria", "Karin", "Kristina", "Lena", "Sara", "Emma", "Kerstin", "Ingrid",
        "Marie", "Malin", "Jenny", "Hanna", "Linda", "Elin", "Sofia", "Johanna", "Fatima", "Amira",
        "Leila", "Zeynep", "Aisha", "Nadia", "Agnieszka", "Mirja",
    ),
    male=(
        "Lars", "Mikael", "Anders", "Johan", "Erik", "Karl", "Thomas", "Jan", "Daniel", "Fredrik",
        "Andreas", "Stefan", "Jonas", "Magnus", "Mattias", "Mohammed", "Ali", "Ahmed", "Hassan",
        "Omar", "Mehmet", "Piotr", "Matti", "Juha", "Dragan",
    ),
    surnames=(
        "Andersson", "Johansson", "Karlsson", "Nilsson", "Eriksson", "Larsson", "Olsson", "Persson",
        "Svensson", "Gustafsson", "Pettersson", "Jonsson", "Jansson", "Hansson", "Bengtsson",
        "Jönsson", "Lindberg", "Jakobsson", "Magnusson", "Lindström", "Olofsson", "Lindqvist",
        "Lindgren", "Axelsson", "Bergström", "Lundberg", "Lundgren", "Mattsson", "Berglund",
        "Fredriksson", "Sandberg", "Henriksson", "Ali", "Mohammed", "Ahmed", "Hassan", "Hussein",
        "Nguyen", "Yilmaz", "Kaya", "Nowak", "Virtanen", "Korhonen", "Petrović",
    ),
    placeholder=True,
)


def luhn_digit(digits: str) -> int:
    """Kontrollsiffran för de nio första siffrorna i ett personnummer (ÅÅMMDDNNN)."""
    total = 0
    for i, d in enumerate(map(int, digits)):
        product = d * (2 if i % 2 == 0 else 1)
        total += product // 10 + product % 10
    return (10 - total % 10) % 10


def placeholder_personnummer(rng: random.Random, gender: str) -> str:
    """Ett personnummer med fel kontrollsiffra, så att det inte kan tillhöra någon.

    Näst sista siffran är udda för män och jämn för kvinnor, som i riktiga personnummer.
    """
    year, month, day = rng.randint(1950, 2000), rng.randint(1, 12), rng.randint(1, 28)
    serial = rng.randint(0, 99) * 10 + rng.choice((1, 3, 5, 7, 9) if gender == "man" else (0, 2, 4, 6, 8))
    nine = f"{year % 100:02d}{month:02d}{day:02d}{serial:03d}"
    wrong = (luhn_digit(nine) + rng.randint(1, 9)) % 10
    return f"{nine[:6]}-{nine[6:]}{wrong}"
