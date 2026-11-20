
import ast
from pathlib import Path


SENSITIVE_KEYWORDS = {
    "pan",
    "card_number",
    "cvv",
    "customer_ssn",
    "account_number",
    "password",
    "access_token",
    "secret_key",
}

DATABASE_METHODS = {
    "save",
    "insert",
    "execute",
    "write",
    "update",
    "create",
}

LOGGING_METHODS = {
    "debug",
    "info",
    "warning",
    "error",
    "exception",
}


def get_call_name(node):
    """Return a readable name for a function or method call."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return ""


def find_sensitive_names(node):
    """Find sensitive-looking identifiers in an AST expression."""
    names = set()

    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id.lower())

        elif isinstance(child, ast.Constant):
            if isinstance(child.value, str):
                names.add(child.value.lower())

    return names


def analyze_compliance(file_path):
    """Identify code patterns that may require security review."""
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    findings = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        method = get_call_name(node.func).lower()
        names = find_sensitive_names(node)

        sensitive_matches = sorted(
            names & SENSITIVE_KEYWORDS
        )

        if not sensitive_matches:
            continue

        if method in DATABASE_METHODS:
            findings.append({
                "severity": "HIGH",
                "rule_id": "DATA_STORAGE_REVIEW",
                "file": str(path),
                "line": node.lineno,
                "evidence": (
                    f"Sensitive-looking data {sensitive_matches} "
                    f"appears in a call to '{method}'."
                ),
                "recommendation": (
                    "Review whether the data requires protection, "
                    "tokenization, masking, or restricted storage."
                ),
            })

        elif method in LOGGING_METHODS:
            findings.append({
                "severity": "HIGH",
                "rule_id": "SENSITIVE_LOGGING_REVIEW",
                "file": str(path),
                "line": node.lineno,
                "evidence": (
                    f"Sensitive-looking data {sensitive_matches} "
                    f"appears in a logging call."
                ),
                "recommendation": (
                    "Review whether sensitive values could be exposed "
                    "in application logs; consider masking them."
                ),
            })

    return findings


def print_findings(findings):
    """Print compliance review findings."""
    print("Compliance Rule Engine")
    print("======================")

    if not findings:
        print("No matching patterns found.")
        return

    for finding in findings:
        print(
            f"\n[{finding['severity']}] "
            f"{finding['rule_id']}"
        )
        print(
            f"Location: {finding['file']}:"
            f"{finding['line']}"
        )
        print(f"Evidence: {finding['evidence']}")
        print(
            f"Recommendation: "
            f"{finding['recommendation']}"
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m src.compliance_rules "
            "<python_file>"
        )
        raise SystemExit(1)

    findings = analyze_compliance(sys.argv[1])
    print_findings(findings)
