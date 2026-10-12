
from src.api_contract import analyze_contracts
from src.dependency_graph import build_dependency_graph
from src.service_detector import detect_service_references
from src.impact_analyzer import (
    find_affected_consumers,
    generate_impact_report,
    print_impact_report,
)

# Build the graph from our existing banking example.
references = detect_service_references(
    "tests/sample_banking_services.py"
)

graph = build_dependency_graph("payment-service", references)

# The modified specification removes transaction_id
# from the payment API response.
findings = analyze_contracts(
    "contracts/openapi.yaml",
    "contracts/openapi_v2.yaml",
)

# Simulate a change in the fraud service API.
changed_service = "fraud-service.internal"

affected = find_affected_consumers(graph, changed_service)

print("Affected consumers:", affected)

report = generate_impact_report(
    changed_service,
    findings,
    graph,
)

print()
print_impact_report(report)
