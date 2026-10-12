
import json
from pathlib import Path

from src.api_contract import analyze_contracts
from src.compliance_rules import analyze_compliance
from src.dependency_graph import build_dependency_graph
from src.impact_analyzer import generate_impact_report
from src.service_detector import detect_service_references


def main():
    old_spec = "contracts/openapi.yaml"
    new_spec = "contracts/openapi_v2.yaml"
    compliance_file = "tests/sample_sensitive_code.py"
    dependency_file = "tests/sample_banking_services.py"
    changed_service = "fraud-service.internal"

    inputs = [
        old_spec,
        new_spec,
        compliance_file,
        dependency_file,
    ]

    for filename in inputs:
        if not Path(filename).is_file():
            raise FileNotFoundError(f"Required input not found: {filename}")

    # 1. Compare API specifications.
    contract_findings = analyze_contracts(old_spec, new_spec)

    # 2. Build the service dependency graph.
    references = detect_service_references(dependency_file)
    graph = build_dependency_graph("payment-service", references)

    # 3. Calculate potential downstream impact.
    impact = generate_impact_report(
        changed_service=changed_service,
        findings=contract_findings,
        graph=graph,
    )

    # 4. Run deterministic compliance checks.
    compliance_findings = analyze_compliance(compliance_file)

    report = {
        "project": "Preflight-CI",
        "mode": "github_actions_without_local_llm",
        "api_contract": {
            "findings": contract_findings,
            "impact": impact,
            "graph_nodes": sorted(graph["nodes"]),
            "graph_edges": graph["edges"],
        },
        "compliance_findings": compliance_findings,
        "summary": {
            "contract_findings": len(contract_findings),
            "compliance_findings": len(compliance_findings),
            "affected_consumers": len(
                impact["affected_consumers"]
            ),
            "impact_risk_level": impact["risk_level"],
            "human_review_required": bool(
                contract_findings or compliance_findings
            ),
        },
        "limitations": [
            "Local Ollama LLM review is not run in GitHub Actions.",
            "The changed service is configured for this demonstration.",
            "Compliance findings are review signals, not confirmed violations.",
        ],
    }

    output_path = Path("reports/preflight_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("Preflight-CI CI Report")
    print("=" * 35)
    print(json.dumps(report["summary"], indent=2))
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
