
import json
import sys
from pathlib import Path

from src.compliance_rules import analyze_compliance
from src.llm_reviewer import review_finding


def run_review(file_path):
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Python file not found: {path}")

    findings = analyze_compliance(path)

    print("Preflight-CI Compliance Review")
    print("=" * 55)
    print(f"File: {path}")
    print(f"Potential findings detected: {len(findings)}")

    if not findings:
        print("\nNo matching patterns found.")
        return

    for index, finding in enumerate(findings, start=1):
        # Add the rule ID so the LLM receives the scanner's rule name.
        finding["type"] = finding["rule_id"]

        # Do not treat a heuristic scanner severity as a confirmed
        # regulatory or security conclusion.
        print(f"\nReviewing finding {index}/{len(findings)}...")

        report = review_finding(finding)
        llm_review = report["llm_review"]

        # Require human review for every heuristic compliance finding.
        llm_review["needs_human_review"] = True

        print("\n" + "-" * 55)
        print(f"Finding: {finding['rule_id']}")
        print(f"Location: {finding['file']}:{finding['line']}")
        print("LLM review:")
        print(json.dumps(llm_review, indent=2))

    print("\n" + "=" * 55)
    print("Review complete. Human verification is required.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python -m src.run_compliance_review "
            "<python_file>"
        )
        raise SystemExit(1)

    try:
        run_review(sys.argv[1])
    except Exception as exc:
        print(f"Review failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
