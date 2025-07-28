#! /usr/bin/env python3
import json
import sys
import requests
import argparse
import subprocess
from typing import List, Optional


def get_commit_list(base_ref: str, release_ref: str) -> List[str]:
    """
    Get list of commit SHAs between base_ref and release_ref.

    Args:
        base_ref: The base git ref (e.g. tag)
        release_ref: The release git ref (e.g. HEAD)

    Returns:
        List of commit SHAs
    """
    try:
        # Check if we are on a detached HEAD
        result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print("Error: Currently on a detached HEAD", file=sys.stderr)
            sys.exit(1)

        # Check if the base ref exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", base_ref],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Base ref exists, get all commit SHAs between release_ref and base_ref (excluding the base_ref commit)
            result = subprocess.run(
                ["git", "log", "--format=%H", f"{base_ref}..{release_ref}"],
                capture_output=True,
                text=True,
                check=True,
            )
            commit_list = [
                commit.strip()
                for commit in result.stdout.strip().split("\n")
                if commit.strip()
            ]
            print(f"Using commits between {release_ref} and {base_ref} ref")
        else:
            # Base ref doesn't exist, fail
            print(f"Error: Ref {base_ref} not found", file=sys.stderr)
            sys.exit(1)

        print(f"Found commits: {' '.join(commit_list)}")
        return commit_list

    except subprocess.CalledProcessError as e:
        print(f"Error executing git command: {e}", file=sys.stderr)
        sys.exit(1)


def make_attestations_request(
    host: str,
    org: str,
    flow_name: Optional[str],
    commit_list: List[str],
    api_token: str,
    attestation_type: str = "pull_request",
) -> dict:
    """
    Make API request to list attestations for criteria.

    Args:
        host: The API host URL
        org: Organization name
        flow_name: Name of the flow (can be None)
        commit_list: List of commit SHAs
        attestation_type: Type of attestation to filter by
        api_token: API token for authorization

    Returns:
        JSON response from the API
    """
    url = f"{host}/api/v2/attestations/{org}/list_attestations_for_criteria"

    # Build query parameters
    params = {"attestation_type": attestation_type}

    # Only include flow_name if it's not None
    if flow_name is not None:
        params["flow_name"] = flow_name

    # Add commit_list parameters - use list to allow multiple values
    params["commit_list"] = commit_list

    headers = {"accept": "application/json", "Authorization": f"Bearer {api_token}"}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        sys.exit(1)


def evaluate_attestation(commit_hash, attestation):
    pull_requests = attestation.get("pull_requests", [])
    result = {
        "commit": commit_hash,
        "pass": False,
        "reason": "",
        "attestation_url": attestation.get("html_url", ""),
    }
    pr_url = pull_requests[0].get("url", "") if pull_requests else ""
    if pr_url:
        result["pr_url"] = pr_url

    att_type = attestation.get("attestation_type")
    is_compliant = attestation.get("is_compliant", False)

    if att_type == "override":
        if is_compliant:
            result["pass"] = True
            result["reason"] = "Overridden as compliant"
        else:
            result["reason"] = "Overridden as non-compliant"
        return result

    if att_type == "pull_request":
        if not pull_requests:
            result["reason"] = "No pull requests in attestation"
            return result

        for pr in pull_requests:
            approvers = pr.get("approvers", [])
            commits = pr.get("commits", [])

            if not approvers:
                result["reason"] = "Pull request has no approvers"
                return result

            # Clean up usernames (e.g., whitespace)
            approver_usernames = list(
                {a["username"].strip() for a in approvers if "username" in a}
            )
            if len(approver_usernames) >= 2:
                continue  # Passes this PR

            # Otherwise, check that ALL approvers are NOT in the commit authors
            commit_authors = [c.get("author_username") for c in commits]
            valid = approver_usernames[0].strip() not in commit_authors

            if not valid:
                result["reason"] = "The only approver of the PR is also a committer"
                return result

        result["pass"] = True
        result["reason"] = "Pull request demonstrates never-alone code review"
        return result

    result["reason"] = (
        f"Attestation is {att_type}, not a pull request or pull-request override"
    )
    return result


