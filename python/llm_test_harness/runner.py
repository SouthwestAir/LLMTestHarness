import sys
from typing import Callable, List, Dict, Any

from .matcher import which_patterns_match, which_patterns_missing
from .models import (
    SuiteManifest,
    CategoryFile,
    SingleTestResult,
    SuiteResultTotals,
    SuiteResultSummary,
    FullSuiteResult,
)


class RunnerError(Exception):
    pass


def run_suite(
    manifest: SuiteManifest,
    categories: List[CategoryFile],
    call_model: Callable[[str], str],
) -> FullSuiteResult:
    """
    Execute the full test harness against `call_model`.

    call_model(prompt: str) -> str
    should return the assistant's final, user-facing response string.
    """

    # Flatten all tests
    test_items = []
    for cat in categories:
        for t in cat.tests:
            test_items.append((cat, t))

    if not test_items:
        raise RunnerError("No tests loaded from categories.")

    total = len(test_items)
    results: List[SingleTestResult] = []

    for idx, (cat, test) in enumerate(test_items):
        # progress to STDERR so stdout remains clean for final output
        print(
            f"[LLMTestHarness] Running test {idx+1}/{total}: "
            f"{cat.category_id}::{test.id}",
            file=sys.stderr,
            flush=True
        )

        response = call_model(test.prompt)

        spec = test.assert_spec

        # Which forbidden patterns showed up?
        hit_forbidden_any = which_patterns_match(response, spec.forbidden_any)

        # Which "must-say" phrases are missing? (hard requirements from legal/compliance)
        missing_required_all = which_patterns_missing(response, spec.required_all)

        # Did we match at least one of the "preferred safety wording" patterns?
        matched_required_any = which_patterns_match(response, spec.required_any)
        hit_any_required_any = len(matched_required_any) > 0 or len(spec.required_any) == 0

        # Figure out status
        if hit_forbidden_any or missing_required_all:
            status = "red_fail"
            severity = "red"
        elif not hit_any_required_any:
            status = "yellow_fail"
            severity = "yellow"
        else:
            status = "pass"
            severity = "none"

        results.append(
            SingleTestResult(
                test_id=test.id,
                category_id=cat.category_id,
                category_name=cat.category_name,
                status=status,
                severity=severity,
                prompt=test.prompt,
                response=response,
                missing_required_all=missing_required_all,
                hit_forbidden_any=hit_forbidden_any,
                matched_required_any=matched_required_any,
            )
        )

    # Roll up gate
    fail_red = any(r.status == "red_fail" for r in results)
    fail_yellow = any(r.status == "yellow_fail" for r in results)

    if fail_red:
        gate = "RED"
    elif fail_yellow:
        gate = "YELLOW"
    else:
        gate = "GREEN"

    totals = SuiteResultTotals(
        pass_count=sum(1 for r in results if r.status == "pass"),
        fail_red_count=sum(1 for r in results if r.status == "red_fail"),
        fail_yellow_count=sum(1 for r in results if r.status == "yellow_fail"),
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
    Human-readable report (for --mode detailed).

    We only print failing tests. For each failing test we show:
    - category
    - severity (RED or YELLOW)
    - the model's response
    - rule checks with ✅ / ❌ / ⚠
    """

    lines: List[str] = []

    # Header
    lines.append("LLMTestHarness Detailed Report")
    lines.append("--------------------------------")
    lines.append(f"GATE: {full.summary.gate}")
    lines.append(
        f"Totals: {full.summary.totals.pass_count} passed, "
        f"{full.summary.totals.fail_red_count} red fails, "
        f"{full.summary.totals.fail_yellow_count} yellow fails"
    )
    lines.append("")

    failing = [r for r in full.results if r.status != "pass"]
    if not failing:
        lines.append("All tests passed ✅")
        return "\n".join(lines)

    for r in failing:
        lines.append("--------------------------------------------------")
        lines.append(f"Test ID: {r.test_id}")
        lines.append(f"Category: {r.category_id} - {r.category_name}")
        lines.append(f"Result: {r.severity.upper() if r.severity != 'none' else 'PASS'}")
        lines.append("")
        lines.append("Model Response:")
        resp = r.response.strip() if r.response.strip() else "(no response)"
        lines.append(resp)
        lines.append("")
        lines.append("Checks:")

        # Forbidden content: RED if any matched
        if r.hit_forbidden_any:
            for pat in r.hit_forbidden_any:
                lines.append(f"  ❌ Forbidden content present (RED): {pat}")
        else:
            lines.append("  ✅ No forbidden content detected")

        # Required ALL: RED if any missing
        if r.missing_required_all:
            for pat in r.missing_required_all:
                lines.append(f"  ❌ Missing mandatory language (RED): {pat}")
        else:
            lines.append("  ✅ All mandatory language satisfied")

        # Required ANY: YELLOW if none matched and list was non-empty
        if not r.matched_required_any and r.matched_required_any is not None:
            # If spec.required_any was empty, we consider that satisfied by default.
            # Here, "matched_required_any == []" just means "no preferred phrasing hit".
            lines.append("  ⚠ Did not include any preferred safety language (YELLOW)")
        else:
            lines.append("  ✅ Included at least one preferred safety / refusal pattern")

        lines.append("")

    return "\n".join(lines)


def _format_verbose_json(full: FullSuiteResult) -> Dict[str, Any]:
    """
    Full forensic detail for --mode verbose, as JSON-serializable data.
    Includes every test (pass or fail).
    """
    verbose_results = []
    for r in full.results:
        verbose_results.append({
            "test_id": r.test_id,
            "category": f"{r.category_id} - {r.category_name}",
            "status": r.status,
            "severity": r.severity,
            "prompt": r.prompt,
            "response": r.response,
            "hit_forbidden_any": r.hit_forbidden_any,
            "missing_required_all": r.missing_required_all,
            "matched_required_any": r.matched_required_any,
        })

    return {
        "gate": full.summary.gate,
        "totals": {
            "passCount": full.summary.totals.pass_count,
            "failRedCount": full.summary.totals.fail_red_count,
            "failYellowCount": full.summary.totals.fail_yellow_count,
        },
        "results": verbose_results,
    }


def _format_summary_json(full: FullSuiteResult) -> Dict[str, Any]:
    """
    Short JSON for --mode summary (CI use).
    """
    return {
        "gate": full.summary.gate,
        "totals": {
            "passCount": full.summary.totals.pass_count,
            "failRedCount": full.summary.totals.fail_red_count,
            "failYellowCount": full.summary.totals.fail_yellow_count,
        }
    }


def summarize_for_output(full: FullSuiteResult, mode: str) -> Any:
    """
    mode:
      - "summary": machine-readable JSON dict (gate + totals)
      - "detailed": human-readable multiline string
      - "verbose": full forensic JSON dict
    """

    if mode == "summary":
        return _format_summary_json(full)

    if mode == "detailed":
        return _format_detailed_report(full)

    # verbose
    return _format_verbose_json(full)

