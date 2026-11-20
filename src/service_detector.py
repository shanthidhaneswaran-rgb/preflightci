
import ast
from pathlib import Path
from urllib.parse import urlparse


HTTP_METHODS = {
    "get", "post", "put", "patch", "delete",
    "head", "options", "request",
}


def get_string_value(node):
    """Return a string literal, or None for dynamic expressions."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    return None


def detect_service_references(file_path):
    """Find common HTTP client calls with statically known URLs."""
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    references = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func

        if not isinstance(function, ast.Attribute):
            continue

        method = function.attr.lower()

        if method not in HTTP_METHODS:
            continue

        # Accept patterns such as requests.get(...) and httpx.post(...).
        client = function.value
        if not isinstance(client, ast.Name):
            continue

        if client.id.lower() not in {
            "requests", "httpx", "client", "session"
        }:
            continue

        url = None

        # Common pattern: requests.get("https://service/path")
        if node.args:
            url = get_string_value(node.args[0])

        # Common pattern: requests.get(url="https://service/path")
        if url is None:
            for keyword in node.keywords:
                if keyword.arg in {"url"}:
                    url = get_string_value(keyword.value)
                    break

        if not url:
            continue

        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue

        references.append({
            "file": str(path),
            "line": node.lineno,
            "client": client.id,
            "method": method.upper(),
            "url": url,
            "host": parsed.hostname,
            "path": parsed.path or "/",
        })

    return references


def main():
    result = detect_service_references("src/main.py")

    print("API/service references")
    print("----------------------")

    if not result:
        print("No statically identifiable HTTP references found.")
        print("This is expected if the file does not make HTTP calls.")
        return

    for item in result:
        print(
            f"{item['method']} {item['url']} "
            f"(host={item['host']}, file={item['file']}, "
            f"line={item['line']})"
        )


if __name__ == "__main__":
    main()
