import json
import os
import subprocess
import tempfile
from pathlib import Path

from src.api_contract import analyze_contracts
from src.compliance_rules import analyze_compliance
from src.dependency_graph import build_dependency_graph
from src.impact_analyzer import generate_impact_report
from src.service_detector import detect_service_references


REPORT_PATH = Path("reports/preflight_report.json")


def git_text(*args):
    """Run a Git command and return its text output."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_pr_event():
    """Read GitHub Actions pull-request event metadata."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not event_path or not Path(event_path).is_file():
        return None

    with open(event_path, "r", encoding="utf-8") as file:
        event = json.load(file)

    if not event.get("pull_request"):
        return None

    return event


def get_changed_files(base_sha, head_sha):
    """Return added, modified, deleted, and renamed file changes."""
    output = git_text(
        "diff", "--name-status", "-M", base_sha, head_sha
    )

    changes = []

    for line in output.splitlines():
        fields = line.split("\t")
        if not fields:
            continue

        status = fields[0]

        if status.startswith("R") or status.startswith("C"):
            if len(fields) >= 3:
                changes.append({
                    "status": status,
                    "old_path": fields[1],
                    "new_path": fields[2],
                })
        elif len(fields) >= 2:
            path = fields[1]
            changes.append({
                "status": status,
                "old_path": None if status.startswith("A") else path,
                "new_path": None if status.startswith("D") else path,
            })

    return changes


def read_commit_file(commit, file_path):
    """Read a file from a specific commit, not the working tree."""
    return git_text("show", f"{commit}:{file_path}")


def is_openapi_file(file_path):
    """Recognize likely OpenAPI or Swagger specification files."""
    if not file_path:
        return False

    path = Path(file_path)
    name = path.name.lower()

    return (
        "openapi" in name
        or "swagger" in name
        or name.startswith("asyncapi")
        or name.endswith((".openapi.yaml", ".openapi.json"))
    )


def write_temp_file(content, original_path):
    """Create a temporary file with a useful extension."""
    suffix = Path(original_path).suffix or ".txt"

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=suffix,
        delete=False,
    ) as file:
        file.write(content)
        return Path(file.name)


