import json
import os
import subprocess


def get_pr_event():
    """Read the GitHub PR event information."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not event_path:
        print("Running outside GitHub Actions.")
        return None

    with open(event_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_git_diff(base_sha, head_sha):
    """Get the changed files and actual diff between two commits."""

    result = subprocess.run(
        ["git", "diff", "--name-status", base_sha, head_sha],
        capture_output=True,
        text=True,
        check=True,
    )

    changed_files = result.stdout.strip()

    diff_result = subprocess.run(
        ["git", "diff", base_sha, head_sha],
        capture_output=True,
        text=True,
        check=True,
    )

    return changed_files, diff_result.stdout


def main():
    print("🚀 Preflight-CI started")
    print()

    event = get_pr_event()

    if not event:
        print("❌ No GitHub PR event found.")
        return

    pull_request = event.get("pull_request", {})

    pr_number = event.get("number")
    base_sha = pull_request.get("base", {}).get("sha")
    head_sha = pull_request.get("head", {}).get("sha")

    print(f"PR Number: #{pr_number}")
    print(f"Base SHA:  {base_sha}")
    print(f"Head SHA:  {head_sha}")
    print()

    changed_files, diff = get_git_diff(base_sha, head_sha)

    print("📁 Changed files:")
    print("----------------")

    if changed_files:
        print(changed_files)
    else:
        print("No changed files detected.")

    print()
    print("📝 PR Diff:")
    print("-----------")

    if diff:
        print(diff)
    else:
        print("No diff detected.")

    print()
    print("✅ Preflight-CI PR analysis completed")


if __name__ == "__main__":
    main()