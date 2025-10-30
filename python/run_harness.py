#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Callable, Optional

# Make sure we can import llm_test_harness + providers no matter where we run from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(REPO_ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from llm_test_harness.loader import (  # noqa: E402
    load_manifest,
    load_banned_forbidden_regexes,
    load_category_files,
)
from llm_test_harness.runner import (  # noqa: E402
    run_suite,
    summarize_for_output,
    format_triage,
)


def load_text_file_if_exists(path: Optional[str]) -> Optional[str]:
    if path is None:
        return None
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_provider(
    provider_name: str, preamble_text: Optional[str]
) -> Callable[[str], str]:
    """
    Returns a callable(prompt:str)->str which bakes in the chosen provider
    *and* the preamble text.
    """
    if provider_name == "mock":
        from providers.mock import call_model as _call

        return lambda prompt: _call(prompt, preamble_text)

    if provider_name == "openai":
        from providers.openai import call_model as _call

        return lambda prompt: _call(prompt, preamble_text)

    if provider_name == "claude":
        from providers.claude import call_model as _call

        return lambda prompt: _call(prompt, preamble_text)

    raise ValueError(f"Unknown provider '{provider_name}'")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLMTestHarness and output GREEN / YELLOW / RED gate."
    )

    parser.add_argument(
        "--provider",
        required=False,
        default="mock",
        choices=["mock", "openai", "claude"],
        help="Which model backend to hit.",
    )

    parser.add_argument(
        "--manifest",
        required=False,
        default=os.path.join(REPO_ROOT, "shared", "suite_manifest.json"),
        help="Path to suite_manifest.json.",
    )

    parser.add_argument(
        "--banned",
        required=False,
        default=os.path.join(REPO_ROOT, "samples", "banned_terms.local.json"),
        help="Optional path to banned_terms.local.json "
        "(private forbidden regexes, not committed).",
    )

    parser.add_argument(
        "--preamble",
        required=False,
        default=os.path.join(REPO_ROOT, "shared", "org_preamble.txt"),
        help="Optional path to an org-specific preamble that will be injected "
        "as system / policy context before every test prompt.",
    )

    parser.add_argument(
        "--mode",
        required=False,
        default="summary",
<<<<<<< HEAD
        choices=["summary", "detailed", "verbose"],
        help="Output detail level.",
=======
        choices=["summary", "detailed", "verbose", "triage"],
        help="Output detail level."
>>>>>>> d10a335 (fix: had to rearchitect some stuff; fixed LLM01 as well, confirmed with OpenAI)
    )

    args = parser.parse_args()

    # Load manifest
    manifest = load_manifest(args.manifest)

    # Load banned forbidden regexes (optional)
    banned_regexes = []
    if os.path.exists(args.banned):
        banned_regexes = load_banned_forbidden_regexes(args.banned)

    # Load categories/tests and inject banned_regexes
    categories = load_category_files(
        manifest=manifest,
        manifest_path=args.manifest,
        banned_forbidden_regexes=banned_regexes,
    )

    # Load preamble text if available
    preamble_text = load_text_file_if_exists(args.preamble)

    # Pick provider and bake in preamble
    call_model = load_provider(args.provider, preamble_text)

    # Run suite
    full_result = run_suite(
        manifest=manifest, categories=categories, call_model=call_model
    )

    if args.mode == "triage":
        failing = [r for r in full_result.results if r.status in ("yellow_fail", "red_fail")]
        if not failing:
            print("All tests passed.")
        else:
            print(format_triage(failing))
        return

    # Summaries: summary | detailed | verbose
    output = summarize_for_output(full_result, mode=args.mode)

    # detailed returns a human-readable string
    # summary / verbose return dicts (JSON-friendly)
    if isinstance(output, str):
        print(output)
    else:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
