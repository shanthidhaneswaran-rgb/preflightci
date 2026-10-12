
import json
import os
import subprocess
from pathlib import Path


def get_pr_event():
    """Read GitHub pull request event information."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not event_path:
        print("Running outside GitHub Actions.")
        return None

    with open(event_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_git_diff(base_sha, head_sha):
    """Get changed files and the actual diff."""
    files_result = subprocess.run(
        ["git", "diff", "--name-status", base_sha, head_sha],
        capture_output=True,
        text=True,
        check=True,
    )

    diff_result = subprocess.run(
        ["git", "diff", base_sha, head_sha],
        capture_output=True,
        text=True,
        check=True,
    )

    return files_result.stdout.strip(), diff_result.stdout


def classify_file(file_path):
    """Classify a changed file by its path and extension."""
    path = Path(file_path)
    name = path.name.lower()
    suffix = path.suffix.lower()
    parts = {part.lower() for part in path.parts}

    # API specifications and schemas
    if (
        name.startswith(("openapi", "swagger", "asyncapi"))
        or name.endswith((".openapi.json", ".openapi.yaml"))
        or "openapi" in name
        or "swagger" in name
    ):
        return "API contract"

    # Tests
    if (
        "tests" in parts
        or "test" in parts
        or name.startswith("test_")
        or name.endswith(("_test.py", ".spec.ts", ".test.ts"))
    ):
        return "Tests"

    # Documentation
    if (
        "docs" in parts
        or suffix in {".md", ".rst"}
        or name in {"license", "changelog"}
    ):
        return "Documentation"

    # Configuration and CI/CD
    if (
        ".github" in parts
        or name in {
            "dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "requirements.txt",
            "pyproject.toml",
            "setup.cfg",
            "makefile",
        }
        or suffix in {".yaml", ".yml", ".toml", ".ini"}
        or name.endswith(".env.example")
    ):
        return "Configuration / CI"

    # Application source code
    if suffix in {
        ".py", ".java", ".js", ".ts", ".jsx", ".tsx",
        ".go", ".rs", ".cpp", ".c", ".cs"
    }:
        return "Backend / application code"

    return "Other"


def parse_changed_files(changed_files):
    """Extract file paths from git diff --name-status output."""
    files = []

    for line in changed_files.splitlines():
        fields = line.split("\t")

        if len(fields) >= 2:
            status = fields[0]
            file_path = fields[-1]

            files.append((status, file_path))

    return files


def main():
    print("Preflight-CI started\n")

    event = get_pr_event()

    if not event:
        print("No GitHub PR event found.")
        return

    pull_request = event.get("pull_request", {})
    pr_number = event.get("number")
    base_sha = pull_request.get("base", {}).get("sha")
    head_sha = pull_request.get("head", {}).get("sha")

    if not base_sha or not head_sha:
        print("Could not determine the PR base/head commits.")
        raise SystemExit(1)

    print(f"PR Number: #{pr_number}")
    print(f"Base SHA:  {base_sha}")
    print(f"Head SHA:  {head_sha}\n")

    changed_files, diff = get_git_diff(base_sha, head_sha)
    files = parse_changed_files(changed_files)

    print("Changed files and classifications")
    print("---------------------------------")

    if not files:
        print("No changed files detected.")
    else:
        for status, file_path in files:
            category = classify_file(file_path)
            print(f"[{category}] {status}: {file_path}")

    print("\nChange summary")
    print("--------------")

    categories = {}

    for _, file_path in files:
        category = classify_file(file_path)
        categories[category] = categories.get(category, 0) + 1

    for category, count in sorted(categories.items()):
        print(f"{category}: {count} file(s)")

    print("\nPR Diff")
    print("-------")
    print(diff if diff else "No diff detected.")

    print("\nPreflight-CI analysis completed")


if __name__ == "__main__":
    main()
