"""One module may only import another through its contracts.py. See Rule 5 in AGENTS.md."""

import ast
from pathlib import Path

import costpilot

MODULES_DIR = Path(costpilot.__file__).parent / "modules"
PREFIX = "costpilot.modules."


def imported_names(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            names += [f"{node.module}.{alias.name}" for alias in node.names]
    return names


def find_violations(modules_dir: Path) -> list[str]:
    violations = []
    for path in modules_dir.rglob("*.py"):
        parts = path.relative_to(modules_dir).parts
        if len(parts) < 2:
            continue
        own_module = parts[0]
        for name in imported_names(path):
            if not name.startswith(PREFIX):
                continue
            target = name.removeprefix(PREFIX).split(".")
            is_other_module = target[0] != own_module and len(target) > 1
            if is_other_module and target[1] != "contracts":
                violations.append(f"{path}: imports {name}")
    return violations


def test_modules_only_use_each_others_contracts() -> None:
    assert find_violations(MODULES_DIR) == []


def test_the_check_catches_a_bad_import(tmp_path: Path) -> None:
    bad_file = tmp_path / "billing" / "application" / "use_case.py"
    bad_file.parent.mkdir(parents=True)
    bad_file.write_text("from costpilot.modules.audit.domain import rules\n")

    assert len(find_violations(tmp_path)) > 0


def test_the_check_allows_contracts(tmp_path: Path) -> None:
    good_file = tmp_path / "billing" / "application" / "use_case.py"
    good_file.parent.mkdir(parents=True)
    good_file.write_text("from costpilot.modules.audit.contracts import record\n")

    assert find_violations(tmp_path) == []
