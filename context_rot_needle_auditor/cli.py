"""CLI for Context Rot Needle Auditor."""
import argparse
import json
from .core import PromptSegment, audit_prompt_assembly


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit prompt assembly for middle-context rot")
    parser.add_argument("--input", required=True, help="JSON list of prompt segments")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    segs = [PromptSegment(**item) for item in raw]
    rep = audit_prompt_assembly(segs)
    print(f"rot_risk={rep.rot_risk_score} dilution={rep.dilution_ratio}x buried={rep.buried_needles}")
    for rec in rep.recommendations:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()
