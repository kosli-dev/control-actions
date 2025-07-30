import pytest
from main import evaluate_attestation


def get_test_case_name(test_case):
    """Extract the test case name from the test case dictionary."""
    return test_case["name"]


# Define test cases as a variable to avoid duplication
TEST_CASES = [
    {
        "name": "TC1: override_attestation_compliant",
        "given": {
            "commit_hash": "abc123",
            "attestation": {
                "attestation_type": "override",
                "is_compliant": True,
                "html_url": "https://example.com/attestation/1",
            },
        },
        "when": "evaluate_attestation is called with a compliant override attestation",
        "then": "should return pass=True with override reason",
        "expected": {
            "commit": "abc123",
            "pass": True,
            "reason": "Overridden as compliant",
            "attestation_url": "https://example.com/attestation/1",
            "review_type": "Override",
        },
    },
    {
        "name": "TC2: override_attestation_non_compliant",
        "given": {
            "commit_hash": "def456",
            "attestation": {
                "attestation_type": "override",
                "is_compliant": False,
                "html_url": "https://example.com/attestation/2",
            },
        },
        "when": "evaluate_attestation is called with a non-compliant override attestation",
        "then": "should return pass=False with override reason",
        "expected": {
            "commit": "def456",
            "pass": False,
            "reason": "Overridden as non-compliant",
            "attestation_url": "https://example.com/attestation/2",
            "review_type": "Override",
        },
    },
    {
        "name": "TC3: pull_request_attestation_with_no_pull_requests",
        "given": {
            "commit_hash": "ghi789",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [],
                "html_url": "https://example.com/attestation/3",
            },
        },
        "when": "evaluate_attestation is called with pull_request type but no pull requests",
        "then": "should return pass=False with no pull requests reason",
        "expected": {
            "commit": "ghi789",
            "pass": False,
            "reason": "No pull requests in attestation",
            "attestation_url": "https://example.com/attestation/3",
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC4: pull_request_no_approvers",
        "given": {
            "commit_hash": "jkl012",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/1",
                        "approvers": [],
                        "commits": [],
                    }
                ],
                "html_url": "https://example.com/attestation/4",
            },
        },
        "when": "evaluate_attestation is called with pull request that has no approvers",
        "then": "should return pass=False with no approvers reason",
        "expected": {
            "commit": "jkl012",
            "pass": False,
            "reason": "Pull request has no approvers",
            "attestation_url": "https://example.com/attestation/4",
            "pr_url": "https://github.com/org/repo/pull/1",
            "pr_number": 1,
            "review_status": "",
            "pr_approvers": [],
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC5: pull_request_with_two_approvers",
        "given": {
            "commit_hash": "mno345",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/2",
                        "approvers": [
                            {"username": "approver1"},
                            {"username": "approver2"},
                        ],
                        "commits": [{"author_username": "author1"}],
                    }
                ],
                "html_url": "https://example.com/attestation/5",
            },
        },
        "when": "evaluate_attestation is called with pull request that has two approvers",
        "then": "should return pass=True with never-alone reason",
        "expected": {
            "commit": "mno345",
            "pass": True,
            "reason": "Pull request demonstrates never-alone code review",
            "attestation_url": "https://example.com/attestation/5",
            "pr_url": "https://github.com/org/repo/pull/2",
            "pr_number": 2,
            "review_status": "",
            "pr_approvers": ["approver1", "approver2"],
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC6: pull_request_one_approver_not_committer",
        "given": {
            "commit_hash": "pqr678",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/3",
                        "approvers": [{"username": "approver1"}],
                        "commits": [{"author_username": "author1"}],
                    }
                ],
                "html_url": "https://example.com/attestation/6",
            },
        },
        "when": "evaluate_attestation is called with pull request that has one approver who is not a committer",
        "then": "should return pass=True with never-alone reason",
        "expected": {
            "commit": "pqr678",
            "pass": True,
            "reason": "Pull request demonstrates never-alone code review",
            "attestation_url": "https://example.com/attestation/6",
            "pr_url": "https://github.com/org/repo/pull/3",
            "pr_number": 3,
            "review_status": "",
            "pr_approvers": ["approver1"],
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC7: pull_request_one_approver_is_committer",
        "given": {
            "commit_hash": "stu901",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/4",
                        "approvers": [{"username": "approver1"}],
                        "commits": [{"author_username": "approver1"}],
                    }
                ],
                "html_url": "https://example.com/attestation/7",
            },
        },
        "when": "evaluate_attestation is called with pull request that has one approver who is also a committer",
        "then": "should return pass=False with approver is committer reason",
        "expected": {
            "commit": "stu901",
            "pass": False,
            "reason": "The only approver of the PR is also a committer",
            "attestation_url": "https://example.com/attestation/7",
            "pr_url": "https://github.com/org/repo/pull/4",
            "pr_number": 4,
            "review_status": "",
            "pr_approvers": ["approver1"],
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC8: pull_request_approver_with_whitespace",
        "given": {
            "commit_hash": "vwx234",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/5",
                        "approvers": [{"username": "  approver1  "}],
                        "commits": [{"author_username": "approver1"}],
                    }
                ],
                "html_url": "https://example.com/attestation/8",
            },
        },
        "when": "evaluate_attestation is called with pull request that has approver with whitespace",
        "then": "should return pass=False with approver is committer reason (whitespace stripped)",
        "expected": {
            "commit": "vwx234",
            "pass": False,
            "reason": "The only approver of the PR is also a committer",
            "attestation_url": "https://example.com/attestation/8",
            "pr_url": "https://github.com/org/repo/pull/5",
            "pr_number": 5,
            "review_status": "",
            "pr_approvers": ["approver1"],
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC9: pull_request_multiple_prs_one_fails",
        "given": {
            "commit_hash": "yza567",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/6",
                        "approvers": [{"username": "approver1"}],
                        "commits": [{"author_username": "approver1"}],
                    },
                    {
                        "url": "https://github.com/org/repo/pull/7",
                        "approvers": [
                            {"username": "approver2"},
                            {"username": "approver3"},
                        ],
                        "commits": [{"author_username": "author1"}],
                    },
                ],
                "html_url": "https://example.com/attestation/9",
            },
        },
        "when": "evaluate_attestation is called with multiple pull requests where first fails",
        "then": "should return pass=False with approver is committer reason (first PR fails)",
        "expected": {
            "commit": "yza567",
            "pass": False,
            "reason": "The only approver of the PR is also a committer",
            "attestation_url": "https://example.com/attestation/9",
            "pr_url": "https://github.com/org/repo/pull/6",
            "pr_number": 6,
            "review_status": "",
            "pr_approvers": ["approver1"],
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC10: pull_request_multiple_prs_all_pass",
        "given": {
            "commit_hash": "bcd890",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/8",
                        "approvers": [{"username": "approver1"}],
                        "commits": [{"author_username": "author1"}],
                    },
                    {
                        "url": "https://github.com/org/repo/pull/9",
                        "approvers": [{"username": "approver2"}],
                        "commits": [{"author_username": "author2"}],
                    },
                ],
                "html_url": "https://example.com/attestation/10",
            },
        },
        "when": "evaluate_attestation is called with multiple pull requests where all pass",
        "then": "should return pass=True with never-alone reason",
        "expected": {
            "commit": "bcd890",
            "pass": True,
            "reason": "Pull request demonstrates never-alone code review",
            "attestation_url": "https://example.com/attestation/10",
            "pr_url": "https://github.com/org/repo/pull/8",
            "pr_number": 8,
            "review_status": "",
            "pr_approvers": ["approver1"],
            "review_type": "Pull request",
        },
    },
    {
        "name": "TC11: unknown_attestation_type",
        "given": {
            "commit_hash": "efg123",
            "attestation": {
                "attestation_type": "unknown_type",
                "html_url": "https://example.com/attestation/11",
            },
        },
        "when": "evaluate_attestation is called with unknown attestation type",
        "then": "should return pass=False with unknown type reason",
        "expected": {
            "commit": "efg123",
            "pass": False,
            "reason": "Attestation is unknown_type, not a pull request or pull-request override",
            "attestation_url": "https://example.com/attestation/11",
        },
    },
    {
        "name": "TC12: pull_request_duplicate_approvers",
        "given": {
            "commit_hash": "klm789",
            "attestation": {
                "attestation_type": "pull_request",
                "pull_requests": [
                    {
                        "url": "https://github.com/org/repo/pull/11",
                        "approvers": [
                            {"username": "approver1"},
                            {"username": "approver1"},  # duplicate
                        ],
                        "commits": [{"author_username": "author1"}],
                    }
                ],
                "html_url": "https://example.com/attestation/13",
            },
        },
        "when": "evaluate_attestation is called with pull request that has duplicate approvers (different to the committer)",
        "then": "should return pass=True (duplicates removed)",
        "expected": {
            "commit": "klm789",
            "pass": True,
            "reason": "Pull request demonstrates never-alone code review",
            "attestation_url": "https://example.com/attestation/13",
            "pr_url": "https://github.com/org/repo/pull/11",
            "pr_number": 11,
            "review_status": "",
            "pr_approvers": ["approver1"],
            "review_type": "Pull request",
        },
    },
]


