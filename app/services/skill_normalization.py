"""Deterministic skill normalization backed by a curated alias whitelist."""

import re
import unicodedata
from collections.abc import Collection, Mapping

SKILL_ALIASES: dict[str, frozenset[str]] = {
    "fastapi": frozenset({"FastAPI", "Fast API"}),
    "vector_db": frozenset({"向量数据库", "Vector DB", "Vector Database"}),
    "llm": frozenset({"LLM", "大语言模型", "Large Language Model"}),
}

_IGNORED_SEPARATORS = re.compile(r"[\s._\-/]+")


def _normalize_surface(value: str) -> str:
    """Normalize harmless textual differences without inferring meaning."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _IGNORED_SEPARATORS.sub("", normalized)


class SkillAliasMap:
    """Resolve only explicitly approved aliases to one canonical skill name."""

    def __init__(self, aliases: Mapping[str, Collection[str]]) -> None:
        self._canonical_by_surface: dict[str, str] = {}
        self._surfaces_by_canonical: dict[str, frozenset[str]] = {}

        for canonical_name, approved_aliases in aliases.items():
            canonical = _normalize_surface(canonical_name)
            surfaces = {
                canonical,
                *(_normalize_surface(alias) for alias in approved_aliases),
            }
            for surface in surfaces:
                existing = self._canonical_by_surface.get(surface)
                if existing is not None and existing != canonical:
                    raise ValueError(
                        f"skill alias {surface!r} belongs to both "
                        f"{existing!r} and {canonical!r}"
                    )
                self._canonical_by_surface[surface] = canonical
            self._surfaces_by_canonical[canonical] = frozenset(surfaces)

    def canonicalize(self, normalized_skill: str) -> str:
        """Return a canonical name when the normalized skill is whitelisted."""

        return self._canonical_by_surface.get(normalized_skill, normalized_skill)

    def evidence_terms(self, canonical_name: str) -> frozenset[str]:
        """Return approved normalized terms that may identify this skill in text."""

        return self._surfaces_by_canonical.get(
            canonical_name,
            frozenset({canonical_name}),
        )


class SkillNormalizer:
    """Apply surface normalization and the same alias rules everywhere."""

    def __init__(self, alias_map: SkillAliasMap | None = None) -> None:
        self.alias_map = alias_map or SkillAliasMap(SKILL_ALIASES)

    def canonical_name(self, skill: str) -> str:
        """Convert one skill spelling into its deterministic comparison key."""

        return self.alias_map.canonicalize(_normalize_surface(skill))

    def evidence_terms(self, skill: str) -> frozenset[str]:
        """Return all approved text forms for evidence lookup."""

        return self.alias_map.evidence_terms(self.canonical_name(skill))

    @staticmethod
    def normalize_evidence(text: str) -> str:
        """Normalize evidence text without treating the whole sentence as a skill."""

        return _normalize_surface(text)

    def equivalent(self, left: str, right: str) -> bool:
        """Return whether two names are the same after explicit normalization."""

        return self.canonical_name(left) == self.canonical_name(right)
