
from src.retrieve_policies import retrieve_policies


def review_finding(finding, top_k=2):
    """Retrieve policy evidence relevant to a compliance finding."""

    query = (
        f"Finding type: {finding.get('type', 'Unknown')}\n"
        f"Evidence: {finding.get('evidence', '')}\n"
        f"Recommendation: {finding.get('recommendation', '')}"
    )

    policies = retrieve_policies(query, top_k=top_k)

    return {
        "finding": finding,
        "policy_evidence": policies,
        "review_status": (
            "REVIEW_REQUIRED" if policies else "NO_POLICY_MATCH"
        ),
    }


if __name__ == "__main__":
    sample_finding = {
        "type": "SENSITIVE_LOGGING_REVIEW",
        "severity": "HIGH",
        "file": "payments.py",
        "line": 42,
        "evidence": (
            "Sensitive-looking data ['card_number'] "
            "appears in a logging call."
        ),
        "recommendation": (
            "Review whether sensitive values could be exposed "
            "in application logs; consider masking them."
        ),
    }

    report = review_finding(sample_finding)

    print("Preflight-CI RAG Review")
    print("=" * 50)
    print(f"Finding: {report['finding']['type']}")
    print(f"Status: {report['review_status']}")
    print("\nRetrieved policy evidence:")

    for policy in report["policy_evidence"]:
        print(f"\nSource: {policy['source']}")
        print(f"Chunk: {policy['chunk_index']}")
        print(f"Policy text:\n{policy['text']}")
