import json
import os
from typing import List, Dict, Any

from .models import (
    SuiteManifest,
    CategoryFile,
    EvalTest,
    AssertSpec,
)


def load_manifest(manifest_path: str) -> SuiteManifest:
    with open(manifest_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return SuiteManifest.from_dict(raw)


def load_banned_forbidden_regexes(banned_path: str) -> List[str]:
    """
    banned_terms.local.json looks like:
    {
      "forbidden_regexes_global": [
        "(?i)secretinternalcodename",
        "(?i)slurregex..."
      ]
    }
    """
    with open(banned_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return list(raw.get("forbidden_regexes_global", []))


def _load_category_file(path: str) -> CategoryFile:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return CategoryFile.from_dict(raw)


def load_category_files(
    manifest: SuiteManifest,
    manifest_path: str,
    banned_forbidden_regexes: List[str],
) -> List[CategoryFile]:
    """
    Load all category files listed in suite_manifest.json, then inject global
    forbidden patterns (like company slurs, internal project names, etc.)
    into each test's assert_spec.forbidden_any.
    """
    base_dir = os.path.dirname(os.path.abspath(manifest_path))

    categories: List[CategoryFile] = []
    for rel in manifest.include_files:
        full = os.path.join(base_dir, rel)
        cat = _load_category_file(full)

        # Inject org-wide forbidden regexes
        if banned_forbidden_regexes:
            for test in cat.tests:
                spec: AssertSpec = test.assert_spec
                # Deduplicate but preserve order: extend only if not already present
                for pat in banned_forbidden_regexes:
                    if pat not in spec.forbidden_any:
                        spec.forbidden_any.append(pat)

        categories.append(cat)

    return categories

