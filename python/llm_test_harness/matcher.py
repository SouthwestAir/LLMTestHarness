import re
from typing import List, Tuple


def _compile(pat: str) -> re.Pattern:
    # We do DOTALL so "." matches newlines. Most patterns already embed (?i) for case-insensitivity.
    return re.compile(pat, re.DOTALL)


def which_patterns_match(text: str, patterns: List[str]) -> List[str]:
    hits = []
    for pat in patterns:
        if _compile(pat).search(text):
            hits.append(pat)
    return hits


def which_patterns_missing(text: str, patterns: List[str]) -> List[str]:
    missing = []
    for pat in patterns:
        if not _compile(pat).search(text):
            missing.append(pat)
    return missing

