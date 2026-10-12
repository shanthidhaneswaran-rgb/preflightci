
def find_affected_consumers(graph, changed_service):
    """
    Find services that call the changed service, including
    indirect consumers through the dependency graph.
    """
    affected = set()
    visited = set()
    pending = [changed_service]

    while pending:
        current_service = pending.pop()

        if current_service in visited:
            continue

        visited.add(current_service)

        for edge in graph["edges"]:
            if edge["target"] == current_service:
                consumer = edge["source"]

                if consumer not in affected:
                    affected.add(consumer)
                    pending.append(consumer)

    return sorted(affected)


def generate_impact_report(changed_service, findings, graph):
    """Combine API contract findings with dependency information."""
    affected = find_affected_consumers(graph, changed_service)

    report = {
        "changed_service": changed_service,
        "contract_findings": findings,
        "affected_consumers": affected,
        "risk_level": "HIGH" if findings and affected else (
            "REVIEW" if findings else "NONE"
        ),
    }

    return report


def print_impact_report(report):
    """Print a readable impact report."""
    print("Preflight-CI Impact Report")
    print("==========================")
    print(f"Changed service: {report['changed_service']}")
    print(f"Risk level: {report['risk_level']}")

    print("\nAPI contract findings:")
    if report["contract_findings"]:
        for finding in report["contract_findings"]:
            print(
                f"  [{finding['severity']}] "
                f"{finding['type']}: {finding['message']}"
            )
    else:
        print("  No contract findings.")

    print("\nPotentially affected consumers:")
    if report["affected_consumers"]:
        for service in report["affected_consumers"]:
            print(f"  - {service}")
    else:
        print("  No consumers identified by the current graph.")
