
import json
from pathlib import Path

from src.service_detector import detect_service_references


SERVICE_MAP_PATH = Path("config/service_map.json")

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "tests",
    "test",
    "fixtures",
    "samples",
}


def load_service_map(path=SERVICE_MAP_PATH):
    """Load explicit service ownership and host mappings."""
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    services = data.get("services", [])

    if not isinstance(services, list):
        raise ValueError("'services' must be a list")

    names = set()

    for service in services:
        if not isinstance(service, dict) or not service.get("name"):
            raise ValueError("Each service must be an object with a name")

        name = service["name"]

        if name in names:
            raise ValueError(f"Duplicate service name: {name}")

        names.add(name)

        for field in ("specs", "source_paths", "hosts"):
            if field in service and not isinstance(service[field], list):
                raise ValueError(
                    f"Service '{name}': '{field}' must be a list"
                )

    return services


def discover_python_files(root=Path(".")):
    """Find Python source files, excluding tests and generated folders."""
    root = Path(root)

    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part.lower() in IGNORED_DIRS for part in path.parts)
    )


def identify_source_service(file_path, services):
    """Identify ownership using configured spec paths or source directories."""
    normalized_path = (
        Path(file_path).as_posix().lower().lstrip("./")
    )

    for service in services:
        for spec in service.get("specs", []):
            mapped_spec = (
                spec.replace("\\", "/").lower().lstrip("./")
            )

            if normalized_path == mapped_spec:
                return service["name"]

        for source_path in service.get("source_paths", []):
            mapped_dir = (
                source_path.replace("\\", "/").lower().strip("/")
            )

            if (
                normalized_path == mapped_dir
                or normalized_path.startswith(mapped_dir + "/")
            ):
                return service["name"]

    return None


def analyze_repository_impact(
    changed_paths,
    root=Path("."),
    service_map_path=SERVICE_MAP_PATH,
):
    """
    Identify potential consumers of changed services using statically
    detectable HTTP calls and explicit service ownership mappings.

    This is repository-wide static analysis, not proof of runtime impact.
    """
    root = Path(root)
    services = load_service_map(service_map_path)

    host_to_service = {}

    for service in services:
        for host in service.get("hosts", []):
            normalized_host = host.lower().strip()
            existing = host_to_service.get(normalized_host)

            if existing and existing != service["name"]:
                raise ValueError(
                    f"Host '{normalized_host}' maps to multiple services: "
                    f"{existing}, {service['name']}"
                )

            host_to_service[normalized_host] = service["name"]

    changed_services = set()
    unresolved_changed_paths = []

    for changed_path in changed_paths:
        owner = identify_source_service(changed_path, services)

        if owner:
            changed_services.add(owner)
        elif changed_path:
            unresolved_changed_paths.append(changed_path)

    edges = []
    scanned_files = []
    scan_errors = []

    for file_path in discover_python_files(root):
        relative_path = file_path.relative_to(root).as_posix()
        scanned_files.append(relative_path)

        try:
            references = detect_service_references(file_path)
        except (OSError, SyntaxError, UnicodeError) as exc:
            scan_errors.append({
                "file": relative_path,
                "error": str(exc),
            })
            continue

        consumer = identify_source_service(relative_path, services)

        # Without explicit ownership, do not guess which service made the call.
        if not consumer:
            continue

        for reference in references:
            target = host_to_service.get(reference["host"].lower())

            # Ignore calls to hosts that are not in the service map.
            if not target:
                continue

            # A service calling itself is not a downstream dependency.
            if consumer == target:
                continue

            edges.append({
                "source": consumer,
                "target": target,
                "method": reference["method"],
                "url": reference["url"],
                "host": reference["host"],
                "path": reference.get("path", "/"),
                "file": relative_path,
                "line": reference["line"],
            })

    # Deduplicate dependency evidence.
    unique_edges = []
    seen_edges = set()

    for edge in edges:
        key = (
            edge["source"],
            edge["target"],
            edge["method"],
            edge["url"],
            edge["file"],
            edge["line"],
        )

        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)

    edges = unique_edges
    affected_services = []

    for changed_service in sorted(changed_services):
        consumers = set()
        pending = [changed_service]
        visited = set()

        # Walk backward: a service calling the changed service is a consumer.
        while pending:
            current = pending.pop()

            if current in visited:
                continue

            visited.add(current)

            for edge in edges:
                if edge["target"] != current:
                    continue

                consumer = edge["source"]

                # Exclude self-dependencies and the changed service itself,
                # including when the graph contains a cycle.
                if consumer == current or consumer == changed_service:
                    continue

                if consumer not in consumers:
                    consumers.add(consumer)
                    pending.append(consumer)

        evidence = [
            edge
            for edge in edges
            if edge["target"] in visited
            and edge["source"] in consumers
        ]

        affected_services.append({
            "changed_service": changed_service,
            "affected_consumers": sorted(consumers),
            "evidence": evidence,
        })

    if not changed_services:
        status = "unknown"
        reason = (
            "Changed files could not be mapped to a service using the "
            "configured service map. No service impact is inferred."
        )
    elif any(
        item["affected_consumers"]
        for item in affected_services
    ):
        status = "analyzed"
        reason = (
            "Potential consumers were identified from statically detected "
            "HTTP calls and explicit service ownership mappings."
        )
    else:
        status = "no_known_consumers"
        reason = (
            "No downstream consumers were identified using the current "
            "static scan and service map. Dynamic calls and unconfigured "
            "services may be missed."
        )

    if scan_errors:
        reason += (
            f" {len(scan_errors)} file(s) could not be scanned; "
            "review scan_errors."
        )

    return {
        "status": status,
        "reason": reason,
        "changed_services": sorted(changed_services),
        "affected_services": affected_services,
        "unresolved_changed_paths": unresolved_changed_paths,
        "scanned_files": scanned_files,
        "dependency_edges": edges,
        "scan_errors": scan_errors,
    }
