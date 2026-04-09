"""Skills loader — reads YAML skill definitions from disk.

Each skill maps to a Handoff conversation block and contains:
- name: block identifier
- description: one-line summary
- prompt: detailed instructions injected into the system prompt
- required_tools: list of tool names needed for this block
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent

_cache: dict[str, Skill] = {}


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    prompt: str
    required_tools: list[str]


def load_skill(name: str) -> Skill:
    """Load a skill by name. Results are cached after first read."""
    if name in _cache:
        return _cache[name]

    path = SKILLS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    skill = Skill(
        name=data["name"],
        description=data["description"],
        prompt=data["prompt"],
        required_tools=data.get("required_tools", []),
    )
    _cache[name] = skill
    log.debug("[skills] Loaded skill '%s' from %s", name, path)
    return skill


def load_all_skills() -> dict[str, Skill]:
    """Load all YAML skills from the skills directory."""
    skills = {}
    for path in sorted(SKILLS_DIR.glob("*.yaml")):
        skill = load_skill(path.stem)
        skills[skill.name] = skill
    return skills


# Block ordering for the Handoff flow
BLOCK_ORDER: list[str] = [
    "saludo",
    "verificacion",
    "diagnostico",
    "configuracion",
    "capacitacion",
    "resolucion",
    "compromiso",
    "cierre",
]


def get_next_block(blocks_completed: dict[str, bool]) -> str | None:
    """Return the next incomplete block in order, or None if all done."""
    for block in BLOCK_ORDER:
        if not blocks_completed.get(block, False):
            return block
    return None
