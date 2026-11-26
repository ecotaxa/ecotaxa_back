# -*- coding: utf-8 -*-
import os
import re
from pathlib import Path
from typing import List, Set, Tuple

import BG_operations.AllJobServices as AllJobServices

APP_ROOT = Path(AllJobServices.__file__).resolve().parent.parent
ALL_JOB_SERVICES_FILE = Path(AllJobServices.__file__).resolve()
JOB_SERVICE_BASE = "JobServiceBase"

_CLASS_RE = re.compile(
    r"^([ \t]*)class\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*:",
    re.MULTILINE,
)
_ABSTRACT_METHOD_RE = re.compile(r"^[ \t]*@(?:abc\.)?abstractmethod\b", re.MULTILINE)
_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([\w.]+)", re.MULTILINE)


def _module_name_from_path(py_file: Path, root: Path) -> str:
    rel = py_file.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _iter_python_files(root: Path) -> List[Path]:
    py_files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d != "__pycache__"
        )
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                py_files.append(Path(dirpath) / filename)
    return py_files


def _parse_bases(bases_str: str) -> Tuple[List[str], bool]:
    bases: List[str] = []
    is_abstract = False
    for raw in bases_str.split(","):
        part = raw.strip()
        if not part:
            continue
        if "=" in part:
            if "ABCMeta" in part:
                is_abstract = True
            continue
        base_name = part.split("[", 1)[0].strip().split(".")[-1]
        if base_name == "ABC":
            is_abstract = True
        bases.append(base_name)
    return bases, is_abstract


def _find_concrete_job_service_modules(root: Path) -> Set[str]:
    # List of (module_name, class_name, base_names, is_abstract)
    classes: List[Tuple[str, str, List[str], bool]] = []

    for py_file in _iter_python_files(root):
        mod_name = _module_name_from_path(py_file, root)
        if not mod_name:
            continue
        text = py_file.read_text(encoding="utf-8")
        if "class " not in text:
            continue

        matches = list(_CLASS_RE.finditer(text))
        for idx, match in enumerate(matches):
            indent, cls_name, bases_str = match.group(1), match.group(2), match.group(3) or ""
            bases, is_abstract = _parse_bases(bases_str)
            if not is_abstract:
                body_end = len(text)
                for next_match in matches[idx + 1 :]:
                    if len(next_match.group(1)) <= len(indent):
                        body_end = next_match.start()
                        break
                if _ABSTRACT_METHOD_RE.search(text, match.end(), body_end):
                    is_abstract = True
            classes.append((mod_name, cls_name, bases, is_abstract))

    job_service_classes: Set[str] = {JOB_SERVICE_BASE}
    changed = True
    while changed:
        changed = False
        for _, cls_name, bases, _ in classes:
            if cls_name not in job_service_classes and any(
                b in job_service_classes for b in bases
            ):
                job_service_classes.add(cls_name)
                changed = True

    return {
        mod_name
        for mod_name, cls_name, _, is_abstract in classes
        if cls_name in job_service_classes
        and cls_name != JOB_SERVICE_BASE
        and not is_abstract
    }


def _parse_imported_modules(py_file: Path) -> Set[str]:
    text = py_file.read_text(encoding="utf-8")
    return set(_IMPORT_RE.findall(text))


def test_all_job_services_imports_all_subclasses():
    """
    Verify via source pattern matching that BG_operations/AllJobServices.py
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
