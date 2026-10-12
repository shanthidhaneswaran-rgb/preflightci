
from pathlib import Path

import yaml


def load_openapi(file_path):
    """Load an OpenAPI YAML file."""
    with open(file_path, "r", encoding="utf-8") as file:
        specification = yaml.safe_load(file)

    if not isinstance(specification, dict):
        raise ValueError(f"Invalid OpenAPI document: {file_path}")

    return specification


def get_schema_fields(schema):
    """Extract schema properties and required fields."""
    if not isinstance(schema, dict):
        return {}, set()

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    return properties, required


def compare_openapi(old_spec, new_spec):
    """Detect potentially breaking API contract changes."""
    findings = []

    old_paths = old_spec.get("paths", {})
    new_paths = new_spec.get("paths", {})

    # Detect removed endpoints and operations.
    for path, old_operations in old_paths.items():
        if path not in new_paths:
            findings.append({
                "severity": "HIGH",
                "type": "ENDPOINT_REMOVED",
                "message": f"Endpoint {path} was removed.",
            })
            continue

        new_operations = new_paths[path]

        for method, old_operation in old_operations.items():
            method = method.lower()

            if method not in new_operations:
                findings.append({
                    "severity": "HIGH",
                    "type": "OPERATION_REMOVED",
                    "message": f"{method.upper()} {path} was removed.",
                })
                continue

            new_operation = new_operations[method]

            # Compare request body schemas.
            old_body = old_operation.get("requestBody", {})
            new_body = new_operation.get("requestBody", {})

            old_schema = (
                old_body.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            new_schema = (
                new_body.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )

            old_fields, old_required = get_schema_fields(old_schema)
            new_fields, new_required = get_schema_fields(new_schema)

            for field in old_fields.keys() - new_fields.keys():
                findings.append({
                    "severity": "HIGH",
                    "type": "REQUEST_FIELD_REMOVED",
                    "message": (
                        f"Request field '{field}' was removed from "
                        f"{method.upper()} {path}."
                    ),
                })

            for field in new_required - old_required:
                if field in new_fields:
                    findings.append({
                        "severity": "HIGH",
                        "type": "NEW_REQUIRED_REQUEST_FIELD",
                        "message": (
                            f"Request field '{field}' is now required in "
                            f"{method.upper()} {path}."
                        ),
                    })

            for field in old_fields.keys() & new_fields.keys():
                old_type = old_fields[field].get("type")
                new_type = new_fields[field].get("type")

                if old_type != new_type:
                    findings.append({
                        "severity": "HIGH",
                        "type": "REQUEST_FIELD_TYPE_CHANGED",
                        "message": (
                            f"Request field '{field}' changed type from "
                            f"'{old_type}' to '{new_type}'."
                        ),
                    })

            # Compare successful response schemas.
            old_responses = old_operation.get("responses", {})
            new_responses = new_operation.get("responses", {})

            for code, old_response in old_responses.items():
                if not str(code).startswith("2"):
                    continue

                new_response = new_responses.get(code)

                if new_response is None:
                    findings.append({
                        "severity": "HIGH",
                        "type": "SUCCESS_RESPONSE_REMOVED",
                        "message": (
                            f"Success response {code} was removed from "
                            f"{method.upper()} {path}."
                        ),
                    })
                    continue

                old_schema = (
                    old_response.get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )
                new_schema = (
                    new_response.get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )

                old_fields, _ = get_schema_fields(old_schema)
                new_fields, _ = get_schema_fields(new_schema)

                for field in old_fields.keys() - new_fields.keys():
                    findings.append({
                        "severity": "HIGH",
                        "type": "RESPONSE_FIELD_REMOVED",
                        "message": (
                            f"Response field '{field}' was removed from "
                            f"{method.upper()} {path}, response {code}."
                        ),
                    })

                for field in old_fields.keys() & new_fields.keys():
                    old_type = old_fields[field].get("type")
                    new_type = new_fields[field].get("type")

                    if old_type != new_type:
                        findings.append({
                            "severity": "HIGH",
                            "type": "RESPONSE_FIELD_TYPE_CHANGED",
                            "message": (
                                f"Response field '{field}' changed type "
                                f"from '{old_type}' to '{new_type}'."
                            ),
                        })

    return findings


def analyze_contracts(old_file, new_file):
    """Load and compare two OpenAPI specification files."""
    old_spec = load_openapi(old_file)
    new_spec = load_openapi(new_file)

    return compare_openapi(old_spec, new_spec)


if __name__ == "__main__":
    print("API contract detector module loaded.")
    print("Use analyze_contracts(old_file, new_file) to compare specifications.")
