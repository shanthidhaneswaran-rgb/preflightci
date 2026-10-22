
from collections import defaultdict

from src.service_detector import detect_service_references


def build_dependency_graph(source_service, references):
    """
    Build a directed graph from a source service to its
    referenced downstream services.
    """
    graph = {
        "nodes": set(),
        "edges": [],
    }

    graph["nodes"].add(source_service)

    for reference in references:
        downstream_service = reference["host"]

        graph["nodes"].add(downstream_service)

        graph["edges"].append({
            "source": source_service,
            "target": downstream_service,
            "method": reference["method"],
            "url": reference["url"],
            "file": reference["file"],
            "line": reference["line"],
        })

    return graph


def find_downstream_services(graph, service):
    """Find direct downstream services called by a service."""
    return sorted({
        edge["target"]
        for edge in graph["edges"]
        if edge["source"] == service
    })


def print_dependency_graph(graph):
    """Display the graph in a readable format."""
    print("Dependency Graph")
    print("================")

    print("\nServices:")
    for node in sorted(graph["nodes"]):
        print(f"  - {node}")

    print("\nConnections:")
    if not graph["edges"]:
        print("  No service connections found.")
        return

    for edge in graph["edges"]:
        print(
            f"  {edge['source']} "
            f"--[{edge['method']}]--> "
            f"{edge['target']}"
        )
        print(f"    URL: {edge['url']}")
        print(f"    Location: {edge['file']}:{edge['line']}")


def main():
    sample_file = "tests/sample_banking_services.py"
    source_service = "payment-service"

    references = detect_service_references(sample_file)

    graph = build_dependency_graph(source_service, references)

    print_dependency_graph(graph)

    print("\nDirect downstream services:")
    for service in find_downstream_services(graph, source_service):
        print(f"  - {service}")


if __name__ == "__main__":
    main()
