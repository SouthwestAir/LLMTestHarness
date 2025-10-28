from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


# ---------- Manifest / test config models ----------

@dataclass
class SuiteManifest:
    suite_name: str
    suite_version: str
    owasp_alignment_version: str
    include_files: List[str]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SuiteManifest":
        # gate_logic used to exist; it's optional now.
        return cls(
            suite_name=d["suite_name"],
            suite_version=d["suite_version"],
            owasp_alignment_version=d["owasp_alignment_version"],
            include_files=list(d["include_files"]),
        )


@dataclass
class AssertSpec:
    method: str  # "regex"
    required_all: List[str]     # MUST all appear (legal must-say); missing -> RED
    required_any: List[str]     # At least one should appear; otherwise -> YELLOW
    forbidden_any: List[str]    # NONE may appear; if any appear -> RED

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AssertSpec":
        # We allow older tests to still have old keys for a while.
        # Fallback logic:
        required_all = d.get("required_all", [])
        required_any = d.get("required_any", [])
        forbidden_any = d.get("forbidden_any", [])

        # Backwards compatibility: if someone still uses the old fields:
        # - required_patterns -> treat like required_any
        # - forbidden_patterns -> treat like forbidden_any
        if not required_any and "required_patterns" in d:
            required_any = list(d.get("required_patterns", []))
        if not forbidden_any and "forbidden_patterns" in d:
            forbidden_any = list(d.get("forbidden_patterns", []))

        return cls(
            method=d["method"],
            required_all=list(required_all),
            required_any=list(required_any),
            forbidden_any=list(forbidden_any),
        )


@dataclass
class EvalTest:
    id: str
    prompt: str
    expected_behavior: str
    assert_spec: AssertSpec

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvalTest":
        return cls(
            id=d["id"],
            prompt=d["prompt"],
            expected_behavior=d["expected_behavior"],
            assert_spec=AssertSpec.from_dict(d["assert"]),
        )


@dataclass
class CategoryFile:
    category_id: str
    category_name: str
    category_description: str
    tests: List[EvalTest]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CategoryFile":
        tests = [EvalTest.from_dict(t) for t in d.get("tests", [])]
        return cls(
            category_id=d["category_id"],
            category_name=d["category_name"],
            category_description=d["category_description"],
            tests=tests,
        )


# ---------- Runtime result models ----------

@dataclass
class SingleTestResult:
    test_id: str
    category_id: str
    category_name: str

    # status is one of: "pass", "yellow_fail", "red_fail"
    status: str

    # severity is: "red", "yellow", or "none" (derived from status)
    severity: str

    prompt: str
    response: str

    # Which strict rules were missed?
    missing_required_all: List[str]

    # Which forbidden rules were triggered?
    hit_forbidden_any: List[str]

    # Which "good" patterns we matched (from required_any)?
    matched_required_any: List[str]


@dataclass
class SuiteResultTotals:
    pass_count: int
    fail_red_count: int
    fail_yellow_count: int


@dataclass
class SuiteResultSummary:
    gate: str  # "GREEN" | "YELLOW" | "RED"
    totals: SuiteResultTotals


@dataclass
class FullSuiteResult:
    summary: SuiteResultSummary
    results: List[SingleTestResult]

