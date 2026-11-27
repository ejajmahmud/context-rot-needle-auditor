"""Audits structured prompt assemblies for lost-in-the-middle context rot."""
import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class PromptSegment:
    name: str
    content: str
    is_needle: bool = False
    priority: int = 1

    def estimated_tokens(self) -> int:
        return max(1, math.ceil(len(self.content) / 4.0))


@dataclass
class NeedleAudit:
    name: str
    relative_depth: float
    zone: str
    salience_score: float
    at_risk: bool


@dataclass
class ContextRotReport:
    total_tokens: int
    needle_tokens: int
    dilution_ratio: float
    rot_risk_score: float
    buried_needles: List[str]
    needle_audits: List[NeedleAudit]
    recommendations: List[str] = field(default_factory=list)


def u_curve_salience(relative_depth: float) -> float:
    """Models primacy/recency U-shaped attention retention in [0.0, 1.0]."""
    d = min(max(relative_depth, 0.0), 1.0)
    # 1.0 at edges (d=0 or d=1), dropping to 0.25 at dead center (d=0.5).
    return round(0.25 + 3.0 * ((d - 0.5) ** 2), 4)


def audit_prompt_assembly(
    segments: List[PromptSegment],
    middle_low: float = 0.25,
    middle_high: float = 0.75,
    max_safe_dilution: float = 12.0,
) -> ContextRotReport:
    """Scores each critical needle's positional salience and global prompt dilution."""
    if not segments:
        raise ValueError("segments must not be empty")
    if not (0.0 < middle_low < middle_high < 1.0):
        raise ValueError("middle bounds must satisfy 0 < middle_low < middle_high < 1")

    token_counts = [s.estimated_tokens() for s in segments]
    total_tokens = sum(token_counts)
    needle_tokens = sum(tc for s, tc in zip(segments, token_counts) if s.is_needle)
    noise_tokens = max(0, total_tokens - needle_tokens)
    dilution_ratio = round(noise_tokens / max(1, needle_tokens), 3)

    audits: List[NeedleAudit] = []
    buried: List[str] = []
    cursor = 0
    for seg, tc in zip(segments, token_counts):
        midpoint = cursor + (tc / 2.0)
        rel_depth = round(midpoint / total_tokens, 4)
        cursor += tc
        if not seg.is_needle:
            continue
        if rel_depth < middle_low:
            zone = "primacy"
        elif rel_depth > middle_high:
            zone = "recency"
        else:
            zone = "middle"
        salience = u_curve_salience(rel_depth)
        at_risk = zone == "middle" or salience < 0.45
        if at_risk:
            buried.append(seg.name)
        audits.append(
            NeedleAudit(
                name=seg.name,
                relative_depth=rel_depth,
                zone=zone,
                salience_score=salience,
                at_risk=at_risk,
            )
        )

    recs: List[str] = []
    if buried:
        recs.append(f"Move middle-buried needles ({', '.join(buried)}) to primacy (<{middle_low}) or recency (>{middle_high}).")
    if needle_tokens > 0 and dilution_ratio > max_safe_dilution:
        recs.append(f"Dilution ratio {dilution_ratio}x exceeds {max_safe_dilution}x; compact or summarize distractor blocks.")

    if audits:
        avg_risk = sum(1.0 - a.salience_score for a in audits) / len(audits)
    else:
        avg_risk = 0.0
    dilution_component = min(1.0, dilution_ratio / (max_safe_dilution * 2.0)) if needle_tokens > 0 else 0.0
    rot_risk_score = round(min(1.0, (0.65 * avg_risk) + (0.35 * dilution_component)), 4)

    return ContextRotReport(
        total_tokens=total_tokens,
        needle_tokens=needle_tokens,
        dilution_ratio=dilution_ratio,
        rot_risk_score=rot_risk_score,
        buried_needles=buried,
        needle_audits=audits,
        recommendations=recs,
    )
