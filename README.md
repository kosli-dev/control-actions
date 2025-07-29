# Code Review GitHub Actions

This repository contains GitHub Actions for evaluating code review controls in Kosli. These actions help ensure that all commits in a release have been properly reviewed before deployment.

## Overview

The repository provides two main actions:

1. **Create Code Review Attestation Type** - Sets up a custom attestation type for code review evaluations
2. **Code Review** - Evaluates code review attestations for commits between two git references


## Prerequisites

1. **Kosli Account**: You need a Kosli account and API token for both of these actions


## Actions

### 1. Create Code Review Attestation Type

This action creates a custom attestation type in Kosli for storing code review evaluation results.
The action can be run in a manually-triggered workflow or be part of your regular workflow (e.g. on push).

The custom attestation type created by this action is required by the code-review action described below.

#### Usage

```yaml
- name: Create Code Review Attestation Type
  uses: ./.github/actions/create-code-review-type
  with:
    kosli_api_token: ${{ secrets.KOSLI_API_TOKEN }}
    kosli_org: your-organization-name
    kosli_cli_version: v2.11.19
    kosli_host_name: https://app.kosli.com  # Optional, defaults to https://app.kosli.com
```

#### Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `kosli_api_token` | The Kosli API token for authorization | Yes | - |
| `kosli_org` | The Kosli organization name | Yes | - |
| `kosli_cli_version` | Kosli CLI version to use | Yes | - |
| `kosli_host_name` | The Kosli host name | No | `https://app.kosli.com` |

#### What it does

- Sets up the Kosli CLI with the specified version
- Creates a custom attestation type called `code-review` with a schema that validates:
  - `commit`: 40-character SHA hash
  - `pass`: boolean indicating if the commit passed review
  - `reason`: string explaining the result
  - `attestation_url`: optional URL to the attestation


### 2. Code Review

## Prerequisites

1. **Git History**: The repository must have sufficient git history to compare releases
2. **Pull Request Attestations**: Your development flow should have pull request attestations for commits
3. **Custom Attestation Type**: The code review attestation type must be created before running evaluations


**How the evaluation works:**

The action evaluates each commit in your release (between the base reference and the current release reference) to determine if it meets the code review requirements. A commit passes the review control if:

1. **The commit has an associated pull-request attestation with an associated pull request** - This means the code was reviewed through a pull request process
2. **The pull request meets the review criteria** - The pull request is considered passing if:
   - It has at least two different reviewers, OR
   - It has at least one reviewer who is not the same person who made the commit, OR
   - The pull-request attestation has been explicitly marked as compliant (overridden)

If every commit in your release passes these criteria, the overall evaluation is marked as **passed**. If any commit fails to meet the requirements, the evaluation is marked as **failed**.

The action then reports these evaluation results to Kosli as an attestation.

#### Usage

```yaml
- name: Evaluate Code Review Control
  uses: ./.github/actions/code-review
  with:
    base_ref: v1.0.0
    release_ref: v1.1.0
    kosli_api_token: ${{ secrets.KOSLI_API_TOKEN }}
    kosli_org: your-organization-name
    kosli_search_flow_name: development
    kosli_code_review_attestation_type: code-review
    kosli_code_review_attestation_name: release-code-review
    kosli_code_review_flow_name: releases
    kosli_code_review_trail_name: v1.1.0
    kosli_host_name: https://app.kosli.com  # Optional
```

#### Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base_ref` | The base git ref (e.g., previous release tag) | Yes | - |
| `release_ref` | The git ref being released | Yes | - |
| `kosli_api_token` | The Kosli API token for authorization | Yes | - |
| `kosli_org` | The Kosli organization name | Yes | - |
| `kosli_search_flow_name` | The Kosli flow where source attestations are stored | Yes | - |
| `kosli_code_review_attestation_type` | The attestation type for reporting code review results | Yes | - |
| `kosli_code_review_attestation_name` | The attestation name for reporting code review results | Yes | - |
| `kosli_code_review_flow_name` | The flow name to report code review attestations to | Yes | - |
| `kosli_code_review_trail_name` | The trail name to report code review attestations to | Yes | - |
| `kosli_host_name` | The Kosli host name | No | `https://app.kosli.com` |

#### What it does

1. **Gets commit list**: Retrieves all commits between `base_ref` and `release_ref`
2. **Fetches attestations**: Queries Kosli API for pull request attestations for each commit
3. **Evaluates reviews**: Checks if each commit passes the code-review control
4. **Reports results**: Creates a new attestation in the specified flow/trail with evaluation results

#### Output

The action generates:
- `attestations_evidence.json`: Raw attestation data from Kosli
- `evaluation_results.json`: Processed evaluation results
- A new attestation in the specified Kosli flow/trail with the evaluation summary

## Complete Workflow Example

Here's a complete example of how to use both actions in a release workflow:

```yaml
name: Release with Code Review Control

on:
  push:
    tags:
      - 'v*'

jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Important: fetch all history for git operations

      - name: Create Code Review Attestation Type
        uses: ./.github/actions/create-code-review-type
        with:
          kosli_api_token: ${{ secrets.KOSLI_API_TOKEN }}
          kosli_org: my-organization
          kosli_cli_version: v2.11.19

  evaluate-code-review:
    runs-on: ubuntu-latest
    needs: setup
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get previous release tag
        id: previous_release
        run: |
          PREVIOUS_TAG=$(git tag --sort=-version:refname | head -n 2 | tail -n 1)
          echo "tag=$PREVIOUS_TAG" >> $GITHUB_OUTPUT

      - name: Evaluate Code Review Control
        uses: ./.github/actions/code-review
        with:
          base_ref: ${{ steps.previous-tag.outputs.previous_tag }}
          release_ref: ${{ github.ref_name }}
          kosli_api_token: ${{ secrets.KOSLI_API_TOKEN }}
          kosli_org: my-organization
          kosli_search_flow_name: development
          kosli_code_review_attestation_type: code-review
          kosli_code_review_attestation_name: release-code-review
          kosli_code_review_flow_name: releases
          kosli_code_review_trail_name: ${{ github.ref_name }}
```


## Troubleshooting

### Common Issues

1. **No commits found**: Ensure `base_ref` exists and `fetch-depth: 0` is set in checkout
2. **API errors**: Check that the Kosli API token is valid and has proper permissions
3. **Custom attestation type not found**: Run the create action before the evaluation action

### Debugging

The actions generate detailed logs for debugging:
- Check the action logs for error messages
