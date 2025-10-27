import re
from typing import List, Tuple


FLAGS = re.IGNORECASE | re.DOTALL  # case-insensitive, dot matches newlines


def all_required_match(text: str, patterns: List[str]) -> Tuple[bool, List[str]]:
    """
    Return (ok, missing_patterns).
    ok == True only if EVERY pattern appears at least once in text.
    """
    missing = []
    for pat in patterns:
        try:
            if re.search(pat, text, FLAGS) is None:
                missing.append(pat)
        except re.error:
            # invalid regex counts as missing
            missing.append(pat)
    return (len(missing) == 0, missing)


def none_forbidden_match(text: str, patterns: List[str]) -> Tuple[bool, List[str]]:
    """
    Return (ok, hit_patterns).
    ok == True only if NONE of the patterns appear in text.
    """
    hits = []
    for pat in patterns:
        try:
            if re.search(pat, text, FLAGS) is not None:
                hits.append(pat)
        except re.error:
            # invalid regex means we can't match it -> ignore
            continue
    return (len(hits) == 0, hits)

