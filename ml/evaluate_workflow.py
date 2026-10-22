#!/usr/bin/env python3
"""Honest fixture-based evaluation; measures rule completeness, not clinical accuracy."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from careflow.agents import investigate
from careflow.fixtures import CASES

EXPECTED = {"CASE-1001": {"RECORD_CONFLICT", "FOLLOWUP_UNCONFIRMED", "RESULT_OWNER_MISSING"},
            "CASE-1002": {"NO_ADMIN_ISSUES"},
            "CASE-1003": {"FOLLOWUP_UNCONFIRMED"},
            "CASE-1004": {"FOLLOWUP_UNCONFIRMED"},
            "CASE-1005": {"NO_ADMIN_ISSUES"}}


def evaluate():
    results=[]
    for item in CASES:
        actual=investigate(item["record"])
        predicted={x["code"] for x in actual["findings"]}
        required=EXPECTED[item["external_ref"]]
        match=predicted==required
        results.append({"case":item["external_ref"],"expected":sorted(required),"observed":sorted(predicted),
                        "exact_match":match,"cited":all(bool(f["evidence_ids"]) for f in actual["findings"]),
                        "execution_mode":actual["execution_mode"]})
    return {"fixture_cases":len(results), "exact_match_fraction":sum(x["exact_match"] for x in results)/len(results),
            "scope":"synthetic fixture acceptance checks; not independent clinical validation", "cases":results}

if __name__=='__main__':
    report=evaluate()
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if all(item["exact_match"] for item in report["cases"]) else 1)
