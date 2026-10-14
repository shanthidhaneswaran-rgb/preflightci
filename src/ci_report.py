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
TEST_DIR_NAMES = {"test", "tests", "__tests__", "fixtures", "samples"}
TEST_FILE_PREFIXES = ("test_",)
TEST_FILE_SUFFIXES = ("_test.py", ".spec.py", ".test.py")


def git_text(*args):
    """Run a Git command and return stdout."""
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    )
    return result.stdout


def get_pr_event():
    """Return GitHub pull-request event data, or None outside PR Actions."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).is_file():
        return None
    try:
        with open(event_path, "r", encoding="utf-8") as file:
            event = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read GitHub event file: {exc}")
        return None
    return event if isinstance(event, dict) and event.get("pull_request") else None


def get_changed_files(base_sha, head_sha):
    """Return changed paths with status and old/new path for renames."""
    output = git_text("diff", "--name-status", "-M", base_sha, head_sha)
    changes = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        if status.startswith(("R", "C")) and len(fields) >= 3:
            changes.append({
                "status": status, "old_path": fields[1], "new_path": fields[2]
            })
        else:
            path = fields[1]
            changes.append({
                "status": status,
                "old_path": None if status.startswith("A") else path,
                "new_path": None if status.startswith("D") else path,
            })
    return changes


def read_commit_file(commit, file_path):
    """Read a file from a specific Git commit."""
    return git_text("show", f"{commit}:{file_path}")


def is_openapi_file(file_path):
    """Recognize likely OpenAPI, Swagger, or AsyncAPI specification files."""
    if not file_path:
        return False
    name = Path(file_path).name.lower()
    return (
        "openapi" in name
        or "swagger" in name
        or name.startswith("asyncapi")
        or name.endswith((".openapi.yaml", ".openapi.yml", ".openapi.json"))
    )


def is_test_or_fixture_path(file_path):
    """Return True for test, fixture, and sample paths/files."""
    if not file_path:
        return False
    path = Path(file_path)
    lower_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return (
        bool(lower_parts & TEST_DIR_NAMES)
        or name.startswith(TEST_FILE_PREFIXES)
        or name.endswith(TEST_FILE_SUFFIXES)
    )


def write_temp_file(content, original_path):
    """Write content to a temporary file while retaining its extension."""
    suffix = Path(original_path).suffix or ".txt"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=suffix, delete=False
    ) as file:
        file.write(content)
        return Path(file.name)


def add_finding_file(findings, file_path):
    """Attach the source file to each finding without mutating analyzer output."""
    tagged = []
    for finding in findings:
        item = dict(finding)
        item["file"] = file_path
        tagged.append(item)
    return tagged


def analyze_pull_request(event):
    """Analyze files changed between the pull-request base and head commits."""
    pr = event["pull_request"]
    base_sha = pr.get("base", {}).get("sha")
    head_sha = pr.get("head", {}).get("sha")
    pr_number = event.get("number")
    if not base_sha or not head_sha:
        raise ValueError("Pull-request event is missing base or head SHA.")

    changes = get_changed_files(base_sha, head_sha)
    contract_findings = []
    compliance_findings = []
    analysis_errors = []
    spec_review_items = []
    skipped_test_python_files = []

    print(f"Analyzing pull request #{pr_number}")
    print(f"Base commit: {base_sha}")
    print(f"Head commit: {head_sha}")

    for change in changes:
        status = change["status"]
        old_path = change["old_path"]
        new_path = change["new_path"]
        print(
            f"[{status}] {old_path or '(new file)'}"
            + (f" -> {new_path}" if new_path and new_path != old_path else "")
        )

        # Compare an API specification only when both versions exist.
        if is_openapi_file(old_path) or is_openapi_file(new_path):
            if not new_path:
                spec_review_items.append({
                    "status": status,
                    "path": old_path,
                    "type": "API_SPEC_DELETED",
                    "message": (
                        "The API specification was deleted. Review whether "
                        "the API is intentionally retired and consumers are affected."
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
                    or "Could not read the specification from the PR head.",
                })
                continue

            if not old_path:
                # Informational only: this is not a confirmed breaking change.
                spec_review_items.append({
                    "status": status,
                    "path": new_path,
                    "type": "API_SPEC_ADDED",
                    "message": (
                        "A new API specification was added. It has no prior "
                        "version at this path, so backward compatibility could "
                        "not be compared."
                    ),
                })
                continue

            try:
                old_content = read_commit_file(base_sha, old_path)
            except subprocess.CalledProcessError:
                spec_review_items.append({
                    "status": status,
                    "path": new_path,
                    "type": "API_BASE_VERSION_UNAVAILABLE",
                    "message": (
                        "The base version could not be retrieved; no breaking-"
                        "change comparison was performed."
                    ),
                })
                continue

            old_temp = None
            new_temp = None
            try:
                old_temp = write_temp_file(old_content, old_path)
                new_temp = write_temp_file(new_content, new_path)
                findings = analyze_contracts(str(old_temp), str(new_temp))
                contract_findings.extend(add_finding_file(findings, new_path))
            except Exception as exc:
                analysis_errors.append({
                    "file": new_path, "analyzer": "api_contract", "error": str(exc)
                })
            finally:
                for temp_file in (old_temp, new_temp):
                    if temp_file:
                        temp_file.unlink(missing_ok=True)

        # Scan changed production Python files, not test/demo fixtures.
        if new_path and new_path.lower().endswith(".py"):
            if is_test_or_fixture_path(new_path):
                skipped_test_python_files.append(new_path)
                continue
            try:
                content = read_commit_file(head_sha, new_path)
                temp_file = write_temp_file(content, new_path)
                try:
                    findings = analyze_compliance(str(temp_file))
                    compliance_findings.extend(
                        add_finding_file(findings, new_path)
                    )
                finally:
                    temp_file.unlink(missing_ok=True)
            except Exception as exc:
                analysis_errors.append({
                    "file": new_path, "analyzer": "compliance", "error": str(exc)
                })

    summary = {
        "changed_files": len(changes),
        "contract_findings": len(contract_findings),
        "compliance_findings": len(compliance_findings),
        "api_spec_review_items": len(spec_review_items),
        "analysis_errors": len(analysis_errors),
        "human_review_required": bool(
            contract_findings or compliance_findings
            or spec_review_items or analysis_errors
        ),
    }
    return {
        "project": "Preflight-CI",
        "mode": "github_pull_request",
        "pull_request": {
            "number": pr_number, "base_sha": base_sha, "head_sha": head_sha
        },
        "changed_files": changes,
        "api_contract": {
            "findings": contract_findings,
            "review_items": spec_review_items,
        },
        "compliance_findings": compliance_findings,
        "skipped_test_python_files": skipped_test_python_files,
        "downstream_impact": {
            "status": "not_analyzed",
            "reason": (
                "Real-PR service ownership and dependency mapping are not yet "
                "connected. The local demo still shows the sample graph."
            ),
        },
        "analysis_errors": analysis_errors,
        "summary": summary,
        "limitations": [
            "Compliance scans inspect full changed production Python files, so "
            "findings may predate the PR.",
            "New API specifications are informational because no prior version "
            "exists at the same path for comparison.",
            "Deleted API specifications are flagged for manual review.",
            "Downstream impact is not yet calculated from real PR changes.",
            "Compliance findings are review signals, not confirmed violations.",
        ],
    }


def analyze_local_demo():
    """Run the original sample-based demo locally."""
    old_spec = "contracts/openapi.yaml"
    new_spec = "contracts/openapi_v2.yaml"
    compliance_file = "tests/sample_sensitive_code.py"
    dependency_file = "tests/sample_banking_services.py"
    changed_service = "fraud-service.internal"

    for filename in (old_spec, new_spec, compliance_file, dependency_file):
        if not Path(filename).is_file():
            raise FileNotFoundError(f"Required demo input not found: {filename}")

    contract_findings = analyze_contracts(old_spec, new_spec)
    references = detect_service_references(dependency_file)
    graph = build_dependency_graph("payment-service", references)
    impact = generate_impact_report(
        changed_service=changed_service, findings=contract_findings, graph=graph
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
            "affected_consumers": len(impact["affected_consumers"]),
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
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nPreflight-CI Report")
    print("=" * 35)
    print(json.dumps(report["summary"], indent=2))
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
