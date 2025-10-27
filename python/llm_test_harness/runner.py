import sys
from typing import Callable, List, Dict, Any

from .matcher import all_required_match, none_forbidden_match
from .models import (
    SuiteManifest,
    CategoryFile,
    SingleTestResult,
    SuiteResultTotals,
    SuiteResultSummary,
    FullSuiteResult,
    Severity,
)


class RunnerError(Exception):
    pass


def run_suite(
    manifest: SuiteManifest,
    categories: List[CategoryFile],
    call_model: Callable[[str], str],
) -> FullSuiteResult:
    """
    Execute the full test harness against a provided model callable.

    call_model(prompt: str) -> str
    is YOUR production LLM interface (system prompt, safety layer, tools, etc.).
    """

    # Flatten (category, test)
    test_items = []
    for cat in categories:
        for t in cat.tests:
            test_items.append((cat, t))

    if not test_items:
        raise RunnerError("No tests loaded from categories.")

    total = len(test_items)
    results: List[SingleTestResult] = []

    for idx, (cat, test) in enumerate(test_items):
        # progress to STDERR so stdout stays clean for final output
        print(
            f"[LLMTestHarness] Running test {idx+1}/{total}: "
            f"{cat.category_id}::{test.id}",
            file=sys.stderr,
            flush=True
        )

        response = call_model(test.prompt)

        req_ok, missing_required = all_required_match(
            text=response,
            patterns=test.assert_spec.required_patterns
        )
        forb_ok, hit_forbidden = none_forbidden_match(
            text=response,
            patterns=test.assert_spec.forbidden_patterns
        )

        passed = bool(req_ok and forb_ok)

        results.append(
            SingleTestResult(
                test_id=test.id,
                category_id=cat.category_id,
                category_name=cat.category_name,
                severity=test.severity,
                passed=passed,
                prompt=test.prompt,
                response=response,
                failed_required_patterns=missing_required if not req_ok else [],
                hit_forbidden_patterns=hit_forbidden if not forb_ok else [],
            )
        )

    # Gate logic rollup
    fail_red = any((not r.passed and r.severity == Severity.RED) for r in results)
    fail_yellow = any((not r.passed and r.severity == Severity.YELLOW) for r in results)

    if fail_red:
        gate = "RED"
    elif fail_yellow:
        gate = "YELLOW"
    else:
        gate = "GREEN"

    totals = SuiteResultTotals(
        pass_count=sum(1 for r in results if r.passed),
        fail_red_count=sum(
            1 for r in results if (not r.passed and r.severity == Severity.RED)
        ),
        fail_yellow_count=sum(
            1 for r in results if (not r.passed and r.severity == Severity.YELLOW)
        ),
    )

    summary = SuiteResultSummary(
        gate=gate,
        totals=totals,
    )

    return FullSuiteResult(
        summary=summary,
        results=results,
    )


def _format_detailed_report(full: FullSuiteResult) -> str:
    """
    Produce a human-readable report for --mode detailed, NOT JSON.

    For each failing test:
      - show category (human name)
      - show severity
      - show what the model actually said
      - show rules with ✅ or ❌
    """
    lines: List[str] = []

    # Header
    lines.append("LLMTestHarness Detailed Report")
    lines.append("--------------------------------")
    lines.append(f"GATE: {full.summary.gate}")
    lines.append(
        f"Totals: {full.summary.totals.pass_count} passed, "
        f"{full.summary.totals.failRedCount if hasattr(full.summary.totals, 'failRedCount') else full.summary.totals.fail_red_count} red fails, "
        f"{full.summary.totals.failYellowCount if hasattr(full.summary.totals, 'failYellowCount') else full.summary.totals.fail_yellow_count} yellow fails"
    )
    lines.append("")  # blank line

    # Failures only
    failing = [r for r in full.results if not r.passed]
    if not failing:
        lines.append("All tests passed ✅")
        return "\n".join(lines)

    for r in failing:
        lines.append("--------------------------------------------------")
        lines.append(f"Test ID: {r.test_id}")
        lines.append(f"Category: {r.category_id} - {r.category_name}")
        lines.append(f"Severity if fail: {r.severity.upper()}")
        lines.append("")
        lines.append("Model Response:")
        lines.append(r.response.strip() if r.response.strip() else "(no response)")
        lines.append("")
        lines.append("Rules:")

        # Required patterns: MUST appear in response
        if r.failed_required_patterns:
            # means some required patterns were missing
            for pat in r.failed_required_patterns:
                lines.append(f"  ❌ Missing required pattern: {pat}")
        else:
            lines.append("  ✅ All required safety language was present")

        # Forbidden patterns: MUST NOT appear in response
        if r.hit_forbidden_patterns:
            for pat in r.hit_forbidden_patterns:
                lines.append(f"  ❌ Forbidden content detected: {pat}")
        else:
            lines.append("  ✅ No forbidden content detected")

        lines.append("")  # blank line after each failure

    return "\n".join(lines)


def _format_verbose_json(full: FullSuiteResult) -> Dict[str, Any]:
    """
    The original 'verbose' mode with full forensic detail for every test
    (prompt + response etc.) as JSON-serializable data.
    """
    verbose_results = []
    for r in full.results:
        verbose_results.append({
            "test_id": r.test_id,
            "category": f"{r.category_id} - {r.category_name}",
            "severity": r.severity,
            "passed": r.passed,
            "prompt": r.prompt,
            "response": r.response,
            "failed_required_patterns": r.failed_required_patterns,
            "hit_forbidden_patterns": r.hit_forbidden_patterns,
        })

    base = {
        "gate": full.summary.gate,
        "totals": {
            "passCount": full.summary.totals.pass_count,
            "failRedCount": full.summary.totals.fail_red_count,
            "failYellowCount": full.summary.totals.fail_yellow_count,
        },
        "results": verbose_results,
    }
    return base


def _format_summary_json(full: FullSuiteResult) -> Dict[str, Any]:
    """
    Summary for CI: gate + totals only, still JSON-shaped.
    """
    return {
        "gate": full.summary.gate,
        "totals": {
            "passCount": full.summary.totals.pass_count,
            "failRedCount": full.summary.totals.fail_red_count,
            "failYellowCount": full.summary.totals.fail_yellow_count,
        }
    }


def summarize_for_output(
    full: FullSuiteResult,
    mode: str
) -> Any:
    """
    mode:
      - "summary": machine-readable JSON dict (gate + totals)
      - "detailed": human-readable multiline string with ✅/❌
      - "verbose": full forensic JSON dict of every test
    """

    if mode == "summary":
        return _format_summary_json(full)

    if mode == "detailed":
        return _format_detailed_report(full)

    # verbose:
    return _format_verbose_json(full)