class TestEvaluateAttestation:
    """Test cases for the evaluate_attestation function."""

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[get_test_case_name(tc) for tc in TEST_CASES],
        scope="class",
    )
    def test_evaluate_attestation(self, test_case):
        """
        Given: {given}
        When: {when}
        Then: {then}
        """

        # Given
        commit_hash = test_case["given"]["commit_hash"]
        attestation = test_case["given"]["attestation"]

        # When
        result = evaluate_attestation(commit_hash, attestation)

        # Then
        expected = test_case["expected"]

        # Enhanced error messages with test case details
        test_case_info = f"\nTest Case: {test_case['name']}\nGiven: {test_case['when']}\nThen: {test_case['then']}\n"

        assert (
            result["commit"] == expected["commit"]
        ), f"{test_case_info}Expected commit {expected['commit']}, got {result['commit']}"
        assert (
            result["pass"] == expected["pass"]
        ), f"{test_case_info}Expected pass {expected['pass']}, got {result['pass']}"
        assert (
            result["reason"] == expected["reason"]
        ), f"{test_case_info}Expected reason '{expected['reason']}', got '{result['reason']}'"
        assert (
            result["attestation_url"] == expected["attestation_url"]
        ), f"{test_case_info}Expected attestation_url {expected['attestation_url']}, got {result['attestation_url']}"

        # Check new fields if they exist in expected
        if "pr_url" in expected:
            assert (
                result["pr_url"] == expected["pr_url"]
            ), f"{test_case_info}Expected pr_url {expected['pr_url']}, got {result['pr_url']}"
            assert (
                result["pr_number"] == expected["pr_number"]
            ), f"{test_case_info}Expected pr_number {expected['pr_number']}, got {result['pr_number']}"
            assert (
                result["review_status"] == expected["review_status"]
            ), f"{test_case_info}Expected review_status {expected['review_status']}, got {result['review_status']}"
            assert (
                result["pr_approvers"] == expected["pr_approvers"]
            ), f"{test_case_info}Expected pr_approvers {expected['pr_approvers']}, got {result['pr_approvers']}"
        else:
            assert (
                "pr_url" not in result
            ), f"{test_case_info}Expected pr_url not to be in result"

        if "review_type" in expected:
            assert (
                result["review_type"] == expected["review_type"]
            ), f"{test_case_info}Expected review_type {expected['review_type']}, got {result['review_type']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