def evaluate_all(data):
    results = []
    for commit_hash, attestations in data.items():
        if not attestations:
            results.append(
                {
                    "commit": commit_hash,
                    "pass": False,
                    "reason": "No attestations found",
                    "attestation_url": None,
                }
            )
            continue

        # Evaluate only the first attestation
        result = evaluate_attestation(commit_hash, attestations[0])
        results.append(result)

    return results


def report_code_review_attestations(
    host: str,
    org: str,
    flow_name: str,
    trail_name: str,
    api_token: str,
    custom_attestation_data: List[dict],
    evidence_file: str,
) -> dict:
    """
    Make API request to report code review custom attestations.

    Args:
        host: The API host URL
        org: Organization name
        flow_name: Name of the flow to report the attestations to
        trail_name: Name of the trail to report the attestations to
        api_token: API token for authorization
        custom_attestation_data: Custom attestation data to report
        evidence_file: Path to the file to upload as attachment

    Returns:
        JSON response from the API
    """
    url = f"{host}/api/v2/attestations/{org}/{flow_name}/trail/{trail_name}/custom"

    headers = {"Authorization": f"Bearer {api_token}"}

    # Prepare the multi-part form data
    files = {
        "data_json": (
            None,
            json.dumps({"attestation_data": custom_attestation_data}),
            "application/json",
        ),
        "attachment_file": (
            evidence_file,
            open(evidence_file, "rb"),
            "application/json",
        ),
    }

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Ensure the file is closed
        if "attachment_file" in files:
            files["attachment_file"][1].close()


def main():
    parser = argparse.ArgumentParser(description="Evaluate code review attestations")
    parser.add_argument(
        "--kosli-host-name", default="https://api.kosli.com", help="API host URL"
    )
    parser.add_argument("--kosli-org", required=True, help="Organization name")
    parser.add_argument(
        "--kosli-search-flow-name",
        required=True,
        help="Flow name to search for attestations in",
    )
    parser.add_argument("--base-ref", required=True, help="Base git ref (e.g. tag)")
    parser.add_argument(
        "--release-ref", required=True, help="Release git ref (e.g. tag)"
    )
    parser.add_argument(
        "--kosli-code-review-flow-name",
        required=True,
        help="Flow name to report code review attestations to",
    )
    parser.add_argument(
        "--kosli-code-review-trail-name",
        required=True,
        help="Trail name to report code review attestations to",
    )
    parser.add_argument(
        "--kosli-api-token", required=True, help="Kosli API token for authorization"
    )
    parser.add_argument("--input-file", help="Input JSON file (optional, for testing)")
    parser.add_argument(
        "--output-file",
        default="evaluation_results.json",
        help="Output JSON file (default: evaluation_results.json)",
    )

    args = parser.parse_args()

    # Get the commit list
    commit_list = get_commit_list(args.base_ref, args.release_ref)

    # Make API request
    data = make_attestations_request(
        args.kosli_host_name,
        args.kosli_org,
        args.kosli_search_flow_name,
        commit_list,
        args.kosli_api_token,
    )

    # Save output to file
    with open("attestations_evidence.json", "w") as f:
        json.dump(data, f, indent=2)

    output = evaluate_all(data)

    # Save output to file
    with open(args.output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Evaluation results saved to: {args.output_file}")
    print(json.dumps(output, indent=2))

    # Report the code review attestations
    try:
        response = report_code_review_attestations(
            args.kosli_host_name,
            args.kosli_org,
            args.kosli_code_review_flow_name,
            args.kosli_code_review_trail_name,
            args.kosli_api_token,
            output,
            "attestations_evidence.json",
        )
        print("Code review attestations reported successfully")
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f"Error reporting code review attestations: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
