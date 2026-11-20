
import argparse
import json
from pathlib import Path

from src.api_contract import analyze_contracts
from src.compliance_rules import analyze_compliance
from src.dependency_graph import build_dependency_graph
from src.impact_analyzer import generate_impact_report
from src.llm_reviewer import review_finding
from src.service_detector import detect_service_references


def analyze_contract_impact(
    old_spec,
    new_spec,
    dependency_file,
    changed_service,
):
    """Compare API specifications and calculate dependency impact."""

    # 1. Detect API contract changes.
    contract_findings = analyze_contracts(old_spec, new_spec)

    # 2. Detect outgoing HTTP calls from the payment service.
    references = detect_service_references(dependency_file)
    graph = build_dependency_graph("payment-service", references)

    # 3. Find services that depend on the configured changed service.
    impact = generate_impact_report(
        changed_service=changed_service,
        findings=contract_findings,
        graph=graph,
    )

    return {
        "findings": contract_findings,
        "impact": impact,
        "graph_nodes": sorted(graph["nodes"]),
        "graph_edges": graph["edges"],
        "note": (
            "The dependency graph is extracted from static HTTP calls. "
            "The changed service is configured by the user. "
            "Automatic mapping between an OpenAPI specification and "
            "its owning service has not been implemented."
        ),
    }


def analyze_compliance_with_llm(source_file):
    """Scan source code and review findings using local LLM + RAG."""

    findings = analyze_compliance(source_file)
    reviewed_findings = []

    for finding in findings:
        llm_input = {
            **finding,
            "type": finding.get("rule_id", "UNKNOWN"),
        }

        # Retrieve policy evidence and obtain a local LLM review.
        result = review_finding(llm_input)

        llm_review = result.get("llm_review", {})

        # Potential compliance findings always require human review.
        llm_review["needs_human_review"] = True

        reviewed_findings.append(
            {
                "scanner_finding": finding,
                "policy_evidence": result.get("policy_evidence", []),
                "llm_review": llm_review,
            }
        )

    return reviewed_findings


def build_combined_report(
    old_spec,
    new_spec,
    source_file,
    dependency_file,
    changed_service="fraud-service.internal",
):
    """Run all Preflight-CI checks and assemble a combined report."""

    contract_result = analyze_contract_impact(
        old_spec=old_spec,
        new_spec=new_spec,
        dependency_file=dependency_file,
        changed_service=changed_service,
    )

    compliance_results = analyze_compliance_with_llm(source_file)

    impact = contract_result["impact"]

    return {
        "project": "Preflight-CI",
        "inputs": {
            "old_openapi_spec": str(old_spec),
            "new_openapi_spec": str(new_spec),
            "compliance_source_file": str(source_file),
            "dependency_source_file": str(dependency_file),
            "configured_changed_service": changed_service,
        },
        "api_contract": contract_result,
        "compliance_reviews": compliance_results,
        "summary": {
            "contract_findings": len(contract_result["findings"]),
            "compliance_findings": len(compliance_results),
            "affected_consumers": len(impact["affected_consumers"]),
            "impact_risk_level": impact["risk_level"],
            "human_review_required": bool(compliance_results),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate a combined Preflight-CI analysis report."
    )

    parser.add_argument(
        "--old-spec",
        default="contracts/openapi.yaml",
        help="Path to the previous OpenAPI specification.",
    )
    parser.add_argument(
        "--new-spec",
        default="contracts/openapi_v2.yaml",
        help="Path to the proposed OpenAPI specification.",
    )
    parser.add_argument(
        "--source-file",
        default="tests/sample_sensitive_code.py",
        help="Python file to scan for potential compliance issues.",
    )
    parser.add_argument(
        "--dependency-file",
        default="tests/sample_banking_services.py",
        help="Python file containing service calls for dependency analysis.",
    )
    parser.add_argument(
        "--changed-service",
        default="fraud-service.internal",
        help="Service whose downstream consumers should be identified.",
    )
    parser.add_argument(
        "--output",
        default="reports/preflight_report.json",
        help="Path for the generated JSON report.",
    )

    args = parser.parse_args()

    # Validate all input files before starting the analysis.
    input_files = {
        "old OpenAPI specification": args.old_spec,
        "new OpenAPI specification": args.new_spec,
        "compliance source file": args.source_file,
        "dependency source file": args.dependency_file,
    }

    for description, filename in input_files.items():
        if not Path(filename).is_file():
            parser.error(
                f"The {description} does not exist: {filename}"
            )

    try:
        report = build_combined_report(
            old_spec=args.old_spec,
            new_spec=args.new_spec,
            source_file=args.source_file,
            dependency_file=args.dependency_file,
            changed_service=args.changed_service,
        )
    except Exception as exc:
        parser.exit(
            status=1,
            message=f"Preflight-CI analysis failed: {exc}\n",
        )

    output_path = Path(args.output)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        parser.exit(
            status=1,
            message=f"Could not write report to {output_path}: {exc}\n",
        )

    summary = report["summary"]

    print("\nPreflight-CI Combined Report")
    print("=" * 45)
    print(f"API contract findings: {summary['contract_findings']}")
    print(f"Compliance findings: {summary['compliance_findings']}")
    print(f"Affected consumers: {summary['affected_consumers']}")
    print(f"Impact risk level: {summary['impact_risk_level']}")
    print(
        "Human review required: "
        f"{summary['human_review_required']}"
    )
    print(f"JSON report saved to: {output_path}")


if __name__ == "__main__":
    main()
