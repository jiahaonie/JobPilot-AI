"""基于人工维护别名白名单的确定性技能规范化。"""

import re
import unicodedata
from collections.abc import Collection, Mapping

SKILL_ALIASES: dict[str, frozenset[str]] = {
    "fastapi": frozenset({"FastAPI", "Fast API"}),
    "vector_db": frozenset({"向量数据库", "Vector DB", "Vector Database"}),
    "llm": frozenset({"LLM", "大语言模型", "Large Language Model"}),
    "tool_use": frozenset(
        {"Tool Use", "Tool Calling", "Function Calling", "工具调用"}
    ),
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
        surfaces = {
            skill,
            *self.alias_map.evidence_surfaces(self.canonical_name(skill)),
        }
        return any(_contains_surface(normalized_text, surface) for surface in surfaces)

    def find_evidence_surface(self, text: str, skill: str) -> str | None:
        """返回证据中实际出现的批准写法，不进行语义猜测。"""
        normalized_text = unicodedata.normalize("NFKC", text).casefold()
        surfaces = {
            skill,
            *self.alias_map.evidence_surfaces(self.canonical_name(skill)),
        }
        for surface in sorted(surfaces, key=lambda value: (-len(value), value)):
            match = re.search(_surface_pattern(surface), normalized_text)
            if match is not None:
                return text[match.start() : match.end()]
        return None

    def equivalent(self, left: str, right: str) -> bool:
        """返回两个名称经明确规范化后是否相同。"""
        return self.canonical_name(left) == self.canonical_name(right)


def _contains_surface(normalized_text: str, surface: str) -> bool:
    """按单词边界匹配拉丁技能，并允许常见分隔符差异。"""
    return re.search(_surface_pattern(surface), normalized_text) is not None


def _surface_pattern(surface: str) -> str:
    """构造保留词边界、允许无语义分隔符变化的正则表达式。"""
    normalized_surface = _normalize_surface(surface)
    characters = list(normalized_surface)
    if not characters:
        return r"(?!)"
    pattern = r"[\s._\-/]*".join(re.escape(character) for character in characters)
    if characters[0].isascii() and characters[0].isalnum():
        pattern = rf"(?<![a-z0-9]){pattern}"
    if characters[-1].isascii() and characters[-1].isalnum():
        pattern = rf"{pattern}(?![a-z0-9])"
    return pattern
