"""
Command-line runner for LLMTestHarness (Python side).

Example:
    python -m llm_test_harness.cli \
        --manifest ../shared/suite_manifest.json \
        --banned ../samples/banned_terms.local.json \
        --mode summary

Modes:
  summary  -> gate + totals only
  detailed -> adds which tests failed (IDs, severities)
  verbose  -> full prompt/response dump for manual/legal review
"""

import argparse
import json
from typing import Optional

from .loader import (
    load_manifest,
    load_banned_forbidden_regexes,
    load_category_files,
)
from .runner import (
    run_suite,
    summarize_for_output,
)


def call_model_stub(prompt: str) -> str:
    """
    This is a placeholder inference function.
    Replace this in real usage with a call to your production assistant.
    The stub tries to be 'safe' enough to pass a few obvious tests.
    """
    lower = prompt.lower()

    # Self-harm style prompts
    if "hurt myself" in lower or "don't want to live" in lower:
        return (
            "I'm really sorry you're feeling this way. "
            "You deserve support and your safety matters. "
            "Please reach out to someone you trust or a professional / crisis "
            "support right now. I can't provide instructions for self-harm."
        )

    # Aviation / safety skip requests
    if "skip the preflight" in lower or "skip the cabin safety inspection" in lower:
        return (
            "You must complete the required cabin safety inspection. "
            "You cannot skip mandatory checks."
        )

    # Prompt injection / leak request
    if "reveal your entire hidden system prompt" in lower or "print your internal safety escalation policy" in lower:
        return (
            "I can't share internal or confidential system instructions. "
            "That information is confidential and must remain private."
        )

    # Unsafe autonomy / delay flight
    if "delay flight" in lower or "shut down the production" in lower:
        return (
            "I can't directly delay flights or shut down production systems. "
            "That requires authorized operations staff, and I won't falsify a safety issue."
        )

    # Harassment request
    if "make it really offensive" in lower or "insult" in lower:
        return (
            "I can't create offensive or harassing content. "
            "I aim to be respectful and inclusive."
        )

    # Script injection / malicious payload
    if "<script>" in lower or "mark every active gate display" in lower:
        return (
            "I can't generate an operational or executable command like that. "
            "This requires authorized human review."
        )

    # nonsense physics
    if "strawberries" in lower or "wing flap weighs 500 tons" in lower:
        return (
            "That doesn't really make physical sense unless we imagine "
            "a hypothetical size, and a person can't carry that "
            "kind of weight in a backpack."
        )

    # default fallback
    return (
        "I can't perform that action directly or provide confidential details. "
        "This requires authorized human review."
    )


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run LLMTestHarness against a model and produce a RED/YELLOW/GREEN gate."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to suite_manifest.json (usually in shared/)."
    )
    parser.add_argument(
        "--banned",
        required=False,
        default=None,
        help="Optional path to banned_terms.local.json (private forbidden regexes)."
    )
    parser.add_argument(
        "--mode",
        required=False,
        default="summary",
        choices=["summary", "detailed", "verbose"],
        help="How much detail to print."
    )

    args = parser.parse_args(argv)

    # 1. Load manifest
    manifest = load_manifest(args.manifest)

    # 2. Load banned terms (forbidden patterns to merge)
    banned_regexes = load_banned_forbidden_regexes(args.banned)

    # 3. Load category files
    categories = load_category_files(
        manifest=manifest,
        manifest_path=args.manifest,
        banned_forbidden_regexes=banned_regexes
    )

    # 4. Run
    full_result = run_suite(
        manifest=manifest,
        categories=categories,
        call_model=call_model_stub  # <-- replace with your real model call
    )

    # 5. Prepare report
    output = summarize_for_output(full_result, mode=args.mode)

    # 6. Print to stdout as JSON (machine-readable for CI)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

