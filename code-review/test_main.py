import pytest
from unittest.mock import patch
from main import evaluate_attestation, evaluate_all, get_commit_list


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


# Define test cases for evaluate_all function
EVALUATE_ALL_TEST_CASES = [
    {
        "name": "TC_ALL1: empty_data",
        "given": {"data": {}},
        "when": "evaluate_all is called with empty data",
        "then": "should return empty list",
        "expected": [],
    },
    {
        "name": "TC_ALL2: single_commit_no_attestations",
        "given": {"data": {"abc123": []}},
        "when": "evaluate_all is called with single commit that has no attestations",
        "then": "should return single result with pass=False and no attestations reason",
        "expected": [
            {
                "commit": "abc123",
                "pass": False,
                "reason": "No attestations found",
                "attestation_url": None,
            }
        ],
    },
    {
        "name": "TC_ALL3: single_commit_with_attestation",
        "given": {
            "data": {
                "abc123": [
                    {
                        "attestation_type": "override",
                        "is_compliant": True,
                        "html_url": "https://example.com/attestation/1",
                    }
                ]
            }
        },
        "when": "evaluate_all is called with single commit that has one attestation",
        "then": "should return single result evaluating the first attestation",
        "expected": [
            {
                "commit": "abc123",
                "pass": True,
                "reason": "Overridden as compliant",
                "attestation_url": "https://example.com/attestation/1",
                "review_type": "Override",
            }
        ],
    },
    {
        "name": "TC_ALL4: multiple_commits_mixed_results",
        "given": {
            "data": {
                "abc123": [
                    {
                        "attestation_type": "override",
                        "is_compliant": True,
                        "html_url": "https://example.com/attestation/1",
                    }
                ],
                "def456": [],
                "ghi789": [
                    {
                        "attestation_type": "pull_request",
                        "pull_requests": [
                            {
                                "url": "https://github.com/org/repo/pull/1",
                                "approvers": [{"username": "approver1"}],
                                "commits": [{"author_username": "author1"}],
                            }
                        ],
                        "html_url": "https://example.com/attestation/2",
                    }
                ],
            }
        },
        "when": "evaluate_all is called with multiple commits with mixed attestations",
        "then": "should return results for all commits evaluating first attestation of each",
        "expected": [
            {
                "commit": "abc123",
                "pass": True,
                "reason": "Overridden as compliant",
                "attestation_url": "https://example.com/attestation/1",
                "review_type": "Override",
            },
            {
                "commit": "def456",
                "pass": False,
                "reason": "No attestations found",
                "attestation_url": None,
            },
            {
                "commit": "ghi789",
                "pass": True,
                "reason": "Pull request demonstrates never-alone code review",
                "attestation_url": "https://example.com/attestation/2",
                "pr_url": "https://github.com/org/repo/pull/1",
                "pr_number": 1,
                "review_status": "",
                "pr_approvers": ["approver1"],
                "review_type": "Pull request",
            },
        ],
    },
    {
        "name": "TC_ALL5: multiple_attestations_ignores_second",
        "given": {
            "data": {
                "abc123": [
                    {
                        "attestation_type": "override",
                        "is_compliant": False,
                        "html_url": "https://example.com/attestation/1",
                    },
                    {
                        "attestation_type": "override",
                        "is_compliant": True,
                        "html_url": "https://example.com/attestation/2",
                    },
                ]
            }
        },
        "when": "evaluate_all is called with commit that has multiple attestations",
        "then": "should return result evaluating only the first attestation",
        "expected": [
            {
                "commit": "abc123",
                "pass": False,
                "reason": "Overridden as non-compliant",
                "attestation_url": "https://example.com/attestation/1",
                "review_type": "Override",
            }
        ],
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


class TestEvaluateAll:
    """Test cases for the evaluate_all function."""

    @pytest.mark.parametrize(
        "test_case",
        EVALUATE_ALL_TEST_CASES,
        ids=[get_test_case_name(tc) for tc in EVALUATE_ALL_TEST_CASES],
        scope="class",
    )
    def test_evaluate_all(self, test_case):
        """
        Given: {given}
        When: {when}
        Then: {then}
        """

        # Given
        data = test_case["given"]["data"]

        # When
        result = evaluate_all(data)

        # Then
        expected = test_case["expected"]

        # Enhanced error messages with test case details
        test_case_info = f"\nTest Case: {test_case['name']}\nGiven: {test_case['when']}\nThen: {test_case['then']}\n"

        assert len(result) == len(
            expected
        ), f"{test_case_info}Expected {len(expected)} results, got {len(result)}"

        for i, (actual_result, expected_result) in enumerate(zip(result, expected)):
            result_info = f"{test_case_info}Result {i}: "

            # Check basic fields
            assert (
                actual_result["commit"] == expected_result["commit"]
            ), f"{result_info}Expected commit {expected_result['commit']}, got {actual_result['commit']}"
            assert (
                actual_result["pass"] == expected_result["pass"]
            ), f"{result_info}Expected pass {expected_result['pass']}, got {actual_result['pass']}"
            assert (
                actual_result["reason"] == expected_result["reason"]
            ), f"{result_info}Expected reason '{expected_result['reason']}', got '{actual_result['reason']}'"
            assert (
                actual_result["attestation_url"] == expected_result["attestation_url"]
            ), f"{result_info}Expected attestation_url {expected_result['attestation_url']}, got {actual_result['attestation_url']}"

            # Check optional fields if they exist in expected
            if "review_type" in expected_result:
                assert (
                    actual_result["review_type"] == expected_result["review_type"]
                ), f"{result_info}Expected review_type {expected_result['review_type']}, got {actual_result['review_type']}"

            if "pr_url" in expected_result:
                assert (
                    actual_result["pr_url"] == expected_result["pr_url"]
                ), f"{result_info}Expected pr_url {expected_result['pr_url']}, got {actual_result['pr_url']}"
                assert (
                    actual_result["pr_number"] == expected_result["pr_number"]
                ), f"{result_info}Expected pr_number {expected_result['pr_number']}, got {actual_result['pr_number']}"
                assert (
                    actual_result["review_status"] == expected_result["review_status"]
                ), f"{result_info}Expected review_status {expected_result['review_status']}, got {actual_result['review_status']}"
                assert (
                    actual_result["pr_approvers"] == expected_result["pr_approvers"]
                ), f"{result_info}Expected pr_approvers {expected_result['pr_approvers']}, got {actual_result['pr_approvers']}"


class TestGetCommitList:
    """Test cases for the get_commit_list function."""

    @patch("main.subprocess.run")
    def test_get_commit_list_success(self, mock_run):
        """Test successful retrieval of commit list between two refs."""
        # Mock the first call (git rev-parse) - base ref exists
        mock_run.return_value.returncode = 0

        # Mock the second call (git log) - return some commit hashes
        mock_run.return_value.stdout = "abc123\ndef456\nghi789\n"
        mock_run.return_value.stderr = ""

        result = get_commit_list("v1.0.0", "HEAD")

        # Verify the result
        expected_commits = ["abc123", "def456", "ghi789"]
        assert result == expected_commits

        # Verify subprocess.run was called correctly
        assert mock_run.call_count == 2

        # Check first call (git rev-parse)
        first_call = mock_run.call_args_list[0]
        assert first_call[0][0] == ["git", "rev-parse", "--verify", "v1.0.0"]

        # Check second call (git log)
        second_call = mock_run.call_args_list[1]
        assert second_call[0][0] == ["git", "log", "--format=%H", "v1.0.0..HEAD"]

    @patch("main.subprocess.run")
    def test_get_commit_list_base_ref_not_found(self, mock_run):
        """Test when base ref doesn't exist."""
        # Mock the first call (git rev-parse) - base ref doesn't exist
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "fatal: ambiguous argument 'v1.0.0': unknown revision or path not in working tree."

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            get_commit_list("v1.0.0", "HEAD")

        assert exc_info.value.code == 1

        # Verify only one call was made
        assert mock_run.call_count == 1
        assert mock_run.call_args[0][0] == ["git", "rev-parse", "--verify", "v1.0.0"]

    @patch("main.subprocess.run")
    def test_get_commit_list_empty_result(self, mock_run):
        """Test when no commits are found between refs."""
        # Mock the first call (git rev-parse) - base ref exists
        mock_run.return_value.returncode = 0

        # Mock the second call (git log) - return empty result
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        result = get_commit_list("v1.0.0", "HEAD")

        # Should return empty list
        assert result == []

    @patch("main.subprocess.run")
    def test_get_commit_list_with_whitespace(self, mock_run):
        """Test handling of whitespace in git log output."""
        # Mock the first call (git rev-parse) - base ref exists
        mock_run.return_value.returncode = 0

        # Mock the second call (git log) - return commits with whitespace
        mock_run.return_value.stdout = "  abc123  \n  def456  \n  ghi789  \n"
        mock_run.return_value.stderr = ""

        result = get_commit_list("v1.0.0", "HEAD")

        # Should return cleaned commit hashes
        expected_commits = ["abc123", "def456", "ghi789"]
        assert result == expected_commits

    @patch("main.subprocess.run")
    def test_get_commit_list_single_commit(self, mock_run):
        """Test when only one commit is found."""
        # Mock the first call (git rev-parse) - base ref exists
        mock_run.return_value.returncode = 0

        # Mock the second call (git log) - return single commit
        mock_run.return_value.stdout = "abc123\n"
        mock_run.return_value.stderr = ""

        result = get_commit_list("v1.0.0", "HEAD")

        # Should return single commit
        assert result == ["abc123"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
