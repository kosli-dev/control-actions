#!/usr/bin/env python3
"""
Script to run the unit tests with specific configuration options.
"""

import subprocess
import sys


def run_tests():
    """Run the unit tests with specific configuration."""

    # Command line options for pytest
    pytest_options = [
        "python3",
        "-m",
        "pytest",
        "test_main.py",  # Test file to run
        "-v",  # verbose output
        "--tb=short",  # short traceback format
        "--maxfail=0",  # Run all tests (don't stop on first failure)
        "--disable-warnings",  # Suppress warnings
        "--no-header",  # Don't show pytest header
        "-s",  # Don't capture output (allows print statements and full error display)
    ]

    print("Running unit tests ...")
    print("=" * 60)

    try:
        result = subprocess.run(pytest_options, check=False)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Please install it with: pip install pytest")
        return 1


def run_tests_with_custom_order():
    """Run tests with explicit ordering using pytest-ordering plugin."""

    pytest_options = [
        "python3",
        "-m",
        "pytest",
        "test_main.py",
        "-v",
        "--tb=short",
        "--maxfail=0",
        "--durations=10",
    ]

    try:
        result = subprocess.run(pytest_options, check=False)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Please install it with: pip install pytest")
        return 1


if __name__ == "__main__":
    print("Unit Test Runner for evaluate_attestation function")
    print("=" * 60)

    # Run tests with default configuration
    exit_code = run_tests()

    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Some tests failed (exit code: {exit_code})")

    sys.exit(exit_code)
