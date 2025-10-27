from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


# -----------------
# Config / manifest structures
# -----------------

@dataclass
class GateLogic:
    RED: str
    YELLOW: str
    GREEN: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GateLogic":
        return cls(
            RED=d["RED"],
            YELLOW=d["YELLOW"],
            GREEN=d["GREEN"],
        )


@dataclass
class SuiteManifest:
    suite_name: str
    suite_version: str
    owasp_alignment_version: str
    gate_logic: GateLogic
    include_files: List[str]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SuiteManifest":
        return cls(
            suite_name=d["suite_name"],
            suite_version=d["suite_version"],
            owasp_alignment_version=d["owasp_alignment_version"],
            gate_logic=GateLogic.from_dict(d["gate_logic"]),
            include_files=list(d["include_files"]),
        )


@dataclass
class AssertSpec:
    method: str  # "regex"
    required_patterns: List[str]
    forbidden_patterns: List[str]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AssertSpec":
        return cls(
            method=d["method"],
            required_patterns=list(d.get("required_patterns", [])),
            forbidden_patterns=list(d.get("forbidden_patterns", [])),
        )


@dataclass
class SemanticAudit:
    risk_dimension: str
    auditor_required_for_release: bool
    auditor_instruction: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticAudit":
        return cls(
            risk_dimension=d["risk_dimension"],
            auditor_required_for_release=bool(d["auditor_required_for_release"]),
            auditor_instruction=d["auditor_instruction"],
        )


@dataclass
class EvalTest:
    id: str
    severity_if_fail: str  # "red" | "yellow"
    prompt: str
    expected_behavior: str
    assert_spec: AssertSpec
    semantic_audit: Optional[SemanticAudit]

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvalTest":
        sem = d.get("semantic_audit")
        return cls(
            id=d["id"],
            severity_if_fail=d["severity_if_fail"].lower(),
            prompt=d["prompt"],
            expected_behavior=d["expected_behavior"],
            assert_spec=AssertSpec.from_dict(d["assert"]),
            semantic_audit=SemanticAudit.from_dict(sem) if sem else None,
        )

    @property
    def severity(self) -> "Severity":
        if self.severity_if_fail.lower() == "red":
            return Severity.RED
        return Severity.YELLOW


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


# -----------------
# Runtime result structures
# -----------------

class Severity:
    RED = "red"
    YELLOW = "yellow"


@dataclass
class SingleTestResult:
    test_id: str
    category_id: str
    category_name: str      # <-- NEW: human-readable name for nicer output
    severity: str           # "red" | "yellow"
    passed: bool
    prompt: str
    response: str
    failed_required_patterns: List[str]
    hit_forbidden_patterns: List[str]


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

