import pytest
from unittest.mock import patch, Mock, mock_open
from main import (
    evaluate_attestation,
    evaluate_all,
    get_commit_list,
    make_attestations_request,
    report_code_review_attestation,
)
import requests


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
        """
        Given: A base ref and HEAD ref that exist in the repository
        When: get_commit_list is called with valid refs
        Then: Should return a list of commit hashes between the refs
        """
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
        """
        Given: A base ref that doesn't exist in the repository
        When: get_commit_list is called with invalid base ref
        Then: Should exit with error code 1
        """
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
        """
        Given: Valid refs but no commits between them
        When: get_commit_list is called with refs that have no commits between them
        Then: Should return an empty list
        """
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
        """
        Given: Git log output with whitespace around commit hashes
        When: get_commit_list is called and git returns hashes with whitespace
        Then: Should return cleaned commit hashes without whitespace
        """
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
        """
        Given: Valid refs with only one commit between them
        When: get_commit_list is called with refs that have one commit between them
        Then: Should return a list with the single commit hash
        """
        # Mock the first call (git rev-parse) - base ref exists
        mock_run.return_value.returncode = 0

        # Mock the second call (git log) - return single commit
        mock_run.return_value.stdout = "abc123\n"
        mock_run.return_value.stderr = ""

        result = get_commit_list("v1.0.0", "HEAD")

        # Should return single commit
        assert result == ["abc123"]


class TestMakeAttestationsRequest:
    """Test cases for the make_attestations_request function."""

    @patch("main.requests.get")
    def test_make_attestations_request_success_with_flow_name(self, mock_get):
        """
        Given: Valid API parameters including flow_name and commit list
        When: make_attestations_request is called with flow_name parameter
        Then: Should return attestations data and make correct API call
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"attestations": {"abc123": []}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Call the function
        result = make_attestations_request(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            commit_list=["abc123", "def456"],
            api_token="test-token",
            attestation_type="pull_request",
        )

        # Verify the result
        assert result == {"attestations": {"abc123": []}}

        # Verify the request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check URL
        assert (
            call_args[0][0]
            == "https://app.kosli.com/api/v2/attestations/test-org/list_attestations_for_criteria"
        )

        # Check parameters
        expected_params = {
            "attestation_type": "pull_request",
            "flow_name": "test-flow",
            "commit_list": ["abc123", "def456"],
        }
        assert call_args[1]["params"] == expected_params

        # Check headers
        expected_headers = {
            "accept": "application/json",
            "Authorization": "Bearer test-token",
        }
        assert call_args[1]["headers"] == expected_headers

    @patch("main.requests.get")
    def test_make_attestations_request_success_without_flow_name(self, mock_get):
        """
        Given: Valid API parameters without flow_name
        When: make_attestations_request is called without flow_name parameter
        Then: Should return attestations data and make API call without flow_name in params
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"attestations": {"abc123": []}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Call the function
        result = make_attestations_request(
            host="https://app.kosli.com",
            org="test-org",
            flow_name=None,
            commit_list=["abc123"],
            api_token="test-token",
            attestation_type="override",
        )

        # Verify the result
        assert result == {"attestations": {"abc123": []}}

        # Verify the request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check parameters (should not include flow_name)
        expected_params = {"attestation_type": "override", "commit_list": ["abc123"]}
        assert call_args[1]["params"] == expected_params

    @patch("main.requests.get")
    def test_make_attestations_request_http_error(self, mock_get):
        """
        Given: API request that returns HTTP error
        When: make_attestations_request is called and server returns HTTP error
        Then: Should exit with error code 1
        """
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            make_attestations_request(
                host="https://app.kosli.com",
                org="test-org",
                flow_name="test-flow",
                commit_list=["abc123"],
                api_token="test-token",
            )

        assert exc_info.value.code == 1

    @patch("main.requests.get")
    def test_make_attestations_request_connection_error(self, mock_get):
        """
        Given: Network connection failure
        When: make_attestations_request is called and connection fails
        Then: Should exit with error code 1
        """
        # Mock connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            make_attestations_request(
                host="https://app.kosli.com",
                org="test-org",
                flow_name="test-flow",
                commit_list=["abc123"],
                api_token="test-token",
            )

        assert exc_info.value.code == 1

    @patch("main.requests.get")
    def test_make_attestations_request_timeout_error(self, mock_get):
        """
        Given: API request that times out
        When: make_attestations_request is called and request times out
        Then: Should exit with error code 1
        """
        # Mock timeout error
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            make_attestations_request(
                host="https://app.kosli.com",
                org="test-org",
                flow_name="test-flow",
                commit_list=["abc123"],
                api_token="test-token",
            )

        assert exc_info.value.code == 1

    @patch("main.requests.get")
    def test_make_attestations_request_empty_commit_list(self, mock_get):
        """
        Given: Empty commit list parameter
        When: make_attestations_request is called with empty commit list
        Then: Should make API call with empty commit_list parameter and return result
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"attestations": {}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Call the function
        result = make_attestations_request(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            commit_list=[],
            api_token="test-token",
        )

        # Verify the result
        assert result == {"attestations": {}}

        # Verify parameters include empty commit_list
        call_args = mock_get.call_args
        expected_params = {
            "attestation_type": "pull_request",
            "flow_name": "test-flow",
            "commit_list": [],
        }
        assert call_args[1]["params"] == expected_params

    @patch("main.requests.get")
    def test_make_attestations_request_custom_attestation_type(self, mock_get):
        """
        Given: Custom attestation type parameter
        When: make_attestations_request is called with custom attestation type
        Then: Should make API call with custom attestation_type parameter
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"attestations": {"abc123": []}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Call the function
        result = make_attestations_request(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            commit_list=["abc123"],
            api_token="test-token",
            attestation_type="custom_type",
        )

        # Verify the result
        assert result == {"attestations": {"abc123": []}}

        # Verify custom attestation type is used
        call_args = mock_get.call_args
        expected_params = {
            "attestation_type": "custom_type",
            "flow_name": "test-flow",
            "commit_list": ["abc123"],
        }
        assert call_args[1]["params"] == expected_params

    @patch("main.requests.get")
    def test_make_attestations_request_complex_response(self, mock_get):
        """
        Given: Complex API response with multiple attestations
        When: make_attestations_request is called and returns complex data
        Then: Should return the complex response data correctly
        """
        # Mock complex response
        complex_response = {
            "attestations": {
                "abc123": [
                    {
                        "attestation_type": "pull_request",
                        "html_url": "https://example.com/attestation/1",
                        "pull_requests": [
                            {
                                "url": "https://github.com/org/repo/pull/1",
                                "approvers": [{"username": "approver1"}],
                                "commits": [{"author_username": "author1"}],
                            }
                        ],
                    }
                ],
                "def456": [],
            }
        }
        mock_response = Mock()
        mock_response.json.return_value = complex_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Call the function
        result = make_attestations_request(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            commit_list=["abc123", "def456"],
            api_token="test-token",
        )

        # Verify the complex result is returned correctly
        assert result == complex_response
        assert "abc123" in result["attestations"]
        assert "def456" in result["attestations"]
        assert len(result["attestations"]["abc123"]) == 1
        assert len(result["attestations"]["def456"]) == 0


