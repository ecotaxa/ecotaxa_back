# -*- coding: utf-8 -*-
import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import BG_operations.AllJobServices as AllJobServices

APP_ROOT = Path(AllJobServices.__file__).resolve().parent.parent
ALL_JOB_SERVICES_FILE = Path(AllJobServices.__file__).resolve()
JOB_SERVICE_BASE = ("API_operations.helpers.JobService", "JobServiceBase")

ClassId = Tuple[str, str]  # (module_name, class_name)


def _module_name_from_path(py_file: Path, root: Path) -> str:
    rel = py_file.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_relative_module(current_module: str, level: int, module: Optional[str]) -> str:
    if level == 0:
        return module or ""
    parts = current_module.split(".")
    # For a regular module a.b.c, level=1 means package a.b
    base = parts[:-level] if level <= len(parts) else []
    if module:
        return ".".join(base + [module])
    return ".".join(base)


def _collect_imports(tree: ast.AST, current_module: str) -> Dict[str, ClassId]:
    """Map local bound name -> (target_module, target_symbol_or_empty)."""
    bindings: Dict[str, ClassId] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".")[0]
                bindings[local_name] = (alias.name, "")
        elif isinstance(node, ast.ImportFrom):
            target_mod = _resolve_relative_module(current_module, node.level, node.module)
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                bindings[local_name] = (target_mod, alias.name)
    return bindings


def _resolve_base(
    base_node: ast.expr,
    current_module: str,
    local_classes: Set[str],
    imports: Dict[str, ClassId],
) -> Optional[ClassId]:
    if isinstance(base_node, ast.Name):
        name = base_node.id
        if name in local_classes:
            return (current_module, name)
        if name in imports:
            mod, sym = imports[name]
            return (mod, sym or name)
        return None
    if isinstance(base_node, ast.Attribute) and isinstance(base_node.value, ast.Name):
        root_name = base_node.value.id
        if root_name in imports:
            mod, sym = imports[root_name]
            full_mod = f"{mod}.{sym}" if sym else mod
            return (full_mod, base_node.attr)
    return None


def _is_abstract_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == "ABC":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "ABC":
            return True
    for kw in node.keywords:
        if kw.arg == "metaclass" and ast.unparse(kw.value).endswith("ABCMeta"):
            return True
    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in stmt.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == "abstractmethod":
                    return True
                if isinstance(dec, ast.Attribute) and dec.attr == "abstractmethod":
                    return True
    return False


def _find_concrete_job_service_modules(root: Path) -> Set[str]:
    class_bases: Dict[ClassId, List[ClassId]] = {}
    abstract_classes: Set[ClassId] = set()

    for py_file in sorted(root.rglob("*.py")):
        mod_name = _module_name_from_path(py_file, root)
        if not mod_name:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        imports = _collect_imports(tree, mod_name)

        class_defs = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        local_classes = {n.name for n in class_defs}

        for cls_node in class_defs:
            cls_id: ClassId = (mod_name, cls_node.name)
            resolved_bases: List[ClassId] = []
            for base in cls_node.bases:
                resolved = _resolve_base(base, mod_name, local_classes, imports)
                if resolved is not None:
                    resolved_bases.append(resolved)
            class_bases[cls_id] = resolved_bases
            if _is_abstract_class(cls_node):
                abstract_classes.add(cls_id)

    memo: Dict[ClassId, bool] = {}

    def descends_from_job_service_base(cls_id: ClassId, visiting: Set[ClassId]) -> bool:
        if cls_id in memo:
            return memo[cls_id]
        if cls_id in visiting:
            return False
        visiting.add(cls_id)
        bases = class_bases.get(cls_id, [])
        result = any(
            b == JOB_SERVICE_BASE or descends_from_job_service_base(b, visiting)
            for b in bases
        )
        visiting.remove(cls_id)
        memo[cls_id] = result
        return result

    modules: Set[str] = set()
    for cls_id in class_bases:
        if cls_id == JOB_SERVICE_BASE or cls_id in abstract_classes:
            continue
        if descends_from_job_service_base(cls_id, set()):
            modules.add(cls_id[0])
    return modules


def _parse_imported_modules(py_file: Path) -> Set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    imported: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_all_job_services_imports_all_subclasses():
    """
    Verify via AST source parsing that BG_operations/AllJobServices.py
    imports every module defining a concrete JobServiceBase subclass.
    """
    expected_modules = _find_concrete_job_service_modules(APP_ROOT)
    imported_modules = _parse_imported_modules(ALL_JOB_SERVICES_FILE)

    assert expected_modules, "No concrete JobServiceBase subclasses found in app source"
    missing = expected_modules - imported_modules
    assert not missing, (
        "BG_operations/AllJobServices.py does not import all modules defining "
        f"concrete JobServiceBase subclasses. Missing: {sorted(missing)}"
    )
    extra = imported_modules - expected_modules
    assert not extra, (
        "BG_operations/AllJobServices.py imports modules without concrete "
        f"JobServiceBase subclasses: {sorted(extra)}"
    )
