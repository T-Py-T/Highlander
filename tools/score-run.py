#!/usr/bin/env python3
"""Score a Highlander run using only retained evidence."""

import argparse
import json
import sys


WEIGHTS = {
    "correctness": 30,
    "autonomy": 25,
    "throughput": 15,
    "portability": 15,
    "operator_experience": 15,
}


def score(scorecard):
    failures = scorecard.get("hard_gate_failures", [])
    if failures:
        return {"status": "DISQUALIFIED", "hard_gate_failures": failures}

    scores = scorecard.get("scores", {})
    missing = sorted(set(WEIGHTS) - set(scores))
    if missing:
        raise ValueError(f"missing scores: {', '.join(missing)}")
    invalid = {name: value for name, value in scores.items() if not 0 <= value <= 100}
    if invalid:
        raise ValueError(f"scores must be between 0 and 100: {invalid}")

    weighted = sum(scores[name] * weight for name, weight in WEIGHTS.items()) / 100
    hours = float(scorecard.get("active_operator_hours", 0))
    correct_prs = float(scorecard.get("correct_maintainable_draft_prs", 0))
    yield_per_hour = correct_prs / hours if hours > 0 else 0.0
    return {
        "status": "QUALIFIED_FOR_COMPARISON",
        "weighted_score": round(weighted, 2),
        "correct_prs_per_active_operator_hour": round(yield_per_hour, 4),
        "weights": WEIGHTS,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", required=True)
    args = parser.parse_args()
    with open(args.scorecard, encoding="utf-8") as handle:
        scorecard = json.load(handle)
    try:
        result = score(scorecard)
    except (TypeError, ValueError) as exc:
        print(f"Invalid scorecard: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
