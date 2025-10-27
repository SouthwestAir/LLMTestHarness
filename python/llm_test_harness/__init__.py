"""
LLMTestHarness (Python)

This package loads LLM safety/compliance test suites 
and runs them against a model to produce a GREEN / YELLOW / RED gate.

Typical entrypoints:
- run_harness.py  (friendly wrapper script)
- llm_test_harness/cli.py  (module runner for CI)

You usually won't import from llm_test_harness directly.
Instead you'll import submodules like:

    from llm_test_harness.loader import load_manifest, load_category_files
    from llm_test_harness.runner import run_suite

"""

__all__ = []

