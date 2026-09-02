"""基于人工维护别名白名单的确定性技能规范化。"""

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
    """规范化无关语义的文本差异，不推断额外含义。"""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _IGNORED_SEPARATORS.sub("", normalized)


class SkillAliasMap:
    """仅将明确批准的别名解析为统一技能名。"""

    def __init__(self, aliases: Mapping[str, Collection[str]]) -> None:
        self._canonical_by_surface: dict[str, str] = {}
        self._evidence_surfaces_by_canonical: dict[str, frozenset[str]] = {}

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
                        f"skill alias {surface!r} belongs to both {existing!r} and {canonical!r}"
                    )
                self._canonical_by_surface[surface] = canonical
            self._evidence_surfaces_by_canonical[canonical] = frozenset(
                {canonical_name, *approved_aliases}
            )

    def canonicalize(self, normalized_skill: str) -> str:
        """规范化技能命中白名单时返回统一名称。"""
        return self._canonical_by_surface.get(normalized_skill, normalized_skill)

    def evidence_surfaces(self, canonical_name: str) -> frozenset[str]:
        """返回用于证据边界匹配的原始技能写法。"""
        return self._evidence_surfaces_by_canonical.get(
            canonical_name,
            frozenset({canonical_name}),
        )


class SkillNormalizer:
    """统一应用表面规范化和别名规则。"""

    def __init__(self, alias_map: SkillAliasMap | None = None) -> None:
        self.alias_map = alias_map or SkillAliasMap(SKILL_ALIASES)

    def canonical_name(self, skill: str) -> str:
        """将一种技能写法转换为确定性比较键。"""
        return self.alias_map.canonicalize(_normalize_surface(skill))

    def contains_evidence(self, text: str, skill: str) -> bool:
        """判断证据是否包含完整技能词项，避免短词误命中。"""
        normalized_text = unicodedata.normalize("NFKC", text).casefold()
        surfaces = self.alias_map.evidence_surfaces(self.canonical_name(skill))
        return any(_contains_surface(normalized_text, surface) for surface in surfaces)

    def equivalent(self, left: str, right: str) -> bool:
        """返回两个名称经明确规范化后是否相同。"""
        return self.canonical_name(left) == self.canonical_name(right)


def _contains_surface(normalized_text: str, surface: str) -> bool:
    """按单词边界匹配拉丁技能，并允许常见分隔符差异。"""
    normalized_surface = unicodedata.normalize("NFKC", surface).casefold()
    parts = [part for part in _IGNORED_SEPARATORS.split(normalized_surface) if part]
    if not parts:
        return False
    pattern = r"[\s._\-/]*".join(re.escape(part) for part in parts)
    if parts[0][0].isascii() and parts[0][0].isalnum():
        pattern = rf"(?<![a-z0-9]){pattern}"
    if parts[-1][-1].isascii() and parts[-1][-1].isalnum():
        pattern = rf"{pattern}(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None
