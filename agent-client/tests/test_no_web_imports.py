"""
agent-client/tests/test_no_web_imports.py

Architectural Boundary Test.
Enforces the one-way dependency rule:
The core package (incident_agent) and its tests must NEVER import:
- fastapi
- starlette / sse_starlette
- uvicorn
- web-backend application modules (app, runs, server)
"""

import ast
from pathlib import Path

FORBIDDEN_MODULES = {
    "fastapi",
    "starlette",
    "sse_starlette",
    "uvicorn",
    "app",
    "runs",
    "server",
}


def _extract_imports(file_path: Path) -> set[str]:
    """Parse a Python file and extract top-level imported module names."""
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    return imported


def test_core_package_has_no_web_dependencies():
    """Verify that no file in incident_agent/ imports forbidden web modules."""
    core_dir = Path(__file__).resolve().parent.parent / "incident_agent"
    py_files = list(core_dir.glob("*.py"))
    assert len(py_files) > 0, "No python files found in incident_agent/"

    violations = []
    for py_file in py_files:
        imports = _extract_imports(py_file)
        forbidden_hits = imports.intersection(FORBIDDEN_MODULES)
        if forbidden_hits:
            violations.append(f"{py_file.name} imports forbidden: {forbidden_hits}")

    assert not violations, f"Architectural violation detected in core package:\n" + "\n".join(violations)


def test_core_tests_have_no_web_dependencies():
    """Verify that no file in agent-client/tests/ imports forbidden web modules."""
    tests_dir = Path(__file__).resolve().parent
    py_files = [p for p in tests_dir.glob("*.py") if p.name != "test_no_web_imports.py"]
    assert len(py_files) > 0, "No test files found in agent-client/tests/"

    violations = []
    for py_file in py_files:
        imports = _extract_imports(py_file)
        forbidden_hits = imports.intersection(FORBIDDEN_MODULES)
        if forbidden_hits:
            violations.append(f"{py_file.name} imports forbidden: {forbidden_hits}")

    assert not violations, f"Architectural violation detected in core tests:\n" + "\n".join(violations)