def analyze_pull_request(event):
    """Analyze files from the actual PR base and head commits."""
    pr = event["pull_request"]
    base_sha = pr["base"]["sha"]
    head_sha = pr["head"]["sha"]
    pr_number = event.get("number")

    changes = get_changed_files(base_sha, head_sha)

    contract_findings = []
    compliance_findings = []
    analysis_errors = []
    deleted_or_renamed_specs = []

    print(f"Analyzing pull request #{pr_number}")
    print(f"Base commit: {base_sha}")
    print(f"Head commit: {head_sha}")

    with tempfile.TemporaryDirectory(prefix="preflight-") as temp_dir:
        temp_root = Path(temp_dir)

        for change in changes:
            status = change["status"]
            old_path = change["old_path"]
            new_path = change["new_path"]

            print(
                f"[{status}] "
                f"{old_path or '(new file)'}"
                + (
                    f" -> {new_path}"
                    if new_path and new_path != old_path
                    else ""
                )
            )

            # Analyze changed OpenAPI specifications.
            if is_openapi_file(old_path) or is_openapi_file(new_path):
                if not new_path:
                    deleted_or_renamed_specs.append({
                        "status": status,
                        "path": old_path,
                        "message": (
                            "OpenAPI specification was deleted; "
                            "review API compatibility."
                        ),
                    })
                    continue

                try:
                    new_content = read_commit_file(head_sha, new_path)
                except subprocess.CalledProcessError as exc:
                    analysis_errors.append({
                        "file": new_path,
                        "analyzer": "api_contract",
                        "error": exc.stderr.strip()
                        or "Could not read the PR version of the file.",
                    })
                    continue

                if not old_path:
                    contract_findings.append({
                        "severity": "REVIEW",
                        "type": "API_SPEC_ADDED",
                        "file": new_path,
                        "message": (
                            "A new API specification was added. "
                            "No previous version exists at this path "
                            "to compare."
                        ),
                    })
                    continue

                try:
                    old_content = read_commit_file(base_sha, old_path)
                except subprocess.CalledProcessError:
                    contract_findings.append({
                        "severity": "REVIEW",
                        "type": "API_BASE_VERSION_UNAVAILABLE",
                        "file": new_path,
                        "message": (
                            "The base version of this API specification "
                            "could not be retrieved for comparison."
                        ),
                    })
                    continue

                old_temp = None
                new_temp = None

                try:
                    old_temp = write_temp_file(
                        old_content, old_path
                    )
                    new_temp = write_temp_file(
                        new_content, new_path
                    )

                    findings = analyze_contracts(
                        str(old_temp), str(new_temp)
                    )

                    for finding in findings:
                        finding["file"] = new_path

                    contract_findings.extend(findings)

                except Exception as exc:
                    analysis_errors.append({
                        "file": new_path,
                        "analyzer": "api_contract",
                        "error": str(exc),
                    })
                finally:
                    for temp_file in (old_temp, new_temp):
                        if temp_file:
                            temp_file.unlink(missing_ok=True)

            # Scan the PR version of changed Python files.
            if new_path and new_path.lower().endswith(".py"):
                try:
                    content = read_commit_file(head_sha, new_path)
                    temp_file = write_temp_file(
                        content, new_path
                    )

                    try:
                        findings = analyze_compliance(str(temp_file))

                        for finding in findings:
                            finding["file"] = new_path

                        compliance_findings.extend(findings)
                    finally:
                        temp_file.unlink(missing_ok=True)

                except Exception as exc:
                    analysis_errors.append({
                        "file": new_path,
                        "analyzer": "compliance",
                        "error": str(exc),
                    })

    summary = {
        "changed_files": len(changes),
        "contract_findings": len(contract_findings),
        "compliance_findings": len(compliance_findings),
        "analysis_errors": len(analysis_errors),
        "human_review_required": bool(
            contract_findings
            or compliance_findings
            or analysis_errors
            or deleted_or_renamed_specs
        ),
    }

    return {
        "project": "Preflight-CI",
        "mode": "github_pull_request",
        "pull_request": {
            "number": pr_number,
            "base_sha": base_sha,
            "head_sha": head_sha,
        },
        "changed_files": changes,
        "api_contract": {
            "findings": contract_findings,
            "deleted_or_renamed_specs": deleted_or_renamed_specs,
        },
        "compliance_findings": compliance_findings,
        "downstream_impact": {
            "status": "not_analyzed",
            "reason": (
                "Real-PR service ownership and dependency mapping "
                "are not yet connected."
            ),
        },
        "analysis_errors": analysis_errors,
        "summary": summary,
        "limitations": [
            "Compliance checks inspect the full contents of changed "
            "Python files, so findings are not necessarily introduced "
            "by the PR.",
            "New API specifications have no previous version to compare.",
            "Downstream impact is not yet calculated from real PR files.",
            "Compliance findings are review signals, not confirmed violations.",
        ],
    }


def analyze_local_demo():
    """Keep the existing sample-based demo available locally."""
    old_spec = "contracts/openapi.yaml"
    new_spec = "contracts/openapi_v2.yaml"
    compliance_file = "tests/sample_sensitive_code.py"
    dependency_file = "tests/sample_banking_services.py"
    changed_service = "fraud-service.internal"

    for filename in (
        old_spec,
        new_spec,
        compliance_file,
        dependency_file,
    ):
        if not Path(filename).is_file():
            raise FileNotFoundError(
                f"Required demo input not found: {filename}"
            )

    contract_findings = analyze_contracts(old_spec, new_spec)

    references = detect_service_references(dependency_file)
    graph = build_dependency_graph("payment-service", references)

    impact = generate_impact_report(
        changed_service=changed_service,
        findings=contract_findings,
        graph=graph,
    )

    compliance_findings = analyze_compliance(compliance_file)

    return {
        "project": "Preflight-CI",
        "mode": "local_demo",
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
            "This is a sample-based local demonstration, not a PR analysis.",
            "The changed service is configured for this demonstration.",
            "Compliance findings are review signals, not confirmed violations.",
        ],
    }


def main():
    event = get_pr_event()

    if event:
        report = analyze_pull_request(event)
    else:
        print("No GitHub PR event found; running local demo mode.")
        report = analyze_local_demo()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nPreflight-CI Report")
    print("=" * 35)
    print(json.dumps(report["summary"], indent=2))
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()