
import ast
from pathlib import Path


def analyze_python_file(file_path):
    """Extract functions, imports, and function calls from Python code."""
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        return {
            "file": str(path),
            "error": str(error),
            "functions": [],
            "imports": [],
            "calls": [],
        }

    functions = []
    imports = []
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "async": isinstance(node, ast.AsyncFunctionDef),
            })

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                call_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                call_name = node.func.attr
            else:
                continue

            calls.append({
                "name": call_name,
                "line": node.lineno,
            })

    return {
        "file": str(path),
        "error": None,
        "functions": functions,
        "imports": sorted(set(imports)),
        "calls": calls,
    }


def main():
    result = analyze_python_file("src/main.py")

    print(f"File: {result['file']}")

    if result["error"]:
        print(f"Syntax error: {result['error']}")
        return

    print("\nFunctions:")
    for function in result["functions"]:
        print(f"  {function['name']} (line {function['line']})")

    print("\nImports:")
    for module in result["imports"]:
        print(f"  {module}")

    print("\nFunction calls:")
    for call in result["calls"]:
        print(f"  {call['name']} (line {call['line']})")


if __name__ == "__main__":
    main()
