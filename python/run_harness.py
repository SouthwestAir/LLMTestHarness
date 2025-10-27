#!/usr/bin/env python3
import argparse
import json
import os
import sys

# Make sure we can import llm_test_harness + providers no matter where we run from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(REPO_ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from llm_test_harness.loader import (
    load_manifest,
    load_banned_forbidden_regexes,
    load_category_files,
)
from llm_test_harness.runner import (
    run_suite,
    summarize_for_output,
)

def load_provider(provider_name: str):
    """
    Dynamically import one of:
      providers.mock
      providers.openai
      providers.claude

    Each provider must expose: call_model(prompt: str) -> str
    """
    if provider_name == "mock":
        from providers.mock import call_model
        return call_model
    elif provider_name == "openai":
        from providers.openai import call_model
        return call_model
    elif provider_name == "claude":
        from providers.claude import call_model
        return call_model
    else:
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
        help="Which model backend to hit. 'mock' is the built-in stub; 'openai' and 'claude' call real APIs."
    )

    parser.add_argument(
        "--manifest",
        required=False,
        default=os.path.join(REPO_ROOT, "shared", "suite_manifest.json"),
        help="Path to suite_manifest.json. Default points to shared/suite_manifest.json."
    )

    parser.add_argument(
        "--banned",
        required=False,
        default=os.path.join(REPO_ROOT, "samples", "banned_terms.local.json"),
        help="Optional path to banned_terms.local.json (private forbidden regex list)."
    )

    parser.add_argument(
        "--mode",
        required=False,
        default="summary",
        choices=["summary", "detailed", "verbose"],
        help="Output detail level."
    )

    args = parser.parse_args()

    # Load manifest + banned list + categories
    manifest = load_manifest(args.manifest)

    banned_regexes = []
    if os.path.exists(args.banned):
        banned_regexes = load_banned_forbidden_regexes(args.banned)

    categories = load_category_files(
        manifest=manifest,
        manifest_path=args.manifest,
        banned_forbidden_regexes=banned_regexes
    )

    # Pick provider (mock, openai, claude)
    call_model = load_provider(args.provider)

    # Run suite
    full_result = run_suite(
        manifest=manifest,
        categories=categories,
        call_model=call_model
    )

    # Summaries: summary | detailed | verbose
    output = summarize_for_output(full_result, mode=args.mode)

    # detailed returns a string (human readable)
    # summary & verbose return dicts (JSON-friendly)
    if isinstance(output, str):
        print(output)
    else:
        import json
        print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()

