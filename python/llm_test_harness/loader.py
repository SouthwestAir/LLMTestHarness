import json
import os
from typing import List, Dict, Any, Optional

from .models import (
    SuiteManifest,
    CategoryFile,
    EvalTest,
    AssertSpec,
)


class LoaderError(Exception):
    pass


def _read_json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest(manifest_path: str) -> SuiteManifest:
    """
    Load suite_manifest.json (or a variant) from disk.
    """
    data = _read_json_file(manifest_path)
    return SuiteManifest.from_dict(data)


def load_banned_forbidden_regexes(banned_path: Optional[str]) -> List[str]:
    """
    banned_path points to something like samples/banned_terms.local.json
    {
      "forbidden_regexes_global": [
        "(?i)\\bINTERNAL_CODE_NAME\\b",
        "(?i)\\b(ACTUAL_SLUR_1|ACTUAL_SLUR_2)\\b"
      ]
    }
    """
    if banned_path is None:
        return []
    data = _read_json_file(banned_path)
    return list(data.get("forbidden_regexes_global", []))


def _patch_tests_with_banned_terms(category: CategoryFile, banned_regexes: List[str]) -> CategoryFile:
    """
    Returns a new CategoryFile with banned_regexes appended to each test's
    forbidden_patterns.
    """
    if not banned_regexes:
        return category

    patched_tests: List[EvalTest] = []
    for t in category.tests:
        new_forbidden = list(t.assert_spec.forbidden_patterns) + list(banned_regexes)
        new_assert = AssertSpec(
            method=t.assert_spec.method,
            required_patterns=list(t.assert_spec.required_patterns),
            forbidden_patterns=new_forbidden,
        )
        patched_tests.append(
            EvalTest(
                id=t.id,
                severity_if_fail=t.severity_if_fail,
                prompt=t.prompt,
                expected_behavior=t.expected_behavior,
                assert_spec=new_assert,
                semantic_audit=t.semantic_audit,
            )
        )

    return CategoryFile(
        category_id=category.category_id,
        category_name=category.category_name,
        category_description=category.category_description,
        tests=patched_tests,
    )


def load_category_files(
    manifest: SuiteManifest,
    manifest_path: str,
    banned_forbidden_regexes: Optional[List[str]] = None
) -> List[CategoryFile]:
    """
    Load each category file listed in manifest.include_files.
    Paths in include_files are relative to the manifest's directory
    (normally repo_root/shared/).

    Also merges in banned_forbidden_regexes for each test.
    """
    base_dir = os.path.dirname(os.path.abspath(manifest_path))
    banned_forbidden_regexes = banned_forbidden_regexes or []

    categories: List[CategoryFile] = []

    for rel_path in manifest.include_files:
        full_path = os.path.join(base_dir, rel_path)

        if not os.path.exists(full_path):
            raise LoaderError(f"Category file not found: {full_path}")

        data = _read_json_file(full_path)

        try:
            cat = CategoryFile.from_dict(data)
        except Exception as e:
            raise LoaderError(f"Failed to decode {full_path}: {e}") from e

        cat = _patch_tests_with_banned_terms(cat, banned_forbidden_regexes)

        categories.append(cat)

    return categories