class TestReportCodeReviewAttestation:
    """Test cases for the report_code_review_attestation function."""

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_success(self, mock_post, mock_file):
        """
        Given: Valid attestation data and evidence file
        When: report_code_review_attestation is called with valid parameters
        Then: Should successfully post attestation data and return response
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "id": "attestation-123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test data
        custom_attestation_data = [
            {
                "commit": "abc123",
                "pass": True,
                "reason": "Pull request demonstrates never-alone code review",
                "attestation_url": "https://example.com/attestation/1",
            }
        ]

        # Call the function
        result = report_code_review_attestation(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            trail_name="test-trail",
            attestation_type="code_review",
            attestation_name="test-attestation",
            api_token="test-token",
            custom_attestation_data=custom_attestation_data,
            evidence_file="test_evidence.json",
        )

        # Verify the result
        assert result == {"status": "success", "id": "attestation-123"}

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check URL
        expected_url = "https://app.kosli.com/api/v2/attestations/test-org/test-flow/trail/test-trail/custom"
        assert call_args[0][0] == expected_url

        # Check headers
        expected_headers = {"Authorization": "Bearer test-token"}
        assert call_args[1]["headers"] == expected_headers

        # Check files parameter
        files = call_args[1]["files"]
        assert "data_json" in files
        assert "attachment_file" in files

        # Check data_json content
        data_json = files["data_json"]
        assert data_json[0] is None  # filename is None
        assert data_json[2] == "application/json"  # content type

        # Parse the JSON data to verify content
        import json

        json_data = json.loads(data_json[1])
        assert json_data["type_name"] == "code_review"
        assert json_data["attestation_name"] == "test-attestation"
        assert json_data["attestation_data"] == custom_attestation_data

        # Check attachment_file
        attachment_file = files["attachment_file"]
        assert attachment_file[0] == "test_evidence.json"
        assert attachment_file[2] == "application/json"

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_http_error(self, mock_post, mock_file):
        """
        Given: API request that returns HTTP error
        When: report_code_review_attestation is called and server returns HTTP error
        Then: Should exit with error code 1
        """
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Bad Request"
        )
        mock_response.text = "Bad request error"
        mock_post.return_value = mock_response

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            report_code_review_attestation(
                host="https://app.kosli.com",
                org="test-org",
                flow_name="test-flow",
                trail_name="test-trail",
                attestation_type="code_review",
                attestation_name="test-attestation",
                api_token="test-token",
                custom_attestation_data=[],
                evidence_file="test_evidence.json",
            )

        assert exc_info.value.code == 1

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_connection_error(
        self, mock_post, mock_file
    ):
        """
        Given: Network connection failure
        When: report_code_review_attestation is called and connection fails
        Then: Should exit with error code 1
        """
        # Mock connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            report_code_review_attestation(
                host="https://app.kosli.com",
                org="test-org",
                flow_name="test-flow",
                trail_name="test-trail",
                attestation_type="code_review",
                attestation_name="test-attestation",
                api_token="test-token",
                custom_attestation_data=[],
                evidence_file="test_evidence.json",
            )

        assert exc_info.value.code == 1

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_timeout_error(self, mock_post, mock_file):
        """
        Given: API request that times out
        When: report_code_review_attestation is called and request times out
        Then: Should exit with error code 1
        """
        # Mock timeout error
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            report_code_review_attestation(
                host="https://app.kosli.com",
                org="test-org",
                flow_name="test-flow",
                trail_name="test-trail",
                attestation_type="code_review",
                attestation_name="test-attestation",
                api_token="test-token",
                custom_attestation_data=[],
                evidence_file="test_evidence.json",
            )

        assert exc_info.value.code == 1

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_empty_data(self, mock_post, mock_file):
        """
        Given: Empty attestation data list
        When: report_code_review_attestation is called with empty data
        Then: Should successfully post empty attestation data
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Call the function with empty data
        result = report_code_review_attestation(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            trail_name="test-trail",
            attestation_type="code_review",
            attestation_name="test-attestation",
            api_token="test-token",
            custom_attestation_data=[],
            evidence_file="test_evidence.json",
        )

        # Verify the result
        assert result == {"status": "success"}

        # Verify the JSON data contains empty list
        call_args = mock_post.call_args
        files = call_args[1]["files"]
        data_json = files["data_json"]

        import json

        json_data = json.loads(data_json[1])
        assert json_data["attestation_data"] == []

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_complex_data(self, mock_post, mock_file):
        """
        Given: Complex attestation data with multiple fields
        When: report_code_review_attestation is called with complex data
        Then: Should successfully serialize and post complex attestation data
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Complex test data
        complex_data = [
            {
                "commit": "abc123",
                "pass": True,
                "reason": "Pull request demonstrates never-alone code review",
                "attestation_url": "https://example.com/attestation/1",
                "pr_url": "https://github.com/org/repo/pull/1",
                "pr_number": 1,
                "review_status": "approved",
                "pr_approvers": ["approver1", "approver2"],
                "review_type": "Pull request",
            },
            {
                "commit": "def456",
                "pass": False,
                "reason": "No attestations found",
                "attestation_url": None,
            },
        ]

        # Call the function
        result = report_code_review_attestation(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            trail_name="test-trail",
            attestation_type="custom_review",
            attestation_name="complex-attestation",
            api_token="test-token",
            custom_attestation_data=complex_data,
            evidence_file="complex_evidence.json",
        )

        # Verify the result
        assert result == {"status": "success"}

        # Verify the complex data is correctly serialized
        call_args = mock_post.call_args
        files = call_args[1]["files"]
        data_json = files["data_json"]

        import json

        json_data = json.loads(data_json[1])
        assert json_data["type_name"] == "custom_review"
        assert json_data["attestation_name"] == "complex-attestation"
        assert json_data["attestation_data"] == complex_data
        assert len(json_data["attestation_data"]) == 2

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_file_closure(self, mock_post, mock_file):
        """
        Given: Evidence file that needs to be opened and closed
        When: report_code_review_attestation is called successfully
        Then: Should properly close the file after the request
        """
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Call the function
        result = report_code_review_attestation(
            host="https://app.kosli.com",
            org="test-org",
            flow_name="test-flow",
            trail_name="test-trail",
            attestation_type="code_review",
            attestation_name="test-attestation",
            api_token="test-token",
            custom_attestation_data=[],
            evidence_file="test_evidence.json",
        )

        # Verify the file was opened and closed
        mock_file.assert_called_once_with("test_evidence.json", "rb")
        mock_file().close.assert_called_once()

    @patch("builtins.open", new_callable=mock_open, read_data="test file content")
    @patch("main.requests.post")
    def test_report_code_review_attestation_file_closure_on_error(
        self, mock_post, mock_file
    ):
        """
        Given: Evidence file that needs to be opened and closed
        When: report_code_review_attestation is called and an error occurs
        Then: Should still properly close the file despite the error
        """
        # Mock error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Internal Server Error"
        )
        mock_response.text = "Server error"
        mock_post.return_value = mock_response

        # Should exit with error, but file should still be closed
        with pytest.raises(SystemExit):
            report_code_review_attestation(
                host="https://app.kosli.com",
                org="test-org",
                flow_name="test-flow",
                trail_name="test-trail",
                attestation_type="code_review",
                attestation_name="test-attestation",
                api_token="test-token",
                custom_attestation_data=[],
                evidence_file="test_evidence.json",
            )

        # Verify the file was still closed despite the error
        mock_file().close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
