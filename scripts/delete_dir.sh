#!/usr/bin/env bash
# delete_dir_open_pr.sh
# Delete a folder from a GitHub repo WITHOUT cloning:
#  - creates a new branch from base
#  - commits deletions (batched)
#  - opens a Pull Request
#
# Usage:
#   ./delete_dir_open_pr.sh owner/repo [base-branch] [dir] [new-branch]
# Example:
#   ./delete_dir_open_pr.sh octo-org/my-repo main .hoa delete-hoa-$(date +%Y%m%d%H%M%S)

set -euo pipefail

command -v gh >/dev/null 2>&1 || { echo "ERROR: gh (GitHub CLI) required." >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq required." >&2; exit 1; }

REPO="${1:-}"
BASE_BRANCH="${2:-}"
DIR="${3:-.hoa}"
NEW_BRANCH="${4:-delete-dir-$(date +%Y%m%d%H%M%S)}"
COMMIT_MSG="ci: delete '${DIR}' directory"
PR_TITLE="[automated-generated-pr] ci: delete '${DIR}' directory"
PR_BODY="This PR removes the '${DIR}' directory and all files under it."

if [[ -z "$REPO" || "$REPO" != */* ]]; then
  echo "Usage: $0 owner/repo [base-branch] [dir] [new-branch]" >&2
  exit 1
fi

DIR="${DIR#/}"; DIR="${DIR%/}"

# Resolve default branch if not provided
if [[ -z "$BASE_BRANCH" ]]; then
  BASE_BRANCH="$(gh api "repos/${REPO}" --jq .default_branch)"
fi

echo "Repo:      $REPO"
echo "Base:      $BASE_BRANCH"
echo "Dir:       $DIR/"
echo "New head:  $NEW_BRANCH"
echo

# Get base commit & tree
BASE_HEAD_SHA="$(gh api "repos/${REPO}/git/refs/heads/${BASE_BRANCH}" --jq .object.sha)"
BASE_TREE_SHA="$(gh api "repos/${REPO}/git/commits/${BASE_HEAD_SHA}" --jq .tree.sha)"

# List all files under DIR/
FILES_JSON="$(gh api "repos/${REPO}/git/trees/${BASE_TREE_SHA}?recursive=1")"
mapfile -t FILES < <(echo "$FILES_JSON" | jq -r --arg p "${DIR}/" '.tree[] | select(.type=="blob" and (.path | startswith($p))) | .path')

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "Nothing to delete: '${DIR}/' not found on ${BASE_BRANCH}."
  exit 0
fi

echo "Found ${#FILES[@]} file(s) to delete (showing first 20):"
printf '  - %s\n' "${FILES[@]:0:20}"
[[ ${#FILES[@]} -gt 20 ]] && echo "  ... and $(( ${#FILES[@]} - 20 )) more"
echo

# Create branch from base (fail if exists)
if gh api "repos/${REPO}/branches/${NEW_BRANCH}" >/dev/null 2>&1; then
  echo "ERROR: Branch '${NEW_BRANCH}' already exists. Pick another." >&2
  exit 1
fi
echo "Creating branch '${NEW_BRANCH}' from ${BASE_HEAD_SHA}..."
gh api "repos/${REPO}/git/refs" -X POST -f ref="refs/heads/${NEW_BRANCH}" -f sha="${BASE_HEAD_SHA}" >/dev/null

# GraphQL mutation
GQL='mutation(
  $repo:String!,
  $branch:String!,
  $expectedHeadOid:GitObjectID!,
  $message:String!,
  $deletions:[FileDeletion!]!
) {
  createCommitOnBranch(input:{
    branch:{ repositoryNameWithOwner:$repo, branchName:$branch },
    message:{ headline:$message },
    expectedHeadOid:$expectedHeadOid,
    fileChanges:{ deletions: $deletions }
  }) {
    commit { oid url }
  }
}'

# Batch to stay well under limits
BATCH_SIZE=900
CURRENT_HEAD="$BASE_HEAD_SHA"
COMMIT_URLS=()

commit_batch () {
  local from_idx="$1"
  local to_idx="$2"
  local -a BATCH=( "${FILES[@]:from_idx:to_idx-from_idx}" )

  # Build args array for gh with nested fields: deletions[][path]=<file>
  local -a ARGS
  ARGS=(-f query="$GQL" -F repo="$REPO" -F branch="$NEW_BRANCH" -F expectedHeadOid="$CURRENT_HEAD" -F message="$COMMIT_MSG")
  for p in "${BATCH[@]}"; do
    ARGS+=(-F "deletions[][path]=$p")
  done

  echo "Creating commit for files [$from_idx, $((to_idx-1))]..."
  local RESP
  RESP="$(gh api graphql "${ARGS[@]}")" || { echo "ERROR: commit failed"; exit 1; }

  local NEW_OID NEW_URL
  NEW_OID="$(echo "$RESP" | jq -r '.data.createCommitOnBranch.commit.oid')"
  NEW_URL="$(echo "$RESP" | jq -r '.data.createCommitOnBranch.commit.url')"

  if [[ -z "$NEW_OID" || "$NEW_OID" == "null" ]]; then
    echo "ERROR: Commit failed. Response:"
    echo "$RESP"
    exit 1
  fi

  COMMIT_URLS+=("$NEW_URL")
  CURRENT_HEAD="$NEW_OID"
}

TOTAL=${#FILES[@]}
START=0
while [[ $START -lt $TOTAL ]]; do
  END=$(( START + BATCH_SIZE ))
  (( END > TOTAL )) && END=$TOTAL
  commit_batch "$START" "$END"
  START="$END"
done

# Open PR
PR_BODY+="

Commits:
$(printf -- '- %s\n' "${COMMIT_URLS[@]}")"

echo "Opening Pull Request..."
PR_JSON="$(gh api "repos/${REPO}/pulls" -X POST \
  -f title="$PR_TITLE" \
  -f head="$NEW_BRANCH" \
  -f base="$BASE_BRANCH" \
  -f body="$PR_BODY")"

PR_URL="$(echo "$PR_JSON" | jq -r .html_url)"

echo
echo "Done!"
echo "Branch: ${NEW_BRANCH}"
echo "PR:     ${PR_URL}"