"""Structured match criteria models."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MatchCriterionItem:
    """A single criterion item within match criteria."""

    id: str
    text: str
    enabled: bool = True
    weight: int = 0  # Only used by core_requirements


@dataclass
class MatchCriteria:
    """Structured machine-readable match criteria derived from JD analysis."""

    dealbreakers: List[MatchCriterionItem] = field(default_factory=list)
    core_requirements: List[MatchCriterionItem] = field(default_factory=list)
    basic_requirements: List[MatchCriterionItem] = field(default_factory=list)
    bonuses: List[MatchCriterionItem] = field(default_factory=list)
    misjudgment_reminders: List[str] = field(default_factory=list)
    version: int = 1
    confirmed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MatchCriteria":
        """Build MatchCriteria from a plain dictionary."""
        if not data:
            return cls()
        return cls(
            dealbreakers=[
                MatchCriterionItem(**item)
                for item in data.get("dealbreakers", [])
            ],
            core_requirements=[
                MatchCriterionItem(**item)
                for item in data.get("core_requirements", [])
            ],
            basic_requirements=[
                MatchCriterionItem(**item)
                for item in data.get("basic_requirements", [])
            ],
            bonuses=[
                MatchCriterionItem(**item)
                for item in data.get("bonuses", [])
            ],
            misjudgment_reminders=list(data.get("misjudgment_reminders", [])),
            version=int(data.get("version", 1)),
            confirmed_at=data.get("confirmed_at") or None,
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "dealbreakers": [
                {
                    "id": item.id,
                    "text": item.text,
                    "enabled": item.enabled,
                    "weight": item.weight,
                }
                for item in self.dealbreakers
            ],
            "core_requirements": [
                {
                    "id": item.id,
                    "text": item.text,
                    "enabled": item.enabled,
                    "weight": item.weight,
                }
                for item in self.core_requirements
            ],
            "basic_requirements": [
                {
                    "id": item.id,
                    "text": item.text,
                    "enabled": item.enabled,
                    "weight": item.weight,
                }
                for item in self.basic_requirements
            ],
            "bonuses": [
                {
                    "id": item.id,
                    "text": item.text,
                    "enabled": item.enabled,
                    "weight": item.weight,
                }
                for item in self.bonuses
            ],
            "misjudgment_reminders": list(self.misjudgment_reminders),
            "version": self.version,
            "confirmed_at": self.confirmed_at,
        }

    def validate(self) -> List[str]:
        """Return a list of human-readable validation errors."""
        errors = []
        active_core = [c for c in self.core_requirements if c.enabled]
        if not active_core:
            errors.append("至少要有 1 条启用的核心要求")
        else:
            total_weight = sum(c.weight for c in active_core)
            if total_weight != 100:
                errors.append(f"核心要求权重之和必须等于 100，当前为 {total_weight}")
        return errors
